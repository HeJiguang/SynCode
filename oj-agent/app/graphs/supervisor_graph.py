from typing import NotRequired, TypedDict
from uuid import uuid4

from langgraph.graph import END, START, StateGraph

from app.graphs.capabilities.diagnose_graph import build_diagnose_graph
from app.graphs.capabilities.plan_graph import build_plan_graph
from app.graphs.capabilities.profile_graph import build_profile_graph
from app.graphs.capabilities.recommend_graph import build_recommend_graph
from app.graphs.capabilities.review_graph import build_review_graph
from app.graphs.capabilities.tutor_graph import build_tutor_graph
from app.runtime.enums import RiskLevel, RunStatus, TaskType
from app.runtime.models import EvidenceState, ExecutionState, GuardrailState, OutcomeState, RequestContext, UnifiedAgentState, WriteIntent
from app.schemas.training_plan_request import TrainingPlanRequest


class SupervisorState(TypedDict):
    request: RequestContext
    execution: NotRequired[ExecutionState]
    training_request: NotRequired[TrainingPlanRequest]
    unified_state: NotRequired[UnifiedAgentState]


def _infer_chat_task_type(request: RequestContext) -> TaskType:
    message = (request.user_message or "").casefold()

    profile_keywords = [
        "profile",
        "learning profile",
        "weakness",
        "strength",
        "ability",
        "focus tag",
    ]
    review_keywords = [
        "review",
        "summarize my recent practice",
        "recent practice",
        "recent training",
        "mistake",
        "summary",
        "reflect",
    ]

    if any(keyword in message for keyword in profile_keywords):
        return TaskType.PROFILE
    if any(keyword in message for keyword in review_keywords):
        return TaskType.REVIEW
    return TaskType.CHAT


def _execution_for(request: RequestContext) -> ExecutionState:
    return ExecutionState(
        run_id=str(uuid4()),
        graph_name="supervisor_graph",
        status=RunStatus.RUNNING,
        active_node="route_task",
        branch_name=request.task_type.value,
    )


def route_task_node(state: SupervisorState) -> SupervisorState:
    request = state["request"]
    if request.task_type is TaskType.CHAT:
        request = request.model_copy(update={"task_type": _infer_chat_task_type(request)})
    return {
        **state,
        "request": request,
        "execution": _execution_for(request),
    }


def route_after_task(state: SupervisorState) -> str:
    if state["request"].task_type is TaskType.CHAT:
        return "chat"
    if state["request"].task_type is TaskType.DIAGNOSIS:
        return "diagnosis"
    if state["request"].task_type is TaskType.RECOMMENDATION:
        return "recommendation"
    if state["request"].task_type is TaskType.REVIEW:
        return "review"
    if state["request"].task_type is TaskType.PROFILE:
        return "profile"
    if state["request"].task_type is TaskType.TRAINING_PLAN:
        return "training_plan"
    return "unsupported"


def chat_capability_node(state: SupervisorState) -> SupervisorState:
    result = build_tutor_graph().invoke(
        {
            "request": state["request"],
            "execution": state["execution"],
        }
    )
    return {
        **state,
        "unified_state": result["unified_state"],
    }


def diagnosis_capability_node(state: SupervisorState) -> SupervisorState:
    result = build_diagnose_graph().invoke(
        {
            "request": state["request"],
            "execution": state["execution"],
        }
    )
    return {
        **state,
        "unified_state": result["unified_state"],
    }


def recommendation_capability_node(state: SupervisorState) -> SupervisorState:
    result = build_recommend_graph().invoke(
        {
            "request": state["request"],
            "execution": state["execution"],
        }
    )
    return {
        **state,
        "unified_state": result["unified_state"],
    }


def review_capability_node(state: SupervisorState) -> SupervisorState:
    result = build_review_graph().invoke(
        {
            "request": state["request"],
            "execution": state["execution"],
        }
    )
    return {
        **state,
        "unified_state": result["unified_state"],
    }


def profile_capability_node(state: SupervisorState) -> SupervisorState:
    result = build_profile_graph().invoke(
        {
            "request": state["request"],
            "execution": state["execution"],
        }
    )
    return {
        **state,
        "unified_state": result["unified_state"],
    }


def training_plan_capability_node(state: SupervisorState) -> SupervisorState:
    request = state["request"]
    training_request = state["training_request"]
    result = build_plan_graph().invoke({"request": training_request})
    response = result["response"]
    verification_errors = list(result.get("verification_errors") or [])
    execution = state["execution"].model_copy(
        update={
            "status": RunStatus.SUCCEEDED,
            "active_node": "plan_graph",
        }
    )
    return {
        **state,
        "unified_state": UnifiedAgentState(
            request=request,
            execution=execution,
            evidence=EvidenceState(
                route_names=["plan_graph"],
                coverage_score=1.0,
            ),
            guardrail=GuardrailState(
                risk_level=RiskLevel.MEDIUM if verification_errors else RiskLevel.LOW,
                completeness_ok=True,
                policy_ok=True,
                risk_reasons=verification_errors,
            ),
            outcome=OutcomeState(
                intent="training_plan",
                response_payload=response.model_dump(mode="json"),
                status_events=[
                    {"node": "plan_graph", "message": "Generated plan through graph runtime."}
                ],
                write_intents=[
                    WriteIntent(
                        intent_type="training_plan_write",
                        target_service="oj-friend",
                        payload=response.model_dump(mode="json"),
                    )
                ],
            ),
        ),
    }


def unsupported_task_node(state: SupervisorState) -> SupervisorState:
    request = state["request"]
    execution = state["execution"].model_copy(
        update={
            "status": RunStatus.FAILED,
            "active_node": "unsupported_task",
            "fallback_type": "unsupported_task_type",
        }
    )
    return {
        **state,
        "unified_state": UnifiedAgentState(
            request=request,
            execution=execution,
            evidence=EvidenceState(),
            guardrail=GuardrailState(
                risk_level=RiskLevel.MEDIUM,
                completeness_ok=False,
                policy_ok=True,
                risk_reasons=["unsupported task type"],
            ),
            outcome=OutcomeState(
                intent="unsupported_task",
                answer="The requested task type is not available in the current runtime increment.",
                next_action="Retry with a supported chat task.",
                confidence=0.0,
            ),
        ),
    }


# 顶层主管路由图，负责将请求路由到对应的能力图
def build_supervisor_graph():
    graph = StateGraph(SupervisorState)
    graph.add_node("route_task", route_task_node)
    graph.add_node("chat_capability", chat_capability_node)
    graph.add_node("diagnosis_capability", diagnosis_capability_node)
    graph.add_node("recommendation_capability", recommendation_capability_node)
    graph.add_node("review_capability", review_capability_node)
    graph.add_node("profile_capability", profile_capability_node)
    graph.add_node("training_plan_capability", training_plan_capability_node)
    graph.add_node("unsupported_task", unsupported_task_node)

    graph.add_edge(START, "route_task")
    graph.add_conditional_edges(
        "route_task",
        route_after_task,
        {
            "chat": "chat_capability",
            "diagnosis": "diagnosis_capability",
            "recommendation": "recommendation_capability",
            "review": "review_capability",
            "profile": "profile_capability",
            "training_plan": "training_plan_capability",
            "unsupported": "unsupported_task",
        },
    )
    graph.add_edge("chat_capability", END)
    graph.add_edge("diagnosis_capability", END)
    graph.add_edge("recommendation_capability", END)
    graph.add_edge("review_capability", END)
    graph.add_edge("profile_capability", END)
    graph.add_edge("training_plan_capability", END)
    graph.add_edge("unsupported_task", END)
    return graph.compile()
