package com.sintao.judge.service.impl;

import cn.hutool.core.io.FileUtil;
import com.github.dockerjava.api.DockerClient;
import com.github.dockerjava.api.command.ExecCreateCmdResponse;
import com.github.dockerjava.api.command.StatsCmd;
import com.sintao.common.core.constants.Constants;
import com.sintao.common.core.enums.CodeRunStatus;
import com.sintao.judge.callback.DockerStartResultCallback;
import com.sintao.judge.callback.StatisticsCallback;
import com.sintao.judge.config.DockerSandBoxPool;
import com.sintao.judge.config.SandboxTimeoutProperties;
import com.sintao.judge.domain.CompileResult;
import com.sintao.judge.domain.JudgeLanguageDefinition;
import com.sintao.judge.domain.SandBoxExecuteResult;
import com.sintao.judge.service.ISandboxPoolService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

import java.io.File;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

@Service
@ConditionalOnProperty(name = "sandbox.execution.mode", havingValue = "pool", matchIfMissing = true)
@Slf4j
public class SandboxPoolServiceImpl implements ISandboxPoolService {

    @Autowired
    private DockerSandBoxPool sandBoxPool;

    @Autowired
    private DockerClient dockerClient;

    @Autowired
    private SandboxTimeoutProperties timeoutProperties;

    @Value("${sandbox.limit.time:5}")
    private Long timeLimit;

    @Override
    public SandBoxExecuteResult executeCode(Integer programType, Long userId, String userCode, List<String> inputList) {
        JudgeLanguageDefinition language = JudgeLanguageDefinition.fromProgramType(programType);
        long deadlineNanos = timeoutProperties.deadlineNanos();
        String containerId = sandBoxPool.getContainer();
        String codeDir = sandBoxPool.getCodeDir(containerId);
        boolean reusable = false;
        try {
            createUserCodeFile(codeDir, language.sourceFileName(), userCode);
            CompileResult compileResult = compileCodeByDocker(containerId, language.compileCommand(),
                    language.minimumCompileSeconds(), deadlineNanos);
            if (compileResult.isTimedOut()) {
                sandBoxPool.restartContainer(containerId);
                reusable = true;
                return SandBoxExecuteResult.fail(CodeRunStatus.OUT_OF_TIME, "编译超时");
            }
            if (!compileResult.isCompiled()) {
                reusable = true;
                return SandBoxExecuteResult.fail(CodeRunStatus.COMPILE_FAILED, compileResult.getExeMessage());
            }
            SandBoxExecuteResult result = executeCodeByDocker(
                    containerId, language.runCommand(), inputList, deadlineNanos);
            reusable = true;
            return result;
        } finally {
            boolean cleaned = false;
            try {
                FileUtil.clean(codeDir);
                cleaned = true;
            } finally {
                if (reusable && cleaned) {
                    sandBoxPool.returnContainer(containerId);
                } else {
                    sandBoxPool.replaceContainer(containerId);
                }
            }
        }
    }

    private void createUserCodeFile(String codeDir, String sourceFileName, String userCode) {
        String userCodeFileName = codeDir + File.separator + sourceFileName;
        if (FileUtil.exist(userCodeFileName)) {
            FileUtil.del(userCodeFileName);
        }
        FileUtil.writeString(userCode, userCodeFileName, Constants.UTF8);
    }

    private CompileResult compileCodeByDocker(String containerId, String[] compileCommand,
                                              long minimumCompileSeconds, long deadlineNanos) {
        String cmdId = createExecCmd(DockerExecInputSpec.forCompile(compileCommand), containerId);
        DockerStartResultCallback resultCallback = new DockerStartResultCallback();
        CompileResult compileResult = new CompileResult();
        try {
            long waitMillis = timeoutProperties.compileWaitMillis(deadlineNanos, minimumCompileSeconds);
            boolean completed = waitMillis > 0
                    && dockerClient.execStartCmd(cmdId).exec(resultCallback)
                    .awaitCompletion(waitMillis, TimeUnit.MILLISECONDS);
            if (!completed) {
                compileResult.setTimedOut(true);
                compileResult.setExeMessage("编译超时");
                return compileResult;
            }
            if (resultCallback.isOutputTruncated()) {
                compileResult.setCompiled(false);
                compileResult.setExeMessage("编译输出超出限制");
                return compileResult;
            }
            if (!execSucceeded(cmdId)) {
                compileResult.setCompiled(false);
                compileResult.setExeMessage(execMessage(resultCallback));
            } else {
                compileResult.setCompiled(true);
            }
            return compileResult;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new RuntimeException("Interrupted while compiling code in sandbox", e);
        }
    }

