-- Evidence-backed user learning memory for Hermes.
-- Apply after 2026-10-14-hermes-skill-registry.sql and
-- 2026-10-14-hermes-skill-governance.sql on an existing database.

USE bitoj_dev;

CREATE TABLE IF NOT EXISTS tb_ai_learning_memory (
    memory_id char(64) NOT NULL COMMENT 'deterministic memory id',
    user_id bigint unsigned NOT NULL COMMENT 'owner user id',
    memory_level varchar(16) NOT NULL COMMENT 'event episode pattern',
    memory_type varchar(32) NOT NULL COMMENT 'submission exam_result problem_episode exam_episode error_pattern',
    title varchar(255) NOT NULL,
    summary varchar(2000) NOT NULL,
    knowledge_tags_json longtext COMMENT 'bounded JSON tag list',
    error_type varchar(64) DEFAULT NULL,
    memory_status varchar(16) NOT NULL COMMENT 'active improving resolved superseded',
    confidence decimal(8,6) NOT NULL DEFAULT 1.000000,
    occurrence_count int unsigned NOT NULL DEFAULT 1,
    source_type varchar(32) NOT NULL,
    source_id varchar(192) NOT NULL,
    occurred_at datetime(3) DEFAULT NULL,
    first_seen_at datetime(3) DEFAULT NULL,
    last_seen_at datetime(3) DEFAULT NULL,
    content_hash char(64) NOT NULL,
    structured_payload longtext COMMENT 'derived facts without submitted source code',
    create_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (memory_id),
    UNIQUE KEY uk_ai_learning_memory_source (user_id, memory_level, source_type, source_id),
    KEY idx_ai_learning_memory_recall (user_id, memory_level, memory_status, last_seen_at),
    KEY idx_ai_learning_memory_type (user_id, memory_type, last_seen_at),
    KEY idx_ai_learning_memory_error (user_id, error_type, last_seen_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='rebuildable event episode and pattern learning memories';

CREATE TABLE IF NOT EXISTS tb_ai_learning_memory_evidence (
    memory_id char(64) NOT NULL,
    evidence_type varchar(32) NOT NULL COMMENT 'submission episode exam',
    evidence_id varchar(192) NOT NULL,
    occurred_at datetime(3) DEFAULT NULL,
    snippet varchar(1000) DEFAULT NULL COMMENT 'bounded non-code evidence summary',
    structured_payload longtext,
    create_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (memory_id, evidence_type, evidence_id),
    KEY idx_ai_learning_memory_evidence_source (evidence_type, evidence_id),
    KEY idx_ai_learning_memory_evidence_time (memory_id, occurred_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='traceable source evidence for derived learning memories';

CREATE TABLE IF NOT EXISTS tb_ai_learning_memory_projection_state (
    user_id bigint unsigned NOT NULL,
    source_fingerprint char(64) NOT NULL,
    event_count int unsigned NOT NULL DEFAULT 0,
    episode_count int unsigned NOT NULL DEFAULT 0,
    pattern_count int unsigned NOT NULL DEFAULT 0,
    indexed_fingerprint char(64) DEFAULT NULL,
    last_sync_at datetime NOT NULL,
    last_indexed_at datetime DEFAULT NULL,
    create_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    KEY idx_ai_learning_memory_projection_sync (last_sync_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='per-user source and search-index projection state';

CREATE TABLE IF NOT EXISTS tb_ai_learning_state_memory (
    state_id char(64) NOT NULL COMMENT 'deterministic user and knowledge-tag state id',
    user_id bigint unsigned NOT NULL COMMENT 'owner user id',
    knowledge_tag varchar(100) NOT NULL,
    mastery_level varchar(24) NOT NULL COMMENT 'insufficient foundational developing stable proficient',
    mastery_score decimal(6,2) NOT NULL COMMENT 'explainable score from 0 to 100',
    confidence decimal(8,6) NOT NULL COMMENT 'evidence sufficiency from 0 to 1',
    trend varchar(16) NOT NULL COMMENT 'improving stable declining',
    priority_score decimal(6,2) NOT NULL COMMENT 'review priority from 0 to 100',
    episode_count int unsigned NOT NULL,
    attempt_count int unsigned NOT NULL,
    independent_pass_count int unsigned NOT NULL,
    error_episode_count int unsigned NOT NULL,
    recent_error_types_json longtext,
    first_practiced_at datetime(3) DEFAULT NULL,
    last_practiced_at datetime(3) DEFAULT NULL,
    next_review_at datetime(3) DEFAULT NULL,
    summary varchar(2000) NOT NULL,
    content_hash char(64) NOT NULL,
    structured_payload longtext,
    create_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (state_id),
    UNIQUE KEY uk_ai_learning_state_user_tag (user_id, knowledge_tag),
    KEY idx_ai_learning_state_priority (user_id, priority_score, next_review_at),
    KEY idx_ai_learning_state_level (user_id, mastery_level, trend)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='dynamic per-user knowledge mastery memory';

CREATE TABLE IF NOT EXISTS tb_ai_learning_state_evidence (
    state_id char(64) NOT NULL,
    memory_id char(64) NOT NULL COMMENT 'supporting problem episode memory',
    observed_at datetime(3) DEFAULT NULL,
    contribution decimal(8,6) NOT NULL COMMENT 'episode quality contribution from 0 to 1',
    reason varchar(500) NOT NULL,
    structured_payload longtext,
    create_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (state_id, memory_id),
    KEY idx_ai_learning_state_evidence_memory (memory_id),
    KEY idx_ai_learning_state_evidence_time (state_id, observed_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='problem-episode evidence for knowledge state memory';

CREATE TABLE IF NOT EXISTS tb_ai_learning_state_projection (
    user_id bigint unsigned NOT NULL,
    source_fingerprint char(64) NOT NULL,
    state_count int unsigned NOT NULL DEFAULT 0,
    last_sync_at datetime NOT NULL,
    create_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    KEY idx_ai_learning_state_projection_sync (last_sync_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='per-user learning-state projection status';

INSERT INTO tb_ai_skill (
    skill_id, skill_name, scope, owner_user_id, category, lifecycle_status, current_version
) VALUES
    ('platform:syncode-learning-memory', 'syncode-learning-memory', 'platform', 0, 'education', 'active', '1.2.0'),
    ('platform:syncode-diagnosis', 'syncode-diagnosis', 'platform', 0, 'education', 'active', '1.3.0'),
    ('platform:syncode-training-plan', 'syncode-training-plan', 'platform', 0, 'education', 'active', '1.3.0'),
    ('platform:syncode-tutor', 'syncode-tutor', 'platform', 0, 'education', 'active', '1.3.0')
ON DUPLICATE KEY UPDATE
    category = VALUES(category),
    lifecycle_status = VALUES(lifecycle_status),
    current_version = VALUES(current_version);

INSERT INTO tb_ai_skill_version (
    skill_id, version, content_hash, source_type, review_status, content_uri, metadata_json
) VALUES
    ('platform:syncode-learning-memory', '1.2.0', 'fc0fbfaae39409032dbf2fe157a43a2fa9caa3da1ed9e3345b5fefae8465394f', 'evolution', 'approved', 'hermes/skills/syncode-learning-memory/SKILL.md', NULL),
    ('platform:syncode-diagnosis', '1.3.0', '77e1a01eae99a9e3375f8dccbc5f963d540b96d4b864e5be0376eeaba7c10833', 'evolution', 'approved', 'hermes/skills/syncode-diagnosis/SKILL.md', NULL),
    ('platform:syncode-training-plan', '1.3.0', '7f4490ca740f5c7555c7849683ae53020e783595d5d823ef7c3635af372ed031', 'evolution', 'approved', 'hermes/skills/syncode-training-plan/SKILL.md', NULL),
    ('platform:syncode-tutor', '1.3.0', '790932279b790de7c33d9178c8f8a72e41b6ff9db2fad6156ecf24c80ce6f9b3', 'evolution', 'approved', 'hermes/skills/syncode-tutor/SKILL.md', NULL)
ON DUPLICATE KEY UPDATE
    content_hash = VALUES(content_hash),
    review_status = VALUES(review_status),
    content_uri = VALUES(content_uri);
