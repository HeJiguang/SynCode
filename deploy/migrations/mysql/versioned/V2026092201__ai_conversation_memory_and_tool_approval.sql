-- Purpose: persist user-owned AI conversations, reviewable memories and scoped tool approvals.
-- Compatibility: additive tables; existing application versions ignore them.
-- Lock risk: creates new tables only and does not lock existing business tables.
-- Rollback: rollback_V2026092201__ai_conversation_memory_and_tool_approval.sql keeps data by default.

CREATE TABLE tb_ai_run (
    run_pk bigint unsigned NOT NULL AUTO_INCREMENT,
    public_id varchar(64) NOT NULL COMMENT 'unguessable API run id',
    user_id varchar(64) NOT NULL COMMENT 'opaque run owner id',
    conversation_public_id varchar(64) NULL,
    run_type varchar(48) NOT NULL,
    source varchar(48) NOT NULL,
    status varchar(32) NOT NULL,
    entry_graph varchar(120) NOT NULL,
    active_node varchar(120) NULL,
    priority varchar(16) NOT NULL,
    trace_id varchar(64) NOT NULL,
    context_ref_json json NOT NULL,
    request_json json NOT NULL COMMENT 'normalized request needed to resume an approved turn',
    created_at datetime(3) NOT NULL,
    updated_at datetime(3) NOT NULL,
    completed_at datetime(3) NULL,
    PRIMARY KEY (run_pk),
    UNIQUE KEY uk_ai_run_public_id (public_id),
    KEY idx_ai_run_user_created (user_id, created_at),
    KEY idx_ai_run_conversation_created (conversation_public_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='durable AI agent runs';

CREATE TABLE tb_ai_run_event (
    event_pk bigint unsigned NOT NULL AUTO_INCREMENT,
    public_id varchar(64) NOT NULL,
    run_public_id varchar(64) NOT NULL,
    sequence_no int unsigned NOT NULL,
    event_type varchar(64) NOT NULL,
    level varchar(16) NOT NULL,
    payload_json json NOT NULL,
    created_at datetime(3) NOT NULL,
    PRIMARY KEY (event_pk),
    UNIQUE KEY uk_ai_run_event_public_id (public_id),
    UNIQUE KEY uk_ai_run_event_run_seq (run_public_id, sequence_no),
    KEY idx_ai_run_event_run_created (run_public_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='ordered AI run event timeline';

CREATE TABLE tb_ai_artifact (
    artifact_pk bigint unsigned NOT NULL AUTO_INCREMENT,
    public_id varchar(64) NOT NULL,
    run_public_id varchar(64) NOT NULL,
    artifact_type varchar(64) NOT NULL,
    title varchar(255) NOT NULL,
    summary varchar(1000) NULL,
    body_json json NOT NULL,
    render_hint varchar(48) NOT NULL,
    version int unsigned NOT NULL DEFAULT 1,
    created_at datetime(3) NOT NULL,
    PRIMARY KEY (artifact_pk),
    UNIQUE KEY uk_ai_artifact_public_id (public_id),
    KEY idx_ai_artifact_run_created (run_public_id, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='durable renderable AI run output';

CREATE TABLE tb_ai_conversation (
    conversation_id bigint unsigned NOT NULL AUTO_INCREMENT COMMENT 'internal conversation id',
    public_id varchar(64) NOT NULL COMMENT 'unguessable API conversation id',
    conversation_key varchar(128) NOT NULL COMMENT 'idempotent default/manual conversation key',
    user_id varchar(64) NOT NULL COMMENT 'opaque conversation owner id',
    title varchar(160) NOT NULL COMMENT 'user-visible title',
    status varchar(24) NOT NULL COMMENT 'ACTIVE, ROLLED_OVER or ARCHIVED',
    default_slot tinyint NULL COMMENT '1 for the current default learning chat, null otherwise',
    current_question_id varchar(64) NULL COMMENT 'last active question',
    current_question_title varchar(255) NULL COMMENT 'question title snapshot',
    continued_from_public_id varchar(64) NULL COMMENT 'previous visible chat when rolled over',
    message_count int unsigned NOT NULL DEFAULT 0,
    context_token_estimate int unsigned NOT NULL DEFAULT 0,
    soft_token_limit int unsigned NOT NULL,
    hard_token_limit int unsigned NOT NULL,
    created_at datetime(3) NOT NULL,
    updated_at datetime(3) NOT NULL,
    last_message_at datetime(3) NULL,
    PRIMARY KEY (conversation_id),
    UNIQUE KEY uk_ai_conversation_public_id (public_id),
    UNIQUE KEY uk_ai_conversation_key (conversation_key),
    UNIQUE KEY uk_ai_conversation_user_default (user_id, default_slot),
    KEY idx_ai_conversation_user_updated (user_id, updated_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='user-visible AI chats';

CREATE TABLE tb_ai_message (
    message_id bigint unsigned NOT NULL AUTO_INCREMENT,
    public_id varchar(64) NOT NULL,
    conversation_id bigint unsigned NOT NULL,
    user_id varchar(64) NOT NULL COMMENT 'denormalized owner for audit and isolation',
    run_id varchar(64) NULL,
    role varchar(16) NOT NULL COMMENT 'USER, ASSISTANT or SYSTEM',
    content longtext NOT NULL,
    sequence_no int unsigned NOT NULL,
    question_id varchar(64) NULL,
    context_snapshot json NOT NULL COMMENT 'immutable context used for this turn',
    artifact_json json NULL COMMENT 'renderable assistant artifact snapshot',
    token_estimate int unsigned NOT NULL DEFAULT 0,
    status varchar(16) NOT NULL COMMENT 'COMPLETE or FAILED',
    created_at datetime(3) NOT NULL,
    PRIMARY KEY (message_id),
    UNIQUE KEY uk_ai_message_public_id (public_id),
    UNIQUE KEY uk_ai_message_conversation_seq (conversation_id, sequence_no),
    KEY idx_ai_message_run (run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='durable messages and per-turn context';

CREATE TABLE tb_ai_memory (
    memory_id bigint unsigned NOT NULL AUTO_INCREMENT,
    public_id varchar(64) NOT NULL,
    user_id varchar(64) NOT NULL,
    memory_type varchar(40) NOT NULL,
    content varchar(1000) NOT NULL,
    reason varchar(500) NULL,
    confidence decimal(5,4) NOT NULL DEFAULT 0,
    status varchar(16) NOT NULL COMMENT 'PENDING, APPROVED or REJECTED',
    source_conversation_id varchar(64) NULL,
    source_message_id varchar(64) NULL,
    created_at datetime(3) NOT NULL,
    reviewed_at datetime(3) NULL,
    PRIMARY KEY (memory_id),
    UNIQUE KEY uk_ai_memory_public_id (public_id),
    KEY idx_ai_memory_user_status (user_id, status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='reviewable cross-chat memory items';

CREATE TABLE tb_ai_conversation_memory (
    binding_id bigint unsigned NOT NULL AUTO_INCREMENT,
    conversation_id bigint unsigned NOT NULL,
    memory_id bigint unsigned NOT NULL,
    content_snapshot varchar(1000) NOT NULL COMMENT 'approved value injected into this chat',
    created_at datetime(3) NOT NULL,
    PRIMARY KEY (binding_id),
    UNIQUE KEY uk_ai_conversation_memory (conversation_id, memory_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='auditable memory snapshot selected for a chat';

CREATE TABLE tb_ai_tool_approval (
    approval_id bigint unsigned NOT NULL AUTO_INCREMENT,
    public_id varchar(64) NOT NULL,
    user_id varchar(64) NOT NULL,
    conversation_public_id varchar(64) NULL,
    run_id varchar(64) NOT NULL,
    hermes_run_id varchar(64) NULL,
    hermes_request_id varchar(256) NULL,
    tool_name varchar(120) NOT NULL,
    action varchar(120) NOT NULL,
    resource varchar(1000) NULL,
    arguments_json json NOT NULL,
    risk_level varchar(16) NOT NULL,
    decision varchar(24) NOT NULL COMMENT 'AUTO_ALLOW, ASK_USER or BLOCK',
    status varchar(24) NOT NULL COMMENT 'PENDING, APPROVED, DENIED, EXPIRED or EXECUTED',
    reason varchar(500) NULL,
    created_at datetime(3) NOT NULL,
    expires_at datetime(3) NULL,
    resolved_at datetime(3) NULL,
    PRIMARY KEY (approval_id),
    UNIQUE KEY uk_ai_tool_approval_public_id (public_id),
    UNIQUE KEY uk_ai_tool_approval_remote_request (hermes_run_id, hermes_request_id),
    KEY idx_ai_tool_approval_user_status (user_id, status, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='per-run capability decisions and user approvals';
