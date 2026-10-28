package com.sintao.system.sync;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch.core.IndexRequest;
import co.elastic.clients.elasticsearch.core.IndexResponse;
import co.elastic.clients.util.ObjectBuilder;
import com.sintao.common.redis.service.RedisService;
import com.sintao.system.domain.question.Question;
import com.sintao.system.domain.question.es.QuestionES;
import com.sintao.system.mapper.question.QuestionMapper;
import org.junit.jupiter.api.Test;
import org.springframework.data.elasticsearch.core.ElasticsearchOperations;
import org.springframework.data.elasticsearch.core.convert.ElasticsearchConverter;
import org.springframework.data.elasticsearch.core.document.Document;
import org.springframework.jdbc.core.JdbcTemplate;

import java.util.List;
import java.util.Map;
import java.util.function.Function;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.*;
import static org.mockito.Mockito.*;

class QuestionProjectionTest {
    @Test
    void oldEventMustProjectCurrentRevisionWithExternalVersionProtection() throws Exception {
        exercise(false);
    }

    @Test
    void oldEventAfterPhysicalDeletionMustProjectTombstoneWithoutLoadingDeletedQuestion() throws Exception {
        exercise(true);
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    private void exercise(boolean deleted) throws Exception {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        QuestionMapper questions = mock(QuestionMapper.class);
        ElasticsearchClient client = mock(ElasticsearchClient.class);
        RedisService redis = mock(RedisService.class);
        ElasticsearchOperations operations = mock(ElasticsearchOperations.class);
        ElasticsearchConverter converter = mock(ElasticsearchConverter.class);
        when(jdbc.queryForList(contains("WHERE id=?"), eq(1L)))
                .thenReturn(List.of(Map.of("question_id", 42L, "target", "ES")));
        when(jdbc.queryForMap(contains("FOR UPDATE"), eq(42L)))
                .thenReturn(Map.of("revision", 9L, "deleted", deleted ? 1 : 0));
        if (!deleted) {
            Question question = new Question();
            question.setQuestionId(42L);
            question.setContent("latest authoritative statement");
            when(questions.selectById(42L)).thenReturn(question);
        }
        when(operations.getElasticsearchConverter()).thenReturn(converter);
        when(converter.mapObject(any(QuestionES.class))).thenAnswer(invocation -> {
            QuestionES projection = invocation.getArgument(0);
            assertEquals(9L, projection.getRevision());
            assertEquals(deleted, projection.getDeleted());
            if (!deleted) assertEquals("latest authoritative statement", projection.getContent());
            Document document = Document.create();
            document.put("questionId", 42L);
            document.put("deleted", deleted);
            document.put("revision", 9L);
            return document;
        });
        when(client.index(any(Function.class))).thenAnswer(invocation -> {
            Function<IndexRequest.Builder<Document>, ObjectBuilder<IndexRequest<Document>>> build = invocation.getArgument(0);
            IndexRequest<Document> request = build.apply(new IndexRequest.Builder<>()).build();
            assertEquals(9L, request.version());
            assertEquals(co.elastic.clients.elasticsearch._types.VersionType.ExternalGte, request.versionType());
            assertEquals("42", request.id());
            assertNotNull(request.document().get("contentHash"));
            return mock(IndexResponse.class);
        });
        new QuestionProjection(jdbc, questions, operations, client, redis).apply(1L, "ES");
        verify(jdbc).update(contains("SET es_revision=?"), eq(9L), eq(42L));
        verify(jdbc).update(contains("status='DONE'"), eq(42L), eq("ES"), eq(9L));
        if (deleted) verifyNoInteractions(questions);
        verifyNoInteractions(redis);
    }
}
