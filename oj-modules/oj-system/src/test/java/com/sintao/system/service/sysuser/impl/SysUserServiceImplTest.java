package com.sintao.system.service.sysuser.impl;

import com.sintao.system.domain.sysuser.SysUser;
import com.sintao.system.domain.sysuser.dto.SysUserSaveDTO;
import com.sintao.system.mapper.sysuser.SysUserMapper;
import com.sintao.system.utils.BCryptUtils;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Collections;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class SysUserServiceImplTest {

    @Mock
    private SysUserMapper sysUserMapper;

    @InjectMocks
    private SysUserServiceImpl sysUserService;

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
}
