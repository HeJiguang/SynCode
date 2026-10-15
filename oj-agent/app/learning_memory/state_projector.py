from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
from math import exp
from typing import Any, Iterable

from app.learning_memory.models import LearningStateEvidence, LearningStateMemory, LearningTrend, MasteryLevel


LEARNING_STATE_MODEL_VERSION = "syncode-explainable-mastery-v1"


def _as_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _episode_quality(episode: dict[str, Any]) -> float:
    payload = episode.get("payload") or {}
    if payload.get("final_result") != "passed":
        return 0.0
    attempts = max(1, int(payload.get("attempt_count") or 1))
    error_count = len(payload.get("error_types") or [])
    penalty = min(0.45, (attempts - 1) * 0.08 + error_count * 0.1)
    return round(1.0 - penalty, 4)


def _mastery_level(score: float, confidence: float) -> MasteryLevel:
    if confidence < 0.3:
        return "insufficient"
    if score < 40:
        return "foundational"
    if score < 65:
        return "developing"
    if score < 85:
        return "stable"
    return "proficient"


def _trend(ordered: list[dict[str, Any]]) -> LearningTrend:
    if len(ordered) < 4:
        return "stable"
    recent = ordered[-3:]
    previous = ordered[-6:-3]
    if len(recent) < 2 or len(previous) < 2:
        return "stable"
    recent_score = sum(_episode_quality(item) for item in recent) / len(recent)
    previous_score = sum(_episode_quality(item) for item in previous) / len(previous)
    delta = recent_score - previous_score
    if delta >= 0.12:
        return "improving"
    if delta <= -0.12:
        return "declining"
    return "stable"


def _content_hash(summary: str, payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return sha256(f"{summary}\0{canonical}".encode()).hexdigest()


def project_learning_states(
    *,
    user_id: str,
    episodes: Iterable[dict[str, Any]],
    now: datetime | None = None,
) -> list[LearningStateMemory]:
    current = now or datetime.now(timezone.utc)
    current = current.replace(tzinfo=timezone.utc) if current.tzinfo is None else current.astimezone(timezone.utc)

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for episode in episodes:
        if episode.get("memory_type") != "problem_episode":
            continue
        for raw_tag in episode.get("knowledge_tags") or []:
            tag = str(raw_tag).strip().casefold()[:100]
            if tag:
                grouped[tag].append(episode)

    states: list[LearningStateMemory] = []
    for tag, tag_episodes in grouped.items():
        ordered = sorted(
            tag_episodes,
            key=lambda item: (
                _as_datetime(item.get("last_seen_at")) or datetime.min.replace(tzinfo=timezone.utc),
                item["memory_id"],
            ),
        )
        weighted_score = 0.0
        total_weight = 0.0
        evidence: list[LearningStateEvidence] = []
        question_ids: set[str] = set()
        attempts = 0
        passes = 0
        error_episodes = 0
        recent_errors: list[str] = []

        for episode in ordered:
            payload = episode.get("payload") or {}
            observed_at = _as_datetime(episode.get("last_seen_at"))
            age_days = max(0.0, (current - observed_at).total_seconds() / 86400) if observed_at else 3650.0
            recency_weight = max(0.1, 0.5 ** (age_days / 90))
            difficulty = int(payload.get("difficulty") or 2)
            difficulty_weight = {1: 0.85, 2: 1.0, 3: 1.15}.get(difficulty, 1.0)
            weight = recency_weight * difficulty_weight
            quality = _episode_quality(episode)
            weighted_score += quality * weight
            total_weight += weight

            question_ids.add(str(payload.get("question_id") or episode.get("source_id") or "unknown"))
            attempts += max(1, int(payload.get("attempt_count") or 1))
            if payload.get("final_result") == "passed":
                passes += 1
            errors = [str(value) for value in payload.get("error_types") or []]
            if errors:
                error_episodes += 1
                for error in errors:
                    if error not in recent_errors:
                        recent_errors.append(error)
            evidence.append(LearningStateEvidence(
                memory_id=str(episode["memory_id"]),
                observed_at=observed_at,
                contribution=quality,
                reason=(
                    f"{payload.get('final_result', 'unknown')}，{int(payload.get('attempt_count') or 1)} 次提交，"
                    f"难度 {difficulty}"
                ),
                payload={
                    "question_id": payload.get("question_id"),
                    "final_result": payload.get("final_result"),
                    "attempt_count": int(payload.get("attempt_count") or 1),
                    "difficulty": difficulty,
                    "error_types": errors,
                },
            ))

        episode_count = len(ordered)
        raw_score = round(100 * weighted_score / total_weight, 2) if total_weight else 0.0
        evidence_strength = 0.7 * len(question_ids) + 0.3 * episode_count
        confidence = round(1 - exp(-evidence_strength / 4), 4)
        score = round(50 * (1 - confidence) + raw_score * confidence, 2)
        trend = _trend(ordered)
        level = _mastery_level(score, confidence)
        first_at = _as_datetime(ordered[0].get("first_seen_at"))
        last_at = _as_datetime(ordered[-1].get("last_seen_at"))
        forgetting = min(1.0, max(0.0, (current - last_at).total_seconds() / 86400 / 90)) if last_at else 1.0
        weakness = (100 - score) / 100
        priority = round(100 * (
            0.65 * weakness * max(0.35, confidence)
            + 0.2 * forgetting
            + 0.15 * (1 - confidence)
        ), 2)
        if trend == "declining":
            priority = min(100.0, round(priority + 10, 2))
        review_days = 1 if score < 40 or trend == "declining" else 3 if score < 65 else 7 if score < 85 else 21
        next_review = last_at + timedelta(days=review_days) if last_at else current
        summary = (
            f"用户在 {tag} 上共有 {episode_count} 次独立学习经历、{attempts} 次提交，"
            f"其中 {passes} 次经历最终通过；当前掌握度 {score:.0f}，"
            f"证据置信度 {confidence:.2f}，趋势为 {trend}。"
        )
        payload = {
            "knowledge_tag": tag,
            "distinct_question_count": len(question_ids),
            "episode_count": episode_count,
            "attempt_count": attempts,
            "independent_pass_count": passes,
            "error_episode_count": error_episodes,
            "recent_error_types": recent_errors[-10:],
            "raw_performance_score": raw_score,
            "scoring_model": LEARNING_STATE_MODEL_VERSION,
        }
        states.append(LearningStateMemory(
            state_id=sha256(f"learning-state\0{user_id}\0{tag}".encode()).hexdigest(),
            user_id=user_id,
            knowledge_tag=tag,
            mastery_level=level,
            mastery_score=score,
            confidence=confidence,
            trend=trend,
            priority_score=priority,
            episode_count=episode_count,
            attempt_count=attempts,
            independent_pass_count=passes,
            error_episode_count=error_episodes,
            recent_error_types=tuple(recent_errors[-10:]),
            first_practiced_at=first_at,
            last_practiced_at=last_at,
            next_review_at=next_review,
            summary=summary,
            content_hash=_content_hash(summary, payload),
            payload=payload,
            evidence=tuple(evidence[-50:]),
        ))
    return states
