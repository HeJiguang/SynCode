-- Purpose: add mixed question authoring, immutable answer/grading snapshots and manual review metadata.
-- Compatibility: existing rows remain PROGRAMMING and keep their legacy judge fields.
-- Lock risk: metadata locks on question and grade-item tables; run outside active exams.
-- Rollback: rollback_V2026091601__mixed_question_types.sql is destructive and only safe before mixed writes.

ALTER TABLE tb_question
    MODIFY COLUMN content longtext NOT NULL COMMENT 'question statement',
    MODIFY COLUMN question_case longtext NULL COMMENT 'programming judge cases',
    MODIFY COLUMN default_code longtext NULL COMMENT 'starter code',
    MODIFY COLUMN main_fuc longtext NULL COMMENT 'entry code block',
    ADD COLUMN question_type varchar(32) NOT NULL DEFAULT 'PROGRAMMING' AFTER training_enabled,
    ADD COLUMN answer_config_json json NULL AFTER question_type,
    ADD COLUMN grading_config_json json NULL AFTER answer_config_json,
    ADD KEY idx_question_type (question_type);

ALTER TABLE tb_exam_version_question
    ADD COLUMN answer_config_json json NULL AFTER judge_config_json,
    ADD COLUMN grading_config_json json NULL AFTER answer_config_json;

ALTER TABLE tb_exam_grade_item
    ADD COLUMN feedback varchar(1000) NULL AFTER adjustment_reason;
