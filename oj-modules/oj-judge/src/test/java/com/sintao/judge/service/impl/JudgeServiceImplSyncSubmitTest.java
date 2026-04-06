package com.sintao.judge.service.impl;

import com.sintao.api.domain.dto.JudgeSubmitDTO;
import com.sintao.common.core.enums.CodeRunStatus;
import com.sintao.common.redis.service.JudgeResultPushService;
import com.sintao.judge.domain.SandBoxExecuteResult;
import com.sintao.judge.domain.UserSubmit;
import com.sintao.judge.mapper.UserSubmitMapper;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class JudgeServiceImplSyncSubmitTest {

    @Test
    void syncJudgeSubmitShouldPersistGeneratedRequestId() {
        JudgeServiceImpl judgeService = new JudgeServiceImpl();
        UserSubmitMapper userSubmitMapper = mock(UserSubmitMapper.class);
        SandboxPoolServiceImpl sandboxPoolService = mock(SandboxPoolServiceImpl.class);
        SandboxServiceImpl sandboxService = mock(SandboxServiceImpl.class);
        JudgeResultPushService judgeResultPushService = mock(JudgeResultPushService.class);
        ReflectionTestUtils.setField(judgeService, "userSubmitMapper", userSubmitMapper);
        ReflectionTestUtils.setField(judgeService, "sandboxPoolService", sandboxPoolService);
        ReflectionTestUtils.setField(judgeService, "sandboxService", sandboxService);
        ReflectionTestUtils.setField(judgeService, "judgeResultPushService", judgeResultPushService);

        JudgeSubmitDTO submitDTO = new JudgeSubmitDTO();
        submitDTO.setUserId(1001L);
        submitDTO.setQuestionId(2002L);
        submitDTO.setDifficulty(1);
        submitDTO.setProgramType(0);
        submitDTO.setTimeLimit(1000L);
        submitDTO.setSpaceLimit(1024L);
        submitDTO.setUserCode("public class Solution {}");
        submitDTO.setInputList(List.of("1 2"));
        submitDTO.setOutputList(List.of("3"));

        when(sandboxPoolService.exeJavaCode(any(), any(), any()))
                .thenReturn(SandBoxExecuteResult.success(CodeRunStatus.SUCCEED, List.of("3"), 32L, 12L));

        judgeService.doJudgeJavaCode(submitDTO);

        ArgumentCaptor<UserSubmit> submitCaptor = ArgumentCaptor.forClass(UserSubmit.class);
        verify(userSubmitMapper).insert(submitCaptor.capture());
        UserSubmit savedSubmit = submitCaptor.getValue();
        assertNull(submitDTO.getRequestId());
        assertNotNull(savedSubmit.getRequestId());
        assertTrue(!savedSubmit.getRequestId().isBlank());
    }

    @Test
    void syncJudgeSubmitShouldTreatSpaceLimitAsKilobytes() {
        JudgeServiceImpl judgeService = new JudgeServiceImpl();
        UserSubmitMapper userSubmitMapper = mock(UserSubmitMapper.class);
        SandboxPoolServiceImpl sandboxPoolService = mock(SandboxPoolServiceImpl.class);
        SandboxServiceImpl sandboxService = mock(SandboxServiceImpl.class);
        JudgeResultPushService judgeResultPushService = mock(JudgeResultPushService.class);
        ReflectionTestUtils.setField(judgeService, "userSubmitMapper", userSubmitMapper);
        ReflectionTestUtils.setField(judgeService, "sandboxPoolService", sandboxPoolService);
        ReflectionTestUtils.setField(judgeService, "sandboxService", sandboxService);
        ReflectionTestUtils.setField(judgeService, "judgeResultPushService", judgeResultPushService);

        JudgeSubmitDTO submitDTO = new JudgeSubmitDTO();
        submitDTO.setUserId(1001L);
        submitDTO.setQuestionId(2002L);
        submitDTO.setDifficulty(1);
        submitDTO.setProgramType(0);
        submitDTO.setTimeLimit(1000L);
        submitDTO.setSpaceLimit(262_144L);
        submitDTO.setUserCode("public class Solution {}");
        submitDTO.setInputList(List.of("1 2"));
        submitDTO.setOutputList(List.of("3"));

        when(sandboxPoolService.exeJavaCode(any(), any(), any()))
                .thenReturn(SandBoxExecuteResult.success(CodeRunStatus.SUCCEED, List.of("3"), 77_246_464L, 12L));

        assertEquals(1, judgeService.doJudgeJavaCode(submitDTO).getPass());
    }
}
