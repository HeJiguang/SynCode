-- Dangerous on purpose: full development reset for bitoj_dev.
-- Usage:
--   mysql -h <host> -u <user> -p bitoj_dev < reset-and-init-complete.sql
-- This script drops the current development tables and then reloads
-- init-complete.sql from an absolute path on the machine where mysql runs.

USE bitoj_dev;

SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS tb_ai_learning_state_projection;
DROP TABLE IF EXISTS tb_ai_learning_state_evidence;
DROP TABLE IF EXISTS tb_ai_learning_state_memory;
DROP TABLE IF EXISTS tb_ai_learning_memory_projection_state;
DROP TABLE IF EXISTS tb_ai_learning_memory_evidence;
DROP TABLE IF EXISTS tb_ai_learning_memory;
DROP TABLE IF EXISTS tb_ai_skill_usage_event;
DROP TABLE IF EXISTS tb_ai_skill_governance_heartbeat;
DROP TABLE IF EXISTS tb_ai_skill_lifecycle_review;
DROP TABLE IF EXISTS tb_ai_skill_release;
DROP TABLE IF EXISTS tb_ai_skill_promotion_review_action;
DROP TABLE IF EXISTS tb_ai_skill_promotion_member;
DROP TABLE IF EXISTS tb_ai_skill_promotion_candidate;
DROP TABLE IF EXISTS tb_ai_skill_version;
DROP TABLE IF EXISTS tb_ai_skill;
DROP TABLE IF EXISTS tb_training_task;
DROP TABLE IF EXISTS tb_training_plan;
DROP TABLE IF EXISTS tb_training_profile;
DROP TABLE IF EXISTS tb_notice;
DROP TABLE IF EXISTS tb_message;
DROP TABLE IF EXISTS tb_message_text;
DROP TABLE IF EXISTS tb_user_submit;
DROP TABLE IF EXISTS tb_user_exam;
DROP TABLE IF EXISTS tb_user;
DROP TABLE IF EXISTS tb_exam_question;
DROP TABLE IF EXISTS tb_exam;
DROP TABLE IF EXISTS tb_question;
DROP TABLE IF EXISTS tb_sys_user;

SET FOREIGN_KEY_CHECKS = 1;

SOURCE /root/sql-import/init-complete.sql;
