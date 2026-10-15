-- Hermes Skill registry and append-only invocation accounting.

USE bitoj_dev;

CREATE TABLE IF NOT EXISTS tb_ai_skill (
    skill_id varchar(96) NOT NULL COMMENT 'stable registry id',
    skill_name varchar(64) NOT NULL COMMENT 'Hermes Skill name',
    scope varchar(16) NOT NULL COMMENT 'platform or personal',
    owner_user_id bigint unsigned NOT NULL DEFAULT 0 COMMENT '0 for platform; user id for personal Skills',
    category varchar(64) DEFAULT NULL COMMENT 'governance category',
    lifecycle_status varchar(16) NOT NULL DEFAULT 'active' COMMENT 'active stale archived',
    current_version varchar(32) NOT NULL COMMENT 'currently deployed version',
    create_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (skill_id),
    UNIQUE KEY uk_ai_skill_scope_owner_name (scope, owner_user_id, skill_name),
    KEY idx_ai_skill_name_scope (skill_name, scope),
    KEY idx_ai_skill_lifecycle (lifecycle_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Hermes Skill registry';

CREATE TABLE IF NOT EXISTS tb_ai_skill_version (
    skill_id varchar(96) NOT NULL COMMENT 'registry Skill id',
    version varchar(32) NOT NULL COMMENT 'immutable version',
    content_hash char(64) NOT NULL COMMENT 'sha256 of the packaged Skill',
    source_type varchar(24) NOT NULL COMMENT 'manual personal promotion evolution',
    review_status varchar(16) NOT NULL DEFAULT 'approved' COMMENT 'draft reviewing approved rejected',
    content_uri varchar(500) DEFAULT NULL COMMENT 'immutable package location',
    metadata_json longtext COMMENT 'non-sensitive version metadata',
    create_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (skill_id, version),
    KEY idx_ai_skill_version_review (review_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Hermes Skill versions';

CREATE TABLE IF NOT EXISTS tb_ai_skill_usage_event (
    event_id varchar(192) NOT NULL COMMENT 'idempotency key from the proxy',
    user_id bigint unsigned NOT NULL COMMENT 'internal user id',
    profile_name varchar(96) NOT NULL COMMENT 'Hermes profile used for the run',
    run_id varchar(192) NOT NULL COMMENT 'Hermes run id',
    session_id varchar(192) DEFAULT NULL COMMENT 'Hermes session id',
    skill_name varchar(64) NOT NULL COMMENT 'Skill loaded by Hermes',
    skill_version varchar(32) DEFAULT NULL COMMENT 'resolved deployed version',
    event_type varchar(64) NOT NULL COMMENT 'skill.invoked',
    occurred_at datetime(3) NOT NULL COMMENT 'source event time in UTC',
    payload_json longtext COMMENT 'bounded skill_view metadata',
    create_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (event_id),
    KEY idx_ai_skill_event_run (run_id, occurred_at),
    KEY idx_ai_skill_event_user_time (user_id, occurred_at),
    KEY idx_ai_skill_event_skill_time (skill_name, skill_version, occurred_at),
    KEY idx_ai_skill_event_type_time (event_type, occurred_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='append-only Hermes Skill invocation events';
