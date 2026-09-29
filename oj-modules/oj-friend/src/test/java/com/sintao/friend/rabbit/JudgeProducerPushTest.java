package com.sintao.friend.rabbit;

import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.sintao.api.domain.dto.JudgeSubmitDTO;
import com.sintao.common.core.constants.RabbitMQConstants;
import com.sintao.common.core.enums.JudgeAsyncStatus;
import com.sintao.common.core.enums.JudgeTaskType;
import com.sintao.common.redis.service.JudgeResultPushService;
import com.sintao.common.redis.service.JudgeRuntimeStateService;
import com.sintao.friend.domain.user.UserSubmit;
import com.sintao.friend.mapper.user.UserSubmitMapper;
import org.junit.jupiter.api.Test;
import org.springframework.amqp.core.MessagePostProcessor;
import org.springframework.amqp.rabbit.connection.CorrelationData;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.test.util.ReflectionTestUtils;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class JudgeProducerPushTest {

    @Test
    void examSubmissionShouldRouteToBatchQueue() {
        JudgeProducer producer = new JudgeProducer();
        RabbitTemplate rabbitTemplate = mock(RabbitTemplate.class);
        ReflectionTestUtils.setField(producer, "rabbitTemplate", rabbitTemplate);
        JudgeSubmitDTO payload = new JudgeSubmitDTO();
        payload.setRequestId("req-batch");
        payload.setExamId(99L);

        producer.produceMsg(payload);

        verify(rabbitTemplate).convertAndSend(
                eq(RabbitMQConstants.OJ_JUDGE_EXCHANGE),
                eq(RabbitMQConstants.JUDGE_BATCH_KEY),
                eq(payload),
                any(MessagePostProcessor.class),
                any(CorrelationData.class)
        );
        org.junit.jupiter.api.Assertions.assertEquals(JudgeTaskType.BATCH, payload.getTaskType());
    }

    @Test
    void practiceSubmissionShouldRemainRealtimeByDefault() {
        JudgeProducer producer = new JudgeProducer();
        RabbitTemplate rabbitTemplate = mock(RabbitTemplate.class);
        ReflectionTestUtils.setField(producer, "rabbitTemplate", rabbitTemplate);
        JudgeSubmitDTO payload = new JudgeSubmitDTO();
        payload.setRequestId("req-realtime");

        producer.produceMsg(payload);

        verify(rabbitTemplate).convertAndSend(
                eq(RabbitMQConstants.OJ_JUDGE_EXCHANGE),
                eq(RabbitMQConstants.JUDGE_SUBMIT_KEY),
                eq(payload),
                any(MessagePostProcessor.class),
                any(CorrelationData.class)
        );
        org.junit.jupiter.api.Assertions.assertEquals(JudgeTaskType.REALTIME, payload.getTaskType());
    }

    @Test
    void dispatchFailurePublishesFinalResultEvent() {
        JudgeProducer producer = new JudgeProducer();
        UserSubmitMapper userSubmitMapper = mock(UserSubmitMapper.class);
        JudgeRuntimeStateService judgeRuntimeStateService = mock(JudgeRuntimeStateService.class);
        JudgeResultPushService judgeResultPushService = mock(JudgeResultPushService.class);
        UserSubmit userSubmit = new UserSubmit();
        userSubmit.setRequestId("req-1");
        userSubmit.setUserId(1001L);
        when(userSubmitMapper.selectOne(any())).thenReturn(userSubmit);
        when(userSubmitMapper.update(any(), any(UpdateWrapper.class))).thenReturn(1);
        ReflectionTestUtils.setField(producer, "userSubmitMapper", userSubmitMapper);
        ReflectionTestUtils.setField(producer, "judgeRuntimeStateService", judgeRuntimeStateService);
        ReflectionTestUtils.setField(producer, "judgeResultPushService", judgeResultPushService);

        ReflectionTestUtils.invokeMethod(producer, "markDispatchFailed", "req-1", "confirm failed");

        verify(userSubmitMapper).update(any(), any(UpdateWrapper.class));
        verify(judgeResultPushService).publishFinalResult(argThat(dto ->
                "req-1".equals(dto.getRequestId())
                        && Long.valueOf(1001L).equals(dto.getUserId())
                        && Integer.valueOf(JudgeAsyncStatus.DISPATCH_FAILED.getValue()).equals(dto.getAsyncStatus())
                        && "confirm failed".equals(dto.getLastError())));
    }

    @Test
    void dispatchFailureDoesNotOverwriteCompletedResult() {
        JudgeProducer producer = new JudgeProducer();
        UserSubmitMapper mapper = mock(UserSubmitMapper.class);
        JudgeResultPushService pushService = mock(JudgeResultPushService.class);
        ReflectionTestUtils.setField(producer, "userSubmitMapper", mapper);
        ReflectionTestUtils.setField(producer, "judgeRuntimeStateService", mock(JudgeRuntimeStateService.class));
        ReflectionTestUtils.setField(producer, "judgeResultPushService", pushService);

        ReflectionTestUtils.invokeMethod(producer, "markDispatchFailed", "req-done", "late return");

        verify(mapper).update(any(), any(UpdateWrapper.class));
        verify(pushService, never()).publishFinalResult(any());
    }
}
