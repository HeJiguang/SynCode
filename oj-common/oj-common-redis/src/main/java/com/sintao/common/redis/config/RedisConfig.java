package com.sintao.common.redis.config;

import com.sintao.common.redis.service.JudgeRuntimeStateService;
import com.sintao.common.redis.service.JudgeResultPushService;
import com.sintao.common.redis.service.RedisService;
import com.sintao.common.redis.service.JudgeCaseStore;
import org.springframework.data.redis.core.StringRedisTemplate;
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
    public JudgeCaseStore judgeCaseStore(RedisConnectionFactory connectionFactory,
            @Value("${judge.cases.ttl-hours:168}") long ttlHours,
            @Value("${judge.cases.max-count:10000}") int maxCount,
            @Value("${judge.cases.max-case-bytes:33554432}") int maxCaseBytes,
            @Value("${judge.cases.max-set-bytes:134217728}") long maxSetBytes) {
        return new JudgeCaseStore(new StringRedisTemplate(connectionFactory), ttlHours,
                maxCount, maxCaseBytes, maxSetBytes);
    }

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
