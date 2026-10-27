package com.sintao.judge.sandbox;

import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.sintao.judge.config.GoJudgeProperties;
import com.sun.net.httpserver.HttpServer;
import org.junit.jupiter.api.Test;
import java.net.InetSocketAddress;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import static org.junit.jupiter.api.Assertions.*;

class GoJudgeClientTest {
    @Test void speaksRestArrayProtocolDownloadsBoundedFileAndDeletesIt() throws Exception {
        HttpServer server = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
        AtomicReference<JSONObject> body = new AtomicReference<>();
        AtomicReference<String> auth = new AtomicReference<>();
        AtomicReference<String> deleted = new AtomicReference<>();
        server.createContext("/run", exchange -> {
            body.set(JSON.parseObject(exchange.getRequestBody().readAllBytes()));
            auth.set(exchange.getRequestHeaders().getFirst("Authorization"));
            byte[] bytes = "[{\"status\":\"Accepted\",\"fileIds\":{\"stdout\":\"out1\"}}]".getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(200, bytes.length);
            try (var output = exchange.getResponseBody()) { output.write(bytes); }
        });
        server.createContext("/file/out1", exchange -> {
            if ("DELETE".equals(exchange.getRequestMethod())) deleted.set("out1");
            byte[] bytes = "  answer\n".getBytes(StandardCharsets.UTF_8);
            exchange.sendResponseHeaders(200, bytes.length);
            try (var output = exchange.getResponseBody()) { output.write(bytes); }
        });
        server.start();
        try {
            GoJudgeProperties properties = new GoJudgeProperties();
            properties.setEndpoint("http://127.0.0.1:" + server.getAddress().getPort());
            properties.setToken("test-token");
            GoJudgeClient client = new GoJudgeClient(properties);
            var result = client.run(Map.of("args", new String[]{"/usr/bin/java"}), 1000);
            assertEquals("Accepted", result.getString("status"));
            assertEquals(1, body.get().getJSONArray("cmd").size());
            assertEquals("Bearer test-token", auth.get());
            var file = client.download("out1", 100, System.nanoTime() + TimeUnit.SECONDS.toNanos(5));
            try { assertEquals("  answer\n", Files.readString(file)); }
            finally { GoJudgeClient.deleteLocal(file); }
            assertThrows(IllegalStateException.class,
                    () -> client.download("out1", 3, System.nanoTime() + TimeUnit.SECONDS.toNanos(5)));
            client.deleteResultFiles(result);
            assertEquals("out1", deleted.get());
        } finally { server.stop(0); }
    }
}
