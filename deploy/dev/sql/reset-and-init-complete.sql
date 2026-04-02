-- Dangerous on purpose: full development reset for bitoj_dev.
-- Usage:
--   mysql -h <host> -u <user> -p bitoj_dev < reset-and-init-complete.sql
-- This script drops the current development tables and then reloads
-- init-complete.sql from an absolute path on the machine where mysql runs.

USE bitoj_dev;

SET FOREIGN_KEY_CHECKS = 0;

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
