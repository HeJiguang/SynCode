package com.sintao.judge.config;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SandboxTimeoutPropertiesTest {

    @Test
    void phaseTimeoutIsBoundedByOverallDeadline() {
        SandboxTimeoutProperties properties = new SandboxTimeoutProperties(10, 60);
        long deadline = System.nanoTime() + 50_000_000L;

        long waitMillis = properties.compileWaitMillis(deadline);

        assertTrue(waitMillis > 0 && waitMillis <= 50);
    }

    @Test
    void rejectsInvalidTimeoutConfiguration() {
        assertThrows(IllegalArgumentException.class, () -> new SandboxTimeoutProperties(0, 60));
        assertThrows(IllegalArgumentException.class, () -> new SandboxTimeoutProperties(10, 9));
    }

    @Test
    void goCompileCanUseLongerTimeoutWithinOverallDeadline() {
        SandboxTimeoutProperties properties = new SandboxTimeoutProperties(10, 60);
        long deadline = properties.deadlineNanos();

        long waitMillis = properties.compileWaitMillis(deadline, 30);

        assertTrue(waitMillis >= 29_000 && waitMillis <= 30_000);
    }
}
