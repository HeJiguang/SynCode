-- Logical rollback (safe before or after writes): deploy the previous application images and leave this
-- additive table in place. Existing versions ignore it, while retaining it preserves recommendation history.
-- Do not DROP the table unless a reviewed maintenance window and verified backup explicitly permit data loss.

SELECT COUNT(*) AS preserved_recommendation_event_count
FROM tb_ai_recommendation_event;
