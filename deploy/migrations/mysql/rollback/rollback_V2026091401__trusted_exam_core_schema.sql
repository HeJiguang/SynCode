-- Logical rollback for V2026091401. This file intentionally performs no destructive DDL.
--
-- Safe before new writes:
--   1. Restore the previous application images.
--   2. Leave additive tables and columns in place; legacy services ignore them.
--   3. Verify legacy exam list, question navigation, and practice submission paths.
--
-- After new trusted-exam writes exist:
--   1. Enable maintenance mode for new exam commands.
--   2. Restore the previous application images only if they will not mutate exams that
--      have current_version_id populated.
--   3. Preserve all version, attempt, answer, submission, grade, integrity, audit, and
--      outbox rows for forward recovery.
--   4. Prefer a corrective forward migration. Restore the pre-migration backup only
--      for an immediate correctness/security emergency and only after exporting new rows.
--
-- Verification after application rollback (all counts are informational):
SELECT COUNT(*) AS version_rows FROM tb_exam_version;
SELECT COUNT(*) AS attempt_rows FROM tb_exam_attempt;
SELECT COUNT(*) AS answer_rows FROM tb_exam_answer;
SELECT COUNT(*) AS pending_outbox_rows FROM tb_exam_outbox WHERE status = 0;

-- Destructive DROP statements are deliberately absent. Removing these structures after
-- captured exam activity would destroy auditability and is not an approved rollback.
