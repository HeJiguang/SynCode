package com.sintao.system.sync;

import cn.hutool.core.bean.BeanUtil;
import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch._types.ElasticsearchException;
import co.elastic.clients.elasticsearch._types.VersionType;
import com.sintao.common.core.constants.CacheConstants;
import com.sintao.common.redis.service.RedisService;
import com.sintao.system.domain.question.es.QuestionES;
import com.sintao.system.mapper.question.QuestionMapper;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.data.elasticsearch.core.ElasticsearchOperations;
import org.springframework.data.elasticsearch.core.document.Document;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.Map;
import java.util.TreeMap;

@Service
@ConditionalOnProperty(name = "question.sync.enabled", havingValue = "true")
public class QuestionProjection {
    private final JdbcTemplate jdbc;
    private final QuestionMapper questions;
    private final ElasticsearchOperations operations;
    private final ElasticsearchClient client;
    private final RedisService redis;

    public QuestionProjection(JdbcTemplate jdbc, QuestionMapper questions, ElasticsearchOperations operations,
            ElasticsearchClient client, RedisService redis) {
        this.jdbc = jdbc;
        this.questions = questions;
        this.operations = operations;
        this.client = client;
        this.redis = redis;
    }

    @Transactional(rollbackFor = Exception.class, isolation = org.springframework.transaction.annotation.Isolation.READ_COMMITTED)
    public void apply(long eventId, String expectedTarget) throws Exception {
        var events = jdbc.queryForList("SELECT question_id,target FROM tb_question_outbox WHERE id=?", eventId);
        if (events.isEmpty()) throw new IllegalArgumentException("Unknown question event " + eventId);
        var event = events.get(0);
        if (!expectedTarget.equals(event.get("target"))) throw new IllegalArgumentException("Wrong event target");
        long id = ((Number) event.get("question_id")).longValue();
        // Serialize projection and mutations per question. Always read the latest committed snapshot.
        var state = jdbc.queryForMap("SELECT * FROM tb_question_sync_state WHERE question_id=? FOR UPDATE", id);
        long revision = ((Number) state.get("revision")).longValue();
        if ("ES".equals(expectedTarget)) {
            Document document = document(id, revision, ((Number) state.get("deleted")).intValue() != 0);
            try {
                client.index(r -> r.index("idx_question").id(Long.toString(id))
                        .version(revision).versionType(VersionType.ExternalGte).document(document));
            } catch (ElasticsearchException exception) {
                if (exception.status() != 409) throw exception;
                // The state lock makes current writers monotonic. A conflict here indicates a legacy
                // internal version or database restore; never declare a divergent projection complete.
                throw new IllegalStateException("ES version ahead of MySQL; check baseline/restore procedure", exception);
            }
            jdbc.update("UPDATE tb_question_sync_state SET es_revision=? WHERE question_id=?", revision, id);
        } else {
            // Both caches only contain IDs; invalidation is safe even for duplicate/out-of-order events.
            redis.invalidateVersionedList(CacheConstants.QUESTION_LIST);
            redis.invalidateVersionedList(CacheConstants.QUESTION_HOST_LIST);
            jdbc.update("UPDATE tb_question_sync_state SET redis_revision=? WHERE question_id=?", revision, id);
        }
        jdbc.update("""
            UPDATE tb_question_outbox SET status='DONE',lease_token=NULL,last_error=NULL,updated_at=UTC_TIMESTAMP(3)
            WHERE question_id=? AND target=? AND revision<=?
            """, id, expectedTarget, revision);
    }

    Document document(long id, long revision, boolean deleted) throws Exception {
        QuestionES projection = new QuestionES();
        if (!deleted) {
            var question = questions.selectById(id);
            if (question == null) throw new IllegalStateException("Live state without question: " + id);
            BeanUtil.copyProperties(question, projection);
        }
        projection.setQuestionId(id);
        projection.setRevision(revision);
        projection.setDeleted(deleted);
        Document document = operations.getElasticsearchConverter().mapObject(projection);
        // Stable across map iteration order; no grading/test data is logged.
        document.put("contentHash", hash(document));
        return document;
    }

    private String hash(Map<String, Object> source) throws Exception {
        TreeMap<String, Object> canonicalFields = new TreeMap<>(source);
        canonicalFields.remove("contentHash");
        String canonical = new com.fasterxml.jackson.databind.ObjectMapper().writeValueAsString(canonicalFields);
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                .digest(canonical.getBytes(StandardCharsets.UTF_8)));
    }

    @Transactional(rollbackFor = Exception.class, isolation = org.springframework.transaction.annotation.Isolation.READ_COMMITTED)
    public void reconcile(long id) throws Exception {
        var state = jdbc.queryForMap("SELECT * FROM tb_question_sync_state WHERE question_id=? FOR UPDATE", id);
        long revision = ((Number) state.get("revision")).longValue();
        Document desired = document(id, revision, ((Number) state.get("deleted")).intValue() != 0);
        try {
            var actual = client.get(r -> r.index("idx_question").id(Long.toString(id)), Map.class);
            if (((Number) state.get("es_revision")).longValue() < revision
                    || !actual.found() || actual.source() == null
                    || !desired.get("contentHash").equals(hash(actual.source()))) {
                replay(id, revision, "ES");
            }
        } catch (ElasticsearchException failure) {
            if (failure.status() != 404) throw failure;
            replay(id, revision, "ES");
        }
        // TTL bounds Redis staleness even after eviction/restore; periodic invalidation also repairs bad lists.
        replay(id, revision, "REDIS");
    }

    private void replay(long id, long revision, String target) {
        jdbc.update("""
            INSERT IGNORE INTO tb_question_outbox(question_id,revision,target,available_at,created_at,updated_at)
            VALUES(?,?,?,UTC_TIMESTAMP(3),UTC_TIMESTAMP(3),UTC_TIMESTAMP(3))
            """, id, revision, target);
        jdbc.update("""
            UPDATE tb_question_outbox SET status='PENDING',available_at=UTC_TIMESTAMP(3),lease_token=NULL,
              updated_at=UTC_TIMESTAMP(3) WHERE question_id=? AND revision=? AND target=? AND status='DONE'
            """, id, revision, target);
    }
}
