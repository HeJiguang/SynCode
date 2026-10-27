package com.sintao.judge.sandbox;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.sintao.judge.config.GoJudgeProperties;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.Map;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.file.StandardOpenOption;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.CompletionStage;
import java.util.concurrent.Flow;

/** Only this trusted client can access the runner API; user code never gets its token or file IDs. */
@Component
@ConditionalOnProperty(name = "sandbox.execution.mode", havingValue = "go-judge")
@Slf4j
public class GoJudgeClient {
    private final GoJudgeProperties properties;
    private final HttpClient http;

    public GoJudgeClient(GoJudgeProperties properties) {
        properties.validate();
        this.properties = properties;
        this.http = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(5)).build();
    }

    public JSONObject run(Map<String, Object> command, long clockMillis) {
        try {
            HttpRequest request = request("/run", clockMillis + 10000)
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofByteArray(JSON.toJSONBytes(Map.of("cmd", new Object[]{command}))))
                    .build();
            HttpResponse<String> response = http.send(request, HttpResponse.BodyHandlers.ofString());
            if (response.statusCode() != 200) throw new IOException("Runner HTTP " + response.statusCode());
            // REST /run returns an array, unlike the WebSocket requestId/results envelope.
            JSONArray results = JSON.parseArray(response.body());
            if (results.size() != 1) throw new IOException("Unexpected runner result count");
            JSONObject result = results.getJSONObject(0);
            if (result.getString("status") == null) throw new IOException("Missing runner status");
            return result;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Runner request interrupted; server clock limit remains active", e);
        } catch (IOException e) {
            throw new IllegalStateException("Runner unavailable; execution is never retried on the host", e);
        }
    }

    public Path download(String fileId, long maxBytes, long deadlineNanos) {
        Path file = null;
        try {
            file = Files.createTempFile("oj-output-", ".txt");
            Path target = file;
            long timeout = Math.max(1, Math.min(15000, (deadlineNanos - System.nanoTime()) / 1000000));
            HttpResponse<Path> response = http.send(request(filePath(fileId), timeout).GET().build(),
                    info -> new LimitedFileSubscriber(target, maxBytes, timeout));
            if (response.statusCode() != 200) throw new IOException("Runner file HTTP " + response.statusCode());
            return file;
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            deleteLocal(file);
            throw new IllegalStateException("Runner file request interrupted", e);
        } catch (IOException | RuntimeException e) {
            deleteLocal(file);
            throw new IllegalStateException("Cannot retrieve runner output", e);
        }
    }

    public void deleteFile(String fileId) {
        try {
            var response = http.send(request(filePath(fileId), 5000).DELETE().build(),
                    HttpResponse.BodyHandlers.discarding());
            if (response.statusCode() != 200 && response.statusCode() != 404) {
                throw new IOException("Runner delete HTTP " + response.statusCode());
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.warn("Runner file cleanup interrupted; configured runner file TTL must reclaim it");
        } catch (Exception e) {
            log.warn("Runner file cleanup failed; configured runner file TTL must reclaim it", e);
        }
    }

    public void deleteResultFiles(JSONObject result) {
        JSONObject ids = result.getJSONObject("fileIds");
        if (ids != null) ids.values().stream().map(Object::toString).distinct().forEach(this::deleteFile);
    }

    public static void deleteLocal(Path file) {
        if (file == null) return;
        try { Files.deleteIfExists(file); }
        catch (IOException e) { log.warn("Cannot delete local output preview file {}", file, e); }
    }

    private HttpRequest.Builder request(String path, long timeoutMillis) {
        HttpRequest.Builder builder = HttpRequest.newBuilder(
                URI.create(properties.getEndpoint().replaceAll("/+$", "") + path))
                .timeout(Duration.ofMillis(Math.max(1000, timeoutMillis)));
        if (!properties.getToken().isBlank()) builder.header("Authorization", "Bearer " + properties.getToken());
        return builder;
    }

    private String filePath(String id) {
        if (id == null || !id.matches("[A-Za-z0-9_-]+")) throw new IllegalArgumentException("Invalid runner file ID");
        return "/file/" + id;
    }

    /** Keeps the response incomplete until the stream finishes, so HTTP timeout covers the body too. */
    private static final class LimitedFileSubscriber implements HttpResponse.BodySubscriber<Path> {
        private final CompletableFuture<Path> completed = new CompletableFuture<>();
        private final Path file;
        private final long limit;
        private FileChannel output;
        private Flow.Subscription subscription;
        private long size;

        LimitedFileSubscriber(Path file, long limit, long timeoutMillis) {
            this.file = file;
            this.limit = limit;
            completed.orTimeout(timeoutMillis, java.util.concurrent.TimeUnit.MILLISECONDS)
                    .whenComplete((ignored, error) -> { if (error != null) fail(error); });
        }
        public CompletionStage<Path> getBody() { return completed; }
        public void onSubscribe(Flow.Subscription value) {
            subscription = value;
            try {
                output = FileChannel.open(file, StandardOpenOption.WRITE, StandardOpenOption.TRUNCATE_EXISTING);
                value.request(1);
            } catch (IOException e) { fail(e); }
        }
        public void onNext(List<ByteBuffer> buffers) {
            try {
                for (ByteBuffer buffer : buffers) {
                    size += buffer.remaining();
                    if (size > limit) throw new IOException("Runner output exceeds download limit");
                    while (buffer.hasRemaining()) output.write(buffer);
                }
                subscription.request(1);
            } catch (IOException e) { fail(e); }
        }
        public void onError(Throwable error) { fail(error); }
        public void onComplete() {
            try { if (output != null) output.close(); completed.complete(file); }
            catch (IOException e) { fail(e); }
        }
        private void fail(Throwable error) {
            if (subscription != null) subscription.cancel();
            try { if (output != null) output.close(); } catch (IOException ignored) { }
            completed.completeExceptionally(error);
        }
    }
}
