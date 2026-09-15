-- Purpose: add the Phase 1 trusted-exam data model and immutable publication/runtime records.
-- Compatibility: additive for legacy services; new services use versioned rows for newly published exams.
-- Lock risk: metadata locks on the four altered legacy tables; run after preflight and outside peak exams.
-- Rollback: rollback/rollback_V2026091401__trusted_exam_core_schema.sql (logical rollback preserves data).

ALTER TABLE tb_exam
    ADD COLUMN description text NULL COMMENT 'candidate-facing exam instructions' AFTER title,
    ADD COLUMN latest_start_time datetime(3) NULL COMMENT 'latest time a new attempt may start' AFTER start_time,
    ADD COLUMN duration_minutes int NULL COMMENT 'per-attempt duration in minutes' AFTER end_time,
    ADD COLUMN timezone varchar(64) NOT NULL DEFAULT 'Asia/Shanghai' COMMENT 'display timezone; stored timestamps are UTC' AFTER duration_minutes,
    ADD COLUMN max_formal_submissions int NOT NULL DEFAULT 50 COMMENT 'formal submissions allowed per question' AFTER timezone,
    ADD COLUMN result_release_policy varchar(32) NOT NULL DEFAULT 'MANUAL' COMMENT 'MANUAL or SCHEDULED' AFTER max_formal_submissions,
    ADD COLUMN result_release_time datetime(3) NULL COMMENT 'scheduled result release time' AFTER result_release_policy,
    ADD COLUMN current_version_id bigint unsigned NULL COMMENT 'immutable version used by new attempts' AFTER result_release_time,
    ADD COLUMN version_no int NOT NULL DEFAULT 0 COMMENT 'last allocated immutable version number' AFTER current_version_id,
    ADD COLUMN row_version int NOT NULL DEFAULT 0 COMMENT 'optimistic lock version' AFTER version_no,
    ADD COLUMN published_time datetime(3) NULL COMMENT 'latest publish time' AFTER row_version,
    ADD COLUMN finished_time datetime(3) NULL COMMENT 'server-confirmed finish time' AFTER published_time,
    ADD COLUMN result_released_time datetime(3) NULL COMMENT 'server-confirmed result release time' AFTER finished_time,
    ADD COLUMN cancel_reason varchar(500) NULL COMMENT 'terminal cancellation reason' AFTER result_released_time,
    ADD CONSTRAINT chk_tb_exam_status CHECK (status BETWEEN 0 AND 5),
    ADD CONSTRAINT chk_tb_exam_duration CHECK (duration_minutes IS NULL OR duration_minutes > 0),
    ADD KEY idx_exam_status_time (status, start_time, end_time),
    ADD KEY idx_exam_current_version (current_version_id);

UPDATE tb_exam
SET duration_minutes = GREATEST(1, TIMESTAMPDIFF(MINUTE, start_time, end_time))
WHERE duration_minutes IS NULL;

ALTER TABLE tb_exam
    MODIFY COLUMN duration_minutes int NOT NULL COMMENT 'per-attempt duration in minutes';

ALTER TABLE tb_exam_question
    ADD COLUMN score int NOT NULL DEFAULT 100 COMMENT 'maximum score in draft composition' AFTER question_order,
    ADD COLUMN required_flag tinyint NOT NULL DEFAULT 1 COMMENT '0 optional 1 required' AFTER score,
    ADD COLUMN question_type varchar(32) NOT NULL DEFAULT 'PROGRAMMING' COMMENT 'future-compatible question type' AFTER required_flag,
    ADD CONSTRAINT chk_tb_exam_question_score CHECK (score > 0),
    ADD CONSTRAINT chk_tb_exam_question_required CHECK (required_flag IN (0, 1)),
    ADD UNIQUE KEY uk_exam_question (exam_id, question_id),
    ADD UNIQUE KEY uk_exam_question_order (exam_id, question_order);

ALTER TABLE tb_user_exam
    ADD COLUMN authorization_status tinyint NOT NULL DEFAULT 1 COMMENT '0 revoked 1 authorized' AFTER exam_id,
    ADD COLUMN authorization_source varchar(32) NOT NULL DEFAULT 'LEGACY' COMMENT 'MANUAL IMPORT or LEGACY' AFTER authorization_status,
    ADD COLUMN revoked_by bigint unsigned NULL COMMENT 'administrator revoking access' AFTER exam_rank,
    ADD COLUMN revoked_time datetime(3) NULL COMMENT 'server revoke time' AFTER revoked_by,
    ADD COLUMN revoke_reason varchar(500) NULL COMMENT 'access revoke reason' AFTER revoked_time,
    ADD CONSTRAINT chk_tb_user_exam_authorization CHECK (authorization_status IN (0, 1)),
    ADD UNIQUE KEY uk_user_exam (exam_id, user_id),
    ADD KEY idx_user_exam_user_status (user_id, authorization_status);

