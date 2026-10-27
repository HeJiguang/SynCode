package com.sintao.judge.service.impl;

import com.sintao.api.domain.UserExeResult;
import com.sintao.api.domain.dto.JudgeSubmitDTO;
import com.sintao.common.core.enums.CodeRunStatus;
import com.sintao.judge.domain.SandBoxExecuteResult;
import com.sintao.judge.mapper.UserSubmitMapper;
import com.sintao.judge.sandbox.GoJudgeSandboxService;
import org.junit.jupiter.api.Test;
import org.springframework.test.util.ReflectionTestUtils;
import java.util.List;
import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

class JudgeServiceGoJudgeTest {
    @Test void persistsIncrementalVerdictWithoutComparingTruncatedPreviewsAgain() {
        JudgeServiceImpl service = new JudgeServiceImpl();
        GoJudgeSandboxService sandbox = mock(GoJudgeSandboxService.class);
        ReflectionTestUtils.setField(service, "sandboxExecutionMode", "go-judge");
        ReflectionTestUtils.setField(service, "goJudgeSandboxService", sandbox);
        ReflectionTestUtils.setField(service, "userSubmitMapper", mock(UserSubmitMapper.class));
        JudgeSubmitDTO submission = new JudgeSubmitDTO();
        submission.setUserId(1L);
        submission.setQuestionId(2L);
        submission.setDifficulty(1);
        submission.setTestCaseSetId("a".repeat(64));
        submission.setTestCaseCount(500);
        UserExeResult detail = new UserExeResult();
        detail.setCaseId("case-1");
        detail.setOutput("expected preview");
        detail.setExeOutput("different but equivalent preview");
        detail.setTruncated(true);
        detail.setPassed(true);
        SandBoxExecuteResult result = SandBoxExecuteResult.success(CodeRunStatus.SUCCEED, List.of(), 100L, 10L);
        result.setCaseResults(List.of(detail));
        result.setAllCasesPassed(true);
        result.setExecutedCaseCount(500);
        when(sandbox.execute(submission, false)).thenReturn(result);

        var judged = service.doJudgeJavaCode(submission);
        assertEquals(1, judged.getPass());
        assertEquals("case-1", judged.getUserExeResultList().get(0).getCaseId());
        verify(sandbox).execute(submission, false);
    }

    @Test void sampleRunKeepsFailedCaseIdentityAndTruncation() {
        JudgeServiceImpl service = new JudgeServiceImpl();
        GoJudgeSandboxService sandbox = mock(GoJudgeSandboxService.class);
        ReflectionTestUtils.setField(service, "sandboxExecutionMode", "go-judge");
        ReflectionTestUtils.setField(service, "goJudgeSandboxService", sandbox);
        JudgeSubmitDTO submission = new JudgeSubmitDTO();
        UserExeResult detail = new UserExeResult();
        detail.setCaseId("case-2");
        detail.setPassed(false);
        detail.setCustom(false);
        detail.setTruncated(true);
        SandBoxExecuteResult result = SandBoxExecuteResult.fail(CodeRunStatus.OUT_OF_TIME);
        result.setCaseResults(List.of(detail));
        when(sandbox.execute(submission, true)).thenReturn(result);

        var run = service.runJavaCode(submission);
        assertEquals(CodeRunStatus.OUT_OF_TIME.name(), run.getRunStatus());
        assertEquals("case-2", run.getCaseResults().get(0).getCaseId());
        assertTrue(run.getCaseResults().get(0).getTruncated());
    }
}
