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
import com.sintao.judge.domain.CompileResult;
import com.sintao.judge.domain.SandBoxExecuteResult;
import com.sintao.judge.service.ISandboxService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.io.File;
import java.io.InputStream;
import java.io.IOException;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

@Service
@Slf4j
public class SandboxServiceImpl implements ISandboxService {

    @Value("${sandbox.docker.host:tcp://localhost:2375}")
    private String dockerHost;

    @Value("${sandbox.docker.image:eclipse-temurin:8-jdk-alpine}")
    private String sandboxImage;

    @Value("${sandbox.limit.memory:100000000}")
    private Long memoryLimit;

    @Value("${sandbox.limit.memory-swap:100000000}")
    private Long memorySwapLimit;

    @Value("${sandbox.limit.cpu:1}")
    private Long cpuLimit;

    @Value("${sandbox.limit.time:5}")
    private Long timeLimit;

    @Value("${sandbox.limit.pids:64}")
    private Long pidsLimit;

    @Override
    public SandBoxExecuteResult exeJavaCode(Long userId, String userCode, List<String> inputList) {
        String userCodeDir = createUserCodeFile(userId, userCode);
        SandboxContext context = null;
        try {
            context = initDockerSandbox(userCodeDir);
            CompileResult compileResult = compileCodeByDocker(context);
            if (!compileResult.isCompiled()) {
                return SandBoxExecuteResult.fail(CodeRunStatus.COMPILE_FAILED, compileResult.getExeMessage());
            }
            return executeJavaCodeByDocker(context, inputList);
        } finally {
            deleteContainer(context);
            FileUtil.del(userCodeDir);
        }
    }

    private String createUserCodeFile(Long userId, String userCode) {
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
        String userCodeFileName = userCodeDir + File.separator + JudgeConstants.USER_CODE_JAVA_CLASS_NAME;
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
        pullJavaEnvImage(dockerClient);
        HostConfig hostConfig = getHostConfig(userCodeDir);
        CreateContainerCmd containerCmd = dockerClient
                .createContainerCmd(sandboxImage)
                .withName(JudgeConstants.JAVA_CONTAINER_NAME + "-" + UUID.randomUUID());
        CreateContainerResponse response = containerCmd
                .withHostConfig(hostConfig)
                .withAttachStderr(true)
                .withAttachStdout(true)
                .withTty(true)
                .exec();
        String containerId = response.getId();
        dockerClient.startContainerCmd(containerId).exec();
        return new SandboxContext(dockerClient, containerId);
    }

    private void pullJavaEnvImage(DockerClient dockerClient) {
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
        return hostConfig;
    }

    private CompileResult compileCodeByDocker(SandboxContext context) {
        String cmdId = createExecCmd(context, DockerExecInputSpec.forCompile(JudgeConstants.DOCKER_JAVAC_CMD));
        DockerStartResultCallback resultCallback = new DockerStartResultCallback();
        CompileResult compileResult = new CompileResult();
        try {
            context.dockerClient().execStartCmd(cmdId).exec(resultCallback).awaitCompletion();
            if (CodeRunStatus.FAILED.equals(resultCallback.getCodeRunStatus())) {
                compileResult.setCompiled(false);
                compileResult.setExeMessage(resultCallback.getErrorMessage());
            } else {
                compileResult.setCompiled(true);
            }
            return compileResult;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new RuntimeException("Interrupted while compiling code in sandbox", e);
        }
    }

    private SandBoxExecuteResult executeJavaCodeByDocker(SandboxContext context, List<String> inputList) {
        List<String> outList = new ArrayList<>();
        long maxMemory = 0L;
        long maxUseTime = 0L;
        for (String inputArgs : inputList) {
            DockerExecInputSpec execInputSpec = DockerExecInputSpec.forRun(JudgeConstants.DOCKER_JAVA_EXEC_CMD, inputArgs);
            String cmdId = createExecCmd(context, execInputSpec);
            StatsCmd statsCmd = context.dockerClient().statsCmd(context.containerId());
            StatisticsCallback statisticsCallback = statsCmd.exec(new StatisticsCallback());
            long startNanos = System.nanoTime();
            DockerStartResultCallback resultCallback = new DockerStartResultCallback();
            try {
                boolean completed = execStart(context.dockerClient(), cmdId, execInputSpec.stdin(), resultCallback)
                        .awaitCompletion(timeLimit, TimeUnit.SECONDS);
                if (!completed) {
                    return SandBoxExecuteResult.fail(CodeRunStatus.OUT_OF_TIME, outList, maxMemory, timeLimit * 1000L);
                }
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new RuntimeException("Interrupted while executing code in sandbox", e);
            } finally {
                statsCmd.close();
            }
            if (CodeRunStatus.FAILED.equals(resultCallback.getCodeRunStatus())) {
                return SandBoxExecuteResult.fail(CodeRunStatus.NOT_ALL_PASSED);
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
            dockerClient.stopContainerCmd(containerId).exec();
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
