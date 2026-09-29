package com.sintao.judge.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

@Component
public class JudgeLockProperties {

    private final long leaseSeconds;
    private final long renewIntervalSeconds;

    public JudgeLockProperties(@Value("${judge.lock.lease-seconds:30}") long leaseSeconds,
                               @Value("${judge.lock.renew-interval-seconds:10}") long renewIntervalSeconds) {
        if (leaseSeconds < 3) {
            throw new IllegalArgumentException("Judge lock lease must be at least 3 seconds");
        }
        if (renewIntervalSeconds < 1 || renewIntervalSeconds > leaseSeconds / 3) {
            throw new IllegalArgumentException(
                    "Judge lock renewal interval must be positive and no greater than one third of the lease"
            );
        }
        this.leaseSeconds = leaseSeconds;
        this.renewIntervalSeconds = renewIntervalSeconds;
    }

    public long leaseSeconds() {
        return leaseSeconds;
    }

    public long renewIntervalSeconds() {
        return renewIntervalSeconds;
    }
}
