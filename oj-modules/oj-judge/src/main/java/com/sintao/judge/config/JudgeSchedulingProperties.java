package com.sintao.judge.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class JudgeSchedulingProperties {

    private final int realtimeBurst;
    private final int queueCapacityMultiplier;

    public JudgeSchedulingProperties(
            @Value("${judge.scheduler.realtime-burst:4}") int realtimeBurst,
            @Value("${judge.scheduler.queue-capacity-multiplier:1}") int queueCapacityMultiplier) {
        if (realtimeBurst < 1) {
            throw new IllegalArgumentException("Judge realtime burst must be at least 1");
        }
        if (queueCapacityMultiplier < 0 || queueCapacityMultiplier > 4) {
            throw new IllegalArgumentException("Judge queue capacity multiplier must be between 0 and 4");
        }
        this.realtimeBurst = realtimeBurst;
        this.queueCapacityMultiplier = queueCapacityMultiplier;
    }

    public int realtimeBurst() {
        return realtimeBurst;
    }

    public int queueCapacity(int executionCapacity) {
        return Math.multiplyExact(executionCapacity, queueCapacityMultiplier);
    }
}
