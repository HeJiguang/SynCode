from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.dependencies import get_app_settings, get_db_session
from app.models.candidate import CandidateStatus, UploadStatus
from app.services.ai_client import AIClient
from app.services.candidate_service import CandidateService
from app.services.dedup_service import DedupService, ExistingQuestion
from app.services.discovery_service import DiscoveryService
from app.services.execution_service import ExecutionService
from app.services.generation_service import GenerationService
from app.services.importer_service import ImporterService
from app.services.oj_reader import OJReader
from app.services.remote_db_config_service import RemoteDatabaseConfigService
from app.services.review_pack_service import ReviewPackService

templates = Jinja2Templates(directory="tool/question-curation/app/templates")
router = APIRouter()


STATUS_LABELS = {
    CandidateStatus.DISCOVERED: "已发现",
    CandidateStatus.MATERIAL_COLLECTED: "已采集材料",
    CandidateStatus.NORMALIZED: "已规范化",
    CandidateStatus.DEDUP_CHECKED: "已查重",
    CandidateStatus.ARTIFACTS_GENERATED: "已生成草稿",
    CandidateStatus.REVIEW_READY: "待审核",
    CandidateStatus.APPROVED: "已审核通过",
    CandidateStatus.REJECTED: "已驳回",
    CandidateStatus.IMPORTED: "已导入",
}

UPLOAD_STATUS_LABELS = {
    UploadStatus.NOT_READY: "未准备上传",
    UploadStatus.READY: "待上传",
    UploadStatus.UPLOADED: "已上传",
    UploadStatus.FAILED: "上传失败",
}

DEDUP_DECISION_LABELS = {
    "probable_duplicate": "高度疑似重复题",
    "similar_problem": "疑似同类题",
    "likely_distinct": "大概率不同题",
    "no-scan": "未查重",
}

READINESS_LABELS = {
    "missing-samples": "缺少样例数据",
    "missing-solution": "缺少标准解草稿",
    "missing-java-draft": "缺少 Java 草稿",
    "missing-run-check": "未完成运行校验",
    "review-ready": "可进入审核",
}


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    session: Session = Depends(get_db_session),
) -> HTMLResponse:
    service = CandidateService(session)
    candidates = service.list_candidates()
    context = {
        "request": request,
        "page_title": "题库补充工作台",
        "stats": {
            "discovered": len(candidates),
            "review_ready": sum(1 for item in candidates if item.status == CandidateStatus.REVIEW_READY),
            "approved": sum(1 for item in candidates if item.status == CandidateStatus.APPROVED),
            "imported": sum(1 for item in candidates if item.status == CandidateStatus.IMPORTED),
        },
    }
    return templates.TemplateResponse(request, "dashboard.html", context)


@router.get("/discover", response_class=HTMLResponse)
async def discover_page(request: Request, keyword: str | None = Query(default=None)) -> HTMLResponse:
    leads = []
    if keyword:
        leads = await DiscoveryService().search_codeforces(keyword)
    context = {
        "request": request,
        "page_title": "导入题目",
        "keyword": keyword or "",
        "leads": leads,
        "format_dedup_decision": _format_dedup_decision,
    }
    return templates.TemplateResponse(request, "discover.html", context)


@router.get("/settings/database", response_class=HTMLResponse)
def database_settings_page(
    request: Request,
    session: Session = Depends(get_db_session),
) -> HTMLResponse:
    config_service = RemoteDatabaseConfigService(session)
    config = config_service.get_active_config()
    context = {
        "request": request,
        "page_title": "远端数据库配置",
        "config": config,
        "connection_result": None,
    }
    return templates.TemplateResponse(request, "database_settings.html", context)


@router.post("/settings/database/save", response_class=HTMLResponse)
def save_database_settings(
    request: Request,
    host: str = Form(...),
    port: int = Form(...),
    database_name: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_db_session),
) -> HTMLResponse:
    config_service = RemoteDatabaseConfigService(session)
    config = config_service.save_active_config(
        host=host,
        port=port,
        database_name=database_name,
        username=username,
        password=password,
    )
    context = {
        "request": request,
        "page_title": "远端数据库配置",
        "config": config,
        "connection_result": {"ok": True, "message": "配置已保存到本地 SQLite。"},
    }
    return templates.TemplateResponse(request, "database_settings.html", context)


