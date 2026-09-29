package com.sintao.judge.rabbit;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.UpdateWrapper;
import com.sintao.api.domain.dto.JudgeSubmitDTO;
import com.sintao.common.core.constants.RabbitMQConstants;
import com.sintao.common.core.domain.dto.JudgeResultPushDTO;
import com.sintao.common.core.enums.JudgeAsyncStatus;
import com.sintao.common.core.enums.JudgeTaskType;
import com.sintao.common.redis.service.JudgeResultPushService;
import com.sintao.common.redis.service.JudgeRuntimeStateService;
import com.sintao.judge.config.JudgeLockProperties;
import com.sintao.judge.domain.UserSubmit;
import com.sintao.judge.mapper.UserSubmitMapper;
import com.sintao.judge.scheduler.LocalJudgeScheduler;
import com.sintao.judge.service.IJudgeService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.amqp.rabbit.connection.CorrelationData;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicLong;
import jakarta.annotation.PreDestroy;

@Slf4j
@Component
public class JudgeConsumer {

    // 最大重试次数
    private static final int MAX_RETRY_TIMES = 3;

    private final ScheduledExecutorService lockRenewalExecutor = Executors.newSingleThreadScheduledExecutor(task -> {
        Thread thread = new Thread(task, "judge-lock-renewal");
        thread.setDaemon(true);
        return thread;
    });

    @Autowired
    private IJudgeService judgeService;

    @Autowired
    private UserSubmitMapper userSubmitMapper;

    @Autowired
    private RabbitTemplate rabbitTemplate;

    @Autowired
    private JudgeRuntimeStateService judgeRuntimeStateService;

    @Autowired
    private JudgeResultPushService judgeResultPushService;

    @Autowired
    private LocalJudgeScheduler localJudgeScheduler;

    @Autowired
    private JudgeLockProperties judgeLockProperties;

    @RabbitListener(queues = RabbitMQConstants.OJ_WORK_QUEUE, containerFactory = "judgeListenerContainerFactory")
    public CompletableFuture<Void> consume(JudgeSubmitDTO judgeSubmitDTO, Message message) {
        return dispatch(judgeSubmitDTO, message, JudgeTaskType.REALTIME);
    }

    @RabbitListener(queues = RabbitMQConstants.OJ_BATCH_QUEUE, containerFactory = "judgeListenerContainerFactory")
    public CompletableFuture<Void> consumeBatch(JudgeSubmitDTO judgeSubmitDTO, Message message) {
        return dispatch(judgeSubmitDTO, message, JudgeTaskType.BATCH);
    }

    private CompletableFuture<Void> dispatch(JudgeSubmitDTO judgeSubmitDTO,
                                             Message message,
                                             JudgeTaskType sourceType) {
        String requestId = judgeSubmitDTO == null ? null : judgeSubmitDTO.getRequestId();
        JudgeTaskType taskType = resolveTaskType(judgeSubmitDTO, sourceType);
        return localJudgeScheduler.submit(taskType, requestId,
                () -> processMessage(judgeSubmitDTO, message, taskType));
    }

