package com.sintao.judge.rabbit;

import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.sintao.common.core.enums.JudgeAsyncStatus;
import com.sintao.common.redis.service.JudgeResultPushService;
import com.sintao.common.redis.service.JudgeRuntimeStateService;
import com.sintao.judge.domain.UserSubmit;
import com.sintao.judge.mapper.UserSubmitMapper;
import org.junit.jupiter.api.Test;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.test.util.ReflectionTestUtils;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class JudgeConsumerPushTest {

    @Test
    void deadLetterPathPublishesFinalResultEvent() {
        JudgeConsumer consumer = new JudgeConsumer();
        UserSubmitMapper userSubmitMapper = mock(UserSubmitMapper.class);
        JudgeRuntimeStateService judgeRuntimeStateService = mock(JudgeRuntimeStateService.class);
        JudgeResultPushService judgeResultPushService = mock(JudgeResultPushService.class);
        UserSubmit userSubmit = new UserSubmit();
        userSubmit.setRequestId("req-1");
        userSubmit.setUserId(1001L);
        when(userSubmitMapper.selectOne(any())).thenReturn(userSubmit);
        when(userSubmitMapper.update(any(), any(UpdateWrapper.class))).thenReturn(1);
        ReflectionTestUtils.setField(consumer, "userSubmitMapper", userSubmitMapper);
        ReflectionTestUtils.setField(consumer, "judgeRuntimeStateService", judgeRuntimeStateService);
        ReflectionTestUtils.setField(consumer, "judgeResultPushService", judgeResultPushService);
        ReflectionTestUtils.setField(consumer, "rabbitTemplate", mock(RabbitTemplate.class));

        ReflectionTestUtils.invokeMethod(consumer, "markDeadLetter", "req-1", 3, "judge timeout");

        verify(userSubmitMapper).update(any(), any(UpdateWrapper.class));
        verify(judgeResultPushService).publishFinalResult(argThat(dto ->
                "req-1".equals(dto.getRequestId())
                        && Long.valueOf(1001L).equals(dto.getUserId())
                        && Integer.valueOf(JudgeAsyncStatus.DEAD_LETTER.getValue()).equals(dto.getAsyncStatus())
                        && "judge timeout".equals(dto.getLastError())));
    }
}
