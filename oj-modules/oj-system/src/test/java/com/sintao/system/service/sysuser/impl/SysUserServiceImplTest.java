package com.sintao.system.service.sysuser.impl;

import com.sintao.system.domain.sysuser.SysUser;
import com.sintao.system.domain.sysuser.dto.SysUserSaveDTO;
import com.sintao.system.mapper.sysuser.SysUserMapper;
import com.sintao.system.utils.BCryptUtils;
import com.sintao.common.security.service.TokenService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.Collections;

import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class SysUserServiceImplTest {

    @Mock
    private SysUserMapper sysUserMapper;

    @Mock
    private TokenService tokenService;

    @InjectMocks
    private SysUserServiceImpl sysUserService;

    @org.junit.jupiter.api.BeforeEach
    void setUp() {
        ReflectionTestUtils.setField(sysUserService, "secret", "test-secret");
        ReflectionTestUtils.setField(sysUserService, "testLoginEnabled", true);
        ReflectionTestUtils.setField(sysUserService, "testTeacherEmail", "teacher@syncode.test");
        ReflectionTestUtils.setField(sysUserService, "testTeacherAccount", "admin");
    }

    @Test
    void addShouldPopulateCreateByBeforeInsert() {
        SysUserSaveDTO request = new SysUserSaveDTO();
        request.setUserAccount("csmk1001");
        request.setPassword("Codex123!");

        when(sysUserMapper.selectList(any())).thenReturn(Collections.emptyList());
        when(sysUserMapper.insert(any(SysUser.class))).thenReturn(1);

        int inserted = sysUserService.add(request);

        ArgumentCaptor<SysUser> userCaptor = ArgumentCaptor.forClass(SysUser.class);
        verify(sysUserMapper).insert(userCaptor.capture());
        SysUser savedUser = userCaptor.getValue();
        assertEquals(1, inserted);
        assertEquals("csmk1001", savedUser.getUserAccount());
        assertEquals(1L, savedUser.getCreateBy());
        assertTrue(BCryptUtils.matchesPassword("Codex123!", savedUser.getPassword()));
    }

    @Test
    void testLoginShouldMapAllowlistedEmailToAdminAccount() {
        SysUser admin = new SysUser();
        admin.setUserId(9L);
        admin.setNickName("测试教师");
        when(sysUserMapper.selectOne(any())).thenReturn(admin);
        when(tokenService.createToken(any(), any(), any(), any(), any())).thenReturn("teacher-token");

        assertEquals("teacher-token", sysUserService.testLogin(" TEACHER@SYNCODE.TEST ").getData());
    }

    @Test
    void testLoginShouldRejectEmailOutsideAllowlist() {
        assertEquals(3001, sysUserService.testLogin("other@syncode.test").getCode());
    }
}
