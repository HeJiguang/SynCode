-- Every query before the final summary must return zero rows.

SELECT question_id, title, 'starter_code_json is not parsable' AS problem
FROM tb_question
WHERE question_type = 'PROGRAMMING'
  AND (starter_code_json IS NULL OR NOT JSON_VALID(starter_code_json));

SELECT question_id, title, 'programming question misses a judge-pool starter language' AS problem
FROM tb_question
WHERE question_type = 'PROGRAMMING'
  AND starter_code_json IS NOT NULL
  AND JSON_VALID(starter_code_json)
  AND (
      NULLIF(CASE WHEN JSON_TYPE(JSON_EXTRACT(starter_code_json, '$.java')) = 'STRING'
                  THEN JSON_UNQUOTE(JSON_EXTRACT(starter_code_json, '$.java')) END, '') IS NULL
      OR NULLIF(CASE WHEN JSON_TYPE(JSON_EXTRACT(starter_code_json, '$.cpp')) = 'STRING'
                     THEN JSON_UNQUOTE(JSON_EXTRACT(starter_code_json, '$.cpp')) END, '') IS NULL
      OR NULLIF(CASE WHEN JSON_TYPE(JSON_EXTRACT(starter_code_json, '$.python')) = 'STRING'
                     THEN JSON_UNQUOTE(JSON_EXTRACT(starter_code_json, '$.python')) END, '') IS NULL
      OR NULLIF(CASE WHEN JSON_TYPE(JSON_EXTRACT(starter_code_json, '$.go')) = 'STRING'
                     THEN JSON_UNQUOTE(JSON_EXTRACT(starter_code_json, '$.go')) END, '') IS NULL
  );

SELECT question_id, title, 'answer_config_json does not declare the full judge pool' AS problem
FROM tb_question
WHERE question_type = 'PROGRAMMING'
  AND (
      answer_config_json IS NULL
      OR NOT JSON_VALID(answer_config_json)
      OR JSON_TYPE(answer_config_json) <> 'OBJECT'
      OR COALESCE(JSON_TYPE(JSON_EXTRACT(answer_config_json, '$.languages')), 'MISSING') <> 'ARRAY'
      OR JSON_LENGTH(JSON_EXTRACT(answer_config_json, '$.languages')) < 4
  );

SELECT COUNT(*) AS programming_questions_with_four_language_starters
FROM tb_question
WHERE question_type = 'PROGRAMMING'
  AND JSON_VALID(starter_code_json)
  AND NULLIF(CASE WHEN JSON_TYPE(JSON_EXTRACT(starter_code_json, '$.java')) = 'STRING'
                  THEN JSON_UNQUOTE(JSON_EXTRACT(starter_code_json, '$.java')) END, '') IS NOT NULL
  AND NULLIF(CASE WHEN JSON_TYPE(JSON_EXTRACT(starter_code_json, '$.cpp')) = 'STRING'
                  THEN JSON_UNQUOTE(JSON_EXTRACT(starter_code_json, '$.cpp')) END, '') IS NOT NULL
  AND NULLIF(CASE WHEN JSON_TYPE(JSON_EXTRACT(starter_code_json, '$.python')) = 'STRING'
                  THEN JSON_UNQUOTE(JSON_EXTRACT(starter_code_json, '$.python')) END, '') IS NOT NULL
  AND NULLIF(CASE WHEN JSON_TYPE(JSON_EXTRACT(starter_code_json, '$.go')) = 'STRING'
                  THEN JSON_UNQUOTE(JSON_EXTRACT(starter_code_json, '$.go')) END, '') IS NOT NULL;
