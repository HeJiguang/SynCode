package com.sintao.judge.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Data
@Component
@ConfigurationProperties(prefix = "sandbox.go-judge")
public class GoJudgeProperties {
    private String endpoint = "http://127.0.0.1:5050";
    private String token = "";
    private long compileTimeMs = 30000;
    private long compileMemoryBytes = 536870912L;
    private long maxTimeMs = 60000;
    private long maxMemoryBytes = 2147483648L;
    private long maxSubmissionTimeMs = 600000;
    private int clockMultiplier = 3;
    private int processLimit = 64;
    private int parallelism = 4;
    private long cpuRateLimit = 1000; // go-judge units: 1000 = one CPU
    private long outputLimitBytes = 33554432;
    private long totalOutputLimitBytes = 268435456;
    private long artifactLimitBytes = 67108864;
    private int previewChars = 2048;
    private int maxCaseDetails = 200;
    private int maxCases = 10000;
    private long checkerTimeMs = 10000;

    public void validate() {
        if (compileTimeMs < 1 || compileTimeMs > 600000 || compileMemoryBytes < 16777216
                || maxTimeMs < 1 || maxTimeMs > 600000 || maxMemoryBytes < 16777216
                || maxMemoryBytes > 17179869184L || maxSubmissionTimeMs < compileTimeMs
                || maxSubmissionTimeMs > 86400000 || clockMultiplier < 1 || clockMultiplier > 10
                || processLimit < 1 || parallelism < 1 || cpuRateLimit < 1
                || outputLimitBytes < 1 || outputLimitBytes > 268435456
                || totalOutputLimitBytes < outputLimitBytes || artifactLimitBytes < 1
                || previewChars < 1 || previewChars > 16384 || maxCaseDetails < 1
                || maxCaseDetails > 1000 || maxCases < 1 || checkerTimeMs < 1) {
            throw new IllegalArgumentException("Invalid sandbox.go-judge configuration");
        }
    }
}
