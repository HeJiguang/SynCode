CREATE TABLE IF NOT EXISTS tb_ai_skill (
    skill_id varchar(96) NOT NULL COMMENT 'stable registry id',
    skill_name varchar(64) NOT NULL COMMENT 'Hermes skill name',
    display_name varchar(128) DEFAULT NULL COMMENT 'human readable title',
    description varchar(1000) DEFAULT NULL COMMENT 'bounded trigger description',
    scope varchar(16) NOT NULL COMMENT 'platform or personal',
    owner_user_id bigint unsigned NOT NULL DEFAULT 0 COMMENT '0 for platform; user id for personal skills',
    category varchar(64) DEFAULT NULL COMMENT 'governance category',
    lifecycle_status varchar(16) NOT NULL DEFAULT 'active' COMMENT 'active stale archived',
    current_version varchar(32) NOT NULL COMMENT 'currently deployed version',
    source_path varchar(500) DEFAULT NULL COMMENT 'profile or platform package path',
    last_seen_at datetime DEFAULT NULL COMMENT 'last filesystem synchronization',
    archived_at datetime DEFAULT NULL,
    create_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (skill_id),
    UNIQUE KEY uk_ai_skill_scope_owner_name (scope, owner_user_id, skill_name),
    KEY idx_ai_skill_name_scope (skill_name, scope),
    KEY idx_ai_skill_lifecycle (lifecycle_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Hermes skill registry';

CREATE TABLE IF NOT EXISTS tb_ai_skill_version (
    skill_id varchar(96) NOT NULL COMMENT 'registry skill id',
    version varchar(32) NOT NULL COMMENT 'semantic or immutable version',
    content_hash char(64) NOT NULL COMMENT 'sha256 of the packaged skill',
    source_type varchar(24) NOT NULL COMMENT 'manual personal promotion evolution',
    review_status varchar(16) NOT NULL DEFAULT 'approved' COMMENT 'draft reviewing approved rejected',
    content_uri varchar(500) DEFAULT NULL COMMENT 'immutable package location',
    content_text longtext COMMENT 'versioned SKILL.md snapshot',
    package_json longtext COMMENT 'versioned text package snapshot',
    metadata_json longtext COMMENT 'non-sensitive version metadata',
    created_by_type varchar(16) DEFAULT NULL COMMENT 'hermes admin migration',
    created_by varchar(96) DEFAULT NULL COMMENT 'profile or administrator actor',
    source_candidate_id char(64) DEFAULT NULL,
    create_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (skill_id, version),
    KEY idx_ai_skill_version_review (review_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Hermes skill versions';

CREATE TABLE IF NOT EXISTS tb_ai_skill_promotion_candidate (
    candidate_id char(64) NOT NULL,
    cluster_key char(64) NOT NULL COMMENT 'stable set of contributing personal skills',
    title varchar(128) NOT NULL,
    proposed_skill_name varchar(64) NOT NULL,
    category varchar(64) DEFAULT NULL,
    status varchar(24) NOT NULL COMMENT 'discovered reviewing rejected published',
    summary varchar(1000) DEFAULT NULL,
    draft_content longtext COMMENT 'AI-generalized administrator-editable SKILL.md',
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
    owner_hash char(64) NOT NULL COMMENT 'one-way owner pseudonym',
    similarity_score decimal(10,8) NOT NULL,
    redacted_summary varchar(1000) DEFAULT NULL,
    usage_count_30d int unsigned NOT NULL DEFAULT 0,
    create_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (candidate_id, skill_id),
    KEY idx_ai_skill_promotion_member_skill (skill_id, skill_version),
    KEY idx_ai_skill_promotion_member_owner (owner_hash)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='de-identified evidence behind a platform Skill candidate';

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
    status varchar(16) NOT NULL COMMENT 'active archived rolled_back',
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
    status varchar(16) NOT NULL COMMENT 'pending kept archived',
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='administrator review queue for stale platform Skills';

CREATE TABLE IF NOT EXISTS tb_ai_skill_governance_heartbeat (
    heartbeat_id char(64) NOT NULL,
    status varchar(16) NOT NULL COMMENT 'running completed failed',
    metrics_json longtext,
    error_message varchar(2000) DEFAULT NULL,
    started_at datetime NOT NULL,
    finished_at datetime DEFAULT NULL,
    create_time datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (heartbeat_id),
    KEY idx_ai_skill_heartbeat_status (status, started_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Skill synchronization discovery and lifecycle heartbeat';

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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='append-only Hermes skill usage evidence';

CREATE TABLE IF NOT EXISTS tb_ai_learning_memory (
    memory_id char(64) NOT NULL COMMENT 'deterministic memory id',
    user_id bigint unsigned NOT NULL COMMENT 'owner user id',
    memory_level varchar(16) NOT NULL COMMENT 'event episode pattern',
    memory_type varchar(32) NOT NULL,
    title varchar(255) NOT NULL,
    summary varchar(2000) NOT NULL,
    knowledge_tags_json longtext,
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
    structured_payload longtext,
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
    evidence_type varchar(32) NOT NULL,
    evidence_id varchar(192) NOT NULL,
    occurred_at datetime(3) DEFAULT NULL,
    snippet varchar(1000) DEFAULT NULL,
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
    state_id char(64) NOT NULL,
    user_id bigint unsigned NOT NULL,
    knowledge_tag varchar(100) NOT NULL,
    mastery_level varchar(24) NOT NULL,
    mastery_score decimal(6,2) NOT NULL,
    confidence decimal(8,6) NOT NULL,
    trend varchar(16) NOT NULL,
    priority_score decimal(6,2) NOT NULL,
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
    memory_id char(64) NOT NULL,
    observed_at datetime(3) DEFAULT NULL,
    contribution decimal(8,6) NOT NULL,
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
    ('platform:syncode-tutor', 'syncode-tutor', 'platform', 0, 'education', 'active', '1.3.0'),
    ('platform:syncode-diagnosis', 'syncode-diagnosis', 'platform', 0, 'education', 'active', '1.3.0'),
    ('platform:syncode-training-plan', 'syncode-training-plan', 'platform', 0, 'education', 'active', '1.3.0'),
    ('platform:syncode-learning-memory', 'syncode-learning-memory', 'platform', 0, 'education', 'active', '1.2.0')
ON DUPLICATE KEY UPDATE
    category = VALUES(category),
    lifecycle_status = VALUES(lifecycle_status),
    current_version = VALUES(current_version);

INSERT INTO tb_ai_skill_version (
    skill_id, version, content_hash, source_type, review_status, content_uri, created_by_type, created_by
) VALUES
    ('platform:syncode-tutor', '1.3.0', 'f69683563aa09d2e4224cefe48cb07b02d41cbef37e88ad97efae5bcf20e0f61', 'manual', 'approved', 'hermes/skills/syncode-tutor/SKILL.md', 'migration', 'V2026101401'),
    ('platform:syncode-diagnosis', '1.3.0', '8391682fcdb43193a0ecffa38265a63590eda22f03d66569a36732ab8d10fc0e', 'manual', 'approved', 'hermes/skills/syncode-diagnosis/SKILL.md', 'migration', 'V2026101401'),
    ('platform:syncode-training-plan', '1.3.0', 'd42cbe1e107e31519719de46bbb7e808da1fae08e02ca6fc68db80315269cbcc', 'manual', 'approved', 'hermes/skills/syncode-training-plan/SKILL.md', 'migration', 'V2026101401'),
    ('platform:syncode-learning-memory', '1.2.0', 'e245bfebf5b5f6b972314ebdfdedf08bacb68def3b5a9ab6ee72d504014e7f61', 'manual', 'approved', 'hermes/skills/syncode-learning-memory/SKILL.md', 'migration', 'V2026101401')
ON DUPLICATE KEY UPDATE
    content_hash = VALUES(content_hash),
    review_status = VALUES(review_status),
    content_uri = VALUES(content_uri);
