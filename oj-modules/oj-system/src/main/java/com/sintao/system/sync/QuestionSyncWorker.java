package com.sintao.system.sync;

import com.rabbitmq.client.Channel;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;

@Slf4j
@Component
@ConditionalOnProperty(name = "question.sync.enabled", havingValue = "true")
public class QuestionSyncWorker {
    private final QuestionProjection projection;
    private final QuestionOutbox outbox;
    private final JdbcTemplate jdbc;
    private long cursor;

    public QuestionSyncWorker(QuestionProjection projection, QuestionOutbox outbox, JdbcTemplate jdbc) {
        this.projection = projection;
        this.outbox = outbox;
        this.jdbc = jdbc;
    }

    @RabbitListener(queues = QuestionSyncConfig.ES_QUEUE, containerFactory = "questionSyncListenerFactory")
    public void elasticsearch(Message message, Channel channel) throws Exception { consume(message, channel, "ES"); }

    @RabbitListener(queues = QuestionSyncConfig.REDIS_QUEUE, containerFactory = "questionSyncListenerFactory")
    public void redis(Message message, Channel channel) throws Exception { consume(message, channel, "REDIS"); }

    private void consume(Message message, Channel channel, String target) throws Exception {
        long id;
        try {
            id = Long.parseLong(new String(message.getBody(), StandardCharsets.UTF_8));
        } catch (NumberFormatException malformed) {
            log.error("Malformed question event, messageId={}", message.getMessageProperties().getMessageId());
            channel.basicReject(message.getMessageProperties().getDeliveryTag(), false);
            return;
        }
        try {
            projection.apply(id, target);
        } catch (Exception failure) {
            // If persisting the retry fails, leave the message unacknowledged for broker redelivery.
            outbox.retry(id, null, failure);
        }
        channel.basicAck(message.getMessageProperties().getDeliveryTag(), false);
    }

    @Scheduled(fixedDelayString = "${question.sync.reconcile-delay-ms:60000}", scheduler = "questionSyncScheduler")
    public void reconcile() {
        var ids = jdbc.queryForList("SELECT question_id FROM tb_question_sync_state WHERE question_id>? ORDER BY question_id LIMIT 100",
                Long.class, cursor);
        if (ids.isEmpty()) { cursor = 0; return; }
        for (long id : ids) {
            try { projection.reconcile(id); }
            catch (Exception failure) { log.warn("Question reconciliation failed for {}: {}", id, failure.toString()); }
            cursor = id;
        }
    }
}
