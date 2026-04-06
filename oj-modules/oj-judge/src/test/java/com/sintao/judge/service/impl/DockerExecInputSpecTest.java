package com.sintao.judge.service.impl;

import com.sintao.common.core.constants.JudgeConstants;
import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

class DockerExecInputSpecTest {

    @Test
    void runSpecFeedsSampleInputThroughStdinInsteadOfCommandArguments() throws IOException {
        DockerExecInputSpec spec = DockerExecInputSpec.forRun(JudgeConstants.DOCKER_JAVA_EXEC_CMD, "1 2");

        assertArrayEquals(JudgeConstants.DOCKER_JAVA_EXEC_CMD, spec.command());
        assertEquals("1 2" + System.lineSeparator(), new String(spec.stdin().readAllBytes(), StandardCharsets.UTF_8));
    }

    @Test
    void blankInputKeepsStdinEmpty() {
        DockerExecInputSpec spec = DockerExecInputSpec.forRun(JudgeConstants.DOCKER_JAVA_EXEC_CMD, "   ");

        assertArrayEquals(JudgeConstants.DOCKER_JAVA_EXEC_CMD, spec.command());
        assertNull(spec.stdin());
    }
}
