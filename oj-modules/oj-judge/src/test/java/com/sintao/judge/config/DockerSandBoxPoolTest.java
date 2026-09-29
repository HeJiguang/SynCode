package com.sintao.judge.config;

import com.github.dockerjava.api.DockerClient;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.concurrent.BlockingQueue;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.RETURNS_DEEP_STUBS;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class DockerSandBoxPoolTest {

    @Test
    @SuppressWarnings("unchecked")
    void noMoreThanPoolSizeTasksCanBorrowContainersAtOnce() throws Exception {
        DockerClient dockerClient = mock(DockerClient.class, RETURNS_DEEP_STUBS);
        when(dockerClient.inspectContainerCmd(anyString()).exec().getState().getRunning()).thenReturn(true);
        DockerSandBoxPool pool = new DockerSandBoxPool(
                dockerClient, "java-image", "/code", 100L, 100L, 1L, 64L, 2, "judge-test");
        BlockingQueue<String> available = (BlockingQueue<String>) ReflectionTestUtils.getField(pool, "containerQueue");
        available.add("container-a");
        available.add("container-b");

        String first = pool.getContainer();
        String second = pool.getContainer();
        ExecutorService executor = Executors.newSingleThreadExecutor();
        try {
            var waiting = executor.submit(pool::getContainer);
            assertThrows(TimeoutException.class, () -> waiting.get(150, TimeUnit.MILLISECONDS));
            pool.returnContainer(first);
            assertEquals(first, waiting.get(2, TimeUnit.SECONDS));
            pool.returnContainer(second);
        } finally {
            executor.shutdownNow();
        }
    }
}
