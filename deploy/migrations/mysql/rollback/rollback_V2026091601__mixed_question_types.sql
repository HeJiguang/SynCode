-- Logical rollback. Only use after confirming no mixed-type questions or published snapshots remain.
ALTER TABLE tb_exam_grade_item DROP COLUMN feedback;
ALTER TABLE tb_exam_version_question DROP COLUMN grading_config_json, DROP COLUMN answer_config_json;
ALTER TABLE tb_question DROP KEY idx_question_type, DROP COLUMN grading_config_json,
    DROP COLUMN answer_config_json, DROP COLUMN question_type;
