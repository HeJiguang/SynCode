package com.sintao.judge.config;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class JudgeLockPropertiesTest {

    @Test
    void acceptsRenewalAtOneThirdOfLease() {
        JudgeLockProperties properties = new JudgeLockProperties(30, 10);

        assertEquals(30, properties.leaseSeconds());
        assertEquals(10, properties.renewIntervalSeconds());
    }

    @Test
    void rejectsUnsafeLeaseConfiguration() {
        assertThrows(IllegalArgumentException.class, () -> new JudgeLockProperties(2, 1));
        assertThrows(IllegalArgumentException.class, () -> new JudgeLockProperties(30, 0));
        assertThrows(IllegalArgumentException.class, () -> new JudgeLockProperties(30, 11));
    }
}
