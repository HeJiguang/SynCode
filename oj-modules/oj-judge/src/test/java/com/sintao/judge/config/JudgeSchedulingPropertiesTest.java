package com.sintao.judge.config;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class JudgeSchedulingPropertiesTest {

    @Test
    void derivesBoundedQueueCapacityFromExecutionCapacity() {
        JudgeSchedulingProperties properties = new JudgeSchedulingProperties(4, 1);

        assertEquals(4, properties.realtimeBurst());
        assertEquals(6, properties.queueCapacity(6));
    }

    @Test
    void rejectsUnsafeSchedulingConfiguration() {
        assertThrows(IllegalArgumentException.class, () -> new JudgeSchedulingProperties(0, 1));
        assertThrows(IllegalArgumentException.class, () -> new JudgeSchedulingProperties(4, -1));
        assertThrows(IllegalArgumentException.class, () -> new JudgeSchedulingProperties(4, 5));
    }
}
