SELECT CONCAT('missing table: ', required.table_name) AS violation
FROM (
    SELECT 'tb_ai_skill' AS table_name
    UNION ALL SELECT 'tb_ai_skill_version'
    UNION ALL SELECT 'tb_ai_skill_promotion_candidate'
    UNION ALL SELECT 'tb_ai_skill_promotion_member'
    UNION ALL SELECT 'tb_ai_skill_promotion_review_action'
    UNION ALL SELECT 'tb_ai_skill_release'
    UNION ALL SELECT 'tb_ai_skill_lifecycle_review'
    UNION ALL SELECT 'tb_ai_skill_governance_heartbeat'
    UNION ALL SELECT 'tb_ai_skill_usage_event'
    UNION ALL SELECT 'tb_ai_learning_memory'
    UNION ALL SELECT 'tb_ai_learning_memory_evidence'
    UNION ALL SELECT 'tb_ai_learning_memory_projection_state'
    UNION ALL SELECT 'tb_ai_learning_state_memory'
    UNION ALL SELECT 'tb_ai_learning_state_evidence'
    UNION ALL SELECT 'tb_ai_learning_state_projection'
) AS required
LEFT JOIN information_schema.tables actual
    ON actual.table_schema = DATABASE()
   AND actual.table_name = required.table_name
WHERE actual.table_name IS NULL;

SELECT 'missing tb_ai_skill_version.package_json' AS violation
WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = DATABASE()
      AND table_name = 'tb_ai_skill_version'
      AND column_name = 'package_json'
);

SELECT 'missing tb_ai_learning_state_memory priority index' AS violation
WHERE NOT EXISTS (
    SELECT 1 FROM information_schema.statistics
    WHERE table_schema = DATABASE()
      AND table_name = 'tb_ai_learning_state_memory'
      AND index_name = 'idx_ai_learning_state_priority'
);

SELECT 'missing platform Skill seeds' AS violation
WHERE (
    SELECT COUNT(*)
    FROM tb_ai_skill
    WHERE scope = 'platform'
      AND skill_name IN (
          'syncode-tutor',
          'syncode-diagnosis',
          'syncode-training-plan',
          'syncode-learning-memory'
      )
) <> 4;

SELECT 'Hermes Skill governance and learning-memory migration verified' AS result;
