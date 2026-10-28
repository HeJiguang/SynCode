package com.sintao.common.redis.service;

import com.sintao.common.redis.config.RedisConfig;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.condition.EnabledIfSystemProperty;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.data.redis.connection.lettuce.LettuceConnectionFactory;

import java.net.ServerSocket;
import java.nio.file.Path;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

/** Runs only with an explicitly selected native server; never connects to an existing Redis. */
@EnabledIfSystemProperty(named = "question.test.redis-server", matches = ".+")
class QuestionListRedisIntegrationTest {
    @TempDir Path directory;

    @Test
    void atomicReplacementMustRejectStaleBuilderAndClearEmptyResults() throws Exception {
        int port;
        try (ServerSocket socket = new ServerSocket(0)) { port = socket.getLocalPort(); }
        Process server = new ProcessBuilder(System.getProperty("question.test.redis-server"),
                "--bind", "127.0.0.1", "--port", Integer.toString(port), "--save", "", "--appendonly", "no",
                "--dir", directory.toString()).redirectErrorStream(true)
                .redirectOutput(directory.resolve("redis.log").toFile()).start();
        LettuceConnectionFactory factory = new LettuceConnectionFactory("127.0.0.1", port);
        factory.afterPropertiesSet();
        factory.start();
        try {
            for (int i = 0; ; i++) {
                try (var connection = factory.getConnection()) { connection.ping(); break; }
                catch (Exception failure) { if (i == 50) throw failure; Thread.sleep(100); }
            }
            RedisService redis = new RedisService();
            redis.redisTemplate = new RedisConfig().redisTemplate(factory);
            String key = "q:{test}:list";
            String before = redis.listGeneration(key);
            assertTrue(redis.replaceVersionedList(key, before, List.of(3L, 2L, 1L), 300));
            assertEquals(List.of(3L, 2L, 1L), redis.getCacheListByRange(key, 0, -1, Long.class));
            // Repeated rebuild replaces rather than appends.
            assertTrue(redis.replaceVersionedList(key, before, List.of(3L, 2L, 1L), 300));
            assertEquals(3L, redis.getListSize(key));
            redis.invalidateVersionedList(key);
            assertFalse(redis.replaceVersionedList(key, before, List.of(3L, 2L, 1L), 300));
            assertFalse(redis.hasKey(key));
            String current = redis.listGeneration(key);
            assertTrue(redis.replaceVersionedList(key, current, List.of(4L, 3L), 300));
            assertTrue(redis.getExpire(key, java.util.concurrent.TimeUnit.SECONDS) > 0);
            assertTrue(redis.replaceVersionedList(key, current, List.of(), 300));
            assertFalse(redis.hasKey(key));
        } finally {
            factory.destroy();
            server.destroy();
            if (!server.waitFor(10, java.util.concurrent.TimeUnit.SECONDS)) server.destroyForcibly().waitFor();
        }
    }
}
