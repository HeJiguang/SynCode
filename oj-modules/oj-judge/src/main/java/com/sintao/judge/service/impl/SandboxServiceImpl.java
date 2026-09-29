package com.sintao.judge.service.impl;

import cn.hutool.core.date.LocalDateTimeUtil;
import cn.hutool.core.io.FileUtil;
import com.github.dockerjava.api.DockerClient;
import com.github.dockerjava.api.command.CreateContainerCmd;
import com.github.dockerjava.api.command.CreateContainerResponse;
import com.github.dockerjava.api.command.ExecCreateCmdResponse;
import com.github.dockerjava.api.command.ListImagesCmd;
import com.github.dockerjava.api.command.PullImageCmd;
import com.github.dockerjava.api.command.PullImageResultCallback;
import com.github.dockerjava.api.command.StatsCmd;
import com.github.dockerjava.api.model.Bind;
import com.github.dockerjava.api.model.HostConfig;
import com.github.dockerjava.api.model.Image;
import com.github.dockerjava.api.model.Volume;
import com.github.dockerjava.core.DefaultDockerClientConfig;
import com.github.dockerjava.core.DockerClientBuilder;
import com.github.dockerjava.netty.NettyDockerCmdExecFactory;
import com.sintao.common.core.constants.Constants;
import com.sintao.common.core.constants.JudgeConstants;
import com.sintao.common.core.enums.CodeRunStatus;
import com.sintao.judge.callback.DockerStartResultCallback;
import com.sintao.judge.callback.StatisticsCallback;
import com.sintao.judge.config.SandboxTimeoutProperties;
import com.sintao.judge.domain.CompileResult;
import com.sintao.judge.domain.JudgeLanguageDefinition;
import com.sintao.judge.domain.SandBoxExecuteResult;
import com.sintao.judge.service.ISandboxService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.io.File;
import java.io.InputStream;
import java.io.IOException;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

@Service
@Slf4j
public class SandboxServiceImpl implements ISandboxService {

    private static final String[] KEEPALIVE_CMD = {"sh", "-c", "while true; do sleep 3600; done"};

    @Value("${sandbox.docker.host:tcp://localhost:2375}")
    private String dockerHost;

    @Value("${sandbox.docker.image:syncode/oj-sandbox-multilang:1.0.0}")
    private String sandboxImage;

    @Value("${sandbox.limit.memory:268435456}")
    private Long memoryLimit;

    @Value("${sandbox.limit.memory-swap:268435456}")
    private Long memorySwapLimit;

    @Value("${sandbox.limit.cpu:1}")
    private Long cpuLimit;

    @Value("${sandbox.limit.time:5}")
    private Long timeLimit;

    @Value("${sandbox.limit.pids:64}")
    private Long pidsLimit;

    @Autowired
    private SandboxTimeoutProperties timeoutProperties;

    @Override
    public SandBoxExecuteResult executeCode(Integer programType, Long userId, String userCode, List<String> inputList) {
        JudgeLanguageDefinition language = JudgeLanguageDefinition.fromProgramType(programType);
        long deadlineNanos = timeoutProperties.deadlineNanos();
        String userCodeDir = createUserCodeFile(userId, language.sourceFileName(), userCode);
        SandboxContext context = null;
        try {
            context = initDockerSandbox(userCodeDir);
            CompileResult compileResult = compileCodeByDocker(context, language.compileCommand(),
                    language.minimumCompileSeconds(), deadlineNanos);
            if (compileResult.isTimedOut()) {
                return SandBoxExecuteResult.fail(CodeRunStatus.OUT_OF_TIME, "编译超时");
            }
            if (!compileResult.isCompiled()) {
                return SandBoxExecuteResult.fail(CodeRunStatus.COMPILE_FAILED, compileResult.getExeMessage());
            }
            return executeCodeByDocker(context, language.runCommand(), inputList, deadlineNanos);
        } finally {
            deleteContainer(context);
            FileUtil.del(userCodeDir);
        }
    }

    private String createUserCodeFile(Long userId, String sourceFileName, String userCode) {
        String examCodeDir = System.getProperty("user.dir") + File.separator + JudgeConstants.EXAM_CODE_DIR;
        if (!FileUtil.exist(examCodeDir)) {
            FileUtil.mkdir(examCodeDir);
        }
        String time = LocalDateTimeUtil.format(LocalDateTime.now(), DateTimeFormatter.ofPattern("yyyyMMddHHmmssSSS"));
        String userCodeDir = examCodeDir + File.separator + userId + Constants.UNDERLINE_SEPARATOR
                + time + Constants.UNDERLINE_SEPARATOR + UUID.randomUUID();
        if (!FileUtil.exist(userCodeDir)) {
            FileUtil.mkdir(userCodeDir);
        }
        String userCodeFileName = userCodeDir + File.separator + sourceFileName;
        FileUtil.writeString(userCode, userCodeFileName, Constants.UTF8);
        return userCodeDir;
    }

    private SandboxContext initDockerSandbox(String userCodeDir) {
        DefaultDockerClientConfig clientConfig = DefaultDockerClientConfig.createDefaultConfigBuilder()
                .withDockerHost(dockerHost)
                .build();
        DockerClient dockerClient = DockerClientBuilder
                .getInstance(clientConfig)
                .withDockerCmdExecFactory(new NettyDockerCmdExecFactory())
                .build();
        pullSandboxImage(dockerClient);
        HostConfig hostConfig = getHostConfig(userCodeDir);
        CreateContainerCmd containerCmd = dockerClient
                .createContainerCmd(sandboxImage)
                .withName("oj-sandbox-" + UUID.randomUUID());
        CreateContainerResponse response = containerCmd
                .withHostConfig(hostConfig)
                .withAttachStderr(true)
                .withAttachStdout(true)
                .withTty(true)
                .withCmd(KEEPALIVE_CMD)
                .exec();
        String containerId = response.getId();
        dockerClient.startContainerCmd(containerId).exec();
        return new SandboxContext(dockerClient, containerId);
    }

