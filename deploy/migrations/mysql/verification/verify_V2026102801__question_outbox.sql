-- Read-only verification. Violation queries should return zero rows.
SELECT table_name FROM information_schema.tables
WHERE table_schema=DATABASE() AND table_name IN ('tb_question_outbox','tb_question_sync_state');
SELECT table_name,column_name,data_type FROM information_schema.columns
WHERE table_schema=DATABASE() AND table_name IN ('tb_question_outbox','tb_question_sync_state')
ORDER BY table_name,ordinal_position;
SELECT trigger_name FROM information_schema.triggers
WHERE trigger_schema=DATABASE() AND trigger_name IN
('trg_question_sync_insert','trg_question_sync_update','trg_question_sync_delete');
SELECT index_name,non_unique FROM information_schema.statistics
WHERE table_schema=DATABASE() AND table_name='tb_question_outbox'
GROUP BY index_name,non_unique;
SELECT q.question_id FROM tb_question q LEFT JOIN tb_question_sync_state s USING(question_id)
WHERE s.question_id IS NULL OR s.deleted<>0;
SELECT s.question_id FROM tb_question_sync_state s LEFT JOIN tb_question q USING(question_id)
WHERE (s.deleted=0 AND q.question_id IS NULL) OR s.revision<1
OR s.es_revision>s.revision OR s.redis_revision>s.revision OR s.deleted NOT IN (0,1);
SELECT o.id FROM tb_question_outbox o LEFT JOIN tb_question_sync_state s USING(question_id)
WHERE s.question_id IS NULL OR o.revision>s.revision OR o.target NOT IN ('ES','REDIS')
OR o.status NOT IN ('PENDING','SENDING','SENT','DONE');
SELECT s.question_id FROM tb_question_sync_state s
LEFT JOIN tb_question_outbox e ON e.question_id=s.question_id AND e.revision=s.revision AND e.target='ES'
LEFT JOIN tb_question_outbox r ON r.question_id=s.question_id AND r.revision=s.revision AND r.target='REDIS'
WHERE e.id IS NULL OR r.id IS NULL;
-- Operational status, not a violation during initial backfill or a service outage.
SELECT target,status,COUNT(*) AS events,MIN(created_at) AS oldest_created,MAX(attempts) AS max_attempts
FROM tb_question_outbox GROUP BY target,status;
