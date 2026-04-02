from app.application.artifact_store import ArtifactStore
from app.application.draft_store import DraftStore
from app.application.inbox_store import InboxStore
from app.application.run_store import RunStore
from app.domain.artifacts import Artifact
from app.domain.drafts import Draft, DraftStatus, DraftType
from app.domain.inbox import InboxItem, InboxItemType
from app.domain.policies import PolicyDecision, PolicyDecisionType, evaluate_balanced_policy
from app.domain.runs import ContextRef, EventType, Run, RunSource, RunStatus, RunType
from app.domain.write_intents import WriteExecutionStatus, WriteIntent, WriteIntentType


class RunService:
    """Application service coordinating run records, artifacts, drafts, and inbox items."""

    def __init__(
        self,
        run_store: RunStore | None = None,
        artifact_store: ArtifactStore | None = None,
        draft_store: DraftStore | None = None,
        inbox_store: InboxStore | None = None,
    ) -> None:
        self.run_store = run_store or RunStore()
        self.artifact_store = artifact_store or ArtifactStore()
        self.draft_store = draft_store or DraftStore()
        self.inbox_store = inbox_store or InboxStore()
        self._write_intents: dict[str, list[WriteIntent]] = {}
        self._policy_decisions: dict[str, list[PolicyDecision]] = {}

    def create_run(
        self,
        *,
        run_type: RunType,
        source: RunSource,
        user_id: str,
        conversation_id: str | None = None,
        entry_graph: str = "supervisor_graph",
        context_ref: ContextRef | None = None,
    ) -> Run:
        run = self.run_store.save(
            Run(
                run_type=run_type,
                source=source,
                user_id=user_id,
                conversation_id=conversation_id,
                entry_graph=entry_graph,
                context_ref=context_ref or ContextRef(),
            )
        )
        self.run_store.append_event(
            run.run_id,
            EventType.RUN_ACCEPTED,
            {"runType": run.run_type.value, "source": run.source.value},
        )
        return run

    def add_artifact(self, artifact: Artifact) -> Artifact:
        stored = self.artifact_store.append(artifact)
        self.run_store.append_event(
            artifact.run_id,
            EventType.ARTIFACT_CREATED,
            {"artifactType": artifact.artifact_type.value, "artifactId": artifact.artifact_id},
        )
        return stored

    def register_write_intent(self, write_intent: WriteIntent) -> tuple[WriteIntent, PolicyDecision]:
        decision = evaluate_balanced_policy(write_intent)
        status = (
            WriteExecutionStatus.AUTO_APPROVED
            if decision.decision is PolicyDecisionType.AUTO_APPLY
            else WriteExecutionStatus.DRAFT_REQUIRED
            if decision.decision is PolicyDecisionType.CREATE_DRAFT
            else WriteExecutionStatus.REJECTED
        )
        stored_intent = write_intent.model_copy(update={"execution_status": status})
        self._write_intents.setdefault(write_intent.run_id, []).append(stored_intent)
        self._policy_decisions.setdefault(write_intent.run_id, []).append(decision)
        self.run_store.append_event(
            write_intent.run_id,
            EventType.WRITE_INTENT_CREATED,
            {"writeIntentId": stored_intent.write_intent_id, "intentType": stored_intent.intent_type.value},
        )

        if decision.decision is PolicyDecisionType.CREATE_DRAFT:
            draft = self._create_draft_for_intent(stored_intent)
            self.draft_store.save(draft)
            self.run_store.append_event(
                write_intent.run_id,
                EventType.DRAFT_CREATED,
                {"draftId": draft.draft_id, "draftType": draft.draft_type.value},
            )
            self.inbox_store.append(
                InboxItem(
                    user_id=stored_intent.user_id,
                    run_id=stored_intent.run_id,
                    item_type=InboxItemType.DRAFT_REVIEW,
                    title=draft.title,
                    summary=draft.summary,
                    linked_draft_id=draft.draft_id,
                )
            )
        return stored_intent, decision

    def list_artifacts(self, run_id: str) -> list[Artifact]:
        return self.artifact_store.list_for_run(run_id)

    def get_run(self, run_id: str) -> Run:
        return self.run_store.get(run_id)

    def list_events(self, run_id: str):
        return self.run_store.list_events(run_id)

    def append_event(self, run_id: str, event_type: EventType, payload: dict | None = None):
        return self.run_store.append_event(run_id, event_type, payload)

    def mark_running(self, run_id: str, *, active_node: str | None = None) -> Run:
        run = self.run_store.update_status(run_id, RunStatus.RUNNING, active_node=active_node)
        self.run_store.append_event(
            run_id,
            EventType.RUN_STARTED,
            {"activeNode": active_node or run.entry_graph},
        )
        return run

    def mark_succeeded(self, run_id: str, *, active_node: str | None = None) -> Run:
        run = self.run_store.update_status(run_id, RunStatus.SUCCEEDED, active_node=active_node)
        self.run_store.append_event(
            run_id,
            EventType.RUN_COMPLETED,
            {"status": run.status.value, "activeNode": active_node or run.active_node},
        )
        return run

    def mark_failed(self, run_id: str, *, reason: str, active_node: str | None = None) -> Run:
        run = self.run_store.update_status(run_id, RunStatus.FAILED, active_node=active_node)
        self.run_store.append_event(
            run_id,
            EventType.RUN_FAILED,
            {"status": run.status.value, "reason": reason, "activeNode": active_node or run.active_node},
        )
        return run

    def list_inbox(self, user_id: str) -> list[InboxItem]:
        return self.inbox_store.list_for_user(user_id)

    def list_drafts(self, user_id: str) -> list[Draft]:
        return self.draft_store.list_for_user(user_id)

    def list_write_intents(self, run_id: str) -> list[WriteIntent]:
        return [item.model_copy() for item in self._write_intents.get(run_id, [])]

    def list_policy_decisions(self, run_id: str) -> list[PolicyDecision]:
        return [item.model_copy() for item in self._policy_decisions.get(run_id, [])]

    def approve_draft(self, draft_id: str) -> Draft:
        draft = self.draft_store.update_status(draft_id, DraftStatus.APPROVED)
        self.inbox_store.resolve_by_draft(draft_id)
        self.run_store.append_event(
            draft.run_id,
            EventType.WRITE_APPLIED,
            {"draftId": draft_id, "status": "approved"},
        )
        return draft

    def reject_draft(self, draft_id: str) -> Draft:
        draft = self.draft_store.update_status(draft_id, DraftStatus.REJECTED)
        self.inbox_store.resolve_by_draft(draft_id)
        self.run_store.append_event(
            draft.run_id,
            EventType.WRITE_BLOCKED,
            {"draftId": draft_id, "status": "rejected"},
        )
        return draft

    def clear(self) -> None:
        self.run_store.clear()
        self.artifact_store.clear()
        self.draft_store.clear()
        self.inbox_store.clear()
        self._write_intents.clear()
        self._policy_decisions.clear()

    def _create_draft_for_intent(self, write_intent: WriteIntent) -> Draft:
        draft_type = (
            DraftType.TRAINING_PLAN_REPLACEMENT
            if write_intent.intent_type is WriteIntentType.TRAINING_PLAN_REPLACE
            else DraftType.HIGH_PRIORITY_LEARNING_CONCLUSION
        )
        return Draft(
            run_id=write_intent.run_id,
            write_intent_id=write_intent.write_intent_id,
            user_id=write_intent.user_id,
            draft_type=draft_type,
            title="Review proposed learning change",
            summary="This run proposed a high-impact learning update that needs your approval.",
            current_state={"status": "current_state_not_loaded_yet"},
            proposed_state=write_intent.payload,
            diff={"changedKeys": sorted(write_intent.payload.keys())},
        )


run_service = RunService()
