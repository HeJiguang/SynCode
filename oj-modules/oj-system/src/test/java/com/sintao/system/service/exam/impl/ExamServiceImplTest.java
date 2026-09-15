package com.sintao.system.service.exam.impl;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.sintao.common.core.constants.Constants;
import com.sintao.common.core.enums.ExamStatus;
import com.sintao.common.core.enums.ResultCode;
import com.sintao.common.core.utils.ThreadLocalUtil;
import com.sintao.common.security.exception.ServiceException;
import com.sintao.system.domain.exam.Exam;
import com.sintao.system.domain.exam.ExamAuditEvent;
import com.sintao.system.domain.exam.ExamCommand;
import com.sintao.system.domain.exam.ExamQuestion;
import com.sintao.system.domain.exam.ExamVersion;
import com.sintao.system.domain.exam.ExamVersionQuestion;
import com.sintao.system.domain.exam.dto.ExamAddDTO;
import com.sintao.system.domain.exam.vo.ExamPublicationVO;
import com.sintao.system.domain.question.Question;
import com.sintao.system.manager.ExamCacheManager;
import com.sintao.system.mapper.exam.ExamAuditEventMapper;
import com.sintao.system.mapper.exam.ExamAttemptMapper;
import com.sintao.system.mapper.exam.ExamCommandMapper;
import com.sintao.system.mapper.exam.ExamMapper;
import com.sintao.system.mapper.exam.ExamQuestionMapper;
import com.sintao.system.mapper.exam.ExamVersionMapper;
import com.sintao.system.mapper.exam.ExamVersionQuestionMapper;
import com.sintao.system.mapper.question.QuestionMapper;
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
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class ExamServiceImplTest {

    private static final Instant NOW = Instant.parse("2026-09-14T09:00:00Z");

    @Mock private ExamMapper examMapper;
    @Mock private QuestionMapper questionMapper;
    @Mock private ExamQuestionMapper examQuestionMapper;
    @Mock private ExamVersionMapper examVersionMapper;
    @Mock private ExamVersionQuestionMapper examVersionQuestionMapper;
    @Mock private ExamCommandMapper examCommandMapper;
    @Mock private ExamAuditEventMapper examAuditEventMapper;
    @Mock private ExamAttemptMapper examAttemptMapper;
    @Mock private ExamCacheManager examCacheManager;

    private ExamServiceImpl service;
    private ObjectMapper objectMapper;

    @BeforeEach
    void setUp() {
        objectMapper = new ObjectMapper().findAndRegisterModules();
        service = new ExamServiceImpl(
                examMapper, questionMapper, examQuestionMapper, examVersionMapper,
                examVersionQuestionMapper, examCommandMapper, examAuditEventMapper, examAttemptMapper,
                examCacheManager, objectMapper, Clock.fixed(NOW, ZoneOffset.UTC));
        ThreadLocalUtil.set(Constants.USER_ID, 77L);
    }

    @AfterEach
    void tearDown() {
        ThreadLocalUtil.remove();
    }

    @Test
    void addShouldNormalizeLegacyRequestIntoCompleteDraftRules() {
        ExamAddDTO request = new ExamAddDTO();
        request.setTitle("Lab recruitment");
        request.setStartTime(LocalDateTime.of(2026, 9, 15, 9, 0));
        request.setEndTime(LocalDateTime.of(2026, 9, 15, 11, 0));
        when(examMapper.selectList(any())).thenReturn(List.of());
        doAnswer(invocation -> {
            ((Exam) invocation.getArgument(0)).setExamId(100L);
            return 1;
        }).when(examMapper).insert(any(Exam.class));

        assertEquals("100", service.add(request));

        ArgumentCaptor<Exam> captor = ArgumentCaptor.forClass(Exam.class);
        verify(examMapper).insert(captor.capture());
        Exam saved = captor.getValue();
        assertEquals(ExamStatus.DRAFT.getCode(), saved.getStatus());
        assertEquals(120, saved.getDurationMinutes());
        assertEquals(saved.getEndTime(), saved.getLatestStartTime());
        assertEquals("Asia/Shanghai", saved.getTimezone());
        assertEquals("MANUAL", saved.getResultReleasePolicy());
    }

    @Test
    void publishShouldFreezeVersionQuestionsAndAuditInOneServiceTransaction() {
        Exam exam = validDraft();
        ExamQuestion relation = relation();
        Question question = validQuestion();
        when(examCommandMapper.selectOne(any())).thenReturn(null);
        when(examMapper.selectByIdForUpdate(10L)).thenReturn(exam);
        when(examQuestionMapper.selectList(any())).thenReturn(List.of(relation));
        when(questionMapper.selectBatchIds(any())).thenReturn(List.of(question));
        doAnswer(invocation -> {
            ((ExamVersion) invocation.getArgument(0)).setVersionId(800L);
            return 1;
        }).when(examVersionMapper).insert(any(ExamVersion.class));
        when(examVersionQuestionMapper.insert(any())).thenReturn(1);
        when(examMapper.updateById(any())).thenReturn(1);

        ExamPublicationVO result = service.publish(10L, "publish-key-1", "request-1");

        assertEquals(800L, result.getVersionId());
        assertEquals(1, result.getVersionNo());
        assertFalse(result.isReplayed());
        assertEquals(64, result.getContentHash().length());
        ArgumentCaptor<ExamVersionQuestion> questionCaptor = ArgumentCaptor.forClass(ExamVersionQuestion.class);
        verify(examVersionQuestionMapper).insert(questionCaptor.capture());
        ExamVersionQuestion snapshot = questionCaptor.getValue();
        assertEquals(800L, snapshot.getVersionId());
        assertEquals("[{\"input\":\"1 2\",\"output\":\"3\"}]", snapshot.getQuestionCase());
        assertEquals(40, snapshot.getScore());
        assertEquals("[\"java\"]", snapshot.getAllowedLanguagesJson());
        assertEquals(64, snapshot.getContentHash().length());
        ArgumentCaptor<ExamAuditEvent> auditCaptor = ArgumentCaptor.forClass(ExamAuditEvent.class);
        verify(examAuditEventMapper).insert(auditCaptor.capture());
        assertEquals("EXAM_PUBLISHED", auditCaptor.getValue().getAction());
        verify(examCacheManager).addCache(exam);
    }

    @Test
    void publishShouldReturnAllSafeValidationViolations() {
        Exam exam = validDraft();
        exam.setStartTime(LocalDateTime.of(2026, 9, 14, 8, 0));
        when(examCommandMapper.selectOne(any())).thenReturn(null);
        when(examMapper.selectByIdForUpdate(10L)).thenReturn(exam);
        when(examQuestionMapper.selectList(any())).thenReturn(List.of());

        ServiceException exception = assertThrows(ServiceException.class,
                () -> service.publish(10L, "publish-key-2", "request-2"));

        assertEquals(ResultCode.EXAM_PUBLISH_VALIDATION_FAILED, exception.getResultCode());
        assertNotNull(exception.getDetails());
        String details = exception.getDetails().toString();
        assertTrue(details.contains("startTime"));
        assertTrue(details.contains("questions"));
        verify(examVersionMapper, never()).insert(any());
        verify(examMapper, never()).updateById(any());
    }

    @Test
    void publishShouldReplaySucceededCommandWithoutCreatingAnotherVersion() throws Exception {
        ExamPublicationVO original = new ExamPublicationVO();
        original.setVersionId(800L);
        original.setVersionNo(2);
        original.setContentHash("a".repeat(64));
        original.setPublishedBy(77L);
        original.setPublishedAt(LocalDateTime.of(2026, 9, 14, 9, 0));
        ExamCommand command = new ExamCommand();
        command.setCommandId(90L);
        command.setCommandType("PUBLISH");
        command.setActorId(77L);
        command.setIdempotencyKey("publish-key-3");
        command.setRequestHash(cn.hutool.crypto.digest.DigestUtil.sha256Hex("PUBLISH:10"));
        command.setStatus(1);
        command.setResponseJson(objectMapper.writeValueAsString(original));
        when(examCommandMapper.selectOne(any())).thenReturn(command);

        ExamPublicationVO replay = service.publish(10L, "publish-key-3", "request-3");

        assertTrue(replay.isReplayed());
        assertEquals(800L, replay.getVersionId());
        verify(examMapper, never()).selectByIdForUpdate(any());
        verify(examVersionMapper, never()).insert(any());
    }

    @Test
    void withdrawShouldRejectWhenAnyAttemptExists() {
        Exam published = validDraft();
        published.setStatus(ExamStatus.PUBLISHED.getCode());
        when(examMapper.selectByIdForUpdate(10L)).thenReturn(published);
        when(examAttemptMapper.selectCount(any())).thenReturn(1L);

        ServiceException exception = assertThrows(ServiceException.class,
                () -> service.cancelPublish(10L));

        assertEquals(ResultCode.EXAM_STATE_CONFLICT, exception.getResultCode());
        verify(examMapper, never()).updateById(any());
        verify(examAuditEventMapper, never()).insert(any());
    }

    private Exam validDraft() {
        Exam exam = new Exam();
        exam.setExamId(10L);
        exam.setTitle("Trusted exam");
        exam.setDescription("Instructions");
        exam.setStartTime(LocalDateTime.of(2026, 9, 15, 9, 0));
        exam.setLatestStartTime(LocalDateTime.of(2026, 9, 15, 9, 30));
        exam.setEndTime(LocalDateTime.of(2026, 9, 15, 11, 0));
        exam.setDurationMinutes(90);
        exam.setTimezone("Asia/Shanghai");
        exam.setMaxFormalSubmissions(10);
        exam.setResultReleasePolicy("MANUAL");
        exam.setVersionNo(0);
        exam.setRowVersion(0);
        exam.setStatus(ExamStatus.DRAFT.getCode());
        return exam;
    }

    private ExamQuestion relation() {
        ExamQuestion relation = new ExamQuestion();
        relation.setExamId(10L);
        relation.setQuestionId(20L);
        relation.setQuestionOrder(1);
        relation.setScore(40);
        relation.setRequiredFlag(1);
        relation.setQuestionType("PROGRAMMING");
        return relation;
    }

    private Question validQuestion() {
        Question question = new Question();
        question.setQuestionId(20L);
        question.setTitle("A + B");
        question.setContent("Read two integers and print the sum.");
        question.setTimeLimit(1000L);
        question.setSpaceLimit(131072L);
        question.setQuestionCase("[{\"input\":\"1 2\",\"output\":\"3\"}]");
        question.setDefaultCode("public class Main {}");
        question.setMainFuc("public static void main(String[] args)");
        question.setUpdateTime(LocalDateTime.of(2026, 9, 1, 0, 0));
        return question;
    }
}
