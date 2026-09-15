package com.sintao.runtime.security;

import com.sintao.common.core.constants.CacheConstants;
import com.sintao.common.core.constants.HttpConstants;
import com.sintao.common.core.constants.JwtConstants;
import com.sintao.common.core.domain.LoginUser;
import com.sintao.common.core.enums.ResultCode;
import com.sintao.common.core.enums.UserIdentity;
import com.sintao.common.core.utils.JwtUtils;
import com.sintao.common.redis.service.RedisService;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletRequest;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockFilterChain;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.mock.web.MockHttpServletResponse;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.HashMap;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class CompactAuthFilterTest {

    private static final String SECRET = "compact-runtime-test-secret";

    private RedisService redisService;
    private CompactAuthFilter filter;

    @BeforeEach
    void setUp() {
        redisService = mock(RedisService.class);
        filter = new CompactAuthFilter(new CompactSecurityProperties(), redisService);
        ReflectionTestUtils.setField(filter, "secret", SECRET);
    }

    @Test
    void rejectsMissingToken() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/friend/user/info");
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getStatus()).isEqualTo(200);
        assertThat(response.getContentAsString()).contains(String.valueOf(ResultCode.FAILED_UNAUTHORIZED.getCode()));
    }

    @Test
    void stripsSpoofedHeadersOnPublicRequest() throws Exception {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/friend/question/semiLogin/list");
        request.addHeader(HttpConstants.HEADER_USER_ID, "999");
        request.addHeader(HttpConstants.HEADER_USER_KEY, "spoofed");
        AtomicReference<ServletRequest> forwarded = new AtomicReference<>();
        FilterChain chain = (req, res) -> forwarded.set(req);

        filter.doFilter(request, new MockHttpServletResponse(), chain);

        jakarta.servlet.http.HttpServletRequest sanitized =
                (jakarta.servlet.http.HttpServletRequest) forwarded.get();
        assertThat(sanitized.getHeader(HttpConstants.HEADER_USER_ID)).isNull();
        assertThat(sanitized.getHeader(HttpConstants.HEADER_USER_KEY)).isNull();
    }

    @Test
    void injectsValidatedIdentityAndRenewsSession() throws Exception {
        String userKey = "session-key";
        String token = token("42", userKey);
        LoginUser loginUser = new LoginUser();
        loginUser.setIdentity(UserIdentity.ORDINARY.getValue());
        String tokenKey = CacheConstants.LOGIN_TOKEN_KEY + userKey;
        when(redisService.getCacheObject(tokenKey, LoginUser.class)).thenReturn(loginUser);
        when(redisService.getExpire(tokenKey, TimeUnit.MINUTES)).thenReturn(1L);

        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/friend/user/info");
        request.addHeader(HttpConstants.AUTHENTICATION, HttpConstants.PREFIX + token);
        request.addHeader(HttpConstants.HEADER_USER_ID, "999");
        AtomicReference<ServletRequest> forwarded = new AtomicReference<>();
        FilterChain chain = (req, res) -> forwarded.set(req);

        filter.doFilter(request, new MockHttpServletResponse(), chain);

        jakarta.servlet.http.HttpServletRequest authenticated =
                (jakarta.servlet.http.HttpServletRequest) forwarded.get();
        assertThat(authenticated.getHeader(HttpConstants.HEADER_USER_ID)).isEqualTo("42");
        assertThat(authenticated.getHeader(HttpConstants.HEADER_USER_KEY)).isEqualTo(userKey);
        verify(redisService).expire(tokenKey, CacheConstants.EXP, TimeUnit.MINUTES);
    }

    @Test
    void enforcesSystemRole() throws Exception {
        String userKey = "candidate-session";
        LoginUser loginUser = new LoginUser();
        loginUser.setIdentity(UserIdentity.ORDINARY.getValue());
        when(redisService.getCacheObject(CacheConstants.LOGIN_TOKEN_KEY + userKey, LoginUser.class))
                .thenReturn(loginUser);
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/system/exam/list");
        request.addHeader(HttpConstants.AUTHENTICATION, token("7", userKey));
        MockHttpServletResponse response = new MockHttpServletResponse();

        filter.doFilter(request, response, new MockFilterChain());

        assertThat(response.getContentAsString()).contains("unauthorized");
    }

    private String token(String userId, String userKey) {
        Map<String, Object> claims = new HashMap<>();
        claims.put(JwtConstants.LOGIN_USER_ID, userId);
        claims.put(JwtConstants.LOGIN_USER_KEY, userKey);
        return JwtUtils.createToken(claims, SECRET);
    }
}
