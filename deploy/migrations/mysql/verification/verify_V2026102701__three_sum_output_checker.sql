-- Expected: zero. Explicitly authored rules are not overwritten.
SELECT COUNT(*) AS imported_three_sum_without_checker
FROM tb_question
WHERE question_type = 'PROGRAMMING'
  AND JSON_UNQUOTE(JSON_EXTRACT(
      CASE WHEN JSON_VALID(grading_config_json) THEN grading_config_json ELSE '{}' END,
      '$.source')) = 'leetcode-hot-100'
  AND JSON_UNQUOTE(JSON_EXTRACT(
      CASE WHEN JSON_VALID(grading_config_json) THEN grading_config_json ELSE '{}' END,
      '$.sourceId')) = '15'
  AND JSON_EXTRACT(
      CASE WHEN JSON_VALID(grading_config_json) THEN grading_config_json ELSE '{}' END,
      '$.checker') IS NULL;
