from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import re
from typing import Any, Iterable

from app.learning_memory.models import LearningMemory, LearningMemoryEvidence


SESSION_GAP = timedelta(hours=24)


def _memory_id(*parts: object) -> str:
    return sha256("\0".join(str(part) for part in parts).encode()).hexdigest()


def _as_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        raw = str(value).strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(raw)
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _tags(value: Any, algorithm_tag: Any = None) -> tuple[str, ...]:
    values: list[str] = []
    for source in (algorithm_tag, value):
        if source is None:
            continue
        if isinstance(source, (list, tuple, set)):
            candidates = source
        else:
            text = str(source).strip()
            if text.startswith("["):
                try:
                    parsed = json.loads(text)
                    candidates = parsed if isinstance(parsed, list) else [text]
                except json.JSONDecodeError:
                    candidates = re.split(r"[,，;；]", text)
            else:
                candidates = re.split(r"[,，;；]", text)
        for candidate in candidates:
            tag = str(candidate).strip()
            if tag and tag not in values:
                values.append(tag)
    return tuple(values[:20])


def _error_type(row: dict[str, Any]) -> str | None:
    if int(row.get("pass") or 0) == 1:
        return None
    message = " ".join(
        str(row.get(key) or "") for key in ("exe_message", "last_error")
    ).lower()
    if any(token in message for token in ("compile", "compilation", "编译")):
        return "compile_error"
    if any(token in message for token in ("time limit", "timeout", "超时")):
        return "time_limit"
    if any(token in message for token in ("memory limit", "out of memory", "超内存")):
        return "memory_limit"
    if any(token in message for token in ("runtime", "exception", "signal", "运行错误")):
        return "runtime_error"
    if any(token in message for token in ("wrong answer", "答案错误")):
        return "wrong_answer"
    return "judge_failure"


def _digest(summary: str, payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(f"{summary}\0{canonical}".encode()).hexdigest()


def _submission_event(user_id: str, row: dict[str, Any]) -> LearningMemory:
    submit_id = str(row["submit_id"])
    occurred_at = _as_datetime(row.get("occurred_at"))
    passed = int(row.get("pass") or 0) == 1
    error_type = _error_type(row)
    title = str(row.get("title") or f"题目 {row['question_id']}")
    result = "通过" if passed else f"未通过（{error_type or 'unknown'}）"
    summary = f"用户提交《{title}》，结果为{result}，得分 {int(row.get('score') or 0)}。"
    payload = {
        "submit_id": submit_id,
        "question_id": str(row["question_id"]),
        "exam_id": str(row["exam_id"]) if row.get("exam_id") is not None else None,
        "program_type": row.get("program_type"),
        "passed": passed,
        "score": int(row.get("score") or 0),
        "error_type": error_type,
        "judge_message": str(row.get("exe_message") or "")[:500],
        "runtime_ms": row.get("use_time"),
        "memory_kb": row.get("use_memory"),
    }
    evidence = LearningMemoryEvidence(
        evidence_type="submission",
        evidence_id=submit_id,
        occurred_at=occurred_at,
        snippet=str(row.get("exe_message") or result)[:500],
        payload={"question_id": str(row["question_id"]), "passed": passed},
    )
    return LearningMemory(
        memory_id=_memory_id("learning-event", user_id, "submission", submit_id),
        user_id=user_id,
        level="event",
        memory_type="submission",
        title=f"提交：{title}",
        summary=summary,
        knowledge_tags=_tags(row.get("knowledge_tags"), row.get("algorithm_tag")),
        error_type=error_type,
        status="active",
        confidence=1.0,
        occurrence_count=1,
        source_type="submission",
        source_id=submit_id,
        occurred_at=occurred_at,
        first_seen_at=occurred_at,
        last_seen_at=occurred_at,
        content_hash=_digest(summary, payload),
        payload=payload,
        evidence=(evidence,),
    )


def _submission_episodes(user_id: str, rows: list[dict[str, Any]]) -> list[LearningMemory]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(str(row["question_id"]), str(row.get("exam_id") or "practice"))].append(row)

    episodes: list[LearningMemory] = []
    for (question_id, exam_scope), candidates in grouped.items():
        ordered = sorted(
            candidates,
            key=lambda item: (_as_datetime(item.get("occurred_at")) or datetime.min.replace(tzinfo=timezone.utc), str(item["submit_id"])),
        )
        sessions: list[list[dict[str, Any]]] = []
        for row in ordered:
            when = _as_datetime(row.get("occurred_at"))
            previous = _as_datetime(sessions[-1][-1].get("occurred_at")) if sessions else None
            if not sessions or (when and previous and when - previous > SESSION_GAP):
                sessions.append([row])
            else:
                sessions[-1].append(row)

        for session in sessions:
            first = session[0]
            last = session[-1]
            first_at = _as_datetime(first.get("occurred_at"))
            last_at = _as_datetime(last.get("occurred_at"))
            passed = int(last.get("pass") or 0) == 1
            errors = [value for item in session if (value := _error_type(item))]
            error_types = list(dict.fromkeys(errors))
            title = str(first.get("title") or f"题目 {question_id}")
            result_path = ["AC" if int(item.get("pass") or 0) == 1 else (_error_type(item) or "failed") for item in session]
            error_text = "、".join(error_types) if error_types else "无已识别错误"
            summary = (
                f"用户完成《{title}》的一次学习过程，共提交 {len(session)} 次，"
                f"最终{'通过' if passed else '未通过'}；过程中的错误类型为 {error_text}。"
            )
            payload = {
                "question_id": question_id,
                "exam_id": None if exam_scope == "practice" else exam_scope,
                "difficulty": int(first.get("difficulty") or 2),
                "attempt_count": len(session),
                "result_path": result_path,
                "final_result": "passed" if passed else "failed",
                "error_types": error_types,
                "first_submit_id": str(first["submit_id"]),
                "last_submit_id": str(last["submit_id"]),
            }
            evidence = tuple(
                LearningMemoryEvidence(
                    evidence_type="submission",
                    evidence_id=str(item["submit_id"]),
                    occurred_at=_as_datetime(item.get("occurred_at")),
                    snippet=str(item.get("exe_message") or ("Accepted" if int(item.get("pass") or 0) == 1 else "Failed"))[:500],
                    payload={"passed": int(item.get("pass") or 0) == 1},
                )
                for item in session
            )
            episodes.append(LearningMemory(
                memory_id=_memory_id("learning-episode", user_id, question_id, exam_scope, first["submit_id"]),
                user_id=user_id,
                level="episode",
                memory_type="problem_episode",
                title=f"做题经历：{title}",
                summary=summary,
                knowledge_tags=_tags(first.get("knowledge_tags"), first.get("algorithm_tag")),
                error_type=error_types[0] if len(error_types) == 1 else None,
                status="active",
                confidence=1.0,
                occurrence_count=len(session),
                source_type="question_session",
                source_id=f"{question_id}:{exam_scope}:{first['submit_id']}",
                occurred_at=last_at,
                first_seen_at=first_at,
                last_seen_at=last_at,
                content_hash=_digest(summary, payload),
                payload=payload,
                evidence=evidence,
            ))
    return episodes


