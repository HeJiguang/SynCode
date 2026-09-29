package com.sintao.common.rabbit;

import com.sintao.common.core.constants.RabbitMQConstants;
import org.springframework.amqp.core.AcknowledgeMode;
import org.springframework.amqp.core.Binding;
import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.DirectExchange;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.core.QueueBuilder;
import org.springframework.amqp.rabbit.config.SimpleRabbitListenerContainerFactory;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.support.converter.Jackson2JsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class RabbitConfig {

    private static final int RETRY_DELAY_MILLIS = 15000;

    @Bean
    public DirectExchange judgeExchange() {
        return new DirectExchange(RabbitMQConstants.OJ_JUDGE_EXCHANGE, true, false);
    }

    @Bean
    public DirectExchange judgeDeadLetterExchange() {
        return new DirectExchange(RabbitMQConstants.OJ_JUDGE_DLX_EXCHANGE, true, false);
    }

    @Bean
    public Queue workQueue() {
        return QueueBuilder.durable(RabbitMQConstants.OJ_WORK_QUEUE).build();
    }

    @Bean
    public Queue batchQueue() {
        return QueueBuilder.durable(RabbitMQConstants.OJ_BATCH_QUEUE).build();
    }

    @Bean
    public Queue retryQueue() {
        return QueueBuilder.durable(RabbitMQConstants.OJ_RETRY_QUEUE)
                .ttl(RETRY_DELAY_MILLIS)
                .deadLetterExchange(RabbitMQConstants.OJ_JUDGE_EXCHANGE)
                .deadLetterRoutingKey(RabbitMQConstants.JUDGE_SUBMIT_KEY)
                .build();
    }

    @Bean
    public Queue batchRetryQueue() {
        return QueueBuilder.durable(RabbitMQConstants.OJ_BATCH_RETRY_QUEUE)
                .ttl(RETRY_DELAY_MILLIS)
                .deadLetterExchange(RabbitMQConstants.OJ_JUDGE_EXCHANGE)
                .deadLetterRoutingKey(RabbitMQConstants.JUDGE_BATCH_KEY)
                .build();
    }

    @Bean
    public Queue deadQueue() {
        return QueueBuilder.durable(RabbitMQConstants.OJ_DEAD_QUEUE).build();
    }

    @Bean
    public Binding workQueueBinding(@Qualifier("workQueue") Queue workQueue,
                                    @Qualifier("judgeExchange") DirectExchange judgeExchange) {
        return BindingBuilder.bind(workQueue)
                .to(judgeExchange)
                .with(RabbitMQConstants.JUDGE_SUBMIT_KEY);
    }

    @Bean
    public Binding batchQueueBinding(@Qualifier("batchQueue") Queue batchQueue,
                                     @Qualifier("judgeExchange") DirectExchange judgeExchange) {
        return BindingBuilder.bind(batchQueue)
                .to(judgeExchange)
                .with(RabbitMQConstants.JUDGE_BATCH_KEY);
    }

    @Bean
    public Binding retryQueueBinding(@Qualifier("retryQueue") Queue retryQueue,
                                     @Qualifier("judgeDeadLetterExchange") DirectExchange judgeDeadLetterExchange) {
        return BindingBuilder.bind(retryQueue)
                .to(judgeDeadLetterExchange)
                .with(RabbitMQConstants.JUDGE_RETRY_KEY);
    }

    @Bean
    public Binding batchRetryQueueBinding(@Qualifier("batchRetryQueue") Queue batchRetryQueue,
                                          @Qualifier("judgeDeadLetterExchange") DirectExchange judgeDeadLetterExchange) {
        return BindingBuilder.bind(batchRetryQueue)
                .to(judgeDeadLetterExchange)
                .with(RabbitMQConstants.JUDGE_BATCH_RETRY_KEY);
    }

    @Bean
    public Binding deadQueueBinding(@Qualifier("deadQueue") Queue deadQueue,
                                    @Qualifier("judgeDeadLetterExchange") DirectExchange judgeDeadLetterExchange) {
        return BindingBuilder.bind(deadQueue)
                .to(judgeDeadLetterExchange)
                .with(RabbitMQConstants.JUDGE_DEAD_KEY);
    }

    @Bean
    public MessageConverter messageConverter() {
        return new Jackson2JsonMessageConverter();
    }

    @Bean
    public SimpleRabbitListenerContainerFactory manualAckRabbitListenerContainerFactory(ConnectionFactory connectionFactory,
                                                                                        MessageConverter messageConverter) {
        SimpleRabbitListenerContainerFactory factory = new SimpleRabbitListenerContainerFactory();
        factory.setConnectionFactory(connectionFactory);
        factory.setMessageConverter(messageConverter);
        factory.setAcknowledgeMode(AcknowledgeMode.MANUAL);
        return factory;
    }
}

