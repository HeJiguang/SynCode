from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from app.application.run_service import RunService  # noqa: E402
from app.domain.artifacts import Artifact, ArtifactType, RenderHint  # noqa: E402
from app.domain.runs import ContextRef, EventType, RunSource, RunStatus, RunType  # noqa: E402
from app.domain.write_intents import (  # noqa: E402
    TargetService,
    UserImpactLevel,
    WriteIntent,
    WriteIntentType,
)


def test_create_run_persists_run_and_accept_event():
    service = RunService()

    run = service.create_run(
        run_type=RunType.INTERACTIVE_TUTOR,
        source=RunSource.WORKSPACE_PANEL,
        user_id="u-1",
        conversation_id="conv-1",
        context_ref=ContextRef(question_id="1001"),
    )

    stored = service.run_store.get(run.run_id)
    events = service.list_events(run.run_id)

    assert stored.run_id == run.run_id
    assert stored.status is RunStatus.ACCEPTED
    assert stored.context_ref.question_id == "1001"
    assert events[0].event_type is EventType.RUN_ACCEPTED


def test_add_artifact_persists_structured_result_and_event():
    service = RunService()
    run = service.create_run(
        run_type=RunType.INTERACTIVE_DIAGNOSIS,
        source=RunSource.WORKSPACE_PANEL,
        user_id="u-1",
    )

    artifact = service.add_artifact(
        Artifact(
            run_id=run.run_id,
            artifact_type=ArtifactType.DIAGNOSIS_REPORT,
            title="Diagnosis report",
            summary="Likely edge-case bug.",
            body={"answer": "Check the zero-length array path."},
            render_hint=RenderHint.DIAGNOSIS,
        )
    )

    artifacts = service.list_artifacts(run.run_id)
    events = service.list_events(run.run_id)

    assert artifacts[0].artifact_id == artifact.artifact_id
    assert artifacts[0].artifact_type is ArtifactType.DIAGNOSIS_REPORT
    assert events[-1].event_type is EventType.ARTIFACT_CREATED


def test_balanced_policy_auto_approves_message_delivery():
    service = RunService()
    run = service.create_run(
        run_type=RunType.MESSAGE_DELIVERY,
        source=RunSource.SCHEDULER,
        user_id="u-2",
    )

    write_intent, decision = service.register_write_intent(
        WriteIntent(
            run_id=run.run_id,
            user_id="u-2",
            intent_type=WriteIntentType.MESSAGE_DELIVERY,
            target_service=TargetService.OJ_FRIEND,
            target_aggregate="message",
            payload={"title": "Keep going", "body": "You improved on array problems today."},
        )
    )

    assert write_intent.execution_status.value == "AUTO_APPROVED"
    assert decision.decision.value == "AUTO_APPLY"
    assert service.list_drafts("u-2") == []


def test_balanced_policy_creates_draft_and_inbox_for_high_impact_plan_replace():
    service = RunService()
    run = service.create_run(
        run_type=RunType.PLAN_RECOMPUTE,
        source=RunSource.SCHEDULER,
        user_id="u-3",
    )

    write_intent, decision = service.register_write_intent(
        WriteIntent(
            run_id=run.run_id,
            user_id="u-3",
            intent_type=WriteIntentType.TRAINING_PLAN_REPLACE,
            target_service=TargetService.OJ_FRIEND,
            target_aggregate="training_plan",
            payload={"planTitle": "Replacement plan", "tasks": [101, 102, 103]},
            user_impact_level=UserImpactLevel.HIGH,
        )
    )

    drafts = service.list_drafts("u-3")
    inbox_items = service.list_inbox("u-3")
    events = service.list_events(run.run_id)

    assert write_intent.execution_status.value == "DRAFT_REQUIRED"
    assert decision.decision.value == "CREATE_DRAFT"
    assert drafts[0].write_intent_id == write_intent.write_intent_id
    assert inbox_items[0].linked_draft_id == drafts[0].draft_id
    assert events[-1].event_type is EventType.DRAFT_CREATED

