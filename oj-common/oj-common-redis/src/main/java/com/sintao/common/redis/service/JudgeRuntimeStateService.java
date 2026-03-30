package com.sintao.common.redis.service;

import com.sintao.common.core.constants.CacheConstants;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;

@Component
public class JudgeRuntimeStateService {

    private final RedisService redisService;

    private final long runtimeStateTtlMinutes;

    public JudgeRuntimeStateService(RedisService redisService) {
        this(redisService, 1440);
    }

    public JudgeRuntimeStateService(RedisService redisService,
                                    @Value("${judge.runtime-state.ttl-minutes:1440}") long runtimeStateTtlMinutes) {
        this.redisService = redisService;
        this.runtimeStateTtlMinutes = runtimeStateTtlMinutes;
    }

    public void markAccepted(String requestId) {
        saveRuntimeState(requestId, "ACCEPTED", 0, null);
    }

    public void markPublished(String requestId) {
        saveRuntimeState(requestId, "PUBLISHED", null, null);
    }

    public void markConsuming(String requestId) {
        saveRuntimeState(requestId, "CONSUMING", null, null);
    }

    public void markRetryWaiting(String requestId, Integer retryCount, String lastError) {
        saveRuntimeState(requestId, "RETRY_WAIT", retryCount, lastError);
    }

    public void markDeadLetter(String requestId, Integer retryCount, String lastError) {
        saveRuntimeState(requestId, "DEAD_LETTER", retryCount, lastError);
    }

    public void markDispatchFailed(String requestId, String lastError) {
        saveRuntimeState(requestId, "DISPATCH_FAILED", null, lastError);
    }

    public boolean tryLock(String requestId, String consumerId, long timeoutSeconds) {
        return redisService.setCacheObjectIfAbsent(
                CacheConstants.JUDGE_REQUEST_LOCK + requestId,
                consumerId,
                timeoutSeconds,
                TimeUnit.SECONDS
        );
    }

    public void unlock(String requestId) {
        redisService.deleteObject(CacheConstants.JUDGE_REQUEST_LOCK + requestId);
    }

    private void saveRuntimeState(String requestId, String phase, Integer retryCount, String lastError) {
        Map<String, Object> state = new LinkedHashMap<>();
        state.put("phase", phase);
        state.put("updatedAt", LocalDateTime.now().toString());
        if (retryCount != null) {
            state.put("retryCount", retryCount);
        }
        if (lastError != null) {
            state.put("lastError", lastError);
        }
        redisService.setCacheMap(
                CacheConstants.JUDGE_RUNTIME_STATE + requestId,
                state,
                runtimeStateTtlMinutes,
                TimeUnit.MINUTES
        );
    }
}
