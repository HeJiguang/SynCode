-- Manual recovery only. No automatic UPDATE: an existing authored unorderedTriples rule
-- cannot be distinguished from the backfill without the pre-release backup.
-- Restore grading_config_json ONLY for rows changed by V2026102701 from that backup,
-- then rebuild their ES documents. Do not modify captured exam versions or submissions.
SELECT question_id, title, grading_config_json
FROM tb_question
WHERE question_type = 'PROGRAMMING'
  AND JSON_UNQUOTE(JSON_EXTRACT(
      CASE WHEN JSON_VALID(grading_config_json) THEN grading_config_json ELSE '{}' END,
      '$.source')) = 'leetcode-hot-100'
  AND JSON_UNQUOTE(JSON_EXTRACT(
      CASE WHEN JSON_VALID(grading_config_json) THEN grading_config_json ELSE '{}' END,
      '$.sourceId')) = '15';
