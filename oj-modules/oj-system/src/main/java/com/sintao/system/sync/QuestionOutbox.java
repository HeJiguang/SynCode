package com.sintao.system.sync;

import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageDeliveryMode;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.amqp.rabbit.connection.CorrelationData;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.amqp.rabbit.connection.ConnectionFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.util.UUID;
import java.util.concurrent.TimeUnit;

@Slf4j
@Component
@ConditionalOnProperty(name = "question.sync.enabled", havingValue = "true")
public class QuestionOutbox {
    private final JdbcTemplate jdbc;
    private final RabbitTemplate rabbit;

    @org.springframework.beans.factory.annotation.Autowired
    public QuestionOutbox(JdbcTemplate jdbc,
            ConnectionFactory connectionFactory) {
        this(jdbc, QuestionSyncConfig.questionSyncRabbitTemplate(connectionFactory));
    }

    QuestionOutbox(JdbcTemplate jdbc, RabbitTemplate rabbit) {
        this.jdbc = jdbc;
        this.rabbit = rabbit;
    }

    @Scheduled(fixedDelayString = "${question.sync.publish-delay-ms:1000}", scheduler = "questionSyncScheduler")
    public void publish() {
        // Each row has its own lease; no network call holds the polling transaction open.
        for (int i = 0; i < 20; i++) {
            String token = UUID.randomUUID().toString();
            int claimed = jdbc.update("""
                UPDATE tb_question_outbox SET status='SENDING',lease_token=?,
                  available_at=TIMESTAMPADD(SECOND,60,UTC_TIMESTAMP(3)),updated_at=UTC_TIMESTAMP(3)
                WHERE status IN ('PENDING','SENDING','SENT') AND available_at<=UTC_TIMESTAMP(3)
                ORDER BY available_at,id LIMIT 1
                """, token);
            if (claimed == 0) return;
            var rows = jdbc.queryForList("SELECT id,target FROM tb_question_outbox WHERE lease_token=?", token);
            if (rows.isEmpty()) continue; // A concurrent consumer already completed this event.
            long id = ((Number) rows.get(0).get("id")).longValue();
            try {
                MessageProperties properties = new MessageProperties();
                properties.setDeliveryMode(MessageDeliveryMode.PERSISTENT);
                properties.setContentType(MessageProperties.CONTENT_TYPE_TEXT_PLAIN);
                properties.setMessageId(Long.toString(id));
                CorrelationData correlation = new CorrelationData(token);
                rabbit.send(QuestionSyncConfig.EXCHANGE, rows.get(0).get("target").toString(),
                        new Message(Long.toString(id).getBytes(StandardCharsets.UTF_8), properties), correlation);
                var confirm = correlation.getFuture().get(10, TimeUnit.SECONDS);
                if (!confirm.isAck() || correlation.getReturned() != null) {
                    throw new IllegalStateException("Message not confirmed/routed: " + confirm.getReason());
                }
                // SENT is also leased: lost messages/consumer failures are replayed until DONE.
                jdbc.update("""
                    UPDATE tb_question_outbox SET status='SENT',available_at=TIMESTAMPADD(SECOND,60,UTC_TIMESTAMP(3)),
                      updated_at=UTC_TIMESTAMP(3) WHERE id=? AND lease_token=? AND status='SENDING'
                    """, id, token);
            } catch (Exception failure) {
                retry(id, token, failure);
                if (failure instanceof InterruptedException) {
                    Thread.currentThread().interrupt();
                    return;
                }
            }
        }
    }

    public void retry(long id, String token, Exception failure) {
        String message = failure.getClass().getSimpleName() + ": " + failure.getMessage();
        jdbc.update("""
            UPDATE tb_question_outbox SET status='PENDING',attempts=attempts+1,last_error=?,
              available_at=TIMESTAMPADD(SECOND,LEAST(300,POW(2,LEAST(attempts,8))),UTC_TIMESTAMP(3)),
              updated_at=UTC_TIMESTAMP(3)
            WHERE id=? AND status<>'DONE' AND (? IS NULL OR lease_token=?)
            """, message.substring(0, Math.min(1000, message.length())), id, token, token);
        log.warn("Question sync will retry event {}: {}", id, message);
    }
}
