-- Read-only verification for V2026100901. Queries before the final summary must return zero rows.

SELECT expected.column_name AS recommendation_column_missing
FROM (
    SELECT 'event_id' AS column_name
    UNION ALL SELECT 'user_id'
    UNION ALL SELECT 'recommendation_id'
    UNION ALL SELECT 'action'
    UNION ALL SELECT 'question_id'
    UNION ALL SELECT 'plan_id'
    UNION ALL SELECT 'task_id'
    UNION ALL SELECT 'run_id'
    UNION ALL SELECT 'metadata_json'
    UNION ALL SELECT 'create_time'
) expected
LEFT JOIN information_schema.columns actual
    ON actual.table_schema = DATABASE()
   AND actual.table_name = 'tb_ai_recommendation_event'
   AND actual.column_name = expected.column_name
WHERE actual.column_name IS NULL;

SELECT expected.index_name AS recommendation_index_missing
FROM (
    SELECT 'PRIMARY' AS index_name
    UNION ALL SELECT 'idx_ai_recommendation_user_time'
    UNION ALL SELECT 'idx_ai_recommendation_correlation'
    UNION ALL SELECT 'idx_ai_recommendation_plan_task'
) expected
LEFT JOIN information_schema.statistics actual
    ON actual.table_schema = DATABASE()
   AND actual.table_name = 'tb_ai_recommendation_event'
   AND actual.index_name = expected.index_name
WHERE actual.index_name IS NULL;

SELECT event_id AS invalid_recommendation_action
FROM tb_ai_recommendation_event
WHERE action NOT IN ('impression', 'opened', 'accepted', 'skipped', 'completed', 'reopened');

SELECT VERSION() AS mysql_version, DATABASE() AS database_name,
       (SELECT COUNT(*) FROM tb_ai_recommendation_event) AS recommendation_event_count;
