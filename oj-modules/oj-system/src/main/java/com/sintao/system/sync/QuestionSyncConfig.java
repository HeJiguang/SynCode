package com.sintao.system.sync;

import org.springframework.amqp.core.*;
import org.springframework.amqp.rabbit.config.SimpleRabbitListenerContainerFactory;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.amqp.rabbit.connection.CachingConnectionFactory;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.annotation.EnableScheduling;

@Configuration
@EnableScheduling
@ConditionalOnProperty(name = "question.sync.enabled", havingValue = "true")
public class QuestionSyncConfig {
    public static final String EXCHANGE = "oj.question.sync";
    public static final String ES_QUEUE = "oj.question.sync.es";
    public static final String REDIS_QUEUE = "oj.question.sync.redis";

    @Bean
    public org.springframework.scheduling.concurrent.ThreadPoolTaskScheduler questionSyncScheduler() {
        var scheduler = new org.springframework.scheduling.concurrent.ThreadPoolTaskScheduler();
        scheduler.setPoolSize(2);
        scheduler.setThreadNamePrefix("question-sync-");
        return scheduler;
    }

    @Bean
    public Declarables questionSyncTopology() {
        DirectExchange exchange = new DirectExchange(EXCHANGE, true, false);
        Queue es = QueueBuilder.durable(ES_QUEUE).build();
        Queue redis = QueueBuilder.durable(REDIS_QUEUE).build();
        return new Declarables(exchange, es, redis,
                BindingBuilder.bind(es).to(exchange).with("ES"),
                BindingBuilder.bind(redis).to(exchange).with("REDIS"));
    }

    // Dedicated template: never replace the judge producer's callbacks or converter.
    public static RabbitTemplate questionSyncRabbitTemplate(ConnectionFactory connectionFactory) {
        if (!(connectionFactory instanceof CachingConnectionFactory cf)
                || !cf.isPublisherConfirms() || !cf.isPublisherReturns()) {
            throw new IllegalStateException("Question sync requires correlated publisher confirms and publisher returns");
        }
        RabbitTemplate template = new RabbitTemplate(connectionFactory);
        template.setMandatory(true);
        return template;
    }

    @Bean
    public SimpleRabbitListenerContainerFactory questionSyncListenerFactory(ConnectionFactory connectionFactory) {
        SimpleRabbitListenerContainerFactory factory = new SimpleRabbitListenerContainerFactory();
        factory.setConnectionFactory(connectionFactory);
        factory.setAcknowledgeMode(AcknowledgeMode.MANUAL);
        factory.setPrefetchCount(10);
        return factory;
    }
}