def _exam_memories(user_id: str, rows: list[dict[str, Any]], submissions: list[dict[str, Any]]) -> list[LearningMemory]:
    by_exam: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for submission in submissions:
        if submission.get("exam_id") is not None:
            by_exam[str(submission["exam_id"])].append(submission)
    memories: list[LearningMemory] = []
    for row in rows:
        exam_id = str(row["exam_id"])
        occurred_at = _as_datetime(row.get("occurred_at"))
        related = by_exam.get(exam_id, [])
        passed_count = sum(1 for item in related if int(item.get("pass") or 0) == 1)
        tags = tuple(dict.fromkeys(tag for item in related for tag in _tags(item.get("knowledge_tags"), item.get("algorithm_tag"))))
        title = str(row.get("title") or f"考试 {exam_id}")
        score = int(row.get("score") or 0)
        rank = row.get("exam_rank")
        summary = (
            f"用户参加《{title}》，得分 {score}"
            + (f"，排名 {rank}" if rank is not None else "")
            + f"；系统记录到 {len(related)} 次正式提交，其中 {passed_count} 次通过。"
        )
        payload = {
            "user_exam_id": str(row["user_exam_id"]),
            "exam_id": exam_id,
            "score": score,
            "rank": rank,
            "submission_count": len(related),
            "passed_submission_count": passed_count,
        }
        exam_evidence = LearningMemoryEvidence(
            evidence_type="exam",
            evidence_id=str(row["user_exam_id"]),
            occurred_at=occurred_at,
            snippet=f"考试《{title}》得分 {score}" + (f"，排名 {rank}" if rank is not None else ""),
            payload={"exam_id": exam_id, "score": score, "rank": rank},
        )
        submission_evidence = tuple(
            LearningMemoryEvidence(
                evidence_type="submission",
                evidence_id=str(item["submit_id"]),
                occurred_at=_as_datetime(item.get("occurred_at")),
                snippet=str(item.get("exe_message") or "")[:500],
                payload={"question_id": str(item["question_id"]), "passed": int(item.get("pass") or 0) == 1},
            )
            for item in related
        )
        evidence = (exam_evidence, *submission_evidence)
        common = dict(
            user_id=user_id,
            title=f"考试经历：{title}",
            summary=summary,
            knowledge_tags=tags,
            error_type=None,
            status="active",
            confidence=1.0,
            occurrence_count=max(1, len(related)),
            source_type="exam",
            source_id=exam_id,
            occurred_at=occurred_at,
            first_seen_at=occurred_at,
            last_seen_at=occurred_at,
            content_hash=_digest(summary, payload),
            payload=payload,
            evidence=evidence,
        )
        memories.append(LearningMemory(
            memory_id=_memory_id("learning-event", user_id, "exam", exam_id),
            level="event",
            memory_type="exam_result",
            **common,
        ))
        memories.append(LearningMemory(
            memory_id=_memory_id("learning-episode", user_id, "exam", exam_id),
            level="episode",
            memory_type="exam_episode",
            **common,
        ))
    return memories


