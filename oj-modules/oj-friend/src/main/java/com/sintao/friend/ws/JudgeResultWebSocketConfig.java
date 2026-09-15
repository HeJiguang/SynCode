package com.sintao.friend.ws;

import com.sintao.common.core.constants.CacheConstants;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.listener.PatternTopic;
import org.springframework.data.redis.listener.RedisMessageListenerContainer;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;

@Configuration
@EnableWebSocket
public class JudgeResultWebSocketConfig implements WebSocketConfigurer {

    @Value("${syncode.friend.web-socket-path:/ws/judge/result}")
    private String webSocketPath;


    // 真正处理WebSocket消息的地方
    private final JudgeResultWebSocketHandler handler;

    // 握手时做认证的地方
    private final JudgeResultHandshakeInterceptor handshakeInterceptor;

    // Redis收到消息之后转发给WebSocket的桥
    private final JudgeResultPubSubBridge pubSubBridge;

    public JudgeResultWebSocketConfig(JudgeResultWebSocketHandler handler,
                                      JudgeResultHandshakeInterceptor handshakeInterceptor,
                                      JudgeResultPubSubBridge pubSubBridge) {
        this.handler = handler;
        this.handshakeInterceptor = handshakeInterceptor;
        this.pubSubBridge = pubSubBridge;
    }

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(handler, webSocketPath) // friend内部的WebSocket路径
                .addInterceptors(handshakeInterceptor) // 在升级为WebSocket之前，先走拦截器做校验
                .setAllowedOrigins("*"); // 允许跨域来源
    }

    @Bean
    public RedisMessageListenerContainer judgeResultRedisMessageListenerContainer(RedisConnectionFactory connectionFactory) {
        RedisMessageListenerContainer container = new RedisMessageListenerContainer();
        container.setConnectionFactory(connectionFactory);
        container.addMessageListener(pubSubBridge, new PatternTopic(CacheConstants.JUDGE_RESULT_TOPIC));
        return container;
    }
}
