-- Read-only verification for V2026092201. Every query before the final summary must return zero rows.

SELECT expected.table_name AS ai_table_missing
FROM (
    SELECT 'tb_ai_run' AS table_name
    UNION ALL SELECT 'tb_ai_run_event'
    UNION ALL SELECT 'tb_ai_artifact'
    UNION ALL SELECT 'tb_ai_conversation'
    UNION ALL SELECT 'tb_ai_message'
    UNION ALL SELECT 'tb_ai_memory'
    UNION ALL SELECT 'tb_ai_conversation_memory'
    UNION ALL SELECT 'tb_ai_tool_approval'
) expected
LEFT JOIN information_schema.tables actual
    ON actual.table_schema = DATABASE()
   AND actual.table_name = expected.table_name
WHERE actual.table_name IS NULL;

SELECT expected.table_name, expected.column_name AS ai_column_mismatch
FROM (
    SELECT 'tb_ai_run' AS table_name, 'user_id' AS column_name,
           'varchar' AS data_type, 64 AS character_maximum_length
    UNION ALL SELECT 'tb_ai_run', 'request_json', 'json', NULL
    UNION ALL SELECT 'tb_ai_run_event', 'run_public_id', 'varchar', 64
    UNION ALL SELECT 'tb_ai_artifact', 'run_public_id', 'varchar', 64
    UNION ALL SELECT 'tb_ai_conversation', 'user_id', 'varchar', 64
    UNION ALL SELECT 'tb_ai_conversation', 'current_question_id', 'varchar', 64
    UNION ALL SELECT 'tb_ai_message', 'user_id', 'varchar', 64
    UNION ALL SELECT 'tb_ai_message', 'question_id', 'varchar', 64
    UNION ALL SELECT 'tb_ai_memory', 'user_id', 'varchar', 64
    UNION ALL SELECT 'tb_ai_tool_approval', 'user_id', 'varchar', 64
) expected
LEFT JOIN information_schema.columns actual
    ON actual.table_schema = DATABASE()
   AND actual.table_name = expected.table_name
   AND actual.column_name = expected.column_name
WHERE actual.column_name IS NULL
   OR actual.data_type <> expected.data_type
   OR (
       expected.character_maximum_length IS NOT NULL
       AND actual.character_maximum_length <> expected.character_maximum_length
   );

SELECT expected.table_name, expected.index_name AS ai_index_missing
FROM (
    SELECT 'tb_ai_run' AS table_name, 'uk_ai_run_public_id' AS index_name
    UNION ALL SELECT 'tb_ai_run_event', 'uk_ai_run_event_run_seq'
    UNION ALL SELECT 'tb_ai_artifact', 'uk_ai_artifact_public_id'
    UNION ALL SELECT 'tb_ai_conversation', 'uk_ai_conversation_user_default'
    UNION ALL SELECT 'tb_ai_message', 'uk_ai_message_conversation_seq'
    UNION ALL SELECT 'tb_ai_memory', 'uk_ai_memory_public_id'
    UNION ALL SELECT 'tb_ai_conversation_memory', 'uk_ai_conversation_memory'
    UNION ALL SELECT 'tb_ai_tool_approval', 'uk_ai_tool_approval_remote_request'
) expected
LEFT JOIN information_schema.statistics actual
    ON actual.table_schema = DATABASE()
   AND actual.table_name = expected.table_name
   AND actual.index_name = expected.index_name
WHERE actual.index_name IS NULL OR actual.non_unique <> 0;

SELECT message.public_id AS orphan_message_violation
FROM tb_ai_message message
LEFT JOIN tb_ai_conversation conversation
    ON conversation.conversation_id = message.conversation_id
WHERE conversation.conversation_id IS NULL;

SELECT message.public_id AS cross_user_message_violation
FROM tb_ai_message message
JOIN tb_ai_conversation conversation
    ON conversation.conversation_id = message.conversation_id
WHERE message.user_id <> conversation.user_id;

SELECT user_id, COUNT(*) AS duplicate_default_chat_violation
FROM tb_ai_conversation
WHERE default_slot = 1
GROUP BY user_id
HAVING COUNT(*) > 1;

SELECT public_id AS invalid_memory_status_violation
FROM tb_ai_memory
WHERE status NOT IN ('PENDING', 'APPROVED', 'REJECTED');

SELECT public_id AS invalid_tool_approval_status_violation
FROM tb_ai_tool_approval
WHERE status NOT IN ('PENDING', 'APPROVED', 'DENIED', 'EXPIRED', 'EXECUTED');

SELECT event.public_id AS orphan_run_event_violation
FROM tb_ai_run_event event
LEFT JOIN tb_ai_run run ON run.public_id = event.run_public_id
WHERE run.public_id IS NULL;

SELECT artifact.public_id AS orphan_artifact_violation
FROM tb_ai_artifact artifact
LEFT JOIN tb_ai_run run ON run.public_id = artifact.run_public_id
WHERE run.public_id IS NULL;

SELECT VERSION() AS mysql_version, DATABASE() AS database_name,
       (SELECT COUNT(*) FROM flyway_schema_history WHERE success = 1) AS successful_flyway_migrations;