    private void pullSandboxImage(DockerClient dockerClient) {
        ListImagesCmd listImagesCmd = dockerClient.listImagesCmd();
        List<Image> imageList = listImagesCmd.exec();
        for (Image image : imageList) {
            String[] repoTags = image.getRepoTags();
            if (repoTags != null && repoTags.length > 0 && sandboxImage.equals(repoTags[0])) {
                return;
            }
        }
        PullImageCmd pullImageCmd = dockerClient.pullImageCmd(sandboxImage);
        try {
            pullImageCmd.exec(new PullImageResultCallback()).awaitCompletion();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new RuntimeException("Interrupted while pulling sandbox image " + sandboxImage, e);
        }
    }

    private HostConfig getHostConfig(String userCodeDir) {
        HostConfig hostConfig = new HostConfig();
        hostConfig.setBinds(new Bind(userCodeDir, new Volume(JudgeConstants.DOCKER_USER_CODE_DIR)));
        hostConfig.withMemory(memoryLimit);
        hostConfig.withMemorySwap(memorySwapLimit);
        hostConfig.withNanoCPUs(cpuLimit * 1_000_000_000L);
        hostConfig.withPidsLimit(pidsLimit);
        hostConfig.withNetworkMode("none");
        hostConfig.withReadonlyRootfs(true);
        hostConfig.withTmpFs(Map.of("/tmp", "rw,noexec,nosuid,size=64m"));
        return hostConfig;
    }

    private CompileResult compileCodeByDocker(SandboxContext context, String[] compileCommand,
                                              long minimumCompileSeconds,
                                              long deadlineNanos) {
        String cmdId = createExecCmd(context, DockerExecInputSpec.forCompile(compileCommand));
        DockerStartResultCallback resultCallback = new DockerStartResultCallback();
        CompileResult compileResult = new CompileResult();
        try {
            long waitMillis = timeoutProperties.compileWaitMillis(deadlineNanos, minimumCompileSeconds);
            boolean completed = waitMillis > 0
                    && context.dockerClient().execStartCmd(cmdId).exec(resultCallback)
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
            if (!execSucceeded(context.dockerClient(), cmdId)) {
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

    private SandBoxExecuteResult executeCodeByDocker(SandboxContext context,
                                                     String[] runCommand,
                                                     List<String> inputList,
                                                     long deadlineNanos) {
        List<String> outList = new ArrayList<>();
        long maxMemory = 0L;
        long maxUseTime = 0L;
        for (String inputArgs : inputList) {
            DockerExecInputSpec execInputSpec = DockerExecInputSpec.forRun(runCommand, inputArgs);
            String cmdId = createExecCmd(context, execInputSpec);
            StatsCmd statsCmd = context.dockerClient().statsCmd(context.containerId());
            StatisticsCallback statisticsCallback = statsCmd.exec(new StatisticsCallback());
            long startNanos = System.nanoTime();
            DockerStartResultCallback resultCallback = new DockerStartResultCallback();
            try {
                long waitMillis = timeoutProperties.executionWaitMillis(deadlineNanos, timeLimit);
                boolean completed = waitMillis > 0
                        && execStart(context.dockerClient(), cmdId, execInputSpec.stdin(), resultCallback)
                        .awaitCompletion(waitMillis, TimeUnit.MILLISECONDS);
                if (!completed) {
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
            if (!execSucceeded(context.dockerClient(), cmdId)) {
                return SandBoxExecuteResult.fail(CodeRunStatus.FAILED, execMessage(resultCallback));
            }
            long userTime = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - startNanos);
            maxUseTime = Math.max(maxUseTime, userTime);
            Long memory = statisticsCallback.getMaxMemory();
            if (memory != null) {
                maxMemory = Math.max(maxMemory, memory);
            }
            String message = resultCallback.getMessage();
            outList.add(message != null ? message.trim() : "");
        }
        return getSanBoxResult(inputList, outList, maxMemory, maxUseTime);
    }

    private String createExecCmd(SandboxContext context, DockerExecInputSpec execInputSpec) {
        ExecCreateCmdResponse cmdResponse = context.dockerClient().execCreateCmd(context.containerId())
                .withCmd(execInputSpec.command())
                .withAttachStderr(true)
                .withAttachStdin(true)
                .withAttachStdout(true)
                .exec();
        return cmdResponse.getId();
    }

    private boolean execSucceeded(DockerClient dockerClient, String cmdId) {
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

    private DockerStartResultCallback execStart(DockerClient dockerClient, String cmdId, InputStream stdin,
                                                DockerStartResultCallback resultCallback) {
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

    private void deleteContainer(SandboxContext context) {
        if (context == null) {
            return;
        }
        DockerClient dockerClient = context.dockerClient();
        String containerId = context.containerId();
        try {
            dockerClient.stopContainerCmd(containerId).withTimeout(0).exec();
        } catch (Exception e) {
            log.warn("Failed to stop sandbox container {}", containerId, e);
        }
        try {
            dockerClient.removeContainerCmd(containerId).exec();
        } catch (Exception e) {
            log.warn("Failed to remove sandbox container {}", containerId, e);
        }
        try {
            dockerClient.close();
        } catch (IOException e) {
            log.warn("Failed to close Docker client for sandbox container {}", containerId, e);
        }
    }

    private record SandboxContext(DockerClient dockerClient, String containerId) {
    }
}
