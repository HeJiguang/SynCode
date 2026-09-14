-- Read-only verification for V2026091401.
-- Every query named *_violations or *_missing must return zero rows.

SELECT expected.table_name AS trusted_exam_table_missing
FROM (
    SELECT 'tb_exam_version' AS table_name
    UNION ALL SELECT 'tb_exam_version_question'
    UNION ALL SELECT 'tb_exam_attempt'
    UNION ALL SELECT 'tb_exam_answer'
    UNION ALL SELECT 'tb_exam_grade'
    UNION ALL SELECT 'tb_exam_grade_item'
    UNION ALL SELECT 'tb_integrity_event'
    UNION ALL SELECT 'tb_exam_command'
    UNION ALL SELECT 'tb_exam_audit_event'
    UNION ALL SELECT 'tb_exam_outbox'
) expected
LEFT JOIN information_schema.tables actual
    ON actual.table_schema = DATABASE()
    AND actual.table_name = expected.table_name
WHERE actual.table_name IS NULL;

SELECT expected.table_name, expected.column_name AS trusted_exam_column_missing
FROM (
    SELECT 'tb_exam' AS table_name, 'current_version_id' AS column_name
    UNION ALL SELECT 'tb_exam', 'duration_minutes'
    UNION ALL SELECT 'tb_exam', 'latest_start_time'
    UNION ALL SELECT 'tb_exam_question', 'score'
    UNION ALL SELECT 'tb_exam_question', 'required_flag'
    UNION ALL SELECT 'tb_user_exam', 'authorization_status'
    UNION ALL SELECT 'tb_user_submit', 'attempt_id'
    UNION ALL SELECT 'tb_user_submit', 'version_question_id'
    UNION ALL SELECT 'tb_user_submit', 'answer_version'
) expected
LEFT JOIN information_schema.columns actual
    ON actual.table_schema = DATABASE()
    AND actual.table_name = expected.table_name
    AND actual.column_name = expected.column_name
WHERE actual.column_name IS NULL;

SELECT exam_id, status AS exam_state_violations
FROM tb_exam
WHERE status NOT BETWEEN 0 AND 5;

SELECT exam_id, duration_minutes AS duration_violations
FROM tb_exam
WHERE duration_minutes IS NULL OR duration_minutes <= 0;

SELECT exam_id, question_id, COUNT(*) AS draft_question_duplicate_violations
FROM tb_exam_question
GROUP BY exam_id, question_id
HAVING COUNT(*) > 1;

SELECT exam_id, question_order, COUNT(*) AS draft_order_duplicate_violations
FROM tb_exam_question
GROUP BY exam_id, question_order
HAVING COUNT(*) > 1;

SELECT exam_id, user_id, COUNT(*) AS authorization_duplicate_violations
FROM tb_user_exam
GROUP BY exam_id, user_id
HAVING COUNT(*) > 1;

SELECT version_id, user_id, COUNT(*) AS attempt_duplicate_violations
FROM tb_exam_attempt
GROUP BY version_id, user_id
HAVING COUNT(*) > 1;

SELECT attempt_id, version_question_id, COUNT(*) AS answer_duplicate_violations
FROM tb_exam_answer
GROUP BY attempt_id, version_question_id
HAVING COUNT(*) > 1;

SELECT attempt_id, session_id, client_sequence, COUNT(*) AS integrity_duplicate_violations
FROM tb_integrity_event
GROUP BY attempt_id, session_id, client_sequence
HAVING COUNT(*) > 1;

SELECT attempt.attempt_id AS orphan_attempt_violations
FROM tb_exam_attempt attempt
LEFT JOIN tb_exam exam ON exam.exam_id = attempt.exam_id
LEFT JOIN tb_exam_version version ON version.version_id = attempt.version_id
LEFT JOIN tb_user candidate ON candidate.user_id = attempt.user_id
WHERE exam.exam_id IS NULL OR version.version_id IS NULL OR candidate.user_id IS NULL;

SELECT answer.answer_id AS orphan_answer_violations
FROM tb_exam_answer answer
LEFT JOIN tb_exam_attempt attempt ON attempt.attempt_id = answer.attempt_id
LEFT JOIN tb_exam_version_question question ON question.version_question_id = answer.version_question_id
WHERE attempt.attempt_id IS NULL OR question.version_question_id IS NULL;

SELECT version.version_id AS incomplete_version_violations
FROM tb_exam_version version
LEFT JOIN tb_exam_version_question question ON question.version_id = version.version_id
WHERE version.content_hash IS NULL OR question.version_question_id IS NULL
GROUP BY version.version_id;

SELECT version() AS mysql_version, DATABASE() AS database_name,
       (SELECT COUNT(*) FROM flyway_schema_history WHERE success = 1) AS successful_flyway_migrations;
