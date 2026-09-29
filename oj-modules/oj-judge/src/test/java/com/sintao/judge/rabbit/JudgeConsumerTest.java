package com.sintao.judge.rabbit;

import com.sintao.api.domain.dto.JudgeSubmitDTO;
import com.sintao.common.core.constants.RabbitMQConstants;
import com.sintao.common.core.enums.JudgeAsyncStatus;
import com.sintao.common.core.enums.JudgeTaskType;
import com.sintao.common.redis.service.JudgeResultPushService;
import com.sintao.common.redis.service.JudgeRuntimeStateService;
import com.sintao.judge.config.JudgeLockProperties;
import com.sintao.judge.domain.UserSubmit;
import com.sintao.judge.mapper.UserSubmitMapper;
import com.sintao.judge.scheduler.LocalJudgeScheduler;
import com.sintao.judge.service.IJudgeService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.Spy;
import org.mockito.ArgumentCaptor;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessagePostProcessor;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.amqp.rabbit.connection.CorrelationData;
import org.springframework.amqp.rabbit.core.RabbitTemplate;

import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.TimeUnit;

import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class JudgeConsumerTest {

    @Mock
    private IJudgeService judgeService;

    @Mock
    private UserSubmitMapper userSubmitMapper;

    @Mock
    private RabbitTemplate rabbitTemplate;

    @Mock
    private JudgeRuntimeStateService judgeRuntimeStateService;

    @Mock
    private JudgeResultPushService judgeResultPushService;

    @Mock
    private LocalJudgeScheduler localJudgeScheduler;

    @Spy
    private JudgeLockProperties judgeLockProperties = new JudgeLockProperties(30, 10);

    @InjectMocks
    private JudgeConsumer judgeConsumer;

    @BeforeEach
    void runScheduledWorkInline() {
        when(localJudgeScheduler.submit(any(JudgeTaskType.class), any(), any())).thenAnswer(invocation -> {
            Runnable task = invocation.getArgument(2);
            try {
                task.run();
                return CompletableFuture.completedFuture(null);
            } catch (Throwable throwable) {
                return CompletableFuture.failedFuture(throwable);
            }
        });
    }

    @Test
    void consumeShouldCompleteTerminalMessageWithoutJudging() throws Exception {
        JudgeSubmitDTO dto = buildSubmit("req-1");
        UserSubmit userSubmit = new UserSubmit();
        userSubmit.setJudgeStatus(JudgeAsyncStatus.SUCCESS.getValue());
        when(userSubmitMapper.selectOne(any())).thenReturn(userSubmit);

        judgeConsumer.consume(dto, buildMessage(11L, 0)).get(5, TimeUnit.SECONDS);

        verify(judgeService, never()).doJudgeJavaCode(any());
    }

    @Test
    void consumeShouldRetryWhenRequestLockIsBusy() throws Exception {
        JudgeSubmitDTO dto = buildSubmit("req-2");
        UserSubmit userSubmit = new UserSubmit();
        userSubmit.setJudgeStatus(JudgeAsyncStatus.WAITING.getValue());
        when(userSubmitMapper.selectOne(any())).thenReturn(userSubmit);
        when(judgeRuntimeStateService.tryLock(anyString(), anyString(), any(Long.class))).thenReturn(false);
        mockBrokerAck();

        judgeConsumer.consume(dto, buildMessage(12L, 0)).get(5, TimeUnit.SECONDS);

        verify(judgeRuntimeStateService, never()).markRetryWaiting(anyString(), any(), anyString());
        ArgumentCaptor<MessagePostProcessor> postProcessor = ArgumentCaptor.forClass(MessagePostProcessor.class);
        verify(rabbitTemplate).convertAndSend(anyString(), anyString(), any(JudgeSubmitDTO.class),
                postProcessor.capture(), any(CorrelationData.class));
        Message retried = postProcessor.getValue().postProcessMessage(buildMessage(14L, 0));
        org.junit.jupiter.api.Assertions.assertEquals(0, retried.getMessageProperties().getHeaders().get("retryCount"));
    }

    @Test
    void consumeShouldFailWhenRetryMessageCannotBePublished() {
        JudgeSubmitDTO dto = buildSubmit("req-publish-failed");
        UserSubmit userSubmit = new UserSubmit();
        userSubmit.setJudgeStatus(JudgeAsyncStatus.WAITING.getValue());
        when(userSubmitMapper.selectOne(any())).thenReturn(userSubmit);
        when(judgeRuntimeStateService.tryLock(anyString(), anyString(), any(Long.class))).thenReturn(false);
        mockBrokerNack();

        ExecutionException exception = assertThrows(
                ExecutionException.class,
                () -> judgeConsumer.consume(dto, buildMessage(15L, 0)).get(5, TimeUnit.SECONDS)
        );

        assertInstanceOf(IllegalStateException.class, exception.getCause());
    }

    @Test
    void batchLockContentionShouldReturnToBatchRetryQueue() throws Exception {
        JudgeSubmitDTO dto = buildSubmit("req-batch");
        dto.setExamId(88L);
        dto.setTaskType(JudgeTaskType.BATCH);
        UserSubmit userSubmit = new UserSubmit();
        userSubmit.setJudgeStatus(JudgeAsyncStatus.WAITING.getValue());
        when(userSubmitMapper.selectOne(any())).thenReturn(userSubmit);
        when(judgeRuntimeStateService.tryLock(anyString(), anyString(), any(Long.class))).thenReturn(false);
        mockBrokerAck();

        judgeConsumer.consumeBatch(dto, buildMessage(16L, 0)).get(5, TimeUnit.SECONDS);

        verify(localJudgeScheduler).submit(eq(JudgeTaskType.BATCH), eq("req-batch"), any());
        verify(rabbitTemplate).convertAndSend(
                eq(RabbitMQConstants.OJ_JUDGE_DLX_EXCHANGE),
                eq(RabbitMQConstants.JUDGE_BATCH_RETRY_KEY),
                eq(dto),
                any(MessagePostProcessor.class),
                any(CorrelationData.class)
        );
    }

    @Test
    void consumeShouldDeadLetterWhenJudgeThrowsNonRetryableException() throws Exception {
        JudgeSubmitDTO dto = buildSubmit("req-3");
        UserSubmit userSubmit = new UserSubmit();
        userSubmit.setJudgeStatus(JudgeAsyncStatus.WAITING.getValue());
        when(userSubmitMapper.selectOne(any())).thenReturn(userSubmit);
        when(judgeRuntimeStateService.tryLock(anyString(), anyString(), any(Long.class))).thenReturn(true);
        when(userSubmitMapper.update(any(), any())).thenReturn(1);
        when(judgeService.doJudgeJavaCode(dto)).thenThrow(new IllegalArgumentException("bad request"));
        mockBrokerAck();

        judgeConsumer.consume(dto, buildMessage(13L, 0)).get(5, TimeUnit.SECONDS);

        verify(judgeRuntimeStateService).markDeadLetter("req-3", 1, "bad request");
        verify(judgeResultPushService).publishFinalResult(any());
        ArgumentCaptor<String> owner = ArgumentCaptor.forClass(String.class);
        verify(judgeRuntimeStateService).tryLock(org.mockito.ArgumentMatchers.eq("req-3"), owner.capture(),
                org.mockito.ArgumentMatchers.eq(30L));
        verify(judgeRuntimeStateService).unlock("req-3", owner.getValue());
    }

    private JudgeSubmitDTO buildSubmit(String requestId) {
        JudgeSubmitDTO dto = new JudgeSubmitDTO();
        dto.setRequestId(requestId);
        dto.setUserId(99L);
        dto.setQuestionId(1L);
        return dto;
    }

    private Message buildMessage(long deliveryTag, int retryCount) {
        MessageProperties properties = new MessageProperties();
        properties.setDeliveryTag(deliveryTag);
        properties.setHeader("retryCount", retryCount);
        return new Message(new byte[0], properties);
    }

    private void mockBrokerAck() {
        doAnswer(invocation -> {
            CorrelationData correlationData = invocation.getArgument(4);
            correlationData.getFuture().complete(new CorrelationData.Confirm(true, null));
            return null;
        }).when(rabbitTemplate).convertAndSend(
                anyString(),
                anyString(),
                any(JudgeSubmitDTO.class),
                any(MessagePostProcessor.class),
                any(CorrelationData.class)
        );
    }

    private void mockBrokerNack() {
        doAnswer(invocation -> {
            CorrelationData correlationData = invocation.getArgument(4);
            correlationData.getFuture().complete(new CorrelationData.Confirm(false, "broker nack"));
            return null;
        }).when(rabbitTemplate).convertAndSend(
                anyString(),
                anyString(),
                any(JudgeSubmitDTO.class),
                any(MessagePostProcessor.class),
                any(CorrelationData.class)
        );
    }
}
