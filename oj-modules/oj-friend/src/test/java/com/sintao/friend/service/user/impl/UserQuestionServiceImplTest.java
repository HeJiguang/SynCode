package com.sintao.friend.service.user.impl;

import com.sintao.common.core.constants.Constants;
import com.sintao.common.core.enums.ProgramType;
import com.sintao.common.core.enums.QuestionResType;
import com.sintao.common.redis.service.JudgeRuntimeStateService;
import com.sintao.common.core.utils.ThreadLocalUtil;
import com.sintao.api.domain.dto.JudgeSubmitDTO;
import com.sintao.friend.domain.question.es.QuestionES;
import com.sintao.friend.domain.user.UserSubmit;
import com.sintao.friend.domain.user.dto.UserSubmitDTO;
import com.sintao.friend.domain.user.vo.UserSubmissionHistoryVO;
import com.sintao.friend.mapper.question.QuestionMapper;
import com.sintao.friend.mapper.user.UserSubmitMapper;
import com.sintao.friend.rabbit.JudgeProducer;
import com.sintao.api.RemoteJudgeService;
import com.sintao.friend.elasticsearch.FriendQuestionRepository;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InjectMocks;
import org.mockito.InOrder;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.lang.reflect.Field;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class UserQuestionServiceImplTest {

    @Mock
    private FriendQuestionRepository questionRepository;

    @Mock
    private QuestionMapper questionMapper;

    @Mock
    private UserSubmitMapper userSubmitMapper;

    @Mock
    private RemoteJudgeService remoteJudgeService;

    @Mock
    private JudgeProducer judgeProducer;

    @Mock
    private JudgeRuntimeStateService judgeRuntimeStateService;

    @InjectMocks
    private UserQuestionServiceImpl userQuestionService;

    @AfterEach
    void tearDown() {
        ThreadLocalUtil.remove();
    }

    @Test
    void submissionHistoryShouldReturnLatestUserSubmissionsForQuestion() {
        ThreadLocalUtil.set(Constants.USER_ID, 99L);

        UserSubmit latest = new UserSubmit();
        latest.setSubmitId(11L);
        latest.setQuestionId(1L);
        latest.setPass(1);
        latest.setScore(100);
        latest.setExeMessage("Accepted");
        latest.setCreateTime(LocalDateTime.of(2026, 3, 26, 12, 10));

        UserSubmit previous = new UserSubmit();
        previous.setSubmitId(10L);
        previous.setQuestionId(1L);
        previous.setPass(0);
        previous.setScore(0);
        previous.setExeMessage("Wrong answer");
        previous.setCreateTime(LocalDateTime.of(2026, 3, 26, 12, 0));

        when(userSubmitMapper.selectSubmissionHistory(99L, null, 1L, 20)).thenReturn(List.of(latest, previous));

        List<UserSubmissionHistoryVO> history = userQuestionService.submissionHistory(null, 1L);

        assertEquals(2, history.size());
        assertEquals(11L, history.get(0).getSubmitId());
        assertEquals("Accepted", history.get(0).getExeMessage());
        assertEquals(10L, history.get(1).getSubmitId());
        assertEquals("Wrong answer", history.get(1).getExeMessage());
    }

    @Test
    void rabbitSubmitShouldPersistAcceptedRequestBeforePublishingMessage() {
        ThreadLocalUtil.set(Constants.USER_ID, 99L);
        UserSubmitDTO submitDTO = new UserSubmitDTO();
        submitDTO.setQuestionId(1L);
        submitDTO.setProgramType(ProgramType.JAVA.getValue());
        submitDTO.setUserCode("class Main { }");
        QuestionES questionES = new QuestionES();
        questionES.setQuestionId(1L);
        questionES.setQuestionCase("[{\"input\":\"1 2\",\"output\":\"3\"}]");
        questionES.setMainFuc("public static void main(String[] args){}");
        when(questionRepository.findById(1L)).thenReturn(Optional.of(questionES));
        when(userSubmitMapper.insert(any(UserSubmit.class))).thenReturn(1);

        userQuestionService.rabbitSubmit(submitDTO);

        ArgumentCaptor<UserSubmit> submitCaptor = ArgumentCaptor.forClass(UserSubmit.class);
        ArgumentCaptor<JudgeSubmitDTO> messageCaptor = ArgumentCaptor.forClass(JudgeSubmitDTO.class);
        InOrder inOrder = inOrder(userSubmitMapper, judgeProducer);
        inOrder.verify(userSubmitMapper).insert(submitCaptor.capture());
        inOrder.verify(judgeProducer).produceMsg(messageCaptor.capture());
        assertNotNull(readField(submitCaptor.getValue(), "requestId"));
        assertEquals(0, readField(submitCaptor.getValue(), "judgeStatus"));
        assertEquals(QuestionResType.IN_JUDGE.getValue(), submitCaptor.getValue().getPass());
        assertEquals("判题中", submitCaptor.getValue().getExeMessage());
        assertEquals(readField(submitCaptor.getValue(), "requestId"), readField(messageCaptor.getValue(), "requestId"));
    }

    private Object readField(Object target, String fieldName) {
        try {
            Field field = target.getClass().getDeclaredField(fieldName);
            field.setAccessible(true);
            return field.get(target);
        } catch (NoSuchFieldException | IllegalAccessException e) {
            throw new AssertionError(e);
        }
    }
}
