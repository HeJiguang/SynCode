# Database Migration Policy

This directory is the source of truth for database changes made after the Phase 1 trusted-exam baseline.

## Tool and ownership

- Use Flyway Community with MySQL 8.
- Run migrations as a dedicated deployment step before new application services are rolled out.
- Application services must not all run Flyway at startup. This avoids startup races across the current microservice deployment.
- CI validates migrations against a disposable MySQL 8 database.
- The test environment migrates automatically after CI succeeds.
- Production migration remains part of the manually approved production release.
- `deploy/dev/sql/init-complete.sql` remains a development bootstrap snapshot. Editing it never substitutes for a versioned migration.

The migration runner, credentials, and CI workflow will be added with the first Phase 1 schema migration. Migration credentials must only have the permissions needed for schema evolution and must be stored in environment secrets.

## Directory layout

```text
deploy/migrations/
  README.md
  mysql/
    versioned/      Flyway forward migrations
    verification/   read-only post-migration checks
    rollback/       reviewed manual recovery scripts or instructions
```

## Naming

Forward migration:

```text
VYYYYMMDDNN__lower_snake_case_description.sql
```

- `YYYYMMDD` is the authoring date in `Asia/Shanghai`.
- `NN` starts at `01` and is never reused.
- Example: `V2026091301__trusted_exam_core_schema.sql`.
- A merged migration is immutable. Fix it with a new migration instead of editing its checksum.

Verification and rollback artifacts use the same version:

```text
verify_V2026091301__trusted_exam_core_schema.sql
rollback_V2026091301__trusted_exam_core_schema.sql
```

Rollback artifacts are not Flyway undo migrations. They are explicit, manually invoked recovery tools and must default to preserving business data.

## Existing database adoption

SynCode currently has unversioned schemas created from files under `deploy/dev/sql`. Before the first deployment:

1. Back up the target database and record the backup identifier.
2. Run the baseline preflight verification for required schema.
3. Confirm baseline only after the preflight matches the expected legacy schema.
4. Use baseline version `2026091300` and description `trusted_exam_baseline`.
5. Run the first versioned migration `V2026091301`.
6. Run its verification SQL and archive the output with the deployment record.

A new empty CI database may be initialized from the reviewed legacy bootstrap and then baselined at the same version before testing Phase 1 migrations. Production must never use `baselineOnMigrate=true` without the explicit preflight because it can hide a wrongly selected or partially initialized database.

## Change strategy

Every production change follows expand, migrate, contract:

1. **Expand**: add nullable columns, tables, indexes, and compatible code paths.
2. **Migrate**: backfill in bounded batches and verify counts, hashes, and orphan rows.
3. **Contract**: add stricter constraints or remove legacy reads only after the new release is stable.

Contract migrations are separate releases. Phase 1 does not drop captured attempts, answers, submissions, grades, or integrity evidence.

## Authoring rules

- Use `utf8mb4`, InnoDB, explicit types, and comments for new tables.
- New timestamps use `DATETIME(3)` in UTC. Do not depend on the MySQL host timezone.
- All identifier columns follow the existing `bigint unsigned` convention.
- Name every index and constraint. Unique constraints are the final guard for idempotency.
- Avoid foreign keys in the first expand migration until current data is checked and operational impact is measured.
- Avoid long blocking table changes. Large backfills and index builds require an execution estimate and maintenance plan.
- Do not put secrets, environment-specific schema names, or `USE database_name` in versioned migrations.
- Do not mix seed/demo data with production schema migrations.
- Destructive statements require a separate contract migration and explicit production approval.

## Required artifact header

Each forward migration starts with comments containing:

```sql
-- Purpose: concise business purpose
-- Compatibility: application versions that can run before and after this migration
-- Lock risk: expected tables, duration, and mitigation
-- Rollback: matching rollback artifact and data-preservation notes
```

Each verification script is read-only and checks at minimum:

- expected tables and columns exist;
- required unique constraints and indexes exist;
- backfill counts match their source population;
- no orphan references or illegal state values exist;
- immutable snapshot hashes and version numbers are populated where required.

## Deployment gate

A migration is releasable only when all of these are true:

- Forward migration succeeds on an empty CI fixture and a legacy-schema fixture.
- Re-running `flyway migrate` reports no pending work and changes no business rows.
- Verification SQL passes.
- The old application version still starts after the expand migration.
- The new application version starts and its smoke tests pass.
- Backup, rollback point, migration version, output, and elapsed time are recorded.

Test deployment order:

```text
backup/snapshot -> preflight -> flyway migrate -> verify -> deploy services -> smoke test
```

Production uses the same scripts and order, with manual approval. On application failure, roll back the application images first and leave additive schema in place. A database rollback is used only when the schema itself prevents the previous application from operating or creates an immediate correctness/security risk.

## Rollback requirements

Every rollback artifact states:

- whether it is safe before and after new application writes;
- which data would become unreadable or be lost;
- the required application version and maintenance mode;
- the backup identifier and restore alternative;
- verification queries after recovery.

Default rollback for additive Phase 1 migrations is a logical rollback: disable new feature writes, restore the prior application images, and keep new tables/columns. `DROP TABLE`, `DROP COLUMN`, and bulk `DELETE` are not automatic release actions.