@router.post("/settings/database/test", response_class=HTMLResponse)
def test_database_settings(
    request: Request,
    host: str = Form(...),
    port: int = Form(...),
    database_name: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    session: Session = Depends(get_db_session),
) -> HTMLResponse:
    config_service = RemoteDatabaseConfigService(session)
    config = config_service.save_active_config(
        host=host,
        port=port,
        database_name=database_name,
        username=username,
        password=password,
    )
    result = config_service.test_connection(config)
    context = {
        "request": request,
        "page_title": "远端数据库配置",
        "config": config,
        "connection_result": {"ok": result.ok, "message": result.message},
    }
    return templates.TemplateResponse(request, "database_settings.html", context)


@router.get("/candidates", response_class=HTMLResponse)
def candidate_list(
    request: Request,
    session: Session = Depends(get_db_session),
) -> HTMLResponse:
    service = CandidateService(session)
    dedup_service = DedupService(session)
    importer = ImporterService(get_app_settings(), session=session)
    candidates = service.list_candidates()
    candidate_rows = []
    for candidate in candidates:
        matches = dedup_service.list_matches(candidate.candidate_id)
        top_match = matches[0] if matches else None
        readiness = _candidate_readiness(candidate)
        candidate_rows.append(
            {
                "candidate": candidate,
                "top_dedup_match": top_match,
                "readiness": readiness,
            }
        )
    config = RemoteDatabaseConfigService(session).get_active_config()
    context = {
        "request": request,
        "page_title": "候选题",
        "candidate_rows": candidate_rows,
        "remote_config": config,
        "format_status": _format_status,
        "format_upload_status": _format_upload_status,
        "format_dedup_decision": _format_dedup_decision,
        "format_readiness": _format_readiness,
        "batch_result": None,
        "importer": importer,
    }
    return templates.TemplateResponse(request, "candidate_list.html", context)


@router.post("/imports/batch-upload", response_class=HTMLResponse)
def batch_upload_candidates(
    request: Request,
    session: Session = Depends(get_db_session),
    settings=Depends(get_app_settings),
) -> HTMLResponse:
    service = CandidateService(session)
    dedup_service = DedupService(session)
    importer = ImporterService(settings, session=session)
    summary = importer.batch_import_approved_candidates(service.list_candidates())
    candidate_rows = []
    for candidate in service.list_candidates():
        matches = dedup_service.list_matches(candidate.candidate_id)
        top_match = matches[0] if matches else None
        candidate_rows.append(
            {
                "candidate": candidate,
                "top_dedup_match": top_match,
                "readiness": _candidate_readiness(candidate),
            }
        )
    context = {
        "request": request,
        "page_title": "候选题",
        "candidate_rows": candidate_rows,
        "remote_config": RemoteDatabaseConfigService(session).get_active_config(),
        "format_status": _format_status,
        "format_upload_status": _format_upload_status,
        "format_dedup_decision": _format_dedup_decision,
        "format_readiness": _format_readiness,
        "batch_result": summary,
        "importer": importer,
    }
    return templates.TemplateResponse(request, "candidate_list.html", context)


@router.post("/candidates")
def create_candidate(
    title: str = Form(...),
    source_type: str = Form(...),
    source_platform: str = Form(...),
    statement_markdown: str = Form(...),
    session: Session = Depends(get_db_session),
) -> RedirectResponse:
    candidate = CandidateService(session).create_candidate(
        title=title,
        source_type=source_type,
        source_platform=source_platform,
        statement_markdown=statement_markdown,
    )
    return RedirectResponse(url=f"/candidates/{candidate.candidate_id}", status_code=303)


@router.post("/discover/intake")
def intake_discovered_lead(
    title: str = Form(...),
    source_platform: str = Form(...),
    source_url: str = Form(...),
    source_problem_id: str = Form(default=""),
    difficulty: int | None = Form(default=None),
    tags: str = Form(default=""),
    session: Session = Depends(get_db_session),
) -> RedirectResponse:
    service = CandidateService(session)
    candidate = service.create_candidate(
        title=title,
        source_type="reference_url",
        source_platform=source_platform,
        statement_markdown=f"Reference source: {source_url}",
    )
    service.update_candidate(
        candidate,
        source_url=source_url,
        source_problem_id=source_problem_id or None,
        difficulty=difficulty,
        knowledge_tags=tags or None,
    )
    return RedirectResponse(url=f"/candidates/{candidate.candidate_id}", status_code=303)


