package com.sintao.friend.service.exam.impl;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sintao.api.domain.dto.JudgeSubmitDTO;
import com.sintao.common.core.constants.Constants;
import com.sintao.common.core.enums.ExamAttemptStatus;
import com.sintao.common.core.enums.ExamStatus;
import com.sintao.common.core.enums.ResultCode;
import com.sintao.common.core.utils.ThreadLocalUtil;
import com.sintao.common.redis.service.JudgeRuntimeStateService;
import com.sintao.common.security.exception.ServiceException;
import com.sintao.friend.domain.exam.Exam;
import com.sintao.friend.domain.exam.ExamAnswer;
import com.sintao.friend.domain.exam.ExamAttempt;
import com.sintao.friend.domain.exam.ExamGrade;
import com.sintao.friend.domain.exam.ExamVersion;
import com.sintao.friend.domain.exam.ExamVersionQuestion;
import com.sintao.friend.domain.exam.dto.ExamSubmissionDTO;
import com.sintao.friend.domain.exam.dto.SaveAnswerDTO;
import com.sintao.friend.domain.exam.dto.StartExamDTO;
import com.sintao.friend.domain.exam.vo.ExamAnswerVO;
import com.sintao.friend.domain.exam.vo.ExamAttemptVO;
import com.sintao.friend.domain.exam.vo.ExamFinalizeVO;
import com.sintao.friend.domain.exam.vo.ExamSubmissionVO;
import com.sintao.friend.domain.user.User;
import com.sintao.friend.domain.user.UserExam;
import com.sintao.friend.domain.user.UserSubmit;
import com.sintao.friend.mapper.exam.ExamAnswerMapper;
import com.sintao.friend.mapper.exam.ExamAttemptMapper;
import com.sintao.friend.mapper.exam.ExamAuditEventMapper;
import com.sintao.friend.mapper.exam.ExamCommandMapper;
import com.sintao.friend.mapper.exam.ExamGradeMapper;
import com.sintao.friend.mapper.exam.ExamMapper;
import com.sintao.friend.mapper.exam.ExamVersionMapper;
import com.sintao.friend.mapper.exam.ExamVersionQuestionMapper;
import com.sintao.friend.mapper.user.UserExamMapper;
import com.sintao.friend.mapper.user.UserMapper;
import com.sintao.friend.mapper.user.UserSubmitMapper;
import com.sintao.friend.rabbit.JudgeProducer;
import com.sintao.friend.service.exam.ExamAttemptExpiredException;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InOrder;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.Clock;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class TrustedExamServiceImplTest {

    private static final Instant NOW = Instant.parse("2026-09-14T09:00:00Z");
    private static final LocalDateTime NOW_UTC = LocalDateTime.ofInstant(NOW, ZoneOffset.UTC);

    @Mock private ExamMapper examMapper;
    @Mock private ExamVersionMapper versionMapper;
    @Mock private ExamVersionQuestionMapper versionQuestionMapper;
    @Mock private ExamAttemptMapper attemptMapper;
    @Mock private ExamAnswerMapper answerMapper;
    @Mock private ExamCommandMapper commandMapper;
    @Mock private ExamAuditEventMapper auditMapper;
    @Mock private ExamGradeMapper gradeMapper;
    @Mock private UserExamMapper userExamMapper;
    @Mock private UserMapper userMapper;
    @Mock private UserSubmitMapper userSubmitMapper;
    @Mock private JudgeProducer judgeProducer;
    @Mock private JudgeRuntimeStateService judgeRuntimeStateService;

    private TrustedExamServiceImpl service;

    @BeforeEach
    void setUp() {
        service = new TrustedExamServiceImpl(
                examMapper, versionMapper, versionQuestionMapper, attemptMapper, answerMapper,
                commandMapper, auditMapper, gradeMapper, userExamMapper, userMapper,
                userSubmitMapper, judgeProducer, judgeRuntimeStateService,
                new ObjectMapper().findAndRegisterModules(), Clock.fixed(NOW, ZoneOffset.UTC), "test-salt");
        ThreadLocalUtil.set(Constants.USER_ID, 99L);
    }

    @AfterEach
    void tearDown() {
        ThreadLocalUtil.remove();
    }

    @Test
    void startShouldUseServerDeadlineAndReturnSanitizedSnapshot() {
        stubStartDependencies();
        doAnswer(invocation -> {
            ((ExamAttempt) invocation.getArgument(0)).setAttemptId(900L);
            return 1;
        }).when(attemptMapper).insert(any(ExamAttempt.class));
        StartExamDTO request = new StartExamDTO();
        request.setSessionId("session-1");

        ExamAttemptVO result = service.start(10L, request, "start-key", "request-1",
                "192.0.2.1", "Test Browser");

        assertEquals(900L, result.getAttemptId());
        assertEquals(NOW_UTC.plusMinutes(90), result.getDeadlineAt());
        assertEquals(1, result.getQuestions().size());
        assertEquals("Problem statement", result.getQuestions().get(0).getContent());
        assertEquals("class Main {}", result.getQuestions().get(0).getStarterCode().get("java"));
        ArgumentCaptor<ExamAttempt> attemptCaptor = ArgumentCaptor.forClass(ExamAttempt.class);
        verify(attemptMapper).insert(attemptCaptor.capture());
        assertNotEquals("192.0.2.1", attemptCaptor.getValue().getFirstIpHash());
        assertEquals(64, attemptCaptor.getValue().getFirstIpHash().length());
    }

    @Test
    void saveShouldCreateFirstVersionAndRejectStaleOverwrite() {
        ExamAttempt attempt = inProgressAttempt(NOW_UTC.plusMinutes(30));
        when(attemptMapper.selectByIdForUpdate(900L)).thenReturn(attempt);
        when(versionQuestionMapper.selectById(801L)).thenReturn(question());
        when(answerMapper.selectOne(any())).thenReturn(null);
        doAnswer(invocation -> {
            ((ExamAnswer) invocation.getArgument(0)).setAnswerId(910L);
            return 1;
        }).when(answerMapper).insert(any(ExamAnswer.class));
        SaveAnswerDTO request = answerRequest(0, "class Main { public static void main(String[] args) {} }");

        ExamAnswerVO result = service.saveAnswer(900L, 801L, request);

        assertEquals(1, result.getAnswerVersion());
        assertEquals(64, result.getContentHash().length());

        ExamAnswer existing = answer(2);
        when(answerMapper.selectOne(any())).thenReturn(existing);
        ServiceException conflict = assertThrows(ServiceException.class,
                () -> service.saveAnswer(900L, 801L, answerRequest(1, "older")));
        assertEquals(ResultCode.EXAM_ANSWER_VERSION_CONFLICT, conflict.getResultCode());
        verify(answerMapper, never()).updateById(existing);
    }

    @Test
    void expiredSaveShouldFinalizeAndFreezeBeforeReturningExpiryError() {
        ExamAttempt attempt = inProgressAttempt(NOW_UTC);
        when(attemptMapper.selectByIdForUpdate(900L)).thenReturn(attempt);
        when(gradeMapper.selectCount(any())).thenReturn(0L);
        when(versionQuestionMapper.selectList(any())).thenReturn(List.of(question()));

        assertThrows(ExamAttemptExpiredException.class,
                () -> service.saveAnswer(900L, 801L, answerRequest(0, "code")));

        assertEquals(ExamAttemptStatus.TIMED_OUT.getCode(), attempt.getStatus());
        assertEquals("DEADLINE", attempt.getFinalizationReason());
        verify(attemptMapper).updateById(attempt);
        verify(answerMapper).update(any(), any());
        verify(gradeMapper).insert(any(ExamGrade.class));
        verify(versionQuestionMapper, never()).selectById(any());
    }

    @Test
    void formalSubmissionShouldUseFrozenAnswerAndSnapshotJudgeCases() {
        ExamAttempt attempt = inProgressAttempt(NOW_UTC.plusMinutes(30));
        ExamAnswer answer = answer(3);
        when(userSubmitMapper.selectOne(any())).thenReturn(null);
        when(attemptMapper.selectByIdForUpdate(900L)).thenReturn(attempt);
        when(versionMapper.selectById(800L)).thenReturn(version());
        when(versionQuestionMapper.selectById(801L)).thenReturn(question());
        when(answerMapper.selectOne(any())).thenReturn(answer);
        when(userSubmitMapper.selectCount(any())).thenReturn(0L);
        doAnswer(invocation -> {
            ((UserSubmit) invocation.getArgument(0)).setSubmitId(920L);
            return 1;
        }).when(userSubmitMapper).insert(any(UserSubmit.class));
        ExamSubmissionDTO request = new ExamSubmissionDTO();
        request.setVersionQuestionId(801L);
        request.setAnswerVersion(3);
        request.setSubmitKind("FORMAL");

        ExamSubmissionVO result = service.submit(900L, request, "judge-request-1");

        assertEquals(9, result.getRemainingFormalSubmissions());
        ArgumentCaptor<UserSubmit> submitCaptor = ArgumentCaptor.forClass(UserSubmit.class);
        ArgumentCaptor<JudgeSubmitDTO> payloadCaptor = ArgumentCaptor.forClass(JudgeSubmitDTO.class);
        InOrder order = inOrder(userSubmitMapper, judgeProducer);
        order.verify(userSubmitMapper).insert(submitCaptor.capture());
        order.verify(judgeProducer).produceMsg(payloadCaptor.capture());
        UserSubmit saved = submitCaptor.getValue();
        JudgeSubmitDTO payload = payloadCaptor.getValue();
        assertEquals(900L, saved.getAttemptId());
        assertEquals(801L, saved.getVersionQuestionId());
        assertEquals(910L, saved.getAnswerId());
        assertEquals(3, saved.getAnswerVersion());
        assertEquals(List.of("1 2"), payload.getInputList());
        assertEquals(List.of("3"), payload.getOutputList());
        assertEquals("trusted code", payload.getUserCode());
    }

    @Test
    void finalizeShouldFreezeAnswersAndCreateWaitingGrade() {
        ExamAttempt attempt = inProgressAttempt(NOW_UTC.plusMinutes(30));
        when(commandMapper.selectOne(any())).thenReturn(null);
        when(attemptMapper.selectByIdForUpdate(900L)).thenReturn(attempt);
        when(gradeMapper.selectCount(any())).thenReturn(0L);
        when(versionQuestionMapper.selectList(any())).thenReturn(List.of(question()));
        when(gradeMapper.selectOne(any())).thenReturn(null);

        ExamFinalizeVO result = service.finalizeAttempt(900L, "final-key", "request-final");

        assertEquals("SUBMITTED", result.getStatus());
        assertEquals("CANDIDATE_SUBMIT", result.getFinalizationReason());
        assertFalse(result.isReplayed());
        verify(answerMapper).update(any(), any());
        ArgumentCaptor<ExamGrade> gradeCaptor = ArgumentCaptor.forClass(ExamGrade.class);
        verify(gradeMapper).insert(gradeCaptor.capture());
        assertEquals(100, gradeCaptor.getValue().getMaxScore());
    }

    private void stubStartDependencies() {
        when(commandMapper.selectOne(any())).thenReturn(null);
        when(examMapper.selectByIdForUpdate(10L)).thenReturn(exam());
        when(versionMapper.selectById(800L)).thenReturn(version());
        UserExam authorization = new UserExam();
        authorization.setAuthorizationStatus(1);
        when(userExamMapper.selectOne(any())).thenReturn(authorization);
        User user = new User();
        user.setStatus(1);
        when(userMapper.selectById(99L)).thenReturn(user);
        when(attemptMapper.selectOne(any())).thenReturn(null);
        when(versionQuestionMapper.selectList(any())).thenReturn(List.of(question()));
        when(answerMapper.selectList(any())).thenReturn(List.of());
    }

    private Exam exam() {
        Exam exam = new Exam();
        exam.setExamId(10L);
        exam.setStatus(ExamStatus.ACTIVE.getCode());
        exam.setCurrentVersionId(800L);
        exam.setStartTime(NOW_UTC.minusMinutes(1));
        exam.setEndTime(NOW_UTC.plusHours(2));
        exam.setRowVersion(1);
        return exam;
    }

    private ExamVersion version() {
        ExamVersion version = new ExamVersion();
        version.setVersionId(800L);
        version.setExamId(10L);
        version.setTitle("Trusted exam");
        version.setDescription("Instructions");
        version.setStartTime(NOW_UTC.minusMinutes(1));
        version.setLatestStartTime(NOW_UTC.plusMinutes(30));
        version.setEndTime(NOW_UTC.plusHours(2));
        version.setDurationMinutes(90);
        version.setTimezone("Asia/Shanghai");
        version.setMaxFormalSubmissions(10);
        return version;
    }

    private ExamVersionQuestion question() {
        ExamVersionQuestion question = new ExamVersionQuestion();
        question.setVersionQuestionId(801L);
        question.setVersionId(800L);
        question.setQuestionId(20L);
        question.setQuestionOrder(1);
        question.setScore(100);
        question.setRequiredFlag(1);
        question.setQuestionType("PROGRAMMING");
        question.setTitle("A + B");
        question.setContent("Problem statement");
        question.setTimeLimit(1000L);
        question.setSpaceLimit(131072L);
        question.setQuestionCase("[{\"input\":\"1 2\",\"output\":\"3\"}]");
        question.setAllowedLanguagesJson("[\"java\"]");
        question.setStarterCodeJson("{\"java\":\"class Main {}\"}");
        return question;
    }

    private ExamAttempt inProgressAttempt(LocalDateTime deadline) {
        ExamAttempt attempt = new ExamAttempt();
        attempt.setAttemptId(900L);
        attempt.setExamId(10L);
        attempt.setVersionId(800L);
        attempt.setUserId(99L);
        attempt.setStatus(ExamAttemptStatus.IN_PROGRESS.getCode());
        attempt.setRowVersion(0);
        attempt.setStartedTime(NOW_UTC.minusMinutes(10));
        attempt.setDeadlineTime(deadline);
        attempt.setLastActiveTime(NOW_UTC.minusMinutes(1));
        return attempt;
    }

    private ExamAnswer answer(int version) {
        ExamAnswer answer = new ExamAnswer();
        answer.setAnswerId(910L);
        answer.setAttemptId(900L);
        answer.setVersionQuestionId(801L);
        answer.setAnswerType("CODE");
        answer.setLanguageCode("java");
        answer.setAnswerContent("trusted code");
        answer.setContentHash("a".repeat(64));
        answer.setAnswerVersion(version);
        answer.setSavedTime(NOW_UTC.minusMinutes(1));
        return answer;
    }

    private SaveAnswerDTO answerRequest(int expectedVersion, String content) {
        SaveAnswerDTO request = new SaveAnswerDTO();
        request.setExpectedVersion(expectedVersion);
        request.setAnswerType("CODE");
        request.setLanguage("java");
        request.setContent(content);
        return request;
    }
}
