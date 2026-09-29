package com.sintao.judge.config;

import org.junit.jupiter.api.Test;
import org.springframework.amqp.rabbit.config.SimpleRabbitListenerEndpoint;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.listener.SimpleMessageListenerContainer;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.test.util.ReflectionTestUtils;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.mock;

class JudgeListenerConfigTest {

    @Test
    void oneConsumerUsesLocalExecutionCapacityAsPrefetch() {
        JudgeListenerConfig config = new JudgeListenerConfig();
        JudgeExecutionCapacity capacity = new JudgeExecutionCapacity("pool", 4, 0);
        var factory = config.judgeListenerContainerFactory(
                mock(ConnectionFactory.class), mock(MessageConverter.class), capacity, 0);
        SimpleRabbitListenerEndpoint endpoint = new SimpleRabbitListenerEndpoint();
        endpoint.setId("judge-test");
        endpoint.setQueueNames("oj-work-queue");
        endpoint.setMessageListener(message -> { });

        SimpleMessageListenerContainer container = factory.createListenerContainer(endpoint);

        assertEquals(1, ReflectionTestUtils.getField(container, "concurrentConsumers"));
        assertEquals(1, ReflectionTestUtils.getField(container, "maxConcurrentConsumers"));
        assertEquals(4, ReflectionTestUtils.getField(container, "prefetchCount"));
    }

    @Test
    void configuredCapacityAndPrefetchCannotExceedSandboxCapacity() {
        assertEquals(1, new JudgeExecutionCapacity("standalone", 4, 0).value());
        assertEquals(2, new JudgeExecutionCapacity("pool", 4, 2).value());
        assertEquals(2, JudgeListenerConfig.resolvePrefetch(4, 2));
        assertThrows(IllegalArgumentException.class,
                () -> new JudgeExecutionCapacity("pool", 4, 5));
        assertThrows(IllegalArgumentException.class,
                () -> JudgeListenerConfig.resolvePrefetch(4, 5));
    }
}