@router.post("/discover/fetch")
async def fetch_reference_url(
    source_platform: str = Form(...),
    source_url: str = Form(...),
    session: Session = Depends(get_db_session),
    settings=Depends(get_app_settings),
) -> RedirectResponse:
    material = await DiscoveryService().fetch_reference_material(source_url)
    service = CandidateService(session)
    candidate = service.create_candidate(
        title=material["title"],
        source_type="reference_url",
        source_platform=source_platform,
        statement_markdown=material["statement_markdown"],
    )
    draft = GenerationService(ai_client=AIClient(settings)).generate_from_statement(
        title=candidate.title,
        statement_markdown=candidate.statement_markdown,
    )
    service.update_candidate(
        candidate,
        source_url=material["source_url"],
        difficulty=draft.difficulty,
        algorithm_tag=draft.algorithm_tag,
        knowledge_tags=draft.knowledge_tags,
        estimated_minutes=draft.estimated_minutes,
        time_limit_ms=draft.time_limit_ms,
        space_limit_kb=draft.space_limit_kb,
        question_case_json=draft.question_case_json,
        default_code_java=draft.default_code_java,
        main_fuc_java=draft.main_fuc_java,
        solution_outline=draft.solution_outline,
        solution_code_java=draft.solution_code_java,
        status=CandidateStatus.ARTIFACTS_GENERATED,
    )
    _refresh_candidate_dedup(session, settings, candidate)
    return RedirectResponse(url=f"/candidates/{candidate.candidate_id}", status_code=303)


@router.post("/discover/batch")
async def batch_fetch_reference_urls(
    source_platform: str = Form(...),
    urls_text: str = Form(...),
    session: Session = Depends(get_db_session),
    settings=Depends(get_app_settings),
) -> RedirectResponse:
    service = CandidateService(session)
    discovery = DiscoveryService()
    urls = [line.strip() for line in urls_text.splitlines() if line.strip()]
    for url in urls:
        material = await discovery.fetch_reference_material(url)
        candidate = service.create_candidate(
            title=material["title"],
            source_type="reference_url",
            source_platform=source_platform,
            statement_markdown=material["statement_markdown"],
        )
        draft = GenerationService(ai_client=AIClient(settings)).generate_from_statement(
            title=candidate.title,
            statement_markdown=candidate.statement_markdown,
        )
        service.update_candidate(
            candidate,
            source_url=material["source_url"],
            difficulty=draft.difficulty,
            algorithm_tag=draft.algorithm_tag,
            knowledge_tags=draft.knowledge_tags,
            estimated_minutes=draft.estimated_minutes,
            time_limit_ms=draft.time_limit_ms,
            space_limit_kb=draft.space_limit_kb,
            question_case_json=draft.question_case_json,
            default_code_java=draft.default_code_java,
            main_fuc_java=draft.main_fuc_java,
            solution_outline=draft.solution_outline,
            solution_code_java=draft.solution_code_java,
            status=CandidateStatus.ARTIFACTS_GENERATED,
        )
        _refresh_candidate_dedup(session, settings, candidate)
    return RedirectResponse(url="/candidates", status_code=303)


@router.get("/candidates/{candidate_id}", response_class=HTMLResponse)
def candidate_detail(
    candidate_id: int,
    request: Request,
    session: Session = Depends(get_db_session),
    settings=Depends(get_app_settings),
) -> HTMLResponse:
    service = CandidateService(session)
    candidate = service.get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="未找到候选题。")
    review_pack_path = ReviewPackService(settings).write_review_pack(candidate)
    import_preview = ImporterService(settings, session=session).build_preview(candidate)
    dedup_matches = DedupService(session).list_matches(candidate.candidate_id)
    context = {
        "request": request,
        "page_title": f"候选题 #{candidate.candidate_id}",
        "candidate": candidate,
        "review_pack_path": str(review_pack_path),
        "import_preview": import_preview,
        "dedup_matches": dedup_matches,
        "execution_result": None,
        "format_status": _format_status,
        "format_upload_status": _format_upload_status,
        "format_dedup_decision": _format_dedup_decision,
        "format_dedup_reason": _format_dedup_reason,
    }
    return templates.TemplateResponse(request, "candidate_detail.html", context)


