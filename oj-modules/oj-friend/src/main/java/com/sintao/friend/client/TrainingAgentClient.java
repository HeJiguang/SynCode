package com.sintao.friend.client;

import com.fasterxml.jackson.databind.DeserializationFeature;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.json.JsonMapper;
import com.sintao.friend.client.dto.AgentTrainingPlanRequest;
import com.sintao.friend.client.dto.AgentTrainingPlanResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.client.ServiceInstance;
import org.springframework.cloud.client.discovery.DiscoveryClient;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.util.StringUtils;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.List;
import java.util.function.LongConsumer;
import java.util.function.LongSupplier;

@Component
public class TrainingAgentClient {

    private static final ObjectMapper OBJECT_MAPPER = JsonMapper.builder()
            .findAndAddModules()
            .disable(DeserializationFeature.FAIL_ON_UNKNOWN_PROPERTIES)
            .build();

    private HttpClient httpClient;

    private LongSupplier currentTimeMillisSupplier = System::currentTimeMillis;

    private LongConsumer sleepFunction = millis -> {
        try {
            Thread.sleep(millis);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("Training agent retry sleep interrupted", e);
        }
    };

    private final Object circuitMonitor = new Object();

    private int consecutiveFailureCount;

    private long circuitOpenedAtMillis = -1L;

    private final Object rateLimitMonitor = new Object();

    private long rateWindowStartMillis = -1L;

    private int rateWindowCount;

    @Value("${training.agent.base-url:}")
    private String baseUrl;

    @Value("${training.agent.service-id:oj-agent}")
    private String serviceId;

    @Value("${training.agent.plan-path:/api/training/plan}")
    private String planPath;

    @Value("${training.agent.client.connect-timeout-ms:1000}")
    private long connectTimeoutMillis;

    @Value("${training.agent.client.request-timeout-ms:5000}")
    private long requestTimeoutMillis;

    @Value("${training.agent.client.max-attempts:3}")
    private int maxAttempts;

    @Value("${training.agent.client.retry-backoff-ms:200}")
    private long retryBackoffMillis;

    @Value("${training.agent.client.circuit-failure-threshold:5}")
    private int circuitFailureThreshold;

    @Value("${training.agent.client.circuit-open-ms:30000}")
    private long circuitOpenMillis;

    @Value("${training.agent.client.rate-limit-per-minute:60}")
    private int rateLimitPerMinute;

    @Autowired(required = false)
    private DiscoveryClient discoveryClient;

    public AgentTrainingPlanResponse generatePlan(AgentTrainingPlanRequest request) {
        long now = currentTimeMillisSupplier.getAsLong();
        assertCircuitClosed(now);
        acquireRateLimit(now);

        Exception lastFailure = null;
        int attemptLimit = Math.max(1, maxAttempts);
        try {
            for (int attempt = 1; attempt <= attemptLimit; attempt++) {
                try {
                    HttpResponse<String> response = sendRequest(request);
                    if (response.statusCode() >= 200 && response.statusCode() < 300) {
                        onInvocationSuccess();
                        return OBJECT_MAPPER.readValue(response.body(), AgentTrainingPlanResponse.class);
                    }
                    IllegalStateException statusFailure = new IllegalStateException(
                            "Training agent returned HTTP " + response.statusCode() + ": " + response.body()
                    );
                    if (!isRetryableStatus(response.statusCode()) || attempt == attemptLimit) {
                        lastFailure = statusFailure;
                        break;
                    }
                    lastFailure = statusFailure;
                    backoffBeforeRetry(attempt);
                } catch (Exception e) {
                    if (e instanceof InterruptedException) {
                        Thread.currentThread().interrupt();
                        lastFailure = e;
                        break;
                    }
                    if (!isRetryableException(e) || attempt == attemptLimit) {
                        lastFailure = e;
                        break;
                    }
                    lastFailure = e;
                    backoffBeforeRetry(attempt);
                }
            }
        } catch (RuntimeException e) {
            onInvocationFailure(now);
            throw e;
        }

        onInvocationFailure(now);
        throw new IllegalStateException("Failed to call training agent", lastFailure);
    }