ALTER TABLE tb_user_submit
    ADD COLUMN attempt_id bigint unsigned NULL COMMENT 'trusted exam attempt; null for practice/legacy' AFTER exam_id,
    ADD COLUMN version_question_id bigint unsigned NULL COMMENT 'immutable version question' AFTER attempt_id,
    ADD COLUMN answer_id bigint unsigned NULL COMMENT 'source answer record' AFTER version_question_id,
    ADD COLUMN answer_version int NULL COMMENT 'frozen answer version submitted to judge' AFTER answer_id,
    ADD COLUMN submit_kind varchar(16) NOT NULL DEFAULT 'FORMAL' COMMENT 'RUN or FORMAL' AFTER answer_version,
    ADD CONSTRAINT chk_tb_user_submit_kind CHECK (submit_kind IN ('RUN', 'FORMAL')),
    ADD KEY idx_submit_attempt_question (attempt_id, version_question_id, create_time),
    ADD KEY idx_submit_answer_version (answer_id, answer_version);

CREATE TABLE tb_exam_version (
    version_id bigint unsigned NOT NULL COMMENT 'immutable exam version id',
    exam_id bigint unsigned NOT NULL COMMENT 'source exam id',
    version_no int NOT NULL COMMENT 'monotonic version within exam',
    title varchar(100) NOT NULL COMMENT 'title snapshot',
    description text NULL COMMENT 'instruction snapshot',
    start_time datetime(3) NOT NULL COMMENT 'global start time UTC',
    latest_start_time datetime(3) NOT NULL COMMENT 'latest attempt start UTC',
    end_time datetime(3) NOT NULL COMMENT 'hard global end UTC',
    duration_minutes int NOT NULL COMMENT 'individual attempt duration',
    timezone varchar(64) NOT NULL COMMENT 'display timezone',
    max_formal_submissions int NOT NULL COMMENT 'formal submissions per question',
    result_release_policy varchar(32) NOT NULL COMMENT 'MANUAL or SCHEDULED',
    result_release_time datetime(3) NULL COMMENT 'scheduled release UTC',
    feedback_policy_json json NULL COMMENT 'candidate judge feedback rules',
    integrity_policy_json json NULL COMMENT 'enabled integrity evidence rules',
    content_hash char(64) NOT NULL COMMENT 'SHA-256 of canonical version payload',
    published_by bigint unsigned NOT NULL COMMENT 'publishing administrator',
    published_time datetime(3) NOT NULL COMMENT 'publication time UTC',
    PRIMARY KEY (version_id),
    UNIQUE KEY uk_exam_version_no (exam_id, version_no),
    UNIQUE KEY uk_exam_version_hash (exam_id, content_hash),
    KEY idx_exam_version_schedule (start_time, end_time),
    CONSTRAINT chk_exam_version_schedule CHECK (start_time < latest_start_time AND latest_start_time <= end_time),
    CONSTRAINT chk_exam_version_duration CHECK (duration_minutes > 0),
    CONSTRAINT chk_exam_version_submit_limit CHECK (max_formal_submissions > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='immutable published exam versions';

CREATE TABLE tb_exam_version_question (
    version_question_id bigint unsigned NOT NULL COMMENT 'immutable question snapshot id',
    version_id bigint unsigned NOT NULL COMMENT 'exam version id',
    question_id bigint unsigned NOT NULL COMMENT 'source question id for traceability',
    question_order int NOT NULL COMMENT 'display order in version',
    score int NOT NULL COMMENT 'maximum score snapshot',
    required_flag tinyint NOT NULL COMMENT '0 optional 1 required',
    question_type varchar(32) NOT NULL COMMENT 'PROGRAMMING in Phase 1',
    title varchar(100) NOT NULL COMMENT 'title snapshot',
    content longtext NOT NULL COMMENT 'statement snapshot',
    time_limit int NOT NULL COMMENT 'judge time limit ms snapshot',
    space_limit int NOT NULL COMMENT 'judge memory limit KB snapshot',
    question_case longtext NULL COMMENT 'hidden judge case snapshot',
    default_code longtext NULL COMMENT 'legacy starter code snapshot',
    main_fuc longtext NULL COMMENT 'legacy entry template snapshot',
    allowed_languages_json json NOT NULL COMMENT 'allowed language codes',
    starter_code_json json NULL COMMENT 'starter code by language',
    judge_config_json json NULL COMMENT 'judge mode and comparison rules',
    source_update_time datetime(3) NULL COMMENT 'source question update time at publication',
    content_hash char(64) NOT NULL COMMENT 'SHA-256 of canonical question snapshot',
    PRIMARY KEY (version_question_id),
    UNIQUE KEY uk_version_question_source (version_id, question_id),
    UNIQUE KEY uk_version_question_order (version_id, question_order),
    KEY idx_version_question_version (version_id),
    CONSTRAINT chk_version_question_score CHECK (score > 0),
    CONSTRAINT chk_version_question_required CHECK (required_flag IN (0, 1)),
    CONSTRAINT chk_version_question_order CHECK (question_order > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='immutable exam question snapshots';

CREATE TABLE tb_exam_attempt (
    attempt_id bigint unsigned NOT NULL COMMENT 'candidate attempt id',
    exam_id bigint unsigned NOT NULL COMMENT 'exam id',
    version_id bigint unsigned NOT NULL COMMENT 'immutable exam version id',
    user_id bigint unsigned NOT NULL COMMENT 'candidate id',
    status tinyint NOT NULL DEFAULT 0 COMMENT '0 in-progress 1 submitted 2 timed-out 3 cancelled',
    row_version int NOT NULL DEFAULT 0 COMMENT 'optimistic lock version',
    started_time datetime(3) NOT NULL COMMENT 'server start time UTC',
    deadline_time datetime(3) NOT NULL COMMENT 'server deadline UTC',
    last_active_time datetime(3) NOT NULL COMMENT 'last heartbeat/activity UTC',
    submitted_time datetime(3) NULL COMMENT 'candidate submission time UTC',
    finalized_time datetime(3) NULL COMMENT 'terminal transition time UTC',
    finalization_reason varchar(32) NULL COMMENT 'CANDIDATE_SUBMIT DEADLINE ADMIN_CANCEL EXAM_CANCEL',
    finalization_key varchar(64) NULL COMMENT 'idempotency key for terminal transition',
    first_ip_hash char(64) NULL COMMENT 'salted SHA-256 IP evidence',
    latest_ip_hash char(64) NULL COMMENT 'latest salted SHA-256 IP evidence',
    user_agent_hash char(64) NULL COMMENT 'SHA-256 user-agent evidence',
    current_session_id varchar(64) NULL COMMENT 'active browser session identifier',
    risk_level tinyint NOT NULL DEFAULT 0 COMMENT '0 none 1 low 2 medium 3 high',
    create_time datetime(3) NOT NULL COMMENT 'created time UTC',
    update_time datetime(3) NULL COMMENT 'updated time UTC',
    PRIMARY KEY (attempt_id),
    UNIQUE KEY uk_attempt_version_user (version_id, user_id),
    UNIQUE KEY uk_attempt_finalization_key (finalization_key),
    KEY idx_attempt_exam_status (exam_id, status),
    KEY idx_attempt_status_deadline (status, deadline_time),
    KEY idx_attempt_user_status (user_id, status),
    CONSTRAINT chk_exam_attempt_status CHECK (status BETWEEN 0 AND 3),
    CONSTRAINT chk_exam_attempt_risk CHECK (risk_level BETWEEN 0 AND 3),
    CONSTRAINT chk_exam_attempt_time CHECK (started_time < deadline_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='trusted exam attempts';

CREATE TABLE tb_exam_answer (
    answer_id bigint unsigned NOT NULL COMMENT 'attempt answer id',
    attempt_id bigint unsigned NOT NULL COMMENT 'exam attempt id',
    version_question_id bigint unsigned NOT NULL COMMENT 'immutable question snapshot id',
    answer_type varchar(32) NOT NULL DEFAULT 'CODE' COMMENT 'future-compatible answer type',
    language_code varchar(32) NULL COMMENT 'judge language code',
    answer_content longtext NULL COMMENT 'code text or typed JSON payload',
    content_hash char(64) NOT NULL COMMENT 'SHA-256 answer content hash',
    answer_version int NOT NULL COMMENT 'monotonic optimistic version',
    saved_time datetime(3) NOT NULL COMMENT 'server save time UTC',
    frozen_time datetime(3) NULL COMMENT 'attempt finalization freeze time UTC',
    latest_submit_id bigint unsigned NULL COMMENT 'latest formal submission',
    latest_accepted_submit_id bigint unsigned NULL COMMENT 'latest accepted formal submission',
    create_time datetime(3) NOT NULL COMMENT 'created time UTC',
    update_time datetime(3) NULL COMMENT 'updated time UTC',
    PRIMARY KEY (answer_id),
    UNIQUE KEY uk_answer_attempt_question (attempt_id, version_question_id),
    KEY idx_answer_attempt_saved (attempt_id, saved_time),
    CONSTRAINT chk_exam_answer_version CHECK (answer_version > 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='versioned candidate answers';

CREATE TABLE tb_exam_grade (
    grade_id bigint unsigned NOT NULL COMMENT 'grade revision id',
    attempt_id bigint unsigned NOT NULL COMMENT 'exam attempt id',
    revision int NOT NULL COMMENT 'monotonic grade revision',
    status tinyint NOT NULL DEFAULT 0 COMMENT '0 waiting 1 ready 2 released 3 needs-review',
    total_score int NOT NULL DEFAULT 0 COMMENT 'awarded total score',
    max_score int NOT NULL COMMENT 'version maximum score',
    calculation_source varchar(32) NOT NULL DEFAULT 'AUTO' COMMENT 'AUTO MANUAL or MIXED',
    current_flag tinyint NOT NULL DEFAULT 1 COMMENT '1 current revision',
    calculated_time datetime(3) NULL COMMENT 'calculation time UTC',
    released_time datetime(3) NULL COMMENT 'release time UTC',
    create_by bigint unsigned NOT NULL COMMENT 'service or administrator id',
    create_time datetime(3) NOT NULL COMMENT 'created time UTC',
    update_by bigint unsigned NULL COMMENT 'updater id',
    update_time datetime(3) NULL COMMENT 'updated time UTC',
    PRIMARY KEY (grade_id),
    UNIQUE KEY uk_grade_attempt_revision (attempt_id, revision),
    KEY idx_grade_attempt_current (attempt_id, current_flag),
    CONSTRAINT chk_exam_grade_status CHECK (status BETWEEN 0 AND 3),
    CONSTRAINT chk_exam_grade_score CHECK (total_score >= 0 AND max_score > 0 AND total_score <= max_score),
    CONSTRAINT chk_exam_grade_current CHECK (current_flag IN (0, 1))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='exam grade revisions';

CREATE TABLE tb_exam_grade_item (
    grade_item_id bigint unsigned NOT NULL COMMENT 'grade item id',
    grade_id bigint unsigned NOT NULL COMMENT 'grade revision id',
    version_question_id bigint unsigned NOT NULL COMMENT 'immutable question snapshot id',
    submit_id bigint unsigned NULL COMMENT 'submission used for automatic score',
    awarded_score int NOT NULL DEFAULT 0 COMMENT 'awarded score',
    max_score int NOT NULL COMMENT 'question maximum score',
    grading_mode varchar(32) NOT NULL DEFAULT 'AUTO' COMMENT 'AUTO or MANUAL',
    adjustment_reason varchar(500) NULL COMMENT 'manual adjustment reason',
    create_by bigint unsigned NOT NULL COMMENT 'service or administrator id',
    create_time datetime(3) NOT NULL COMMENT 'created time UTC',
    update_by bigint unsigned NULL COMMENT 'updater id',
    update_time datetime(3) NULL COMMENT 'updated time UTC',
    PRIMARY KEY (grade_item_id),
    UNIQUE KEY uk_grade_item_question (grade_id, version_question_id),
    KEY idx_grade_item_submit (submit_id),
    CONSTRAINT chk_exam_grade_item_score CHECK (awarded_score >= 0 AND max_score > 0 AND awarded_score <= max_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='per-question grade details';

CREATE TABLE tb_integrity_event (
    integrity_event_id bigint unsigned NOT NULL COMMENT 'integrity evidence event id',
    attempt_id bigint unsigned NOT NULL COMMENT 'exam attempt id',
    session_id varchar(64) NOT NULL COMMENT 'browser session id',
    client_sequence bigint unsigned NOT NULL COMMENT 'monotonic sequence within session',
    event_type varchar(32) NOT NULL COMMENT 'FOCUS_LOST FULLSCREEN_EXIT PASTE SESSION_CHANGE etc',
    client_observed_time datetime(3) NULL COMMENT 'untrusted client observation time',
    server_received_time datetime(3) NOT NULL COMMENT 'authoritative receipt time UTC',
    metadata_json json NULL COMMENT 'minimal non-content metadata',
    risk_points int NOT NULL DEFAULT 0 COMMENT 'rule-generated points; not a cheating verdict',
    create_time datetime(3) NOT NULL COMMENT 'created time UTC',
    PRIMARY KEY (integrity_event_id),
    UNIQUE KEY uk_integrity_session_sequence (attempt_id, session_id, client_sequence),
    KEY idx_integrity_attempt_time (attempt_id, server_received_time),
    KEY idx_integrity_attempt_type (attempt_id, event_type),
    CONSTRAINT chk_integrity_risk_points CHECK (risk_points >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='append-only exam integrity evidence';

CREATE TABLE tb_exam_command (
    command_id bigint unsigned NOT NULL COMMENT 'idempotent command record id',
    command_type varchar(32) NOT NULL COMMENT 'PUBLISH START FINALIZE CANCEL RELEASE_RESULTS',
    actor_id bigint unsigned NOT NULL COMMENT 'authenticated actor id',
    idempotency_key varchar(64) NOT NULL COMMENT 'client command key',
    request_hash char(64) NOT NULL COMMENT 'SHA-256 canonical request hash',
    target_type varchar(32) NOT NULL COMMENT 'EXAM ATTEMPT or GRADE',
    target_id bigint unsigned NULL COMMENT 'resulting domain target id',
    status tinyint NOT NULL DEFAULT 0 COMMENT '0 processing 1 succeeded 2 failed',
    result_code int NULL COMMENT 'stable API result code',
    response_json json NULL COMMENT 'safe replay response payload',
    expires_time datetime(3) NOT NULL COMMENT 'retention expiry UTC',
    create_time datetime(3) NOT NULL COMMENT 'created time UTC',
    update_time datetime(3) NULL COMMENT 'updated time UTC',
    PRIMARY KEY (command_id),
    UNIQUE KEY uk_exam_command_key (command_type, actor_id, idempotency_key),
    KEY idx_exam_command_target (target_type, target_id),
    KEY idx_exam_command_expiry (expires_time),
    CONSTRAINT chk_exam_command_status CHECK (status BETWEEN 0 AND 2)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='trusted exam command idempotency ledger';

CREATE TABLE tb_exam_audit_event (
    audit_event_id bigint unsigned NOT NULL COMMENT 'audit event id',
    exam_id bigint unsigned NULL COMMENT 'exam id',
    attempt_id bigint unsigned NULL COMMENT 'attempt id',
    actor_id bigint unsigned NOT NULL COMMENT 'authenticated actor or service id',
    actor_type varchar(16) NOT NULL COMMENT 'ADMIN CANDIDATE or SYSTEM',
    action varchar(64) NOT NULL COMMENT 'domain action',
    request_id varchar(64) NOT NULL COMMENT 'correlation request id',
    result_code int NOT NULL COMMENT 'stable API result code',
    metadata_json json NULL COMMENT 'safe metadata without source code or secrets',
    server_time datetime(3) NOT NULL COMMENT 'authoritative event time UTC',
    PRIMARY KEY (audit_event_id),
    KEY idx_audit_exam_time (exam_id, server_time),
    KEY idx_audit_attempt_time (attempt_id, server_time),
    KEY idx_audit_request (request_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='append-only trusted exam audit trail';

CREATE TABLE tb_exam_outbox (
    outbox_id bigint unsigned NOT NULL COMMENT 'transactional outbox id',
    aggregate_type varchar(32) NOT NULL COMMENT 'EXAM ATTEMPT SUBMISSION or GRADE',
    aggregate_id bigint unsigned NOT NULL COMMENT 'aggregate id',
    event_type varchar(64) NOT NULL COMMENT 'event name',
    event_key varchar(128) NOT NULL COMMENT 'deduplication key',
    payload_json json NOT NULL COMMENT 'event payload',
    status tinyint NOT NULL DEFAULT 0 COMMENT '0 pending 1 published 2 failed',
    retry_count int NOT NULL DEFAULT 0 COMMENT 'publish retry count',
    available_time datetime(3) NOT NULL COMMENT 'next delivery time UTC',
    published_time datetime(3) NULL COMMENT 'successful delivery time UTC',
    last_error varchar(1000) NULL COMMENT 'sanitized latest delivery error',
    create_time datetime(3) NOT NULL COMMENT 'created time UTC',
    update_time datetime(3) NULL COMMENT 'updated time UTC',
    PRIMARY KEY (outbox_id),
    UNIQUE KEY uk_exam_outbox_event_key (event_key),
    KEY idx_exam_outbox_dispatch (status, available_time),
    CONSTRAINT chk_exam_outbox_status CHECK (status BETWEEN 0 AND 2),
    CONSTRAINT chk_exam_outbox_retry CHECK (retry_count >= 0)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='transactional exam event outbox';
