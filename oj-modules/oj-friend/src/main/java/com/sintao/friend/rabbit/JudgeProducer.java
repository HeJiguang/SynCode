package com.sintao.friend.rabbit;

import com.sintao.api.domain.dto.JudgeSubmitDTO;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.sintao.common.core.constants.RabbitMQConstants;
import com.sintao.common.core.domain.dto.JudgeResultPushDTO;
import com.sintao.common.core.enums.JudgeAsyncStatus;
import com.sintao.common.core.enums.JudgeTaskType;
import com.sintao.common.core.enums.ResultCode;
import com.sintao.common.redis.service.JudgeResultPushService;
import com.sintao.common.redis.service.JudgeRuntimeStateService;
import com.sintao.common.security.exception.ServiceException;
import com.sintao.friend.domain.user.UserSubmit;
import com.sintao.friend.mapper.user.UserSubmitMapper;
import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.rabbit.connection.CorrelationData;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;

@Component
@Slf4j
public class JudgeProducer {

    @Autowired
    private RabbitTemplate rabbitTemplate;

    @Autowired
    private UserSubmitMapper userSubmitMapper;

    @Autowired
    private JudgeRuntimeStateService judgeRuntimeStateService;

    @Autowired
    private JudgeResultPushService judgeResultPushService;

    @PostConstruct
    public void initCallbacks() {
        rabbitTemplate.setMandatory(true);
        rabbitTemplate.setConfirmCallback((correlationData, ack, cause) -> {
            if (correlationData == null || correlationData.getId() == null) {
                return;
            }
            if (ack && correlationData.getReturned() == null) {
                judgeRuntimeStateService.markPublished(correlationData.getId());
                return;
            }
            String error = correlationData.getReturned() == null ? cause : correlationData.getReturned().getReplyText();
            markDispatchFailed(correlationData.getId(), error);
        });
        rabbitTemplate.setReturnsCallback(returned ->
                markDispatchFailed(returned.getMessage().getMessageProperties().getCorrelationId(), returned.getReplyText()));
    }

    public void produceMsg(JudgeSubmitDTO judgeSubmitDTO) {
        try {
            JudgeTaskType taskType = JudgeTaskType.resolve(
                    judgeSubmitDTO.getTaskType(),
                    judgeSubmitDTO.getExamId()
            );
            judgeSubmitDTO.setTaskType(taskType);
            String routingKey = taskType == JudgeTaskType.BATCH
                    ? RabbitMQConstants.JUDGE_BATCH_KEY
                    : RabbitMQConstants.JUDGE_SUBMIT_KEY;
            CorrelationData correlationData = new CorrelationData(judgeSubmitDTO.getRequestId());
            rabbitTemplate.convertAndSend(
                    RabbitMQConstants.OJ_JUDGE_EXCHANGE,
                    routingKey,
                    judgeSubmitDTO,
                    message -> {
                        message.getMessageProperties().setCorrelationId(judgeSubmitDTO.getRequestId());
                        message.getMessageProperties().setMessageId(judgeSubmitDTO.getRequestId());
                        message.getMessageProperties().setHeader("judgeTaskType", taskType.name());
                        return message;
                    },
                    correlationData
            );
        } catch (Exception e) {
            log.error("Failed to publish judge message", e);
            markDispatchFailed(judgeSubmitDTO.getRequestId(), e.getMessage());
            throw new ServiceException(ResultCode.FAILED_RABBIT_PRODUCE);
        }
    }

    private void markDispatchFailed(String requestId, String lastError) {
        if (requestId == null) {
            return;
        }
        UserSubmit userSubmit = userSubmitMapper.selectOne(new QueryWrapper<UserSubmit>()
                .select("request_id", "user_id")
                .eq("request_id", requestId));
        LocalDateTime finishTime = LocalDateTime.now();
        int updated = userSubmitMapper.update(null, new UpdateWrapper<UserSubmit>()
                .eq("request_id", requestId)
                .eq("judge_status", JudgeAsyncStatus.WAITING.getValue())
                .set("judge_status", JudgeAsyncStatus.DISPATCH_FAILED.getValue())
                .set("last_error", lastError)
                .set("finish_time", finishTime));
        if (updated == 0) {
            return;
        }
        judgeRuntimeStateService.markDispatchFailed(requestId, lastError);
        JudgeResultPushDTO pushDTO = new JudgeResultPushDTO();
        pushDTO.setRequestId(requestId);
        if (userSubmit != null) {
            pushDTO.setUserId(userSubmit.getUserId());
        }
        pushDTO.setAsyncStatus(JudgeAsyncStatus.DISPATCH_FAILED.getValue());
        pushDTO.setLastError(lastError);
        pushDTO.setFinishTime(finishTime);
        judgeResultPushService.publishFinalResult(pushDTO);
    }
}