    private HttpResponse<String> sendRequest(AgentTrainingPlanRequest request) throws IOException, InterruptedException {
        HttpRequest httpRequest = HttpRequest.newBuilder()
                .uri(URI.create(resolvePlanUrl()))
                .timeout(Duration.ofMillis(Math.max(1L, requestTimeoutMillis)))
                .header("Content-Type", MediaType.APPLICATION_JSON_VALUE)
                .header("Accept", MediaType.APPLICATION_JSON_VALUE)
                .POST(HttpRequest.BodyPublishers.ofString(
                        OBJECT_MAPPER.writeValueAsString(request),
                        StandardCharsets.UTF_8
                ))
                .build();

        return getOrCreateHttpClient().send(httpRequest, HttpResponse.BodyHandlers.ofString(StandardCharsets.UTF_8));
    }

    private HttpClient getOrCreateHttpClient() {
        if (httpClient != null) {
            return httpClient;
        }
        synchronized (this) {
            if (httpClient == null) {
                httpClient = HttpClient.newBuilder()
                        .version(HttpClient.Version.HTTP_1_1)
                        .connectTimeout(Duration.ofMillis(Math.max(1L, connectTimeoutMillis)))
                        .build();
            }
            return httpClient;
        }
    }

    private void backoffBeforeRetry(int attempt) {
        if (retryBackoffMillis <= 0) {
            return;
        }
        sleepFunction.accept(retryBackoffMillis * attempt);
    }

    private boolean isRetryableException(Exception exception) {
        return exception instanceof IOException;
    }

    private boolean isRetryableStatus(int statusCode) {
        return statusCode == 429 || statusCode >= 500;
    }

    private void assertCircuitClosed(long now) {
        synchronized (circuitMonitor) {
            if (circuitOpenedAtMillis < 0) {
                return;
            }
            if (now - circuitOpenedAtMillis >= circuitOpenMillis) {
                circuitOpenedAtMillis = -1L;
                consecutiveFailureCount = 0;
                return;
            }
            throw new IllegalStateException("Training agent circuit breaker is open");
        }
    }

    private void onInvocationSuccess() {
        synchronized (circuitMonitor) {
            consecutiveFailureCount = 0;
            circuitOpenedAtMillis = -1L;
        }
    }

    private void onInvocationFailure(long now) {
        synchronized (circuitMonitor) {
            consecutiveFailureCount++;
            if (consecutiveFailureCount >= Math.max(1, circuitFailureThreshold)) {
                circuitOpenedAtMillis = now;
            }
        }
    }

    private void acquireRateLimit(long now) {
        if (rateLimitPerMinute <= 0) {
            return;
        }
        synchronized (rateLimitMonitor) {
            if (rateWindowStartMillis < 0 || now - rateWindowStartMillis >= 60_000L) {
                rateWindowStartMillis = now;
                rateWindowCount = 0;
            }
            if (rateWindowCount >= rateLimitPerMinute) {
                throw new IllegalStateException("Training agent client rate limit exceeded");
            }
            rateWindowCount++;
        }
    }

    private String resolvePlanUrl() {
        String resolvedBaseUrl = resolveBaseUrl();
        if (resolvedBaseUrl.endsWith("/") && planPath.startsWith("/")) {
            return resolvedBaseUrl.substring(0, resolvedBaseUrl.length() - 1) + planPath;
        }
        if (!resolvedBaseUrl.endsWith("/") && !planPath.startsWith("/")) {
            return resolvedBaseUrl + "/" + planPath;
        }
        return resolvedBaseUrl + planPath;
    }

    private String resolveBaseUrl() {
        if (StringUtils.hasText(baseUrl)) {
            return baseUrl.trim();
        }
        if (discoveryClient == null) {
            throw new IllegalStateException("Training agent base-url is blank and DiscoveryClient is unavailable");
        }
        List<ServiceInstance> instances = discoveryClient.getInstances(serviceId);
        if (instances == null || instances.isEmpty()) {
            throw new IllegalStateException("No available training agent instance for serviceId=" + serviceId);
        }
        String serviceUri = instances.get(0).getUri().toString();
        if (!StringUtils.hasText(serviceUri)) {
            throw new IllegalStateException("Resolved training agent instance has an empty URI");
        }
        return serviceUri;
    }
}
