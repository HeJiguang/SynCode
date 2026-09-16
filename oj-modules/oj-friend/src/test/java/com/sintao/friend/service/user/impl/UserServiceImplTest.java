package com.sintao.friend.service.user.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.sintao.common.message.service.MailService;
import com.sintao.common.redis.service.RedisService;
import com.sintao.common.security.service.TokenService;
import com.sintao.friend.domain.user.User;
import com.sintao.friend.domain.user.dto.UserDTO;
import com.sintao.friend.manager.UserCacheManager;
import com.sintao.friend.mapper.user.UserMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.assertDoesNotThrow;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class UserServiceImplTest {

    @Mock
    private UserMapper userMapper;

    @Mock
    private TokenService tokenService;

    @Mock
    private MailService mailService;

    @Mock
    private RedisService redisService;

    @Mock
    private UserCacheManager userCacheManager;

    @InjectMocks
    private UserServiceImpl userService;

    @BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(userService, "emailCodeExpiration", 5L);
        ReflectionTestUtils.setField(userService, "sendLimit", 3);
        ReflectionTestUtils.setField(userService, "isSend", false);
        ReflectionTestUtils.setField(userService, "secret", "test-secret");
        ReflectionTestUtils.setField(userService, "downloadUrl", "https://cdn.example.com/");
        ReflectionTestUtils.setField(userService, "testLoginEnabled", false);
        ReflectionTestUtils.setField(userService, "testStudentEmail", "student@syncode.test");
    }

    @Test
    void sendCodeShouldAcceptEmailAddressAndCacheCode() {
        UserDTO userDTO = new UserDTO();
        userDTO.setEmail("user@example.com");

        when(redisService.getExpire(anyString(), eq(TimeUnit.SECONDS))).thenReturn(null);
        when(redisService.getCacheObject(anyString(), eq(Long.class))).thenReturn(null);

        boolean result = assertDoesNotThrow(() -> userService.sendCode(userDTO));

        assertTrue(result);
        verify(redisService).setCacheObject(
                anyString(),
                anyString(),
                eq(5L),
                eq(TimeUnit.MINUTES)
        );
        verify(redisService).increment(anyString());
    }

    @Test
    void codeLoginShouldCreateUserWithEmailWhenUserDoesNotExist() {
        String email = "user@example.com";
        String code = "123456";

        when(redisService.getCacheObject(anyString(), eq(String.class))).thenReturn(code);
        when(userMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(null);
        when(tokenService.createToken(any(), anyString(), any(), any(), any())).thenReturn("token-1");

        String token = userService.codeLogin(email, code);

        assertEquals("token-1", token);

        ArgumentCaptor<User> userCaptor = ArgumentCaptor.forClass(User.class);
        verify(userMapper).insert(userCaptor.capture());

        User insertedUser = userCaptor.getValue();
        assertEquals(email, insertedUser.getEmail());
        assertNull(insertedUser.getPhone());
    }

    @Test
    void testLoginShouldRequireSwitchAndExactAllowlist() {
        assertThrows(RuntimeException.class, () -> userService.testLogin("student@syncode.test"));

        ReflectionTestUtils.setField(userService, "testLoginEnabled", true);
        assertThrows(RuntimeException.class, () -> userService.testLogin("other@syncode.test"));
    }

    @Test
    void testLoginShouldCreateAllowlistedStudent() {
        ReflectionTestUtils.setField(userService, "testLoginEnabled", true);
        when(userMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(null);
        when(tokenService.createToken(any(), anyString(), any(), any(), any())).thenReturn("test-token");

        assertEquals("test-token", userService.testLogin(" STUDENT@SYNCODE.TEST "));
        ArgumentCaptor<User> userCaptor = ArgumentCaptor.forClass(User.class);
        verify(userMapper).insert(userCaptor.capture());
        assertEquals("student@syncode.test", userCaptor.getValue().getEmail());
        assertEquals("测试学生", userCaptor.getValue().getNickName());
    }
}
