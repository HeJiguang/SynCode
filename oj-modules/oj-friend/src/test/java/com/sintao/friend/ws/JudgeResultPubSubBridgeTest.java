package com.sintao.friend.ws;

import com.alibaba.fastjson2.JSON;
import com.sintao.common.core.enums.JudgeAsyncStatus;
import com.sintao.common.core.domain.dto.JudgeResultPushDTO;
import org.junit.jupiter.api.Test;
import org.springframework.data.redis.connection.Message;

import java.time.LocalDateTime;

import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class JudgeResultPubSubBridgeTest {

    @Test
    void redisMessageIsConvertedIntoFinalResultPush() {
        JudgeResultSessionRegistry registry = mock(JudgeResultSessionRegistry.class);
        JudgeResultPubSubBridge bridge = new JudgeResultPubSubBridge(registry);
        JudgeResultPushDTO dto = new JudgeResultPushDTO();
        dto.setRequestId("req-1");
        dto.setUserId(1001L);
        dto.setAsyncStatus(JudgeAsyncStatus.SUCCESS.getValue());
        dto.setFinishTime(LocalDateTime.now());
        Message message = mock(Message.class);
        when(message.getBody()).thenReturn(JSON.toJSONString(dto).getBytes());

        bridge.onMessage(message, null);

        verify(registry).pushFinalResult(argThat(result ->
                "req-1".equals(result.getRequestId())
                        && Integer.valueOf(JudgeAsyncStatus.SUCCESS.getValue()).equals(result.getAsyncStatus())));
    }

    @Test
    void redisMessageSupportsDoubleEncodedJsonPayload() {
        JudgeResultSessionRegistry registry = mock(JudgeResultSessionRegistry.class);
        JudgeResultPubSubBridge bridge = new JudgeResultPubSubBridge(registry);
        JudgeResultPushDTO dto = new JudgeResultPushDTO();
        dto.setRequestId("req-2");
        dto.setUserId(1002L);
        dto.setAsyncStatus(JudgeAsyncStatus.SUCCESS.getValue());
        dto.setFinishTime(LocalDateTime.now());
        Message message = mock(Message.class);
        String payload = JSON.toJSONString(JSON.toJSONString(dto));
        when(message.getBody()).thenReturn(payload.getBytes());

        bridge.onMessage(message, null);

        verify(registry).pushFinalResult(argThat(result ->
                "req-2".equals(result.getRequestId())
                        && Integer.valueOf(JudgeAsyncStatus.SUCCESS.getValue()).equals(result.getAsyncStatus())));
    }
}
