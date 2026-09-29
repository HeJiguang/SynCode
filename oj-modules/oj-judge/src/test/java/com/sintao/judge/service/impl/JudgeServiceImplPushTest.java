package com.sintao.judge.service.impl;

import com.sintao.api.domain.dto.JudgeSubmitDTO;
import com.sintao.common.core.enums.CodeRunStatus;
import com.sintao.common.core.enums.JudgeAsyncStatus;
import com.sintao.common.redis.service.JudgeResultPushService;
import com.sintao.common.redis.service.JudgeRuntimeStateService;
import com.sintao.judge.domain.SandBoxExecuteResult;
import com.sintao.judge.mapper.UserSubmitMapper;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;

import java.util.List;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class JudgeServiceImplPushTest {

    @Test
    void requestBasedJudgeCompletionPublishesSuccessFinalResult() {
        JudgeServiceImpl judgeService = new JudgeServiceImpl();
        UserSubmitMapper userSubmitMapper = mock(UserSubmitMapper.class);
        SandboxPoolServiceImpl sandboxPoolService = mock(SandboxPoolServiceImpl.class);
        SandboxServiceImpl sandboxService = mock(SandboxServiceImpl.class);
        JudgeResultPushService judgeResultPushService = mock(JudgeResultPushService.class);
        JudgeRuntimeStateService runtimeStateService = mock(JudgeRuntimeStateService.class);
        ReflectionTestUtils.setField(judgeService, "userSubmitMapper", userSubmitMapper);
        ReflectionTestUtils.setField(judgeService, "sandboxPoolService", sandboxPoolService);
        ReflectionTestUtils.setField(judgeService, "sandboxService", sandboxService);
        ReflectionTestUtils.setField(judgeService, "judgeResultPushService", judgeResultPushService);
        ReflectionTestUtils.setField(judgeService, "judgeRuntimeStateService", runtimeStateService);

        JudgeSubmitDTO submitDTO = new JudgeSubmitDTO();
        submitDTO.setRequestId("req-1");
        submitDTO.setUserId(1001L);
        submitDTO.setProgramType(0);
        submitDTO.setDifficulty(1);
        submitDTO.setTimeLimit(1000L);
        submitDTO.setSpaceLimit(1024L);
        submitDTO.setInputList(List.of("1 2"));
        submitDTO.setOutputList(List.of("3"));
        when(sandboxPoolService.executeCode(any(), any(), any(), any()))
                .thenReturn(SandBoxExecuteResult.success(CodeRunStatus.SUCCEED, List.of("3"), 32L, 12L));
        when(userSubmitMapper.update(any(), any())).thenReturn(1);

        judgeService.doJudgeJavaCode(submitDTO);

        verify(userSubmitMapper).update(any(), any());
        verify(runtimeStateService).markSuccess("req-1");
        verify(judgeResultPushService).publishFinalResult(argThat(dto ->
                "req-1".equals(dto.getRequestId())
                        && Integer.valueOf(1001).equals(dto.getUserId().intValue())
                        && Integer.valueOf(JudgeAsyncStatus.SUCCESS.getValue()).equals(dto.getAsyncStatus())
                        && dto.getPass() != null
                        && dto.getExeMessage() != null));
    }

    @Test
    void duplicateCompletionDoesNotPushAnotherFinalResult() {
        JudgeServiceImpl judgeService = new JudgeServiceImpl();
        SandboxPoolServiceImpl pool = mock(SandboxPoolServiceImpl.class);
        JudgeResultPushService pushService = mock(JudgeResultPushService.class);
        ReflectionTestUtils.setField(judgeService, "sandboxPoolService", pool);
        ReflectionTestUtils.setField(judgeService, "judgeResultPushService", pushService);
        ReflectionTestUtils.setField(judgeService, "judgeRuntimeStateService", mock(JudgeRuntimeStateService.class));
        ReflectionTestUtils.setField(judgeService, "userSubmitMapper", mock(UserSubmitMapper.class));

        JudgeSubmitDTO submitDTO = new JudgeSubmitDTO();
        submitDTO.setRequestId("req-done");
        submitDTO.setUserId(1001L);
        submitDTO.setProgramType(0);
        submitDTO.setInputList(List.of("1"));
        submitDTO.setOutputList(List.of("3"));
        when(pool.executeCode(any(), any(), any(), any()))
                .thenReturn(SandBoxExecuteResult.fail(CodeRunStatus.COMPILE_FAILED, "bad code"));

        judgeService.doJudgeJavaCode(submitDTO);

        verify(pushService, never()).publishFinalResult(any());
    }
}
