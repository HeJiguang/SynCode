package com.sintao.gateway.config;

import com.sintao.gateway.properties.AiRouteProperties;
import org.springframework.cloud.gateway.route.RouteLocator;
import org.springframework.cloud.gateway.route.builder.RouteLocatorBuilder;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.util.StringUtils;

@Configuration
public class AiRouteConfig {

    @Bean
    public RouteLocator aiRouteLocator(RouteLocatorBuilder builder, AiRouteProperties properties) {
        if (Boolean.FALSE.equals(properties.getRouteEnabled()) || !StringUtils.hasText(properties.getUri())) {
            return builder.routes().build();
        }

        String publicPrefix = normalizePrefix(properties.getPublicPrefix(), "/ai");
        String targetPrefix = normalizePrefix(properties.getTargetPrefix(), "/api");

        return builder.routes()
                .route("oj-agent-route", route -> route
                        .path(publicPrefix, publicPrefix + "/**")
                        .filters(filter -> filter.rewritePath(
                                publicPrefix + "/(?<segment>.*)",
                                targetPrefix + "/${segment}"
                        ))
                        .uri(properties.getUri()))
                .build();
    }

    private String normalizePrefix(String raw, String fallback) {
        if (!StringUtils.hasText(raw)) {
            return fallback;
        }
        return raw.startsWith("/") ? raw : "/" + raw;
    }
}
