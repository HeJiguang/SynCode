package com.sintao.judge.service.impl;

import com.github.dockerjava.api.DockerClient;
import com.github.dockerjava.api.model.Frame;
import com.github.dockerjava.api.model.StreamType;
import com.sintao.judge.callback.DockerStartResultCallback;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.Mockito.RETURNS_DEEP_STUBS;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class SandboxProcessExitTest {

    @Test
    void processExitCodeControlsSuccessEvenWhenStderrIsPresent() {
        DockerClient dockerClient = mock(DockerClient.class, RETURNS_DEEP_STUBS);
        SandboxPoolServiceImpl service = new SandboxPoolServiceImpl();
        ReflectionTestUtils.setField(service, "dockerClient", dockerClient);
        DockerStartResultCallback callback = new DockerStartResultCallback();
        callback.onNext(new Frame(StreamType.STDERR, "warning".getBytes(StandardCharsets.UTF_8)));

        when(dockerClient.inspectExecCmd("ok").exec().getExitCodeLong()).thenReturn(0L);
        when(dockerClient.inspectExecCmd("failed").exec().getExitCodeLong()).thenReturn(1L);

        assertTrue(ReflectionTestUtils.<Boolean>invokeMethod(service, "execSucceeded", "ok"));
        assertFalse(ReflectionTestUtils.<Boolean>invokeMethod(service, "execSucceeded", "failed"));
    }
}
