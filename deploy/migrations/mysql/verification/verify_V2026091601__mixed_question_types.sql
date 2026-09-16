-- Read-only verification for V2026091601. Every query before the final summary must return zero rows.

SELECT expected.table_name, expected.column_name AS mixed_question_column_missing
FROM (
    SELECT 'tb_question' AS table_name, 'question_type' AS column_name
    UNION ALL SELECT 'tb_question', 'answer_config_json'
    UNION ALL SELECT 'tb_question', 'grading_config_json'
    UNION ALL SELECT 'tb_exam_version_question', 'answer_config_json'
    UNION ALL SELECT 'tb_exam_version_question', 'grading_config_json'
    UNION ALL SELECT 'tb_exam_grade_item', 'feedback'
) expected
LEFT JOIN information_schema.columns actual
    ON actual.table_schema = DATABASE()
    AND actual.table_name = expected.table_name
    AND actual.column_name = expected.column_name
WHERE actual.column_name IS NULL;

SELECT question_id, question_type AS unsupported_question_type
FROM tb_question
WHERE question_type NOT IN ('PROGRAMMING','SINGLE_CHOICE','MULTIPLE_CHOICE','TRUE_FALSE','FILL_BLANK','SHORT_ANSWER','SQL','FILE','PROJECT');

SELECT COUNT(*) AS programming_questions, VERSION() AS mysql_version
FROM tb_question
WHERE question_type = 'PROGRAMMING';
