package com.sintao.system.sync;

import org.junit.jupiter.api.Test;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.ReturnedMessage;
import org.springframework.amqp.rabbit.connection.CorrelationData;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.jdbc.core.JdbcTemplate;

import java.util.List;
import java.util.Map;

import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class QuestionOutboxTest {
    @Test
    void markSentOnlyAfterPositiveConfirmAndSuccessfulRouting() {
        exercise(true, false);
    }

    @Test
    void positiveConfirmWithReturnedMessageMustRetry() {
        exercise(true, true);
    }

    @Test
    void brokerNackMustRetry() {
        exercise(false, false);
    }

    private void exercise(boolean ack, boolean returned) {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        RabbitTemplate rabbit = mock(RabbitTemplate.class);
        when(jdbc.update(contains("ORDER BY available_at,id LIMIT 1"), any(Object.class))).thenReturn(1, 0);
        when(jdbc.queryForList(contains("WHERE lease_token=?"), any(Object.class)))
                .thenReturn(List.of(Map.of("id", 12L, "target", "ES")));
        doAnswer(invocation -> {
            CorrelationData data = invocation.getArgument(3);
            if (returned) data.setReturned(new ReturnedMessage(invocation.getArgument(2), 312,
                    "NO_ROUTE", QuestionSyncConfig.EXCHANGE, "ES"));
            data.getFuture().complete(new CorrelationData.Confirm(ack, ack ? null : "nack"));
            return null;
        }).when(rabbit).send(eq(QuestionSyncConfig.EXCHANGE), eq("ES"), any(Message.class), any(CorrelationData.class));
        new QuestionOutbox(jdbc, rabbit).publish();
        if (ack && !returned) {
            verify(jdbc).update(contains("SET status='SENT'"), eq(12L), anyString());
        } else {
            verify(jdbc, never()).update(contains("SET status='SENT'"), eq(12L), anyString());
            verify(jdbc).update(contains("attempts=attempts+1"), anyString(), eq(12L), anyString(), anyString());
        }
    }
}
