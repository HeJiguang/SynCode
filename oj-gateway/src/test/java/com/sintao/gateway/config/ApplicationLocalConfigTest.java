package com.sintao.gateway.config;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.config.YamlPropertiesFactoryBean;
import org.springframework.core.io.ClassPathResource;

import java.util.Properties;

import static org.junit.jupiter.api.Assertions.assertEquals;

class ApplicationLocalConfigTest {

    @Test
    void localProfileKeepsGatewayRedisOnTheDevPort() {
        YamlPropertiesFactoryBean factory = new YamlPropertiesFactoryBean();
        factory.setResources(new ClassPathResource("application-local.yml"));

        Properties properties = factory.getObject();

        assertEquals("${REDIS_HOST:127.0.0.1}", properties.getProperty("spring.data.redis.host"));
        assertEquals("${REDIS_PORT:16379}", properties.getProperty("spring.data.redis.port"));
        assertEquals("${REDIS_PASSWORD:change-me-local}", properties.getProperty("spring.data.redis.password"));
    }
}
