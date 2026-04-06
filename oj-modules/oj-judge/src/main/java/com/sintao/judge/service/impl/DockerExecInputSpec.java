package com.sintao.judge.service.impl;

import java.io.ByteArrayInputStream;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

/**
 * Build docker exec inputs in the same format as the generated question main method:
 * keep the java command stable and feed sample data through stdin.
 */
record DockerExecInputSpec(String[] command, InputStream stdin) {

    static DockerExecInputSpec forCompile(String[] baseCommand) {
        return new DockerExecInputSpec(Arrays.copyOf(baseCommand, baseCommand.length), null);
    }

    static DockerExecInputSpec forRun(String[] baseCommand, String inputArgs) {
        InputStream stdin = null;
        if (inputArgs != null && !inputArgs.isBlank()) {
            stdin = new ByteArrayInputStream((inputArgs.strip() + System.lineSeparator())
                    .getBytes(StandardCharsets.UTF_8));
        }
        return new DockerExecInputSpec(Arrays.copyOf(baseCommand, baseCommand.length), stdin);
    }
}
