package com.sintao.common.redis.service;

import com.sintao.common.core.constants.CacheConstants;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.util.Map;
import java.util.concurrent.TimeUnit;

import static org.mockito.ArgumentMatchers.anyMap;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.junit.jupiter.api.Assertions.assertEquals;

class JudgeRuntimeStateServiceTest {

    @Test
    void markAcceptedShouldPersistRuntimeStateWithTtl() {
        RedisService redisService = mock(RedisService.class);
        JudgeRuntimeStateService service = new JudgeRuntimeStateService(redisService, 30);

        service.markAccepted("req-accepted");

        verify(redisService).setCacheMap(
                eq(CacheConstants.JUDGE_RUNTIME_STATE + "req-accepted"),
                anyMap(),
                eq(30L),
                eq(TimeUnit.MINUTES)
        );
    }

    @Test
    void markRetryWaitingShouldPersistRetryMetadataWithTtl() {
        RedisService redisService = mock(RedisService.class);
        JudgeRuntimeStateService service = new JudgeRuntimeStateService(redisService, 45);
        ArgumentCaptor<Map<String, Object>> stateCaptor = ArgumentCaptor.forClass(Map.class);

        service.markRetryWaiting("req-retry", 2, "sandbox busy");

        verify(redisService).setCacheMap(
                eq(CacheConstants.JUDGE_RUNTIME_STATE + "req-retry"),
                stateCaptor.capture(),
                eq(45L),
                eq(TimeUnit.MINUTES)
        );
        Map<String, Object> persistedState = stateCaptor.getValue();
        assertEquals("RETRY_WAIT", persistedState.get("phase"));
        assertEquals(2, persistedState.get("retryCount"));
        assertEquals("sandbox busy", persistedState.get("lastError"));
    }
}
