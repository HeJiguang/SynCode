-- Logical rollback only; no DROP/DELETE is performed.
-- Before or after new writes: pause admin/import/SQL question mutations first.
-- Disable question.sync.enabled and stop new consumers/publishers, retain all tables/triggers/events.
-- Do not run old unversioned ES writers concurrently with this projection version scheme.
-- Keep the new MySQL detail/judge readers where possible. If restoring old application images,
-- keep question writes paused and rebuild/reconcile ES before permitting reads of old ES details.
-- Record the release backup ID in the deployment record. Restore a backup to a separate database
-- if schema recovery is needed; never reset revision counters against an existing index.
-- Resuming the new release replays durable events. No event/business data is lost by this logical rollback.
SELECT target,status,COUNT(*) FROM tb_question_outbox GROUP BY target,status;
SELECT COUNT(*) AS state_rows,MAX(revision) AS highest_revision FROM tb_question_sync_state;
