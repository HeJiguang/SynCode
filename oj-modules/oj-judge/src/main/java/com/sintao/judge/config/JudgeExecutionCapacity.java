package com.sintao.judge.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.beans.factory.annotation.Autowired;

@Component
public class JudgeExecutionCapacity {

    private final int value;

    @Autowired
    public JudgeExecutionCapacity(@Value("${sandbox.execution.mode:go-judge}") String executionMode,
                                  @Value("${sandbox.docker.pool.size:4}") int poolSize,
                                  @Value("${sandbox.go-judge.parallelism:4}") int runnerParallelism,
                                  @Value("${judge.scheduler.workers:0}") int configuredWorkers) {
        this.value = resolve(executionMode,
                "go-judge".equalsIgnoreCase(executionMode) ? runnerParallelism : poolSize, configuredWorkers);
    }

    public JudgeExecutionCapacity(String executionMode, int poolSize, int configuredWorkers) {
        this.value = resolve(executionMode, poolSize, configuredWorkers);
    }

    public int value() {
        return value;
    }

    static int resolve(String executionMode, int poolSize, int configuredWorkers) {
        int sandboxCapacity = "standalone".equalsIgnoreCase(executionMode) ? 1 : poolSize;
        if (sandboxCapacity < 1) {
            throw new IllegalArgumentException("Sandbox execution capacity must be at least 1");
        }
        if (configuredWorkers < 0 || configuredWorkers > sandboxCapacity) {
            throw new IllegalArgumentException(
                    "Judge scheduler workers must be between 1 and sandbox capacity " + sandboxCapacity
            );
        }
        return configuredWorkers == 0 ? sandboxCapacity : configuredWorkers;
    }
}