    private SandBoxExecuteResult executeCodeByDocker(String containerId,
                                                     String[] runCommand,
                                                     List<String> inputList,
                                                     long deadlineNanos) {
        List<String> outList = new ArrayList<>();
        long maxMemory = 0L;
        long maxUseTime = 0L;
        for (String inputArgs : inputList) {
            DockerExecInputSpec execInputSpec = DockerExecInputSpec.forRun(runCommand, inputArgs);
            String cmdId = createExecCmd(execInputSpec, containerId);
            StatsCmd statsCmd = dockerClient.statsCmd(containerId);
            StatisticsCallback statisticsCallback = statsCmd.exec(new StatisticsCallback());
            long startNanos = System.nanoTime();
            DockerStartResultCallback resultCallback = new DockerStartResultCallback();
            try {
                long waitMillis = timeoutProperties.executionWaitMillis(deadlineNanos, timeLimit);
                boolean completed = waitMillis > 0 && execStart(cmdId, execInputSpec.stdin(), resultCallback)
                        .awaitCompletion(waitMillis, TimeUnit.MILLISECONDS);
                if (!completed) {
                    sandBoxPool.restartContainer(containerId);
                    long reportedTime = waitMillis > 0 ? waitMillis : timeLimit * 1000L;
                    return SandBoxExecuteResult.fail(CodeRunStatus.OUT_OF_TIME, outList, maxMemory, reportedTime);
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new RuntimeException("Interrupted while executing code in sandbox", e);
            } finally {
                statsCmd.close();
            }
            if (resultCallback.isOutputTruncated()) {
                return SandBoxExecuteResult.fail(CodeRunStatus.FAILED, "程序输出超出限制");
            }
            if (!execSucceeded(cmdId)) {
                return SandBoxExecuteResult.fail(CodeRunStatus.FAILED, execMessage(resultCallback));
            }
            long userTime = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - startNanos);
            maxUseTime = Math.max(userTime, maxUseTime);
            Long memory = statisticsCallback.getMaxMemory();
            if (memory != null) {
                maxMemory = Math.max(maxMemory, memory);
            }
            String message = resultCallback.getMessage();
            outList.add(message != null ? message.trim() : "");
        }
        return getSanBoxResult(inputList, outList, maxMemory, maxUseTime);
    }

    private String createExecCmd(DockerExecInputSpec execInputSpec, String containerId) {
        ExecCreateCmdResponse cmdResponse = dockerClient.execCreateCmd(containerId)
                .withCmd(execInputSpec.command())
                .withAttachStderr(true)
                .withAttachStdin(true)
                .withAttachStdout(true)
                .exec();
        return cmdResponse.getId();
    }

    private boolean execSucceeded(String cmdId) {
        Long exitCode = dockerClient.inspectExecCmd(cmdId).exec().getExitCodeLong();
        if (exitCode == null) {
            throw new IllegalStateException("Sandbox exec has no exit code: " + cmdId);
        }
        return exitCode == 0;
    }

    private String execMessage(DockerStartResultCallback callback) {
        String stderr = callback.getErrorMessage();
        if (stderr != null && !stderr.isBlank()) {
            return stderr;
        }
        String stdout = callback.getMessage();
        return stdout != null && !stdout.isBlank() ? stdout : CodeRunStatus.FAILED.getMsg();
    }

    private DockerStartResultCallback execStart(String cmdId, InputStream stdin, DockerStartResultCallback resultCallback) {
        if (stdin != null) {
            return dockerClient.execStartCmd(cmdId)
                    .withStdIn(stdin)
                    .exec(resultCallback);
        }
        return dockerClient.execStartCmd(cmdId).exec(resultCallback);
    }

    private SandBoxExecuteResult getSanBoxResult(List<String> inputList, List<String> outList,
                                                 long maxMemory, long maxUseTime) {
        if (inputList.size() != outList.size()) {
            return SandBoxExecuteResult.fail(CodeRunStatus.NOT_ALL_PASSED, outList, maxMemory, maxUseTime);
        }
        return SandBoxExecuteResult.success(CodeRunStatus.SUCCEED, outList, maxMemory, maxUseTime);
    }

}
