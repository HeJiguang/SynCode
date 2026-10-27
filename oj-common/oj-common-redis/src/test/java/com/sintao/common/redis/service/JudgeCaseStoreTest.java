package com.sintao.common.redis.service;

import org.junit.jupiter.api.Test;
import org.springframework.data.redis.core.HashOperations;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.RedisScript;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class JudgeCaseStoreTest {
    @Test void contentVersionRoundTripsWhitespaceAndChangesWithOrderOrAnswer() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        HashOperations<String, Object, Object> hash = mock(HashOperations.class);
        when(redis.opsForHash()).thenReturn(hash);
        when(redis.expire(anyString(), any(java.time.Duration.class))).thenReturn(true);
        Map<String, Map<Object, Object>> data = new HashMap<>();
        when(redis.execute(any(RedisScript.class), anyList(), any(Object[].class))).thenAnswer(inv -> {
            String key = ((List<String>) inv.getArgument(1)).get(0);
            Object[] args = (Object[]) inv.getRawArguments()[2];
            Map<Object, Object> fields = data.computeIfAbsent(key, ignored -> new HashMap<>());
            for (int i = 1; i < args.length; i += 2) fields.put(args[i], args[i + 1]);
            return 1L;
        });
        doAnswer(inv -> {
            data.get(inv.getArgument(0)).put(inv.getArgument(1), inv.getArgument(2)); return null;
        }).when(hash).put(anyString(), any(), any());
        when(hash.get(anyString(), any())).thenAnswer(inv ->
                data.getOrDefault(inv.getArgument(0), Map.of()).get(inv.getArgument(1)));
        doAnswer(inv -> { data.put(inv.getArgument(1), data.remove(inv.getArgument(0))); return null; })
                .when(redis).rename(anyString(), anyString());
        when(redis.delete(anyString())).thenAnswer(inv -> data.remove(inv.getArgument(0)) != null);
        JudgeCaseStore store = new JudgeCaseStore(redis, 168, 1000, 1048576, 8388608);

        var original = store.save(List.of("  first\n\n", ""), List.of("one", "two"));
        var same = store.save(List.of("  first\n\n", ""), List.of("one", "two"));
        assertEquals(original, same);
        assertEquals(2, store.count(original.id()));
        assertEquals(new JudgeCaseStore.TestCase("case-1", "  first\n\n", "one"), store.read(original.id(), 0));
        assertEquals("", store.read(original.id(), 1).input());
        assertNotEquals(original.id(), store.save(List.of("", "  first\n\n"), List.of("two", "one")).id());
        assertNotEquals(original.id(), store.save(List.of("  first\n\n", ""), List.of("changed", "two")).id());
        verify(redis, times(3)).execute(any(RedisScript.class), anyList(), any(Object[].class));
        assertTrue(data.keySet().stream().noneMatch(key -> key.contains("upload:")));
        assertThrows(IllegalStateException.class, () -> store.count("f".repeat(64)));
    }

    @Test void rejectsInvalidOrOversizedTestSetsBeforePublishingReference() {
        StringRedisTemplate redis = mock(StringRedisTemplate.class);
        JudgeCaseStore store = new JudgeCaseStore(redis, 168, 2, 100, 200);
        assertThrows(IllegalArgumentException.class, () -> store.save(List.of(), List.of()));
        assertThrows(IllegalArgumentException.class, () -> store.save(List.of("a"), List.of()));
        assertThrows(IllegalArgumentException.class, () -> store.save(List.of("a".repeat(101)), List.of("b")));
        verify(redis, never()).rename(anyString(), anyString());
    }
}