@router.post("/candidates/{candidate_id}/save")
def save_candidate(
    candidate_id: int,
    title: str = Form(...),
    difficulty: int | None = Form(default=None),
    algorithm_tag: str = Form(default=""),
    knowledge_tags: str = Form(default=""),
    estimated_minutes: int | None = Form(default=None),
    time_limit_ms: int | None = Form(default=None),
    space_limit_kb: int | None = Form(default=None),
    statement_markdown: str = Form(default=""),
    question_case_json: str = Form(default="[]"),
    default_code_java: str = Form(default=""),
    main_fuc_java: str = Form(default=""),
    solution_outline: str = Form(default=""),
    solution_code_java: str = Form(default=""),
    session: Session = Depends(get_db_session),
) -> RedirectResponse:
    service = CandidateService(session)
    candidate = service.get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="未找到候选题。")
    service.update_candidate(
        candidate,
        title=title,
        difficulty=difficulty,
        algorithm_tag=algorithm_tag or None,
        knowledge_tags=knowledge_tags or None,
        estimated_minutes=estimated_minutes,
        time_limit_ms=time_limit_ms,
        space_limit_kb=space_limit_kb,
        statement_markdown=statement_markdown,
        question_case_json=question_case_json,
        default_code_java=default_code_java,
        main_fuc_java=main_fuc_java,
        solution_outline=solution_outline or None,
        solution_code_java=solution_code_java or None,
    )
    return RedirectResponse(url=f"/candidates/{candidate_id}", status_code=303)


@router.post("/candidates/{candidate_id}/generate")
def generate_candidate(
    candidate_id: int,
    session: Session = Depends(get_db_session),
    settings=Depends(get_app_settings),
) -> RedirectResponse:
    service = CandidateService(session)
    candidate = service.get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="未找到候选题。")
    draft = GenerationService(ai_client=AIClient(settings)).generate_from_statement(
        title=candidate.title,
        statement_markdown=candidate.statement_markdown,
    )
    service.update_candidate(
        candidate,
        difficulty=draft.difficulty,
        algorithm_tag=draft.algorithm_tag,
        knowledge_tags=draft.knowledge_tags,
        estimated_minutes=draft.estimated_minutes,
        time_limit_ms=draft.time_limit_ms,
        space_limit_kb=draft.space_limit_kb,
        question_case_json=draft.question_case_json,
        default_code_java=draft.default_code_java,
        main_fuc_java=draft.main_fuc_java,
        solution_outline=draft.solution_outline,
        solution_code_java=draft.solution_code_java,
        status=CandidateStatus.ARTIFACTS_GENERATED,
    )
    _refresh_candidate_dedup(session, settings, candidate)
    return RedirectResponse(url=f"/candidates/{candidate_id}", status_code=303)


@router.post("/candidates/{candidate_id}/run-java", response_class=HTMLResponse)
def run_java_draft(
    candidate_id: int,
    request: Request,
    session: Session = Depends(get_db_session),
    settings=Depends(get_app_settings),
) -> HTMLResponse:
    service = CandidateService(session)
    candidate = service.get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="未找到候选题。")
    execution_service = ExecutionService(settings)
    result = execution_service.run_java_source(
        java_source=f"{candidate.default_code_java or ''}\n{candidate.main_fuc_java or ''}",
        inputs=_load_sample_inputs(candidate.question_case_json or "[]"),
        workdir=settings.execution_dir / str(candidate.candidate_id),
    )
    review_pack_path = ReviewPackService(settings).write_review_pack(candidate)
    import_preview = ImporterService(settings, session=session).build_preview(candidate)
    dedup_matches = DedupService(session).list_matches(candidate.candidate_id)
    context = {
        "request": request,
        "page_title": f"候选题 #{candidate.candidate_id}",
        "candidate": candidate,
        "review_pack_path": str(review_pack_path),
        "import_preview": import_preview,
        "dedup_matches": dedup_matches,
        "execution_result": result,
        "format_status": _format_status,
        "format_upload_status": _format_upload_status,
        "format_dedup_decision": _format_dedup_decision,
        "format_dedup_reason": _format_dedup_reason,
    }
    return templates.TemplateResponse(request, "candidate_detail.html", context)


