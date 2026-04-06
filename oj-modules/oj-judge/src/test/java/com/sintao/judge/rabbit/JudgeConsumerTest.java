package com.sintao.judge.rabbit;

import com.rabbitmq.client.Channel;
import com.sintao.api.domain.dto.JudgeSubmitDTO;
import com.sintao.common.core.enums.JudgeAsyncStatus;
import com.sintao.common.redis.service.JudgeResultPushService;
import com.sintao.common.redis.service.JudgeRuntimeStateService;
import com.sintao.judge.domain.UserSubmit;
import com.sintao.judge.mapper.UserSubmitMapper;
import com.sintao.judge.service.IJudgeService;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessagePostProcessor;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.amqp.rabbit.connection.CorrelationData;
import org.springframework.amqp.rabbit.core.RabbitTemplate;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
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
    private Channel channel;

    @InjectMocks
    private JudgeConsumer judgeConsumer;

    @Test
    void consumeShouldAckTerminalMessageWithoutJudging() throws Exception {
        JudgeSubmitDTO dto = buildSubmit("req-1");
        UserSubmit userSubmit = new UserSubmit();
        userSubmit.setJudgeStatus(JudgeAsyncStatus.SUCCESS.getValue());
        when(userSubmitMapper.selectOne(any())).thenReturn(userSubmit);

        judgeConsumer.consume(dto, buildMessage(11L, 0), channel);

        verify(channel).basicAck(11L, false);
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

        judgeConsumer.consume(dto, buildMessage(12L, 0), channel);

        verify(judgeRuntimeStateService).markRetryWaiting("req-2", 1, "Request already locked");
        verify(channel).basicAck(12L, false);
    }

    @Test
    void consumeShouldDeadLetterWhenJudgeThrowsNonRetryableException() throws Exception {
        JudgeSubmitDTO dto = buildSubmit("req-3");
        UserSubmit userSubmit = new UserSubmit();
        userSubmit.setJudgeStatus(JudgeAsyncStatus.WAITING.getValue());
        when(userSubmitMapper.selectOne(any())).thenReturn(userSubmit);
        when(judgeRuntimeStateService.tryLock(anyString(), anyString(), any(Long.class))).thenReturn(true);
        when(judgeService.doJudgeJavaCode(dto)).thenThrow(new IllegalArgumentException("bad request"));
        mockBrokerAck();

        judgeConsumer.consume(dto, buildMessage(13L, 0), channel);

        verify(judgeRuntimeStateService).markDeadLetter("req-3", 1, "bad request");
        verify(judgeResultPushService).publishFinalResult(any());
        verify(channel).basicAck(13L, false);
        verify(judgeRuntimeStateService).unlock("req-3");
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
}
