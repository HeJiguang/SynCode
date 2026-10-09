-- Purpose: persist the recommendation feedback events produced by controlled Hermes learning tools.
-- Compatibility: additive table; previous application versions ignore it.
-- Lock risk: creates one new table only and does not alter existing business tables.
-- Rollback: rollback_V2026100901__agent_recommendation_feedback.sql preserves data by default.

CREATE TABLE tb_ai_recommendation_event (
    event_id bigint unsigned NOT NULL AUTO_INCREMENT,
    user_id bigint unsigned NOT NULL COMMENT 'trusted SynCode user derived from the Hermes profile',
    recommendation_id varchar(128) NOT NULL COMMENT 'stable recommendation or plan-task correlation id',
    action varchar(24) NOT NULL COMMENT 'impression, opened, accepted, skipped, completed or reopened',
    question_id bigint unsigned NULL,
    plan_id bigint unsigned NULL,
    task_id bigint unsigned NULL,
    run_id varchar(160) NULL COMMENT 'public Runtime run id when available',
    metadata_json json NOT NULL,
    create_time datetime(3) NOT NULL,
    PRIMARY KEY (event_id),
    KEY idx_ai_recommendation_user_time (user_id, create_time),
    KEY idx_ai_recommendation_correlation (recommendation_id, create_time),
    KEY idx_ai_recommendation_plan_task (plan_id, task_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='Hermes recommendation feedback timeline';
