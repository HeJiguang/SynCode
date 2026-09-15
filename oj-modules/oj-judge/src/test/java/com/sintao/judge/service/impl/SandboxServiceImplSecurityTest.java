package com.sintao.judge.service.impl;

import com.github.dockerjava.api.model.HostConfig;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SandboxServiceImplSecurityTest {

    @Test
    void fallbackSandboxShouldApplyLinuxResourceAndIsolationLimits() {
        SandboxServiceImpl service = new SandboxServiceImpl();
        ReflectionTestUtils.setField(service, "memoryLimit", 100_000_000L);
        ReflectionTestUtils.setField(service, "memorySwapLimit", 100_000_000L);
        ReflectionTestUtils.setField(service, "cpuLimit", 1L);
        ReflectionTestUtils.setField(service, "pidsLimit", 64L);

        HostConfig hostConfig = ReflectionTestUtils.invokeMethod(service, "getHostConfig", "/tmp/sandbox-test");

        assertEquals(100_000_000L, hostConfig.getMemory());
        assertEquals(100_000_000L, hostConfig.getMemorySwap());
        assertEquals(1_000_000_000L, hostConfig.getNanoCPUs());
        assertEquals(64L, hostConfig.getPidsLimit());
        assertEquals("none", hostConfig.getNetworkMode());
        assertTrue(hostConfig.getReadonlyRootfs());
    }
}
