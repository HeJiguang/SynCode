package com.sintao.system.service.exam.impl;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sintao.common.core.constants.Constants;
import com.sintao.common.core.enums.ExamAttemptStatus;
import com.sintao.common.core.enums.ExamGradeStatus;
import com.sintao.common.core.enums.ExamStatus;
import com.sintao.common.core.enums.ResultCode;
import com.sintao.common.core.utils.ThreadLocalUtil;
import com.sintao.common.security.exception.ServiceException;
import com.sintao.system.domain.exam.Exam;
import com.sintao.system.domain.exam.ExamAuditEvent;
import com.sintao.system.domain.exam.ExamAttempt;
import com.sintao.system.domain.exam.ExamGrade;
import com.sintao.system.domain.exam.ExamGradeItem;
import com.sintao.system.domain.exam.ExamVersionQuestion;
import com.sintao.system.domain.exam.IntegrityEvent;
import com.sintao.system.domain.exam.UserExam;
import com.sintao.system.domain.exam.dto.CandidateAuthorizationDTO;
import com.sintao.system.domain.exam.dto.ExamGradeReviewDTO;
import com.sintao.system.domain.user.User;
import com.sintao.system.mapper.exam.ExamAnswerMapper;
import com.sintao.system.mapper.exam.ExamAttemptMapper;
import com.sintao.system.mapper.exam.ExamAuditEventMapper;
import com.sintao.system.mapper.exam.ExamGradeMapper;
import com.sintao.system.mapper.exam.ExamGradeItemMapper;
import com.sintao.system.mapper.exam.ExamVersionQuestionMapper;
import com.sintao.system.mapper.exam.ExamMapper;
import com.sintao.system.mapper.exam.UserExamMapper;
import com.sintao.system.mapper.exam.IntegrityEventMapper;
import com.sintao.system.mapper.user.UserMapper;
import org.junit.jupiter.api.AfterEach;
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
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class ExamAdministrationServiceImplTest {

    private static final Instant NOW = Instant.parse("2026-09-14T09:00:00Z");
    private static final LocalDateTime NOW_UTC = LocalDateTime.ofInstant(NOW, ZoneOffset.UTC);

    @Mock private ExamMapper examMapper;
    @Mock private UserExamMapper userExamMapper;
    @Mock private UserMapper userMapper;
    @Mock private ExamAttemptMapper attemptMapper;
    @Mock private ExamAnswerMapper answerMapper;
    @Mock private ExamGradeMapper gradeMapper;
    @Mock private ExamGradeItemMapper gradeItemMapper;
    @Mock private ExamVersionQuestionMapper versionQuestionMapper;
    @Mock private ExamAuditEventMapper auditMapper;
    @Mock private IntegrityEventMapper integrityEventMapper;

    private ExamAdministrationServiceImpl service;

    @BeforeEach
    void setUp() {
        service = new ExamAdministrationServiceImpl(examMapper, userExamMapper, userMapper,
                attemptMapper, answerMapper, gradeMapper, gradeItemMapper, versionQuestionMapper,
                auditMapper, integrityEventMapper,
                new ObjectMapper().findAndRegisterModules(), Clock.fixed(NOW, ZoneOffset.UTC));
        ThreadLocalUtil.set(Constants.USER_ID, 77L);
    }

    @AfterEach
    void tearDown() {
        ThreadLocalUtil.remove();
    }

    @Test
    void authorizeShouldDeduplicateUsersAndCreateAuditedRelations() {
        when(examMapper.selectById(10L)).thenReturn(exam(ExamStatus.PUBLISHED));
        User first = user(1L);
        User second = user(2L);
        when(userMapper.selectBatchIds(any())).thenReturn(List.of(first, second));
        when(userExamMapper.selectOne(any())).thenReturn(null);
        when(userExamMapper.selectList(any())).thenReturn(List.of());
        CandidateAuthorizationDTO request = new CandidateAuthorizationDTO();
        request.setUserIds(List.of(1L, 1L, 2L));
        request.setSource("IMPORT");

        service.authorizeCandidates(10L, request, "authorize-request");

        ArgumentCaptor<UserExam> captor = ArgumentCaptor.forClass(UserExam.class);
        verify(userExamMapper, org.mockito.Mockito.times(2)).insert(captor.capture());
        assertEquals(List.of(1L, 2L), captor.getAllValues().stream().map(UserExam::getUserId).toList());
        verify(auditMapper).insert(any());
    }

    @Test
    void revokeShouldRejectCandidateWhoAlreadyStarted() {
        when(examMapper.selectById(10L)).thenReturn(exam(ExamStatus.ACTIVE));
        when(attemptMapper.selectCount(any())).thenReturn(1L);

        ServiceException exception = assertThrows(ServiceException.class,
                () -> service.revokeCandidate(10L, 1L, "duplicate account", "revoke-request"));

        assertEquals(ResultCode.EXAM_STATE_CONFLICT, exception.getResultCode());
        verify(userExamMapper, never()).updateById(any());
    }

    @Test
    void cancelShouldFinalizeActiveAttemptsAndFreezeAnswers() {
        Exam exam = exam(ExamStatus.ACTIVE);
        ExamAttempt attempt = attempt();
        when(examMapper.selectByIdForUpdate(10L)).thenReturn(exam);
        when(attemptMapper.selectList(any())).thenReturn(List.of(attempt));

        service.cancel(10L, "room power outage", "cancel-request");

        assertEquals(ExamStatus.CANCELLED.getCode(), exam.getStatus());
        assertEquals(ExamAttemptStatus.CANCELLED.getCode(), attempt.getStatus());
        assertEquals("EXAM_CANCEL", attempt.getFinalizationReason());
        verify(answerMapper).update(any(), any());
        verify(auditMapper).insert(any());
    }

    @Test
    void cancelShouldRejectFinishedExam() {
        Exam exam = exam(ExamStatus.FINISHED);
        when(examMapper.selectByIdForUpdate(10L)).thenReturn(exam);

        ServiceException exception = assertThrows(ServiceException.class,
                () -> service.cancel(10L, "late cancellation", "cancel-request"));

        assertEquals(ResultCode.EXAM_STATE_CONFLICT, exception.getResultCode());
        verify(attemptMapper, never()).selectList(any());
        verify(examMapper, never()).updateById(any());
    }

    @Test
    void releaseShouldRejectUntilEveryGradeIsReady() {
        Exam exam = exam(ExamStatus.FINISHED);
        exam.setEndTime(NOW_UTC.minusMinutes(1));
        ExamAttempt attempt = attempt();
        when(examMapper.selectByIdForUpdate(10L)).thenReturn(exam);
        when(attemptMapper.selectList(any())).thenReturn(List.of(attempt));
        ExamGrade waiting = grade(ExamGradeStatus.WAITING_FOR_JUDGE);
        when(gradeMapper.selectList(any())).thenReturn(List.of(waiting));

        ServiceException exception = assertThrows(ServiceException.class,
                () -> service.releaseResults(10L, "release-key", "release-request"));

        assertEquals(ResultCode.EXAM_GRADE_NOT_READY, exception.getResultCode());
        verify(examMapper, never()).updateById(exam);
    }

    @Test
    void releaseShouldPublishReadyGradesAndExamAtomically() {
        Exam exam = exam(ExamStatus.FINISHED);
        exam.setEndTime(NOW_UTC.minusMinutes(1));
        ExamAttempt attempt = attempt();
        ExamGrade ready = grade(ExamGradeStatus.READY);
        when(examMapper.selectByIdForUpdate(10L)).thenReturn(exam);
        when(attemptMapper.selectList(any())).thenReturn(List.of(attempt));
        when(gradeMapper.selectList(any())).thenReturn(List.of(ready));

        service.releaseResults(10L, "release-key", "release-request");

        assertEquals(ExamGradeStatus.RELEASED.getCode(), ready.getStatus());
        assertEquals(ExamStatus.RESULT_RELEASED.getCode(), exam.getStatus());
        assertEquals(NOW_UTC, exam.getResultReleasedTime());
        verify(gradeMapper).updateById(ready);
        verify(examMapper).updateById(exam);
        verify(auditMapper).insert(any());
    }

    @Test
    void releaseShouldRejectExamWithoutAttempts() {
        Exam exam = exam(ExamStatus.FINISHED);
        exam.setEndTime(NOW_UTC.minusMinutes(1));
        when(examMapper.selectByIdForUpdate(10L)).thenReturn(exam);
        when(attemptMapper.selectList(any())).thenReturn(List.of());

        ServiceException exception = assertThrows(ServiceException.class,
                () -> service.releaseResults(10L, "release-key", "release-request"));

        assertEquals(ResultCode.EXAM_GRADE_NOT_READY, exception.getResultCode());
        verify(gradeMapper, never()).selectList(any());
        verify(examMapper, never()).updateById(exam);
    }

    @Test
    void evidenceShouldMergeIntegrityAndAuditEventsChronologically() {
        ExamAttempt attempt = attempt();
        when(examMapper.selectById(10L)).thenReturn(exam(ExamStatus.FINISHED));
        when(attemptMapper.selectById(100L)).thenReturn(attempt);
        IntegrityEvent integrity = new IntegrityEvent();
        integrity.setEventType("WINDOW_BLUR");
        integrity.setServerReceivedTime(NOW_UTC.minusSeconds(1));
        integrity.setRiskPoints(1);
        ExamAuditEvent audit = new ExamAuditEvent();
        audit.setAction("ATTEMPT_STARTED");
        audit.setServerTime(NOW_UTC.minusMinutes(5));
        when(integrityEventMapper.selectList(any())).thenReturn(List.of(integrity));
        when(auditMapper.selectList(any())).thenReturn(List.of(audit));

        var evidence = service.evidence(10L, 100L);

        assertEquals(2, evidence.size());
        assertEquals("AUDIT", evidence.get(0).getCategory());
        assertEquals("INTEGRITY", evidence.get(1).getCategory());
        assertTrue(evidence.get(1).getRiskPoints() > 0);
    }

    @Test
    void reviewShouldScoreManualItemsAndMarkGradeReady() {
        ExamAttempt attempt = attempt();
        attempt.setStatus(ExamAttemptStatus.SUBMITTED.getCode());
        ExamGrade grade = grade(ExamGradeStatus.NEEDS_REVIEW);
        grade.setTotalScore(40);
        ExamGradeItem automatic = gradeItem(201L, "AUTO", 40, 40);
        ExamGradeItem manual = gradeItem(202L, "MANUAL", 0, 60);
        ExamVersionQuestion autoQuestion = versionQuestion(201L, 1, 40, "MULTIPLE_CHOICE");
        ExamVersionQuestion manualQuestion = versionQuestion(202L, 2, 60, "SHORT_ANSWER");
        when(examMapper.selectById(10L)).thenReturn(exam(ExamStatus.FINISHED));
        when(attemptMapper.selectById(100L)).thenReturn(attempt);
        when(gradeMapper.selectOne(any())).thenReturn(grade);
        when(gradeItemMapper.selectList(any())).thenReturn(List.of(automatic, manual));
        when(versionQuestionMapper.selectList(any())).thenReturn(List.of(autoQuestion, manualQuestion));
        when(answerMapper.selectList(any())).thenReturn(List.of());
        when(userMapper.selectById(1L)).thenReturn(user(1L));
        ExamGradeReviewDTO.Item score = new ExamGradeReviewDTO.Item();
        score.setVersionQuestionId(202L);
        score.setAwardedScore(55);
        score.setFeedback("结构完整");
        ExamGradeReviewDTO request = new ExamGradeReviewDTO();
        request.setItems(List.of(score));

        var result = service.reviewGrade(10L, 100L, request, "review-request");

        assertEquals(ExamGradeStatus.READY.getCode(), grade.getStatus());
        assertEquals(95, grade.getTotalScore());
        assertEquals("MIXED", grade.getCalculationSource());
        assertEquals("结构完整", manual.getFeedback());
        assertEquals("READY", result.getStatus());
        assertEquals("按完整性评分", result.getItems().get(1).getGradingRubric());
        verify(gradeItemMapper).updateById(manual);
        verify(auditMapper).insert(any());
    }

    private Exam exam(ExamStatus status) {
        Exam exam = new Exam();
        exam.setExamId(10L);
        exam.setStatus(status.getCode());
        exam.setStartTime(NOW_UTC.minusMinutes(10));
        exam.setEndTime(NOW_UTC.plusMinutes(60));
        exam.setRowVersion(1);
        return exam;
    }

    private User user(Long userId) {
        User user = new User();
        user.setUserId(userId);
        user.setNickName("Candidate " + userId);
        return user;
    }

    private ExamAttempt attempt() {
        ExamAttempt attempt = new ExamAttempt();
        attempt.setAttemptId(100L);
        attempt.setExamId(10L);
        attempt.setVersionId(20L);
        attempt.setUserId(1L);
        attempt.setStatus(ExamAttemptStatus.IN_PROGRESS.getCode());
        attempt.setRowVersion(0);
        attempt.setStartedTime(NOW_UTC.minusMinutes(5));
        attempt.setLastActiveTime(NOW_UTC);
        return attempt;
    }

    private ExamGradeItem gradeItem(Long questionId, String mode, int score, int maxScore) {
        ExamGradeItem item = new ExamGradeItem();
        item.setGradeId(200L);
        item.setVersionQuestionId(questionId);
        item.setGradingMode(mode);
        item.setAwardedScore(score);
        item.setMaxScore(maxScore);
        return item;
    }

    private ExamVersionQuestion versionQuestion(Long questionId, int order, int score, String type) {
        ExamVersionQuestion question = new ExamVersionQuestion();
        question.setVersionQuestionId(questionId);
        question.setVersionId(20L);
        question.setQuestionOrder(order);
        question.setScore(score);
        question.setQuestionType(type);
        question.setTitle("Question " + order);
        question.setGradingConfigJson("{\"rubric\":\"按完整性评分\"}");
        return question;
    }

    private ExamGrade grade(ExamGradeStatus status) {
        ExamGrade grade = new ExamGrade();
        grade.setGradeId(200L);
        grade.setAttemptId(100L);
        grade.setStatus(status.getCode());
        grade.setCurrentFlag(1);
        grade.setTotalScore(100);
        grade.setMaxScore(100);
        return grade;
    }
}
