-- Native Hermes personal Skill isolation and cross-user platform Skill governance.
-- Apply after 2026-10-14-hermes-skill-registry.sql on an existing database.

USE bitoj_dev;

ALTER TABLE tb_ai_skill
    ADD COLUMN display_name varchar(128) DEFAULT NULL COMMENT 'human readable title' AFTER skill_name,
    ADD COLUMN description varchar(1000) DEFAULT NULL COMMENT 'bounded trigger description' AFTER display_name,
    ADD COLUMN source_path varchar(500) DEFAULT NULL COMMENT 'profile or platform package path' AFTER current_version,
    ADD COLUMN last_seen_at datetime DEFAULT NULL COMMENT 'last filesystem synchronization' AFTER source_path,
    ADD COLUMN archived_at datetime DEFAULT NULL AFTER last_seen_at;

ALTER TABLE tb_ai_skill_version
    ADD COLUMN content_text longtext COMMENT 'versioned SKILL.md snapshot' AFTER content_uri,
    ADD COLUMN package_json longtext COMMENT 'versioned text package snapshot' AFTER content_text,
    ADD COLUMN created_by_type varchar(16) DEFAULT NULL COMMENT 'hermes admin migration' AFTER metadata_json,
    ADD COLUMN created_by varchar(96) DEFAULT NULL COMMENT 'profile or administrator actor' AFTER created_by_type,
    ADD COLUMN source_candidate_id char(64) DEFAULT NULL AFTER created_by;

CREATE TABLE IF NOT EXISTS tb_ai_skill_promotion_candidate (
    candidate_id char(64) NOT NULL,
    cluster_key char(64) NOT NULL,
    title varchar(128) NOT NULL,
    proposed_skill_name varchar(64) NOT NULL,
    category varchar(64) DEFAULT NULL,
    status varchar(24) NOT NULL,
    summary varchar(1000) DEFAULT NULL,
    draft_content longtext,
    distinct_owner_count int unsigned NOT NULL,
    member_count int unsigned NOT NULL,
    usage_count_30d int unsigned NOT NULL DEFAULT 0,
    min_similarity decimal(10,8) DEFAULT NULL,
    similarity_method varchar(96) NOT NULL,
    reviewed_by varchar(96) DEFAULT NULL,
    review_note varchar(1000) DEFAULT NULL,
    reviewed_at datetime DEFAULT NULL,
    published_skill_id varchar(96) DEFAULT NULL,
    published_version varchar(32) DEFAULT NULL,
    create_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (candidate_id),
    UNIQUE KEY uk_ai_skill_promotion_cluster (cluster_key),
    KEY idx_ai_skill_promotion_status (status, distinct_owner_count, usage_count_30d)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='cross-user personal Skill promotion candidates';

CREATE TABLE IF NOT EXISTS tb_ai_skill_promotion_member (
    candidate_id char(64) NOT NULL,
    skill_id varchar(96) NOT NULL,
    skill_version varchar(32) NOT NULL,
    owner_hash char(64) NOT NULL,
    similarity_score decimal(10,8) NOT NULL,
    redacted_summary varchar(1000) DEFAULT NULL,
    usage_count_30d int unsigned NOT NULL DEFAULT 0,
    create_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (candidate_id, skill_id),
    KEY idx_ai_skill_promotion_member_skill (skill_id, skill_version),
    KEY idx_ai_skill_promotion_member_owner (owner_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='de-identified promotion evidence';

CREATE TABLE IF NOT EXISTS tb_ai_skill_promotion_review_action (
    action_id char(64) NOT NULL,
    candidate_id char(64) NOT NULL,
    reviewer varchar(96) NOT NULL,
    action varchar(16) NOT NULL,
    before_status varchar(24) NOT NULL,
    after_status varchar(24) NOT NULL,
    note varchar(1000) DEFAULT NULL,
    create_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (action_id),
    KEY idx_ai_skill_promotion_action_candidate (candidate_id, create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='platform Skill promotion audit log';

CREATE TABLE IF NOT EXISTS tb_ai_skill_release (
    release_id char(64) NOT NULL,
    skill_id varchar(96) NOT NULL,
    version varchar(32) NOT NULL,
    source_candidate_id char(64) DEFAULT NULL,
    status varchar(16) NOT NULL,
    published_by varchar(96) NOT NULL,
    published_at datetime NOT NULL,
    create_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (release_id),
    UNIQUE KEY uk_ai_skill_release_version (skill_id, version),
    KEY idx_ai_skill_release_status (status, published_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='immutable platform Skill releases';

CREATE TABLE IF NOT EXISTS tb_ai_skill_lifecycle_review (
    review_id char(64) NOT NULL,
    skill_id varchar(96) NOT NULL,
    skill_version varchar(32) NOT NULL,
    reason varchar(500) NOT NULL,
    status varchar(16) NOT NULL,
    usage_count_30d int unsigned NOT NULL DEFAULT 0,
    last_used_at datetime(3) DEFAULT NULL,
    reviewed_by varchar(96) DEFAULT NULL,
    review_note varchar(1000) DEFAULT NULL,
    reviewed_at datetime DEFAULT NULL,
    create_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (review_id),
    UNIQUE KEY uk_ai_skill_lifecycle_version_reason (skill_id, skill_version, reason),
    KEY idx_ai_skill_lifecycle_status (status, create_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='stale platform Skill review queue';

CREATE TABLE IF NOT EXISTS tb_ai_skill_governance_heartbeat (
    heartbeat_id char(64) NOT NULL,
    status varchar(16) NOT NULL,
    metrics_json longtext,
    error_message varchar(2000) DEFAULT NULL,
    started_at datetime NOT NULL,
    finished_at datetime DEFAULT NULL,
    create_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (heartbeat_id),
    KEY idx_ai_skill_heartbeat_status (status, started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Skill governance heartbeat history';
