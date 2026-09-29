package com.sintao.judge.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.concurrent.TimeUnit;

@Component
public class SandboxTimeoutProperties {

    private final long compileSeconds;
    private final long totalSeconds;

    public SandboxTimeoutProperties(
            @Value("${sandbox.limit.compile-time:10}") long compileSeconds,
            @Value("${sandbox.limit.total-time:60}") long totalSeconds) {
        if (compileSeconds < 1) {
            throw new IllegalArgumentException("Sandbox compile timeout must be at least 1 second");
        }
        if (totalSeconds < compileSeconds) {
            throw new IllegalArgumentException("Sandbox total timeout must not be shorter than compile timeout");
        }
        this.compileSeconds = compileSeconds;
        this.totalSeconds = totalSeconds;
    }

    public long deadlineNanos() {
        return System.nanoTime() + TimeUnit.SECONDS.toNanos(totalSeconds);
    }

    public long compileWaitMillis(long deadlineNanos) {
        return boundedWaitMillis(deadlineNanos, compileSeconds);
    }

    public long compileWaitMillis(long deadlineNanos, long minimumSeconds) {
        return boundedWaitMillis(deadlineNanos, Math.max(compileSeconds, minimumSeconds));
    }

    public long executionWaitMillis(long deadlineNanos, long perCaseSeconds) {
        return boundedWaitMillis(deadlineNanos, perCaseSeconds);
    }

    private long boundedWaitMillis(long deadlineNanos, long phaseSeconds) {
        long remainingNanos = deadlineNanos - System.nanoTime();
        if (remainingNanos <= 0) {
            return 0;
        }
        long phaseNanos = TimeUnit.SECONDS.toNanos(Math.max(1, phaseSeconds));
        long allowedNanos = Math.min(remainingNanos, phaseNanos);
        return Math.max(1, TimeUnit.NANOSECONDS.toMillis(allowedNanos));
    }
}
