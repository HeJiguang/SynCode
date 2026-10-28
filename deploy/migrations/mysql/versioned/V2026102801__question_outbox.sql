-- Purpose: capture every question mutation and independently deliver search/cache projections.
-- Compatibility: additive schema; deploy new writers/readers before enabling question.sync.enabled.
-- Lock risk: brief metadata locks for triggers; pause question writes during migration/backfill.
-- Rollback: rollback_V2026102801__question_outbox.sql; retain events and state.
CREATE TABLE tb_question_sync_state (
  question_id BIGINT UNSIGNED NOT NULL,
  revision BIGINT NOT NULL DEFAULT 1,
  deleted TINYINT NOT NULL DEFAULT 0,
  es_revision BIGINT NOT NULL DEFAULT 0,
  redis_revision BIGINT NOT NULL DEFAULT 0,
  updated_at DATETIME(3) NOT NULL,
  PRIMARY KEY (question_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Durable question projection revisions, including deletion tombstones';

CREATE TABLE tb_question_outbox (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  question_id BIGINT UNSIGNED NOT NULL,
  revision BIGINT NOT NULL,
  target VARCHAR(8) NOT NULL,
  status VARCHAR(12) NOT NULL DEFAULT 'PENDING',
  attempts INT NOT NULL DEFAULT 0,
  available_at DATETIME(3) NOT NULL,
  lease_token VARCHAR(36) NULL,
  last_error VARCHAR(1000) NULL,
  created_at DATETIME(3) NOT NULL,
  updated_at DATETIME(3) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_question_revision_target (question_id, revision, target),
  KEY idx_question_outbox_poll (status, available_at),
  KEY idx_question_outbox_lease (lease_token)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='Transactional question outbox; DONE means projection applied';

DELIMITER $$
CREATE TRIGGER trg_question_sync_insert AFTER INSERT ON tb_question FOR EACH ROW
BEGIN
  INSERT INTO tb_question_sync_state(question_id,revision,deleted,updated_at)
  VALUES(NEW.question_id,1,0,UTC_TIMESTAMP(3))
  ON DUPLICATE KEY UPDATE revision=revision+1,deleted=0,updated_at=UTC_TIMESTAMP(3);
  INSERT INTO tb_question_outbox(question_id,revision,target,available_at,created_at,updated_at)
  SELECT question_id,revision,'ES',UTC_TIMESTAMP(3),UTC_TIMESTAMP(3),UTC_TIMESTAMP(3)
  FROM tb_question_sync_state WHERE question_id=NEW.question_id;
  INSERT INTO tb_question_outbox(question_id,revision,target,available_at,created_at,updated_at)
  SELECT question_id,revision,'REDIS',UTC_TIMESTAMP(3),UTC_TIMESTAMP(3),UTC_TIMESTAMP(3)
  FROM tb_question_sync_state WHERE question_id=NEW.question_id;
END$$
CREATE TRIGGER trg_question_sync_update AFTER UPDATE ON tb_question FOR EACH ROW
BEGIN
  IF OLD.question_id <> NEW.question_id THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='question_id is immutable';
  END IF;
  INSERT INTO tb_question_sync_state(question_id,revision,deleted,updated_at)
  VALUES(NEW.question_id,1,0,UTC_TIMESTAMP(3))
  ON DUPLICATE KEY UPDATE revision=revision+1,deleted=0,updated_at=UTC_TIMESTAMP(3);
  INSERT INTO tb_question_outbox(question_id,revision,target,available_at,created_at,updated_at)
  SELECT question_id,revision,'ES',UTC_TIMESTAMP(3),UTC_TIMESTAMP(3),UTC_TIMESTAMP(3)
  FROM tb_question_sync_state WHERE question_id=NEW.question_id;
  INSERT INTO tb_question_outbox(question_id,revision,target,available_at,created_at,updated_at)
  SELECT question_id,revision,'REDIS',UTC_TIMESTAMP(3),UTC_TIMESTAMP(3),UTC_TIMESTAMP(3)
  FROM tb_question_sync_state WHERE question_id=NEW.question_id;
END$$
CREATE TRIGGER trg_question_sync_delete AFTER DELETE ON tb_question FOR EACH ROW
BEGIN
  INSERT INTO tb_question_sync_state(question_id,revision,deleted,updated_at)
  VALUES(OLD.question_id,1,1,UTC_TIMESTAMP(3))
  ON DUPLICATE KEY UPDATE revision=revision+1,deleted=1,updated_at=UTC_TIMESTAMP(3);
  INSERT INTO tb_question_outbox(question_id,revision,target,available_at,created_at,updated_at)
  SELECT question_id,revision,'ES',UTC_TIMESTAMP(3),UTC_TIMESTAMP(3),UTC_TIMESTAMP(3)
  FROM tb_question_sync_state WHERE question_id=OLD.question_id;
  INSERT INTO tb_question_outbox(question_id,revision,target,available_at,created_at,updated_at)
  SELECT question_id,revision,'REDIS',UTC_TIMESTAMP(3),UTC_TIMESTAMP(3),UTC_TIMESTAMP(3)
  FROM tb_question_sync_state WHERE question_id=OLD.question_id;
END$$
DELIMITER ;

-- Baseline existing rows. Run with question writes paused; see deployment runbook.
INSERT IGNORE INTO tb_question_sync_state(question_id,revision,deleted,updated_at)
SELECT question_id,1,0,UTC_TIMESTAMP(3) FROM tb_question;
INSERT IGNORE INTO tb_question_outbox(question_id,revision,target,available_at,created_at,updated_at)
SELECT question_id,revision,'ES',UTC_TIMESTAMP(3),UTC_TIMESTAMP(3),UTC_TIMESTAMP(3) FROM tb_question_sync_state;
INSERT IGNORE INTO tb_question_outbox(question_id,revision,target,available_at,created_at,updated_at)
SELECT question_id,revision,'REDIS',UTC_TIMESTAMP(3),UTC_TIMESTAMP(3),UTC_TIMESTAMP(3) FROM tb_question_sync_state;
