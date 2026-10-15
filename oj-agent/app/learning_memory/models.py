from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal


MemoryLevel = Literal["event", "episode", "pattern"]
MemoryStatus = Literal["active", "improving", "resolved", "superseded"]
MEMORY_LEVELS: tuple[MemoryLevel, ...] = ("pattern", "episode", "event")
MasteryLevel = Literal["insufficient", "foundational", "developing", "stable", "proficient"]
LearningTrend = Literal["improving", "stable", "declining"]


@dataclass(frozen=True)
class LearningMemoryEvidence:
    evidence_type: str
    evidence_id: str
    occurred_at: datetime | None
    snippet: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LearningMemory:
    memory_id: str
    user_id: str
    level: MemoryLevel
    memory_type: str
    title: str
    summary: str
    knowledge_tags: tuple[str, ...]
    error_type: str | None
    status: MemoryStatus
    confidence: float
    occurrence_count: int
    source_type: str
    source_id: str
    occurred_at: datetime | None
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    content_hash: str
    payload: dict[str, Any]
    evidence: tuple[LearningMemoryEvidence, ...] = ()


@dataclass(frozen=True)
class LearningStateEvidence:
    memory_id: str
    observed_at: datetime | None
    contribution: float
    reason: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LearningStateMemory:
    state_id: str
    user_id: str
    knowledge_tag: str
    mastery_level: MasteryLevel
    mastery_score: float
    confidence: float
    trend: LearningTrend
    priority_score: float
    episode_count: int
    attempt_count: int
    independent_pass_count: int
    error_episode_count: int
    recent_error_types: tuple[str, ...]
    first_practiced_at: datetime | None
    last_practiced_at: datetime | None
    next_review_at: datetime | None
    summary: str
    content_hash: str
    payload: dict[str, Any]
    evidence: tuple[LearningStateEvidence, ...] = ()