def _patterns(user_id: str, episodes: list[LearningMemory], *, now: datetime) -> list[LearningMemory]:
    problem_episodes = [item for item in episodes if item.memory_type == "problem_episode"]
    by_tag_error: dict[tuple[str, str], list[LearningMemory]] = defaultdict(list)
    by_tag: dict[str, list[LearningMemory]] = defaultdict(list)
    cutoff = now - timedelta(days=90)
    for episode in problem_episodes:
        if episode.last_seen_at and episode.last_seen_at < cutoff:
            continue
        for tag in episode.knowledge_tags:
            by_tag[tag].append(episode)
            for error in episode.payload.get("error_types") or []:
                by_tag_error[(tag, str(error))].append(episode)

    patterns: list[LearningMemory] = []
    for (tag, error), evidence_episodes in by_tag_error.items():
        if len(evidence_episodes) < 2:
            continue
        last_error_at = max(
            (item.last_seen_at for item in evidence_episodes if item.last_seen_at),
            default=None,
        )
        clean_after = [
            item for item in by_tag[tag]
            if item.last_seen_at and last_error_at and item.last_seen_at > last_error_at
            and item.payload.get("final_result") == "passed"
            and error not in (item.payload.get("error_types") or [])
        ]
        status = "resolved" if len(clean_after) >= 5 else "improving" if len(clean_after) >= 2 else "active"
        base_confidence = len(evidence_episodes) / (len(evidence_episodes) + 2)
        confidence = max(0.1, round(base_confidence * (0.45 if status == "resolved" else 0.7 if status == "improving" else 1.0), 4))
        first_seen = min((item.first_seen_at for item in evidence_episodes if item.first_seen_at), default=None)
        last_seen = max((item.last_seen_at for item in evidence_episodes if item.last_seen_at), default=None)
        if status == "active":
            trend = "当前仍需关注"
        elif status == "improving":
            trend = f"之后已有 {len(clean_after)} 次干净通过，正在改善"
        else:
            trend = f"之后已有 {len(clean_after)} 次干净通过，当前视为基本解决"
        summary = (
            f"最近 90 天，用户在 {tag} 相关题目中有 {len(evidence_episodes)} 次学习经历出现 "
            f"{error}；{trend}。"
        )
        payload = {
            "knowledge_tag": tag,
            "error_type": error,
            "episode_count": len(evidence_episodes),
            "clean_successes_after_last_error": len(clean_after),
            "window_days": 90,
        }
        evidence = tuple(
            LearningMemoryEvidence(
                evidence_type="episode",
                evidence_id=item.memory_id,
                occurred_at=item.last_seen_at,
                snippet=item.summary[:500],
                payload={"source_id": item.source_id},
            )
            for item in evidence_episodes
        )
        patterns.append(LearningMemory(
            memory_id=_memory_id("learning-pattern", user_id, tag, error),
            user_id=user_id,
            level="pattern",
            memory_type="error_pattern",
            title=f"{tag}：{error}",
            summary=summary,
            knowledge_tags=(tag,),
            error_type=error,
            status=status,
            confidence=confidence,
            occurrence_count=len(evidence_episodes),
            source_type="derived_pattern",
            source_id=f"{tag}:{error}",
            occurred_at=last_seen,
            first_seen_at=first_seen,
            last_seen_at=last_seen,
            content_hash=_digest(summary, payload),
            payload=payload,
            evidence=evidence,
        ))
    return patterns


def project_learning_memories(
    *,
    user_id: str,
    submissions: Iterable[dict[str, Any]],
    exams: Iterable[dict[str, Any]],
    now: datetime | None = None,
) -> list[LearningMemory]:
    submission_rows = list(submissions)
    exam_rows = list(exams)
    events = [_submission_event(user_id, row) for row in submission_rows]
    problem_episodes = _submission_episodes(user_id, submission_rows)
    exam_memories = _exam_memories(user_id, exam_rows, submission_rows)
    episodes = problem_episodes + [item for item in exam_memories if item.level == "episode"]
    patterns = _patterns(user_id, problem_episodes, now=now or datetime.now(timezone.utc))
    exam_events = [item for item in exam_memories if item.level == "event"]
    return patterns + episodes + events + exam_events
