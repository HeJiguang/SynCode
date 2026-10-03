-- Purpose: repair judge-case JSON rows whose string values contain raw control characters
--   (typically real newlines inside multi-line inputs). Strict parsers such as hutool reject
--   those documents with "Unterminated string", which broke the question detail and submit
--   endpoints for the affected legacy questions.
-- Compatibility: only rows that are invalid now AND become valid JSON after escaping are
--   touched, so already-valid rows (including pretty-printed layouts) stay byte-identical.
--   CHAR(92) is used instead of a backslash literal so the statement behaves identically
--   regardless of the server's NO_BACKSLASH_ESCAPES sql_mode.
-- Lock risk: full-table UPDATEs on tb_question and tb_exam_version_question (small tables);
--   run outside active exams.
-- Rollback: forward-only; the escaped forms are the correct JSON representation. See
--   rollback_V2026100301__question_case_control_char_repair.sql for the note.

UPDATE tb_question
SET question_case = REPLACE(
        REPLACE(
            REPLACE(question_case,
                CHAR(10), CONCAT(CHAR(92), 'n')),
            CHAR(13), CONCAT(CHAR(92), 'r')),
        CHAR(9), CONCAT(CHAR(92), 't'))
WHERE question_case IS NOT NULL
  AND NOT JSON_VALID(question_case)
  AND JSON_VALID(REPLACE(
        REPLACE(
            REPLACE(question_case,
                CHAR(10), CONCAT(CHAR(92), 'n')),
            CHAR(13), CONCAT(CHAR(92), 'r')),
        CHAR(9), CONCAT(CHAR(92), 't')));

UPDATE tb_exam_version_question
SET question_case = REPLACE(
        REPLACE(
            REPLACE(question_case,
                CHAR(10), CONCAT(CHAR(92), 'n')),
            CHAR(13), CONCAT(CHAR(92), 'r')),
        CHAR(9), CONCAT(CHAR(92), 't'))
WHERE question_case IS NOT NULL
  AND NOT JSON_VALID(question_case)
  AND JSON_VALID(REPLACE(
        REPLACE(
            REPLACE(question_case,
                CHAR(10), CONCAT(CHAR(92), 'n')),
            CHAR(13), CONCAT(CHAR(92), 'r')),
        CHAR(9), CONCAT(CHAR(92), 't')));
