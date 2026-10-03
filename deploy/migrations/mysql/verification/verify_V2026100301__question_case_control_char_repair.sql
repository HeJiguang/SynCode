-- Every query before the final summary must return zero rows.
-- Only rows the migration was supposed to repair (invalid now, valid after control-char
-- escaping) are reported; rows invalid for other reasons are out of scope here.

SELECT question_id, title, 'question_case still contains repairable raw control characters' AS problem
FROM tb_question
WHERE question_case IS NOT NULL
  AND NOT JSON_VALID(question_case)
  AND JSON_VALID(REPLACE(
        REPLACE(
            REPLACE(question_case,
                CHAR(10), CONCAT(CHAR(92), 'n')),
            CHAR(13), CONCAT(CHAR(92), 'r')),
        CHAR(9), CONCAT(CHAR(92), 't')));

SELECT version_question_id, question_id, 'exam snapshot still contains repairable raw control characters' AS problem
FROM tb_exam_version_question
WHERE question_case IS NOT NULL
  AND NOT JSON_VALID(question_case)
  AND JSON_VALID(REPLACE(
        REPLACE(
            REPLACE(question_case,
                CHAR(10), CONCAT(CHAR(92), 'n')),
            CHAR(13), CONCAT(CHAR(92), 'r')),
        CHAR(9), CONCAT(CHAR(92), 't')));

SELECT COUNT(*) AS questions_with_valid_question_case_json
FROM tb_question
WHERE question_case IS NULL OR JSON_VALID(question_case);
