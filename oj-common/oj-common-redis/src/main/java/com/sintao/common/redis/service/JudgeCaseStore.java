package com.sintao.common.redis.service;

import com.alibaba.fastjson2.JSON;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Duration;
import java.util.Base64;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.LinkedHashMap;
import java.util.UUID;
import java.util.zip.GZIPInputStream;
import java.util.zip.GZIPOutputStream;

/** Immutable, compressed cases; readers fetch only the current case, never the entire set. */
public class JudgeCaseStore {
    private static final String PREFIX = "judge:cases:v1:";
    private static final DefaultRedisScript<Long> WRITE_BATCH = new DefaultRedisScript<>(
            "for i=2,#ARGV,2 do redis.call('hset',KEYS[1],ARGV[i],ARGV[i+1]) end "
                    + "return redis.call('expire',KEYS[1],ARGV[1])", Long.class);
    private final StringRedisTemplate redis;
    private final Duration ttl;
    private final int maxCases;
    private final int maxCaseBytes;
    private final long maxSetBytes;

    public JudgeCaseStore(StringRedisTemplate redis, long ttlHours, int maxCases,
                          int maxCaseBytes, long maxSetBytes) {
        if (ttlHours < 24 || maxCases < 1 || maxCaseBytes < 1 || maxSetBytes < maxCaseBytes) {
            throw new IllegalArgumentException("Invalid judge case store limits");
        }
        this.redis = redis;
        this.ttl = Duration.ofHours(ttlHours);
        this.maxCases = maxCases;
        this.maxCaseBytes = maxCaseBytes;
        this.maxSetBytes = maxSetBytes;
    }

    public record TestCase(String caseId, String input, String expected) { }
    public record Reference(String id, int count) { }

    public Reference save(List<String> inputs, List<String> outputs) {
        if (inputs == null || outputs == null || inputs.isEmpty()
                || inputs.size() != outputs.size() || inputs.size() > maxCases) {
            throw new IllegalArgumentException("Invalid judge test set");
        }
        String temporary = PREFIX + "upload:" + UUID.randomUUID();
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            long total = 0;
            for (int i = 0; i < inputs.size(); i++) {
                byte[] bytes = caseBytes(inputs, outputs, i);
                total += bytes.length;
                if (bytes.length > maxCaseBytes || total > maxSetBytes) {
                    throw new IllegalArgumentException("Judge test set exceeds configured size limit");
                }
                digest.update(bytes);
            }
            String id = HexFormat.of().formatHex(digest.digest());
            Object existing = redis.opsForHash().get(key(id), "count");
            if (Integer.toString(inputs.size()).equals(existing) && Boolean.TRUE.equals(redis.expire(key(id), ttl))) {
                return new Reference(id, inputs.size());
            }
            Map<String, String> batch = new LinkedHashMap<>();
            long batchBytes = 0;
            for (int i = 0; i < inputs.size(); i++) {
                byte[] bytes = caseBytes(inputs, outputs, i);
                String encoded = encode(bytes);
                batch.put(Integer.toString(i), encoded);
                batchBytes += encoded.length();
                if (batch.size() >= 64 || batchBytes >= 1048576) {
                    flush(temporary, batch);
                    batchBytes = 0;
                }
            }
            flush(temporary, batch);
            redis.opsForHash().put(temporary, "count", Integer.toString(inputs.size()));
            redis.expire(temporary, ttl);
            // Publish only a complete hash. Concurrent writers produce identical data for this ID.
            redis.rename(temporary, key(id));
            return new Reference(id, inputs.size());
        } catch (RuntimeException e) {
            throw e;
        } catch (Exception e) {
            throw new IllegalStateException("Cannot save judge test set", e);
        } finally {
            redis.delete(temporary);
        }
    }

    public int count(String id) {
        String key = key(id);
        Object count = redis.opsForHash().get(key, "count");
        if (count == null) throw new IllegalStateException("Judge test set is missing or expired: " + id);
        redis.expire(key, ttl);
        int size = Integer.parseInt(count.toString());
        if (size < 1 || size > maxCases) throw new IllegalStateException("Invalid stored case count");
        return size;
    }

    public TestCase read(String id, int index) {
        if (index < 0 || index >= maxCases) throw new IllegalArgumentException("Invalid case index");
        Object encoded = redis.opsForHash().get(key(id), Integer.toString(index));
        if (encoded == null) throw new IllegalStateException("Judge test case is missing: " + id + "/" + index);
        TestCase result = JSON.parseObject(decode(encoded.toString()), TestCase.class);
        if (!caseId(index).equals(result.caseId())) throw new IllegalStateException("Judge case ID mismatch");
        return result;
    }

    public static String caseId(int index) { return "case-" + (index + 1); }

    private byte[] caseBytes(List<String> inputs, List<String> outputs, int index) {
        // JSON objects contain IDs/delimiters, so both ordering and answers affect the version.
        return JSON.toJSONBytes(new TestCase(caseId(index), inputs.get(index), outputs.get(index)));
    }

    private void flush(String key, Map<String, String> batch) {
        if (batch.isEmpty()) return;
        java.util.ArrayList<String> args = new java.util.ArrayList<>();
        args.add(Long.toString(ttl.toSeconds()));
        batch.forEach((field, value) -> { args.add(field); args.add(value); });
        // Data and expiry are applied atomically, including partial uploads.
        redis.execute(WRITE_BATCH, List.of(key), args.toArray());
        batch.clear();
    }

    private String key(String id) {
        if (id == null || !id.matches("[0-9a-f]{64}")) throw new IllegalArgumentException("Invalid test set ID");
        return PREFIX + id;
    }

    private String encode(byte[] bytes) throws Exception {
        ByteArrayOutputStream buffer = new ByteArrayOutputStream();
        try (GZIPOutputStream gzip = new GZIPOutputStream(buffer)) { gzip.write(bytes); }
        return Base64.getEncoder().encodeToString(buffer.toByteArray());
    }

    private String decode(String encoded) {
        try (GZIPInputStream gzip = new GZIPInputStream(
                new ByteArrayInputStream(Base64.getDecoder().decode(encoded)))) {
            byte[] bytes = gzip.readNBytes(maxCaseBytes + 1);
            if (bytes.length > maxCaseBytes) throw new IllegalStateException("Stored case exceeds size limit");
            return new String(bytes, StandardCharsets.UTF_8);
        } catch (Exception e) { throw new IllegalStateException("Cannot decode judge test case", e); }
    }
}
