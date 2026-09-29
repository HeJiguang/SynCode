-- Every query before the final summary must return zero rows.

SELECT question_id, title, 'demo question still has TODO-style non-Java starter' AS problem
FROM tb_question
WHERE question_type = 'PROGRAMMING'
  AND title IN ('Two Sum A Plus B', 'Valid Parentheses', 'Binary Search',
                'Number of Islands', 'Longest Increasing Subsequence')
  AND (
      JSON_UNQUOTE(JSON_EXTRACT(starter_code_json, '$.cpp')) LIKE '%TODO%'
      OR JSON_UNQUOTE(JSON_EXTRACT(starter_code_json, '$.python')) LIKE '%TODO%'
      OR JSON_UNQUOTE(JSON_EXTRACT(starter_code_json, '$.go')) LIKE '%TODO%'
  );

SELECT question_id, title, 'legacy bare main_fuc still present' AS problem
FROM tb_question
WHERE main_fuc = 'public static void main(String[] args)';

SELECT question_id, title, 'programming question missing declared languages' AS problem
FROM tb_question
WHERE question_type = 'PROGRAMMING'
  AND (
      answer_config_json IS NULL
      OR JSON_TYPE(JSON_EXTRACT(answer_config_json, '$.languages')) <> 'ARRAY'
      OR JSON_LENGTH(JSON_EXTRACT(answer_config_json, '$.languages')) < 4
  );

SELECT COUNT(*) AS programming_questions_declaring_four_languages
FROM tb_question
WHERE question_type = 'PROGRAMMING'
  AND JSON_LENGTH(JSON_EXTRACT(answer_config_json, '$.languages')) >= 4;