    private void processMessage(JudgeSubmitDTO judgeSubmitDTO, Message message, JudgeTaskType taskType) {
        if (judgeSubmitDTO == null) {
            throw new IllegalArgumentException("Missing judge submit payload");
        }
        String requestId = judgeSubmitDTO.getRequestId();
        // 如果没有请求id，直接丢入死信队列
        if (requestId == null || requestId.isBlank()) {
            handleUnrecoverable(judgeSubmitDTO, 0, "Missing requestId");
            return;
        }

        // 从提交数据中拿到用户提交
        UserSubmit userSubmit = userSubmitMapper.selectOne(new LambdaQueryWrapper<UserSubmit>()
                .eq(UserSubmit::getRequestId, requestId));
        // 如果数据库中没有，则放入死信队列中
        if (userSubmit == null) {
            handleUnrecoverable(judgeSubmitDTO, currentRetryCount(message), "Missing user submit record");
            return;
        }

        // 幂等性校验  判断判题状态，是不是以及被处理过了，及以及到达了最终状态。
        Integer judgeStatus = userSubmit.getJudgeStatus();
        if (JudgeAsyncStatus.SUCCESS.getValue().equals(judgeStatus)
                || JudgeAsyncStatus.DEAD_LETTER.getValue().equals(judgeStatus)
                || JudgeAsyncStatus.DISPATCH_FAILED.getValue().equals(judgeStatus)) {
            return;
        }

        // A second delivery of an in-flight request is not a failed judging attempt.
        String lockOwner = UUID.randomUUID().toString();
        boolean locked = judgeRuntimeStateService.tryLock(
                requestId,
                lockOwner,
                judgeLockProperties.leaseSeconds()
        );
        if (!locked) {
            handleLockContention(judgeSubmitDTO, taskType, currentRetryCount(message));
            return;
        }

        Thread judgeThread = Thread.currentThread();
        AtomicBoolean leaseOwned = new AtomicBoolean(true);
        AtomicLong lastSuccessfulRenewal = new AtomicLong(System.nanoTime());
        long leaseNanos = TimeUnit.SECONDS.toNanos(judgeLockProperties.leaseSeconds());
        ScheduledFuture<?> renewal = lockRenewalExecutor.scheduleAtFixedRate(() -> {
            try {
                boolean renewed = judgeRuntimeStateService.renewLock(
                        requestId,
                        lockOwner,
                        judgeLockProperties.leaseSeconds()
                );
                if (renewed) {
                    lastSuccessfulRenewal.set(System.nanoTime());
                } else {
                    loseLease(requestId, leaseOwned, judgeThread, "lock ownership changed");
                }
            } catch (Exception e) {
                log.error("Could not renew judge lock, requestId={}", requestId, e);
                if (System.nanoTime() - lastSuccessfulRenewal.get() >= leaseNanos) {
                    loseLease(requestId, leaseOwned, judgeThread, "renewal deadline exceeded");
                }
            }
        }, judgeLockProperties.renewIntervalSeconds(), judgeLockProperties.renewIntervalSeconds(), TimeUnit.SECONDS);

        // 更新Redis状态，并且开始判题。
        try {
            judgeRuntimeStateService.markConsuming(requestId);
            log.info("Received judge message, requestId={}", requestId);
            judgeService.doJudgeJavaCode(judgeSubmitDTO);
            if (!leaseOwned.get()) {
                throw new JudgeLeaseLostException("Judge lock lease lost for request " + requestId);
            }
        } catch (Exception e) {
            if (!leaseOwned.get()) {
                throw new JudgeLeaseLostException("Judge lock lease lost for request " + requestId, e);
            }
            // 计算下一次重试次数
            int nextRetryCount = currentRetryCount(message) + 1;
            String lastError = e.getMessage() == null ? e.getClass().getSimpleName() : e.getMessage();
            // 判断这个异常是可以重复的，并且小于最大可重复次数
            if (isRetryable(e) && nextRetryCount <= MAX_RETRY_TIMES) {
                handleRetry(judgeSubmitDTO, taskType, nextRetryCount, lastError);
            } else {
                handleUnrecoverable(judgeSubmitDTO, nextRetryCount, lastError);
            }
        } finally {
            renewal.cancel(false);
            try {
                judgeRuntimeStateService.unlock(requestId, lockOwner);
            } catch (Exception e) {
                log.error("Could not release judge lock, requestId={}", requestId, e);
            }
        }
    }

    @PreDestroy
    public void shutdownLockRenewal() {
        lockRenewalExecutor.shutdownNow();
    }

    private void handleLockContention(JudgeSubmitDTO judgeSubmitDTO,
                                      JudgeTaskType taskType,
                                      int retryCount) {
        if (publishToExchange(judgeSubmitDTO, RabbitMQConstants.OJ_JUDGE_DLX_EXCHANGE,
                retryRoutingKey(taskType), retryCount, "Request already locked")) {
            return;
        }
        throw new IllegalStateException("Could not reroute locked judge task " + judgeSubmitDTO.getRequestId());
    }


    // 先可靠发布重试消息；方法正常返回后，异步监听器才会确认原消息。
    private void handleRetry(JudgeSubmitDTO judgeSubmitDTO,
                             JudgeTaskType taskType,
                             int retryCount,
                             String lastError) {
        // 【第1步：尝试把消息转移到“重试专用队列”】
        if (publishToExchange(judgeSubmitDTO, RabbitMQConstants.OJ_JUDGE_DLX_EXCHANGE,
                retryRoutingKey(taskType), retryCount, lastError)) {

            // 【第2步：转移成功后，更新业务状态】
            judgeRuntimeStateService.markRetryWaiting(judgeSubmitDTO.getRequestId(), retryCount, lastError);

            return;
        }

        // 转移失败时让异步监听器 NACK，保留原消息。
        throw new IllegalStateException("Could not publish judge retry " + judgeSubmitDTO.getRequestId());
    }

    //  放入死信交换机，进入死信队列
    private void handleUnrecoverable(JudgeSubmitDTO judgeSubmitDTO,
                                     int retryCount,
                                     String lastError) {
        if (publishToExchange(judgeSubmitDTO, RabbitMQConstants.OJ_JUDGE_DLX_EXCHANGE, RabbitMQConstants.JUDGE_DEAD_KEY, retryCount, lastError)) {
            markDeadLetter(judgeSubmitDTO.getRequestId(), retryCount, lastError);
            return;
        }
        throw new IllegalStateException("Could not publish dead judge task " + judgeSubmitDTO.getRequestId());
    }


