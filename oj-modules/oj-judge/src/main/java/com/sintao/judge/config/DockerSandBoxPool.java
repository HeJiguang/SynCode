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
import java.util.HashSet;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.BlockingQueue;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.TimeUnit;

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
    private final Set<String> missingContainerNames = new HashSet<>();

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
        this.containerNameMap = new ConcurrentHashMap<>();
    }

    public void initDockerPool() {
        log.info("------ Creating sandbox pool ------");
        for (int i = 0; i < poolSize; i++) {
            createContainer(containerNamePrefix + "-" + i, true);
        }
        log.info("------ Sandbox pool ready ------");
    }

    public String getContainer() {
        try {
            while (true) {
                repairMissingContainers();
                String containerId = containerQueue.poll(5, TimeUnit.SECONDS);
                if (containerId == null) {
                    if (containerNameMap.isEmpty()) {
                        throw new IllegalStateException("No healthy sandbox containers are available");
                    }
                    continue;
                }
                try {
                    ensureContainerRunning(containerId);
                    return containerId;
                } catch (RuntimeException e) {
                    try {
                        replaceContainer(containerId);
                    } catch (RuntimeException replacementError) {
                        e.addSuppressed(replacementError);
                    }
                    throw e;
                }
            }
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

    public synchronized void replaceContainer(String containerId) {
        String containerName = containerNameMap.remove(containerId);
        if (containerName == null) {
            throw new IllegalStateException("Unknown sandbox container: " + containerId);
        }
        missingContainerNames.add(containerName);
        try {
            dockerClient.removeContainerCmd(containerId).withForce(true).exec();
            FileUtil.clean(baseCodeDir() + File.separator + containerName);
            createContainer(containerName, false);
            missingContainerNames.remove(containerName);
        } catch (RuntimeException e) {
            log.error("Could not replace sandbox container {}", containerName, e);
            throw e;
        }
    }

    private synchronized void repairMissingContainers() {
        for (String containerName : List.copyOf(missingContainerNames)) {
            try {
                createContainer(containerName, false);
                missingContainerNames.remove(containerName);
            } catch (RuntimeException e) {
                log.warn("Sandbox container {} remains unavailable", containerName, e);
            }
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

    private void createContainer(String containerName, boolean reuseExisting) {
        pullSandboxImage();
        List<Container> containerList = dockerClient.listContainersCmd().withShowAll(true).exec();
        if (!CollectionUtil.isEmpty(containerList)) {
            String dockerContainerName = JudgeConstants.JAVA_CONTAINER_PREFIX + containerName;
            for (Container container : containerList) {
                String[] containerNames = container.getNames();
                if (containerNames != null && containerNames.length > 0 && dockerContainerName.equals(containerNames[0])) {
                    if (reuseExisting && "running".equals(container.getState()) && hasExpectedIsolation(container.getId())) {
                        containerNameMap.put(container.getId(), containerName);
                        if (!containerQueue.offer(container.getId())) {
                            containerNameMap.remove(container.getId());
                            throw new IllegalStateException("Sandbox pool is full while adopting " + containerName);
                        }
                        return;
                    }
                    dockerClient.removeContainerCmd(container.getId()).withForce(true).exec();
                    break;
                }
            }
        }

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
        containerNameMap.put(containerId, containerName);
        if (!containerQueue.offer(containerId)) {
            containerNameMap.remove(containerId);
            dockerClient.removeContainerCmd(containerId).withForce(true).exec();
            throw new IllegalStateException("Sandbox pool is full while creating " + containerName);
        }
    }

    private boolean hasExpectedIsolation(String containerId) {
        var container = dockerClient.inspectContainerCmd(containerId).exec();
        HostConfig hostConfig = container.getHostConfig();
        return hostConfig != null
                && container.getConfig() != null
                && Objects.equals(sandboxImage, container.getConfig().getImage())
                && Objects.equals(dockerClient.inspectImageCmd(sandboxImage).exec().getId(), container.getImageId())
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

    private void pullSandboxImage() {
        ListImagesCmd listImagesCmd = dockerClient.listImagesCmd();
        List<Image> imageList = listImagesCmd.exec();
        for (Image image : imageList) {
            String[] repoTags = image.getRepoTags();
            if (repoTags != null && Arrays.asList(repoTags).contains(sandboxImage)) {
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
        hostConfig.withTmpFs(Map.of("/tmp", "rw,noexec,nosuid,size=64m"));
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