@router.post("/candidates/{candidate_id}/approve")
def approve_candidate(candidate_id: int, session: Session = Depends(get_db_session)) -> RedirectResponse:
    service = CandidateService(session)
    candidate = service.get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="未找到候选题。")
    service.set_status(candidate, CandidateStatus.APPROVED)
    return RedirectResponse(url=f"/candidates/{candidate_id}", status_code=303)


@router.post("/candidates/{candidate_id}/reject")
def reject_candidate(candidate_id: int, session: Session = Depends(get_db_session)) -> RedirectResponse:
    service = CandidateService(session)
    candidate = service.get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="未找到候选题。")
    service.set_status(candidate, CandidateStatus.REJECTED)
    return RedirectResponse(url=f"/candidates/{candidate_id}", status_code=303)


@router.post("/candidates/{candidate_id}/import")
def import_candidate(
    candidate_id: int,
    session: Session = Depends(get_db_session),
    settings=Depends(get_app_settings),
) -> RedirectResponse:
    service = CandidateService(session)
    candidate = service.get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="未找到候选题。")
    ImporterService(settings, session=session).import_candidate(candidate)
    return RedirectResponse(url=f"/candidates/{candidate_id}", status_code=303)


def _refresh_candidate_dedup(session: Session, settings, candidate) -> None:
    existing_questions = OJReader(settings).load_existing_questions()
    if not existing_questions:
        existing_questions = [
            ExistingQuestion(
                question_id=1000001,
                title="Two Sum",
                content="Given an integer array nums and an integer target, return indices.",
                algorithm_tag="Hash Table",
                knowledge_tags="array,hash",
            ),
            ExistingQuestion(
                question_id=1000002,
                title="Merge Intervals",
                content="Given a collection of intervals, merge overlapping intervals.",
                algorithm_tag="Sorting",
                knowledge_tags="interval,sorting",
            ),
        ]
    DedupService(session).analyze_and_store(candidate, existing_questions)


def _load_sample_inputs(question_case_json: str) -> list[str]:
    try:
        payload = json.loads(question_case_json)
    except json.JSONDecodeError:
        return []
    inputs: list[str] = []
    for item in payload:
        input_value = item.get("input")
        if isinstance(input_value, str):
            inputs.append(input_value)
    return inputs[:1]


def _candidate_readiness(candidate) -> str:
    missing: list[str] = []
    if not candidate.question_case_json or candidate.question_case_json == "[]":
        missing.append("missing-samples")
    if not candidate.solution_code_java:
        missing.append("missing-solution")
    if not candidate.default_code_java or not candidate.main_fuc_java:
        missing.append("missing-java-draft")
    execution_ready = bool(candidate.default_code_java and candidate.main_fuc_java and candidate.question_case_json)
    if execution_ready and candidate.status == CandidateStatus.ARTIFACTS_GENERATED:
        missing.append("missing-run-check")
    if not missing:
        return "review-ready"
    return ", ".join(missing)


def _format_status(status: CandidateStatus | str) -> str:
    if isinstance(status, CandidateStatus):
        return STATUS_LABELS.get(status, status.value)
    return STATUS_LABELS.get(CandidateStatus(status), status) if status in CandidateStatus._value2member_map_ else status


def _format_upload_status(status: UploadStatus | str) -> str:
    if isinstance(status, UploadStatus):
        return UPLOAD_STATUS_LABELS.get(status, status.value)
    return UPLOAD_STATUS_LABELS.get(UploadStatus(status), status) if status in UploadStatus._value2member_map_ else status


def _format_dedup_decision(decision: str) -> str:
    return DEDUP_DECISION_LABELS.get(decision, decision)


def _format_readiness(readiness: str) -> str:
    parts = [item.strip() for item in readiness.split(",") if item.strip()]
    translated = [READINESS_LABELS.get(item, item) for item in parts]
    return "、".join(translated) if translated else readiness


def _format_dedup_reason(reason: str) -> str:
    segments = []
    for chunk in reason.split(","):
        key, _, value = chunk.strip().partition("=")
        if not key:
            continue
        label = {
            "title": "标题相似度",
            "semantic": "题意相似度",
            "tag": "标签相似度",
        }.get(key, key)
        segments.append(f"{label}={value}")
    return "，".join(segments) if segments else reason
