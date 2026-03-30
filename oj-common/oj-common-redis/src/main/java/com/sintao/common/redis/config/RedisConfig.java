package com.sintao.common.redis.config;

import com.sintao.common.redis.service.JudgeRuntimeStateService;
import com.sintao.common.redis.service.JudgeResultPushService;
import com.sintao.common.redis.service.RedisService;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.AutoConfigureBefore;
import org.springframework.boot.autoconfigure.data.redis.RedisAutoConfiguration;
import org.springframework.cache.annotation.CachingConfigurerSupport;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Primary;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.serializer.StringRedisSerializer;

@AutoConfiguration
@AutoConfigureBefore(RedisAutoConfiguration.class)
public class RedisConfig extends CachingConfigurerSupport {

    @Bean
    @Primary
    public RedisTemplate<Object, Object> redisTemplate(RedisConnectionFactory connectionFactory) {
        RedisTemplate<Object, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(connectionFactory);

        JsonRedisSerializer serializer = new JsonRedisSerializer(Object.class);
        template.setKeySerializer(new StringRedisSerializer());
        template.setValueSerializer(serializer);
        template.setHashKeySerializer(new StringRedisSerializer());
        template.setHashValueSerializer(serializer);
        template.afterPropertiesSet();
        return template;
    }

    @Bean
    public RedisService redisService() {
        return new RedisService();
    }

    @Bean
    public JudgeRuntimeStateService judgeRuntimeStateService(RedisService redisService,
                                                             @Value("${judge.runtime-state.ttl-minutes:1440}") long runtimeStateTtlMinutes) {
        return new JudgeRuntimeStateService(redisService, runtimeStateTtlMinutes);
    }

    @Bean
    public JudgeResultPushService judgeResultPushService(RedisService redisService,
                                                         RedisTemplate<Object, Object> redisTemplate) {
        return new JudgeResultPushService(redisService, redisTemplate);
    }
}
