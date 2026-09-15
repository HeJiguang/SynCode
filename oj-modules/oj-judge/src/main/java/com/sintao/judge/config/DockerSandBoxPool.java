package com.sintao.judge.config;

import cn.hutool.core.collection.CollectionUtil;
import cn.hutool.core.io.FileUtil;
import com.github.dockerjava.api.DockerClient;
import com.github.dockerjava.api.command.CreateContainerCmd;
import com.github.dockerjava.api.command.CreateContainerResponse;
import com.github.dockerjava.api.command.ListImagesCmd;
import com.github.dockerjava.api.command.PullImageCmd;
import com.github.dockerjava.api.command.PullImageResultCallback;
import com.github.dockerjava.api.model.Bind;
import com.github.dockerjava.api.model.Container;
import com.github.dockerjava.api.model.HostConfig;
import com.github.dockerjava.api.model.Image;
import com.github.dockerjava.api.model.Volume;
import com.sintao.common.core.constants.JudgeConstants;
import lombok.extern.slf4j.Slf4j;

import java.io.File;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;

@Slf4j
public class DockerSandBoxPool {

    private static final String[] KEEPALIVE_CMD = {"sh", "-c", "while true; do sleep 3600; done"};

    private final DockerClient dockerClient;
    private final String sandboxImage;
    private final String volumeDir;
    private final Long memoryLimit;
    private final Long memorySwapLimit;
    private final Long cpuLimit;
    private final Long pidsLimit;
    private final int poolSize;
    private final String containerNamePrefix;
    private final BlockingQueue<String> containerQueue;
    private final Map<String, String> containerNameMap;

    public DockerSandBoxPool(DockerClient dockerClient,
                             String sandboxImage,
                             String volumeDir,
                             Long memoryLimit,
                             Long memorySwapLimit,
                             Long cpuLimit,
                             Long pidsLimit,
                             int poolSize,
                             String containerNamePrefix) {
        this.dockerClient = dockerClient;
        this.sandboxImage = sandboxImage;
        this.volumeDir = volumeDir;
        this.memoryLimit = memoryLimit;
        this.memorySwapLimit = memorySwapLimit;
        this.cpuLimit = cpuLimit;
        this.pidsLimit = pidsLimit;
        this.poolSize = poolSize;
        this.containerNamePrefix = containerNamePrefix;
        this.containerQueue = new ArrayBlockingQueue<>(poolSize);
        this.containerNameMap = new HashMap<>();
    }

    public void initDockerPool() {
        log.info("------ Creating sandbox pool ------");
        for (int i = 0; i < poolSize; i++) {
            createContainer(containerNamePrefix + "-" + i);
        }
        log.info("------ Sandbox pool ready ------");
    }

    public String getContainer() {
        try {
            String containerId = containerQueue.take();
            ensureContainerRunning(containerId);
            return containerId;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new RuntimeException("Interrupted while waiting for a sandbox container", e);
        }
    }

    public void returnContainer(String containerId) {
        if (containerId == null) {
            return;
        }
        if (!containerQueue.offer(containerId)) {
            throw new IllegalStateException("Sandbox pool is full, cannot return container " + containerId);
        }
    }

    public String getCodeDir(String containerId) {
        String containerName = containerNameMap.get(containerId);
        if (containerName == null) {
            throw new IllegalStateException("Unknown sandbox container: " + containerId);
        }
        return baseCodeDir() + File.separator + containerName;
    }

    public void restartContainer(String containerId) {
        dockerClient.restartContainerCmd(containerId).withTimeout(1).exec();
    }

    private void createContainer(String containerName) {
        List<Container> containerList = dockerClient.listContainersCmd().withShowAll(true).exec();
        if (!CollectionUtil.isEmpty(containerList)) {
            String dockerContainerName = JudgeConstants.JAVA_CONTAINER_PREFIX + containerName;
            for (Container container : containerList) {
                String[] containerNames = container.getNames();
                if (containerNames != null && containerNames.length > 0 && dockerContainerName.equals(containerNames[0])) {
                    if ("running".equals(container.getState()) && hasExpectedIsolation(container.getId())) {
                        containerQueue.offer(container.getId());
                        containerNameMap.put(container.getId(), containerName);
                        return;
                    }
                    dockerClient.removeContainerCmd(container.getId()).withForce(true).exec();
                    break;
                }
            }
        }

        pullJavaEnvImage();
        HostConfig hostConfig = getHostConfig(containerName);
        CreateContainerCmd containerCmd = dockerClient.createContainerCmd(sandboxImage).withName(containerName);
        CreateContainerResponse response = containerCmd
                .withHostConfig(hostConfig)
                .withAttachStderr(true)
                .withAttachStdout(true)
                .withTty(true)
                .withCmd(KEEPALIVE_CMD)
                .exec();
        String containerId = response.getId();
        dockerClient.startContainerCmd(containerId).exec();
        containerQueue.offer(containerId);
        containerNameMap.put(containerId, containerName);
    }

    private boolean hasExpectedIsolation(String containerId) {
        HostConfig hostConfig = dockerClient.inspectContainerCmd(containerId).exec().getHostConfig();
        return hostConfig != null
                && Objects.equals(memoryLimit, hostConfig.getMemory())
                && Objects.equals(memorySwapLimit, hostConfig.getMemorySwap())
                && Objects.equals(cpuLimit * 1_000_000_000L, hostConfig.getNanoCPUs())
                && Objects.equals(pidsLimit, hostConfig.getPidsLimit())
                && Objects.equals("none", hostConfig.getNetworkMode())
                && Boolean.TRUE.equals(hostConfig.getReadonlyRootfs());
    }

    private void ensureContainerRunning(String containerId) {
        Boolean running = dockerClient.inspectContainerCmd(containerId).exec().getState().getRunning();
        if (!Boolean.TRUE.equals(running)) {
            dockerClient.startContainerCmd(containerId).exec();
        }
    }

    private void pullJavaEnvImage() {
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

    private HostConfig getHostConfig(String containerName) {
        String userCodeDir = createContainerDir(containerName);
        HostConfig hostConfig = new HostConfig();
        hostConfig.setBinds(new Bind(userCodeDir, new Volume(volumeDir)));
        hostConfig.withMemory(memoryLimit);
        hostConfig.withMemorySwap(memorySwapLimit);
        hostConfig.withNanoCPUs(cpuLimit * 1_000_000_000L);
        hostConfig.withPidsLimit(pidsLimit);
        hostConfig.withNetworkMode("none");
        hostConfig.withReadonlyRootfs(true);
        return hostConfig;
    }

    private String createContainerDir(String containerName) {
        String codeDir = baseCodeDir();
        if (!FileUtil.exist(codeDir)) {
            FileUtil.mkdir(codeDir);
        }
        String containerDir = codeDir + File.separator + containerName;
        if (!FileUtil.exist(containerDir)) {
            FileUtil.mkdir(containerDir);
        }
        return containerDir;
    }

    private String baseCodeDir() {
        return System.getProperty("user.dir") + File.separator + JudgeConstants.CODE_DIR_POOL;
    }
}
