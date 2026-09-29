-- Logical rollback for V2026092201.
-- Safe before or after new writes: deploy the previous application and retain
-- these additive tables so chat, memory and approval audit data remain recoverable.
-- No DROP or DELETE statements are performed automatically.

SELECT 'Deploy the previous application version; preserve tb_ai_* tables for recovery.' AS rollback_action;

