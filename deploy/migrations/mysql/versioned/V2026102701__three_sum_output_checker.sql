-- Backfill the known Hot100 importer format, preserving explicit rules and exam snapshots.
UPDATE tb_question
SET grading_config_json = JSON_SET(grading_config_json, '$.checker', 'unorderedTriples')
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
