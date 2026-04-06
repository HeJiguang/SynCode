package com.sintao.friend.ws;

import com.alibaba.fastjson2.JSON;
import com.sintao.common.core.domain.dto.JudgeResultPushDTO;
import org.springframework.data.redis.connection.Message;
import org.springframework.data.redis.connection.MessageListener;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;

@Component
public class JudgeResultPubSubBridge implements MessageListener {

    private final JudgeResultSessionRegistry registry;

    public JudgeResultPubSubBridge(JudgeResultSessionRegistry registry) {
        this.registry = registry;
    }

    @Override
    public void onMessage(Message message, byte[] pattern) {
        if (message == null || message.getBody() == null || message.getBody().length == 0) {
            return;
        }
        String payload = new String(message.getBody(), StandardCharsets.UTF_8);
        if (payload.startsWith("\"")) {
            payload = JSON.parseObject(payload, String.class);
        }
        JudgeResultPushDTO dto = JSON.parseObject(payload, JudgeResultPushDTO.class);
        registry.pushFinalResult(dto);
    }
}