    private boolean publishToExchange(JudgeSubmitDTO judgeSubmitDTO,
                                      String exchange,
                                      String routingKey,
                                      int retryCount,
                                      String lastError) {
        try {
            // 请求ID + 路由键 + 第几次重试 拼凑为唯一id
            CorrelationData correlationData = new CorrelationData(
                    judgeSubmitDTO.getRequestId() + "-" + routingKey + "-" + retryCount
            );
            rabbitTemplate.convertAndSend(exchange, routingKey, judgeSubmitDTO, message -> {
                message.getMessageProperties().setCorrelationId(judgeSubmitDTO.getRequestId());
                message.getMessageProperties().setMessageId(judgeSubmitDTO.getRequestId());
                message.getMessageProperties().setHeader("retryCount", retryCount);
                message.getMessageProperties().setHeader("lastError", lastError);
                return message;
            }, correlationData);
            // 在接受到Rabbit明确接受到message的情况下，才返回
            return correlationData.getFuture().get(5, TimeUnit.SECONDS).isAck()
                    && correlationData.getReturned() == null;
        } catch (Exception e) {
            log.error("Failed to reroute judge message, requestId={}", judgeSubmitDTO.getRequestId(), e);
            return false;
        }
    }

    // 死信队列收尾工作，将Redis清理，给前端返回以及处理好
    private void markDeadLetter(String requestId, int retryCount, String lastError) {
        if (requestId == null || requestId.isBlank()) {
            return;
        }
        UserSubmit userSubmit = userSubmitMapper.selectOne(new QueryWrapper<UserSubmit>()
                .select("request_id", "user_id")
                .eq("request_id", requestId));
        LocalDateTime finishTime = LocalDateTime.now();
        int updated = userSubmitMapper.update(null, new UpdateWrapper<UserSubmit>()
                .eq("request_id", requestId)
                .eq("judge_status", JudgeAsyncStatus.WAITING.getValue())
                .set("judge_status", JudgeAsyncStatus.DEAD_LETTER.getValue())
                .set("retry_count", retryCount)
                .set("last_error", lastError)
                .set("finish_time", finishTime));
        if (updated == 0) {
            return;
        }
        judgeRuntimeStateService.markDeadLetter(requestId, retryCount, lastError);
        JudgeResultPushDTO pushDTO = new JudgeResultPushDTO();
        pushDTO.setRequestId(requestId);
        if (userSubmit != null) {
            pushDTO.setUserId(userSubmit.getUserId());
        }
        pushDTO.setAsyncStatus(JudgeAsyncStatus.DEAD_LETTER.getValue());
        pushDTO.setLastError(lastError);
        pushDTO.setFinishTime(finishTime);
        judgeResultPushService.publishFinalResult(pushDTO);
    }

    private int currentRetryCount(Message message) {
        Object retryCount = message.getMessageProperties().getHeaders().get("retryCount");
        if (retryCount instanceof Number number) {
            return number.intValue();
        }
        if (retryCount != null) {
            return Integer.parseInt(String.valueOf(retryCount));
        }
        return 0;
    }

    private boolean isRetryable(Exception e) {
        return !(e instanceof IllegalArgumentException);
    }

    private JudgeTaskType resolveTaskType(JudgeSubmitDTO judgeSubmitDTO, JudgeTaskType sourceType) {
        if (judgeSubmitDTO == null) {
            return sourceType;
        }
        JudgeTaskType resolved = JudgeTaskType.resolve(judgeSubmitDTO.getTaskType(), judgeSubmitDTO.getExamId());
        judgeSubmitDTO.setTaskType(resolved);
        return resolved;
    }

    private String retryRoutingKey(JudgeTaskType taskType) {
        return taskType == JudgeTaskType.BATCH
                ? RabbitMQConstants.JUDGE_BATCH_RETRY_KEY
                : RabbitMQConstants.JUDGE_RETRY_KEY;
    }

    private void loseLease(String requestId,
                           AtomicBoolean leaseOwned,
                           Thread judgeThread,
                           String reason) {
        if (leaseOwned.compareAndSet(true, false)) {
            log.error("Judge lock lease lost, requestId={}, reason={}", requestId, reason);
            judgeThread.interrupt();
        }
    }

    private static class JudgeLeaseLostException extends RuntimeException {
        private JudgeLeaseLostException(String message) {
            super(message);
        }

        private JudgeLeaseLostException(String message, Throwable cause) {
            super(message, cause);
        }
    }
}
