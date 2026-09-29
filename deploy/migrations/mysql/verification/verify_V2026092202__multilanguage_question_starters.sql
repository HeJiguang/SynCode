-- Every query before the final summary must return zero rows.
SELECT 'tb_question.starter_code_json' AS missing_column
WHERE NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'tb_question'
      AND column_name = 'starter_code_json'
);

SELECT question_id, 'missing supported starter code' AS problem
FROM tb_question
WHERE question_type = 'PROGRAMMING'
  AND (
      starter_code_json IS NULL
      OR JSON_TYPE(starter_code_json) <> 'OBJECT'
      OR JSON_EXTRACT(starter_code_json, '$.java') IS NULL
      OR JSON_EXTRACT(starter_code_json, '$.cpp') IS NULL
      OR JSON_EXTRACT(starter_code_json, '$.python') IS NULL
      OR JSON_EXTRACT(starter_code_json, '$.go') IS NULL
  );

SELECT COUNT(*) AS programming_questions_with_multilanguage_starters
FROM tb_question
WHERE question_type = 'PROGRAMMING'
  AND JSON_EXTRACT(starter_code_json, '$.java') IS NOT NULL
  AND JSON_EXTRACT(starter_code_json, '$.cpp') IS NOT NULL
  AND JSON_EXTRACT(starter_code_json, '$.python') IS NOT NULL
  AND JSON_EXTRACT(starter_code_json, '$.go') IS NOT NULL;
