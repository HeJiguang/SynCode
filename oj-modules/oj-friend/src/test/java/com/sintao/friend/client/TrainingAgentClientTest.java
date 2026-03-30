package com.sintao.friend.client;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sintao.friend.client.dto.AgentTrainingPlanResponse;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.cloud.client.ServiceInstance;
import org.springframework.cloud.client.discovery.DiscoveryClient;
import org.springframework.test.util.ReflectionTestUtils;

import java.io.IOException;
import java.net.Authenticator;
import java.net.CookieHandler;
import java.net.ProxySelector;
import java.time.LocalDateTime;
import java.time.Duration;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpHeaders;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.http.HttpTimeoutException;
import java.security.SecureRandom;
import java.security.cert.X509Certificate;
import java.util.List;
import java.util.Optional;
import java.util.concurrent.Executor;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.LongConsumer;
import java.util.function.LongSupplier;

import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLParameters;
import javax.net.ssl.SSLSession;
import javax.net.ssl.TrustManager;
import javax.net.ssl.X509TrustManager;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class TrainingAgentClientTest {

    private static final String SUCCESS_PAYLOAD = """
            {
              "current_level": "starter",
              "target_direction": "algorithm_foundation",
              "weak_points": "binary search timing",
              "strong_points": "array basics",
              "plan_title": "Starter Recovery Cycle",
              "plan_goal": "Rebuild stability.",
              "ai_summary": "Keep the cycle tight.",
              "tasks": []
            }
            """;

    private TrainingAgentClient client;

    @BeforeEach
    void setUp() {
        client = new TrainingAgentClient();
        ReflectionTestUtils.setField(client, "baseUrl", "http://127.0.0.1:8000");
        ReflectionTestUtils.setField(client, "planPath", "/api/training/plan");
        ReflectionTestUtils.setField(client, "serviceId", "oj-agent");
    }

    @Test
    void objectMapperShouldDeserializeDueTimeAndIgnoreFutureFields() throws Exception {
        String payload = """
                {
                  "current_level": "starter",
                  "target_direction": "algorithm_foundation",
                  "weak_points": "binary search timing",
                  "strong_points": "array basics",
                  "plan_title": "Starter Recovery Cycle",
                  "plan_goal": "Rebuild stability.",
                  "ai_summary": "Keep the cycle tight.",
                  "future_summary_hint": "ignore me",
                  "tasks": [
                    {
                      "task_type": "test",
                      "exam_id": 9001,
                      "title_snapshot": "Binary Search Checkpoint",
                      "task_order": 3,
                      "recommended_reason": "Check the current rhythm.",
                      "knowledge_tags_snapshot": "binary search",
                      "due_time": "2026-03-26T10:30:00",
                      "priority_score": 0.93
                    }
                  ]
                }
                """;

        ObjectMapper objectMapper = (ObjectMapper) ReflectionTestUtils.getField(TrainingAgentClient.class, "OBJECT_MAPPER");

        AgentTrainingPlanResponse response = objectMapper.readValue(payload, AgentTrainingPlanResponse.class);

        assertEquals("Starter Recovery Cycle", response.getPlanTitle());
        assertEquals(1, response.getTasks().size());
        assertNotNull(response.getTasks().get(0).getDueTime());
        assertEquals(LocalDateTime.of(2026, 3, 26, 10, 30), response.getTasks().get(0).getDueTime());
    }

    @Test
    void resolvePlanUrlShouldUseDiscoveryClientWhenExplicitBaseUrlIsBlank() {
        ReflectionTestUtils.setField(client, "baseUrl", "");
        ReflectionTestUtils.setField(client, "planPath", "/api/training/plan");
        ReflectionTestUtils.setField(client, "serviceId", "oj-agent");
        ReflectionTestUtils.setField(client, "discoveryClient", new DiscoveryClient() {
            @Override
            public String description() {
                return "test-discovery";
            }

            @Override
            public List<ServiceInstance> getInstances(String serviceId) {
                return List.of(new ServiceInstance() {
                    @Override
                    public String getServiceId() {
                        return "oj-agent";
                    }

                    @Override
                    public String getHost() {
                        return "127.0.0.1";
                    }

                    @Override
                    public int getPort() {
                        return 8000;
                    }

                    @Override
                    public boolean isSecure() {
                        return false;
                    }

                    @Override
                    public URI getUri() {
                        return URI.create("http://127.0.0.1:8000");
                    }

                    @Override
                    public java.util.Map<String, String> getMetadata() {
                        return java.util.Collections.emptyMap();
                    }
                });
            }

            @Override
            public List<String> getServices() {
                return List.of("oj-agent");
            }
        });

        String planUrl = (String) ReflectionTestUtils.invokeMethod(client, "resolvePlanUrl");

        assertEquals("http://127.0.0.1:8000/api/training/plan", planUrl);
    }

    @Test
    void generatePlanShouldRetryTransientFailuresBeforeSucceeding() {
        AtomicInteger attempts = new AtomicInteger();
        setResilienceFields(client, 3, 0, 5, 30_000, 10);
        ReflectionTestUtils.setField(client, "httpClient", new StubHttpClient(request -> {
            int currentAttempt = attempts.incrementAndGet();
            if (currentAttempt < 3) {
                throw new HttpTimeoutException("agent timeout");
            }
            return new StubHttpResponse(200, SUCCESS_PAYLOAD, request);
        }));
        ReflectionTestUtils.setField(client, "sleepFunction", (LongConsumer) millis -> {
        });
        ReflectionTestUtils.setField(client, "currentTimeMillisSupplier", (LongSupplier) () -> 1_000L);

        AgentTrainingPlanResponse response = client.generatePlan(new com.sintao.friend.client.dto.AgentTrainingPlanRequest());

        assertEquals(3, attempts.get());
        assertEquals("Starter Recovery Cycle", response.getPlanTitle());
    }

    @Test
    void generatePlanShouldOpenCircuitAfterRepeatedFailures() {
        AtomicInteger attempts = new AtomicInteger();
        setResilienceFields(client, 1, 0, 1, 30_000, 10);
        ReflectionTestUtils.setField(client, "httpClient", new StubHttpClient(request -> {
            attempts.incrementAndGet();
            throw new IOException("agent unavailable");
        }));
        ReflectionTestUtils.setField(client, "sleepFunction", (LongConsumer) millis -> {
        });
        ReflectionTestUtils.setField(client, "currentTimeMillisSupplier", (LongSupplier) () -> 2_000L);

        assertThrows(IllegalStateException.class,
                () -> client.generatePlan(new com.sintao.friend.client.dto.AgentTrainingPlanRequest()));
        IllegalStateException circuitOpen = assertThrows(IllegalStateException.class,
                () -> client.generatePlan(new com.sintao.friend.client.dto.AgentTrainingPlanRequest()));

        assertEquals(1, attempts.get());
        assertTrue(circuitOpen.getMessage().contains("circuit breaker"));
    }

    @Test
    void generatePlanShouldRejectRequestsWhenRateLimitWindowIsExceeded() {
        AtomicInteger attempts = new AtomicInteger();
        setResilienceFields(client, 1, 0, 5, 30_000, 1);
        ReflectionTestUtils.setField(client, "httpClient", new StubHttpClient(request -> {
            attempts.incrementAndGet();
            return new StubHttpResponse(200, SUCCESS_PAYLOAD, request);
        }));
        ReflectionTestUtils.setField(client, "sleepFunction", (LongConsumer) millis -> {
        });
        ReflectionTestUtils.setField(client, "currentTimeMillisSupplier", (LongSupplier) () -> 3_000L);

        client.generatePlan(new com.sintao.friend.client.dto.AgentTrainingPlanRequest());
        IllegalStateException exceeded = assertThrows(IllegalStateException.class,
                () -> client.generatePlan(new com.sintao.friend.client.dto.AgentTrainingPlanRequest()));

        assertEquals(1, attempts.get());
        assertTrue(exceeded.getMessage().contains("rate limit"));
    }

    private void setResilienceFields(TrainingAgentClient client,
                                     int maxAttempts,
                                     long retryBackoffMillis,
                                     int circuitFailureThreshold,
                                     long circuitOpenMillis,
                                     int rateLimitPerMinute) {
        ReflectionTestUtils.setField(client, "maxAttempts", maxAttempts);
        ReflectionTestUtils.setField(client, "retryBackoffMillis", retryBackoffMillis);
        ReflectionTestUtils.setField(client, "circuitFailureThreshold", circuitFailureThreshold);
        ReflectionTestUtils.setField(client, "circuitOpenMillis", circuitOpenMillis);
        ReflectionTestUtils.setField(client, "rateLimitPerMinute", rateLimitPerMinute);
        ReflectionTestUtils.setField(client, "connectTimeoutMillis", 1_000L);
        ReflectionTestUtils.setField(client, "requestTimeoutMillis", 3_000L);
    }

    @FunctionalInterface
    private interface StubResponder {
        HttpResponse<String> respond(HttpRequest request) throws Exception;
    }

    private static final class StubHttpClient extends HttpClient {

        private final StubResponder responder;

        private StubHttpClient(StubResponder responder) {
            this.responder = responder;
        }

        @Override
        public Optional<CookieHandler> cookieHandler() {
            return Optional.empty();
        }

        @Override
        public Optional<Duration> connectTimeout() {
            return Optional.of(Duration.ofSeconds(1));
        }

        @Override
        public Redirect followRedirects() {
            return Redirect.NEVER;
        }

        @Override
        public Optional<ProxySelector> proxy() {
            return Optional.empty();
        }

        @Override
        public SSLContext sslContext() {
            try {
                TrustManager[] trustAll = new TrustManager[]{
                        new X509TrustManager() {
                            @Override
                            public void checkClientTrusted(X509Certificate[] chain, String authType) {
                            }

                            @Override
                            public void checkServerTrusted(X509Certificate[] chain, String authType) {
                            }

                            @Override
                            public X509Certificate[] getAcceptedIssuers() {
                                return new X509Certificate[0];
                            }
                        }
                };
                SSLContext context = SSLContext.getInstance("TLS");
                context.init(null, trustAll, new SecureRandom());
                return context;
            } catch (Exception e) {
                throw new IllegalStateException(e);
            }
        }

        @Override
        public SSLParameters sslParameters() {
            return new SSLParameters();
        }

        @Override
        public Optional<Authenticator> authenticator() {
            return Optional.empty();
        }

        @Override
        public Version version() {
            return Version.HTTP_1_1;
        }

        @Override
        public Optional<Executor> executor() {
            return Optional.empty();
        }

        @Override
        public <T> HttpResponse<T> send(HttpRequest request, HttpResponse.BodyHandler<T> responseBodyHandler)
                throws IOException, InterruptedException {
            try {
                @SuppressWarnings("unchecked")
                HttpResponse<T> response = (HttpResponse<T>) responder.respond(request);
                return response;
            } catch (IOException e) {
                throw e;
            } catch (InterruptedException e) {
                throw e;
            } catch (Exception e) {
                throw new IllegalStateException(e);
            }
        }

        @Override
        public <T> java.util.concurrent.CompletableFuture<HttpResponse<T>> sendAsync(
                HttpRequest request,
                HttpResponse.BodyHandler<T> responseBodyHandler) {
            throw new UnsupportedOperationException("Not needed in tests");
        }

        @Override
        public <T> java.util.concurrent.CompletableFuture<HttpResponse<T>> sendAsync(
                HttpRequest request,
                HttpResponse.BodyHandler<T> responseBodyHandler,
                HttpResponse.PushPromiseHandler<T> pushPromiseHandler) {
            throw new UnsupportedOperationException("Not needed in tests");
        }
    }

    private record StubHttpResponse(int statusCode, String body, HttpRequest request) implements HttpResponse<String> {
        @Override
        public int statusCode() {
            return statusCode;
        }

        @Override
        public HttpRequest request() {
            return request;
        }

        @Override
        public Optional<HttpResponse<String>> previousResponse() {
            return Optional.empty();
        }

        @Override
        public HttpHeaders headers() {
            return HttpHeaders.of(java.util.Map.of(), (name, value) -> true);
        }

        @Override
        public String body() {
            return body;
        }

        @Override
        public Optional<SSLSession> sslSession() {
            return Optional.empty();
        }

        @Override
        public URI uri() {
            return request.uri();
        }

        @Override
        public HttpClient.Version version() {
            return HttpClient.Version.HTTP_1_1;
        }
    }
}
