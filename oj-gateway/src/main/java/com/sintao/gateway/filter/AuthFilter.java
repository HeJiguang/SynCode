package com.sintao.gateway.filter;

import cn.hutool.core.util.StrUtil;
import com.alibaba.fastjson2.JSON;
import com.sintao.common.core.constants.CacheConstants;
import com.sintao.common.core.constants.HttpConstants;
import com.sintao.common.core.domain.LoginUser;
import com.sintao.common.core.domain.R;
import com.sintao.common.core.enums.ResultCode;
import com.sintao.common.core.enums.UserIdentity;
import com.sintao.common.core.utils.JwtUtils;
import com.sintao.common.redis.service.RedisService;
import com.sintao.gateway.properties.IgnoreWhiteProperties;
import io.jsonwebtoken.Claims;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.cloud.gateway.filter.GatewayFilterChain;
import org.springframework.cloud.gateway.filter.GlobalFilter;
import org.springframework.core.Ordered;
import org.springframework.core.io.buffer.DataBuffer;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.server.reactive.ServerHttpRequest;
import org.springframework.http.server.reactive.ServerHttpResponse;
import org.springframework.stereotype.Component;
import org.springframework.util.AntPathMatcher;
import org.springframework.util.CollectionUtils;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.List;

@Slf4j
@Component
public class AuthFilter implements GlobalFilter, Ordered {

    private static final List<String> BUILT_IN_PUBLIC_PATHS = Arrays.asList(
            "/system/sysUser/login",
            "/friend/message/semiLogin/**"
    );

    @Autowired
    private IgnoreWhiteProperties ignoreWhite;

    @Value("${jwt.secret}")
    private String secret;

    @Autowired
    private RedisService redisService;

    @Override
    public Mono<Void> filter(ServerWebExchange exchange, GatewayFilterChain chain) {
        ServerHttpRequest request = exchange.getRequest();
        String url = request.getURI().getPath();

        if (matches(url, ignoreWhite.getWhites()) || matches(url, BUILT_IN_PUBLIC_PATHS)) {
            return chain.filter(exchange);
        }

        String token = getToken(request);
        if (StrUtil.isBlank(token)) {
            return unauthorizedResponse(exchange, "token can not be empty");
        }

        Claims claims;
        try {
            claims = JwtUtils.parseToken(token, secret);
        } catch (Exception ex) {
            log.warn("parse token failed, path={}", url, ex);
            return unauthorizedResponse(exchange, "token is invalid or expired");
        }
        if (claims == null) {
            return unauthorizedResponse(exchange, "token is invalid or expired");
        }

        String userKey = JwtUtils.getUserKey(claims);
        String userId = JwtUtils.getUserId(claims);
        if (StrUtil.hasBlank(userKey, userId)) {
            return unauthorizedResponse(exchange, "token payload is invalid");
        }

        String tokenKey = getTokenKey(userKey);
        Boolean hasLoginState = redisService.hasKey(tokenKey);
        if (!Boolean.TRUE.equals(hasLoginState)) {
            log.warn("auth redis miss, path={}, userId={}, userKey={}, tokenKey={}", url, userId, userKey, tokenKey);
            return unauthorizedResponse(exchange, "login status has expired");
        }

        LoginUser user = redisService.getCacheObject(tokenKey, LoginUser.class);
        if (user == null) {
            log.warn("auth redis hit but login user is null, path={}, userId={}, userKey={}, tokenKey={}",
                    url, userId, userKey, tokenKey);
            return unauthorizedResponse(exchange, "login status has expired");
        }

        if (url.contains(HttpConstants.SYSTEM_URL_PREFIX)
                && !UserIdentity.ADMIN.getValue().equals(user.getIdentity())) {
            return unauthorizedResponse(exchange, "unauthorized");
        }
        if (url.contains(HttpConstants.FRIEND_URL_PREFIX)
                && !UserIdentity.ORDINARY.getValue().equals(user.getIdentity())) {
            return unauthorizedResponse(exchange, "unauthorized");
        }

        // 【网关统一鉴权透传】将解析后的用户信息注入请求头，传递给下游微服务
        ServerHttpRequest mutatedRequest = exchange.getRequest().mutate()
                .header(HttpConstants.HEADER_USER_ID, userId)
                .header(HttpConstants.HEADER_USER_KEY, userKey)
                .build();
        ServerWebExchange mutatedExchange = exchange.mutate().request(mutatedRequest).build();

        // 【网关统一续期】在网关层完成 Token 续期，下游微服务无需关心
        extendToken(tokenKey);

        return chain.filter(mutatedExchange);
    }

    private boolean matches(String url, List<String> patternList) {
        if (StrUtil.isBlank(url) || CollectionUtils.isEmpty(patternList)) {
            return false;
        }
        for (String pattern : patternList) {
            if (isMatch(pattern, url)) {
                return true;
            }
        }
        return false;
    }

    private boolean isMatch(String pattern, String url) {
        return new AntPathMatcher().match(pattern, url);
    }

    private String getTokenKey(String token) {
        return CacheConstants.LOGIN_TOKEN_KEY + token;
    }

    /**
     * 网关层统一续期：当 Redis 中的登录态剩余时间低于阈值时，自动延长有效期。
     * 此职责原先由下游微服务的 TokenInterceptor 承担，现已统一收归网关处理。
     */
    private void extendToken(String tokenKey) {
        Long expire = redisService.getExpire(tokenKey, java.util.concurrent.TimeUnit.MINUTES);
        if (expire != null && expire < CacheConstants.REFRESH_TIME) {
            redisService.expire(tokenKey, CacheConstants.EXP, java.util.concurrent.TimeUnit.MINUTES);
        }
    }

    private String getToken(ServerHttpRequest request) {
        String token = request.getHeaders().getFirst(HttpConstants.AUTHENTICATION);
        if (StrUtil.isNotEmpty(token) && token.startsWith(HttpConstants.PREFIX)) {
            token = token.replaceFirst(HttpConstants.PREFIX, StrUtil.EMPTY);
        }
        if (StrUtil.isBlank(token) && isWebSocketHandshake(request)) {
            token = request.getQueryParams().getFirst("token");
            if (StrUtil.isNotEmpty(token) && token.startsWith(HttpConstants.PREFIX)) {
                token = token.replaceFirst(HttpConstants.PREFIX, StrUtil.EMPTY);
            }
        }
        return token;
    }

    private boolean isWebSocketHandshake(ServerHttpRequest request) {
        String upgrade = request.getHeaders().getFirst(HttpHeaders.UPGRADE);
        if (StrUtil.isBlank(upgrade)) {
            return false;
        }
        return "websocket".equalsIgnoreCase(upgrade);
    }

    private Mono<Void> unauthorizedResponse(ServerWebExchange exchange, String msg) {
        log.error("auth failed, path={}", exchange.getRequest().getPath());
        return webFluxResponseWriter(
                exchange.getResponse(),
                msg,
                ResultCode.FAILED_UNAUTHORIZED.getCode()
        );
    }

    private Mono<Void> webFluxResponseWriter(ServerHttpResponse response, String msg, int code) {
        response.setStatusCode(HttpStatus.OK);
        response.getHeaders().add(HttpHeaders.CONTENT_TYPE, MediaType.APPLICATION_JSON_VALUE);
        R<?> result = R.fail(code, msg);
        DataBuffer dataBuffer = response
                .bufferFactory()
                .wrap(JSON.toJSONString(result).getBytes(StandardCharsets.UTF_8));
        return response.writeWith(Mono.just(dataBuffer));
    }

    @Override
    public int getOrder() {
        return -200;
    }
}
