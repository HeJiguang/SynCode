package com.sintao.system.sync;

import com.rabbitmq.client.Channel;
import org.junit.jupiter.api.Test;
import org.springframework.amqp.core.Message;
import org.springframework.amqp.core.MessageProperties;
import org.springframework.jdbc.core.JdbcTemplate;

import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.Mockito.*;

class QuestionSyncWorkerTest {
    @Test
    void ackOnlyAfterProjectionCommit() throws Exception {
        QuestionProjection projection = mock(QuestionProjection.class);
        QuestionOutbox outbox = mock(QuestionOutbox.class);
        Channel channel = mock(Channel.class);
        QuestionSyncWorker worker = new QuestionSyncWorker(projection, outbox, mock(JdbcTemplate.class));
        worker.elasticsearch(message(), channel);
        var order = inOrder(projection, channel);
        order.verify(projection).apply(12L, "ES");
        order.verify(channel).basicAck(7L, false);
    }

    @Test
    void failureMustBeDurablyRetriedBeforeAck() throws Exception {
        QuestionProjection projection = mock(QuestionProjection.class);
        QuestionOutbox outbox = mock(QuestionOutbox.class);
        Channel channel = mock(Channel.class);
        Exception outage = new IllegalStateException("ES offline");
        doThrow(outage).when(projection).apply(12L, "ES");
        new QuestionSyncWorker(projection, outbox, mock(JdbcTemplate.class)).elasticsearch(message(), channel);
        var order = inOrder(outbox, channel);
        order.verify(outbox).retry(12L, null, outage);
        order.verify(channel).basicAck(7L, false);
    }

    @Test
    void databaseOutageMustLeaveMessageUnacknowledged() throws Exception {
        QuestionProjection projection = mock(QuestionProjection.class);
        QuestionOutbox outbox = mock(QuestionOutbox.class);
        Channel channel = mock(Channel.class);
        Exception outage = new IllegalStateException("offline");
        doThrow(outage).when(projection).apply(12L, "ES");
        doThrow(outage).when(outbox).retry(12L, null, outage);
        assertThrows(Exception.class, () -> new QuestionSyncWorker(projection, outbox, mock(JdbcTemplate.class))
                .elasticsearch(message(), channel));
        verifyNoInteractions(channel);
    }

    private Message message() {
        MessageProperties properties = new MessageProperties();
        properties.setDeliveryTag(7L);
        return new Message("12".getBytes(java.nio.charset.StandardCharsets.UTF_8), properties);
    }
}
