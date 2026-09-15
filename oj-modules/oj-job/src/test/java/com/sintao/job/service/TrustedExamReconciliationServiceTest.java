package com.sintao.job.service;

import com.sintao.common.core.enums.ExamAttemptStatus;
import com.sintao.common.core.enums.ExamGradeStatus;
import com.sintao.common.core.enums.ExamStatus;
import com.sintao.common.core.enums.JudgeAsyncStatus;
import com.sintao.common.core.enums.QuestionResType;
import com.sintao.job.domain.exam.ExamAttempt;
import com.sintao.job.domain.exam.Exam;
import com.sintao.job.domain.exam.ExamAuditEvent;
import com.sintao.job.domain.exam.ExamGrade;
import com.sintao.job.domain.exam.ExamGradeItem;
import com.sintao.job.domain.exam.ExamVersionQuestion;
import com.sintao.job.domain.user.UserSubmit;
import com.sintao.job.mapper.exam.ExamAnswerMapper;
import com.sintao.job.mapper.exam.ExamAttemptMapper;
import com.sintao.job.mapper.exam.ExamAuditEventMapper;
import com.sintao.job.mapper.exam.ExamGradeItemMapper;
import com.sintao.job.mapper.exam.ExamGradeMapper;
import com.sintao.job.mapper.exam.ExamMapper;
import com.sintao.job.mapper.exam.ExamVersionQuestionMapper;
import com.sintao.job.mapper.exam.IntegrityEventMapper;
import com.sintao.job.mapper.user.UserSubmitMapper;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Clock;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class TrustedExamReconciliationServiceTest {

    private static final Instant NOW = Instant.parse("2026-09-14T09:00:00Z");
    private static final LocalDateTime NOW_UTC = LocalDateTime.ofInstant(NOW, ZoneOffset.UTC);

    @Mock private ExamAttemptMapper attemptMapper;
    @Mock private ExamMapper examMapper;
    @Mock private ExamAuditEventMapper auditMapper;
    @Mock private IntegrityEventMapper integrityEventMapper;
    @Mock private ExamAnswerMapper answerMapper;
    @Mock private ExamVersionQuestionMapper versionQuestionMapper;
    @Mock private ExamGradeMapper gradeMapper;
    @Mock private ExamGradeItemMapper gradeItemMapper;
    @Mock private UserSubmitMapper userSubmitMapper;

    private TrustedExamReconciliationService service;

    @BeforeEach
    void setUp() {
        service = new TrustedExamReconciliationService(attemptMapper, examMapper, auditMapper,
                integrityEventMapper, answerMapper,
                versionQuestionMapper, gradeMapper, gradeItemMapper, userSubmitMapper,
                Clock.fixed(NOW, ZoneOffset.UTC), 180);
    }

    @Test
    void timeoutShouldUseConditionalTransitionFreezeAndCreateGrade() {
        ExamAttempt attempt = attempt(ExamAttemptStatus.IN_PROGRESS);
        when(attemptMapper.selectList(any())).thenReturn(List.of(attempt));
        when(attemptMapper.update(any(), any())).thenReturn(1);
        when(gradeMapper.selectOne(any())).thenReturn(null);
        when(versionQuestionMapper.selectList(any())).thenReturn(List.of(question(100)));

        int count = service.finalizeExpiredAttempts();

        assertEquals(1, count);
        assertEquals(ExamAttemptStatus.TIMED_OUT.getCode(), attempt.getStatus());
        assertEquals("DEADLINE", attempt.getFinalizationReason());
        verify(answerMapper).update(any(), any());
        ArgumentCaptor<ExamGrade> gradeCaptor = ArgumentCaptor.forClass(ExamGrade.class);
        verify(gradeMapper).insert(gradeCaptor.capture());
        assertEquals(100, gradeCaptor.getValue().getMaxScore());
    }

    @Test
    void aggregateShouldWaitForEveryFormalJudgeResult() {
        ExamAttempt attempt = attempt(ExamAttemptStatus.SUBMITTED);
        UserSubmit waiting = submission(JudgeAsyncStatus.WAITING, QuestionResType.IN_JUDGE);
        when(attemptMapper.selectList(any())).thenReturn(List.of(attempt));
        when(userSubmitMapper.selectList(any())).thenReturn(List.of(waiting));

        int count = service.aggregateTerminalGrades();

        assertEquals(0, count);
        verify(gradeMapper, never()).updateById(any());
        verify(gradeItemMapper, never()).insert(any());
    }

    @Test
    void aggregateShouldUseSnapshotScoreAndLatestCompletedSubmission() {
        ExamAttempt attempt = attempt(ExamAttemptStatus.SUBMITTED);
        UserSubmit passed = submission(JudgeAsyncStatus.SUCCESS, QuestionResType.PASS);
        passed.setSubmitId(501L);
        passed.setAnswerId(401L);
        ExamGrade grade = new ExamGrade();
        grade.setGradeId(301L);
        grade.setAttemptId(100L);
        grade.setStatus(ExamGradeStatus.WAITING_FOR_JUDGE.getCode());
        grade.setCurrentFlag(1);
        grade.setMaxScore(75);
        when(attemptMapper.selectList(any())).thenReturn(List.of(attempt));
        when(userSubmitMapper.selectList(any())).thenReturn(List.of(passed));
        when(gradeMapper.selectOne(any())).thenReturn(grade);
        when(versionQuestionMapper.selectList(any())).thenReturn(List.of(question(75)));

        int count = service.aggregateTerminalGrades();

        assertEquals(1, count);
        assertEquals(ExamGradeStatus.READY.getCode(), grade.getStatus());
        assertEquals(75, grade.getTotalScore());
        ArgumentCaptor<ExamGradeItem> itemCaptor = ArgumentCaptor.forClass(ExamGradeItem.class);
        verify(gradeItemMapper).insert(itemCaptor.capture());
        assertEquals(75, itemCaptor.getValue().getAwardedScore());
        assertEquals(501L, itemCaptor.getValue().getSubmitId());
        verify(answerMapper).update(any(), any());
    }

    @Test
    void aggregateShouldNotRebuildReadyGrade() {
        ExamAttempt attempt = attempt(ExamAttemptStatus.SUBMITTED);
        ExamGrade ready = new ExamGrade();
        ready.setGradeId(301L);
        ready.setAttemptId(100L);
        ready.setStatus(ExamGradeStatus.READY.getCode());
        ready.setCurrentFlag(1);
        when(attemptMapper.selectList(any())).thenReturn(List.of(attempt));
        when(gradeMapper.selectOne(any())).thenReturn(ready);

        assertEquals(0, service.aggregateTerminalGrades());

        verify(userSubmitMapper, never()).selectList(any());
        verify(gradeItemMapper, never()).delete(any());
        verify(gradeMapper, never()).updateById(any());
    }

    @Test
    void finishShouldConditionallyAdvanceEndedExam() {
        Exam exam = scheduledExam(ExamStatus.ACTIVE);
        when(examMapper.selectList(any())).thenReturn(List.of(exam));
        when(examMapper.update(any(), any())).thenReturn(1);

        assertEquals(1, service.finishEndedExams());

        verify(examMapper).update(any(), any());
    }

    @Test
    void scheduledReleaseShouldPublishOnlyReadyGradesAndAudit() {
        Exam exam = scheduledExam(ExamStatus.FINISHED);
        ExamAttempt attempt = attempt(ExamAttemptStatus.SUBMITTED);
        ExamGrade grade = new ExamGrade();
        grade.setGradeId(301L);
        grade.setAttemptId(100L);
        grade.setStatus(ExamGradeStatus.READY.getCode());
        grade.setCurrentFlag(1);
        when(examMapper.selectList(any())).thenReturn(List.of(exam));
        when(attemptMapper.selectList(any())).thenReturn(List.of(attempt));
        when(gradeMapper.selectList(any())).thenReturn(List.of(grade));
        when(examMapper.update(any(), any())).thenReturn(1);

        assertEquals(1, service.releaseScheduledResults());

        assertEquals(ExamGradeStatus.RELEASED.getCode(), grade.getStatus());
        assertEquals(NOW_UTC, grade.getReleasedTime());
        verify(gradeMapper).updateById(grade);
        ArgumentCaptor<ExamAuditEvent> auditCaptor = ArgumentCaptor.forClass(ExamAuditEvent.class);
        verify(auditMapper).insert(auditCaptor.capture());
        assertEquals("RESULTS_RELEASED", auditCaptor.getValue().getAction());
        assertEquals("SYSTEM", auditCaptor.getValue().getActorType());
    }

    @Test
    void purgeShouldDeleteOnlyEvidenceOlderThanRetentionWindow() {
        when(integrityEventMapper.delete(any())).thenReturn(3);

        assertEquals(3, service.purgeExpiredIntegrityEvidence());

        verify(integrityEventMapper).delete(any());
    }

    private ExamAttempt attempt(ExamAttemptStatus status) {
        ExamAttempt attempt = new ExamAttempt();
        attempt.setAttemptId(100L);
        attempt.setExamId(10L);
        attempt.setVersionId(20L);
        attempt.setUserId(30L);
        attempt.setStatus(status.getCode());
        attempt.setRowVersion(0);
        attempt.setDeadlineTime(NOW_UTC.minusSeconds(1));
        attempt.setFinalizedTime(NOW_UTC.minusSeconds(1));
        return attempt;
    }

    private Exam scheduledExam(ExamStatus status) {
        Exam exam = new Exam();
        exam.setExamId(10L);
        exam.setStatus(status.getCode());
        exam.setEndTime(NOW_UTC.minusMinutes(1));
        exam.setResultReleasePolicy("SCHEDULED");
        exam.setResultReleaseTime(NOW_UTC.minusSeconds(1));
        exam.setRowVersion(1);
        return exam;
    }

    private ExamVersionQuestion question(int score) {
        ExamVersionQuestion question = new ExamVersionQuestion();
        question.setVersionQuestionId(201L);
        question.setVersionId(20L);
        question.setQuestionOrder(1);
        question.setScore(score);
        return question;
    }

    private UserSubmit submission(JudgeAsyncStatus status, QuestionResType result) {
        UserSubmit submission = new UserSubmit();
        submission.setAttemptId(100L);
        submission.setVersionQuestionId(201L);
        submission.setSubmitKind("FORMAL");
        submission.setJudgeStatus(status.getValue());
        submission.setPass(result.getValue());
        submission.setCreateTime(NOW_UTC.minusSeconds(2));
        return submission;
    }
}
