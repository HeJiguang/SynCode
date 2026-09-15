package com.sintao.runtime.security;

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
import io.jsonwebtoken.Claims;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletRequestWrapper;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.util.AntPathMatcher;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Enumeration;
import java.util.List;
import java.util.concurrent.TimeUnit;

@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 20)
public class CompactAuthFilter extends OncePerRequestFilter {

    private final CompactSecurityProperties properties;
    private final RedisService redisService;
    private final AntPathMatcher pathMatcher = new AntPathMatcher();

    @Value("${jwt.secret}")
    private String secret;

    public CompactAuthFilter(CompactSecurityProperties properties, RedisService redisService) {
        this.properties = properties;
        this.redisService = redisService;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        String path = request.getRequestURI();
        if (isPublic(path)) {
            filterChain.doFilter(new UserHeaderRequest(request, null, null), response);
            return;
        }

        String token = resolveToken(request);
        if (StrUtil.isBlank(token)) {
            writeUnauthorized(response, "token can not be empty");
            return;
        }

        Claims claims;
        try {
            claims = JwtUtils.parseToken(token, secret);
        } catch (Exception ignored) {
            writeUnauthorized(response, "token is invalid or expired");
            return;
        }
        if (claims == null) {
            writeUnauthorized(response, "token is invalid or expired");
            return;
        }

        String userKey = JwtUtils.getUserKey(claims);
        String userId = JwtUtils.getUserId(claims);
        if (StrUtil.hasBlank(userKey, userId)) {
            writeUnauthorized(response, "token payload is invalid");
            return;
        }

        String tokenKey = CacheConstants.LOGIN_TOKEN_KEY + userKey;
        LoginUser user = redisService.getCacheObject(tokenKey, LoginUser.class);
        if (user == null) {
            writeUnauthorized(response, "login status has expired");
            return;
        }
        if (path.startsWith("/system/") && !UserIdentity.ADMIN.getValue().equals(user.getIdentity())) {
            writeUnauthorized(response, "unauthorized");
            return;
        }
        if (path.startsWith("/friend/") && !UserIdentity.ORDINARY.getValue().equals(user.getIdentity())) {
            writeUnauthorized(response, "unauthorized");
            return;
        }

        extendToken(tokenKey);
        filterChain.doFilter(new UserHeaderRequest(request, userId, userKey), response);
    }

    private boolean isPublic(String path) {
        return properties.getPublicPaths().stream().anyMatch(pattern -> pathMatcher.match(pattern, path));
    }

    private String resolveToken(HttpServletRequest request) {
        String token = stripBearer(request.getHeader(HttpConstants.AUTHENTICATION));
        if (StrUtil.isBlank(token) && "websocket".equalsIgnoreCase(request.getHeader(HttpHeaders.UPGRADE))) {
            token = stripBearer(request.getParameter("token"));
        }
        return token;
    }

    private String stripBearer(String token) {
        if (StrUtil.isNotBlank(token) && token.startsWith(HttpConstants.PREFIX)) {
            return token.substring(HttpConstants.PREFIX.length());
        }
        return token;
    }

    private void extendToken(String tokenKey) {
        Long expire = redisService.getExpire(tokenKey, TimeUnit.MINUTES);
        if (expire != null && expire < CacheConstants.REFRESH_TIME) {
            redisService.expire(tokenKey, CacheConstants.EXP, TimeUnit.MINUTES);
        }
    }

    private void writeUnauthorized(HttpServletResponse response, String message) throws IOException {
        response.setStatus(HttpServletResponse.SC_OK);
        response.setCharacterEncoding(StandardCharsets.UTF_8.name());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.getWriter().write(JSON.toJSONString(
                R.fail(ResultCode.FAILED_UNAUTHORIZED.getCode(), message)
        ));
    }

    private static final class UserHeaderRequest extends HttpServletRequestWrapper {

        private final String userId;
        private final String userKey;

        private UserHeaderRequest(HttpServletRequest request, String userId, String userKey) {
            super(request);
            this.userId = userId;
            this.userKey = userKey;
        }

        @Override
        public String getHeader(String name) {
            if (HttpConstants.HEADER_USER_ID.equalsIgnoreCase(name)) {
                return userId;
            }
            if (HttpConstants.HEADER_USER_KEY.equalsIgnoreCase(name)) {
                return userKey;
            }
            return super.getHeader(name);
        }

        @Override
        public Enumeration<String> getHeaders(String name) {
            String value = getHeader(name);
            if (HttpConstants.HEADER_USER_ID.equalsIgnoreCase(name)
                    || HttpConstants.HEADER_USER_KEY.equalsIgnoreCase(name)) {
                return value == null
                        ? Collections.emptyEnumeration()
                        : Collections.enumeration(List.of(value));
            }
            return super.getHeaders(name);
        }

        @Override
        public Enumeration<String> getHeaderNames() {
            List<String> names = new ArrayList<>();
            Enumeration<String> original = super.getHeaderNames();
            while (original.hasMoreElements()) {
                String name = original.nextElement();
                if (!HttpConstants.HEADER_USER_ID.equalsIgnoreCase(name)
                        && !HttpConstants.HEADER_USER_KEY.equalsIgnoreCase(name)) {
                    names.add(name);
                }
            }
            if (userId != null) {
                names.add(HttpConstants.HEADER_USER_ID);
            }
            if (userKey != null) {
                names.add(HttpConstants.HEADER_USER_KEY);
            }
            return Collections.enumeration(names);
        }
    }
}
