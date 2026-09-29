package com.sintao.judge.config;

import org.springframework.amqp.core.AcknowledgeMode;
import org.springframework.amqp.rabbit.config.SimpleRabbitListenerContainerFactory;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class JudgeListenerConfig {

    @Bean
    public SimpleRabbitListenerContainerFactory judgeListenerContainerFactory(
            ConnectionFactory connectionFactory,
            MessageConverter messageConverter,
            JudgeExecutionCapacity executionCapacity,
            @Value("${judge.consumer.prefetch:0}") int configuredPrefetch) {
        int prefetch = resolvePrefetch(executionCapacity.value(), configuredPrefetch);
        SimpleRabbitListenerContainerFactory factory = new SimpleRabbitListenerContainerFactory();
        factory.setConnectionFactory(connectionFactory);
        factory.setMessageConverter(messageConverter);
        factory.setAcknowledgeMode(AcknowledgeMode.MANUAL);
        factory.setConcurrentConsumers(1);
        factory.setMaxConcurrentConsumers(1);
        factory.setPrefetchCount(prefetch);
        factory.setDefaultRequeueRejected(true);
        return factory;
    }

    static int resolvePrefetch(int executionCapacity, int configuredPrefetch) {
        if (configuredPrefetch < 0 || configuredPrefetch > executionCapacity) {
            throw new IllegalArgumentException(
                    "Judge consumer prefetch must be between 1 and execution capacity " + executionCapacity
            );
        }
        return configuredPrefetch == 0 ? executionCapacity : configuredPrefetch;
    }
}
