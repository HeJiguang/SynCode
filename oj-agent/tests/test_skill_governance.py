from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine

from app.skill_governance.repository import SkillGovernanceRepository
from app.skill_governance.service import SkillGovernanceService, SynthesizedSkill
from app.skill_governance.storage import HermesSkillStore


def _schema(database_url: str) -> None:
    engine = create_engine(database_url)
    statements = [
        """CREATE TABLE tb_ai_skill (
            skill_id TEXT PRIMARY KEY, skill_name TEXT, display_name TEXT, description TEXT,
            scope TEXT, owner_user_id INTEGER, category TEXT, lifecycle_status TEXT,
            current_version TEXT, source_path TEXT, last_seen_at TEXT, archived_at TEXT,
            create_time TEXT DEFAULT CURRENT_TIMESTAMP, update_time TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(scope, owner_user_id, skill_name))""",
        """CREATE TABLE tb_ai_skill_version (
            skill_id TEXT, version TEXT, content_hash TEXT, source_type TEXT, review_status TEXT,
            content_uri TEXT, content_text TEXT, package_json TEXT, metadata_json TEXT,
            created_by_type TEXT, created_by TEXT, source_candidate_id TEXT,
            create_time TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(skill_id, version))""",
        """CREATE TABLE tb_ai_skill_usage_event (
            event_id TEXT PRIMARY KEY, user_id INTEGER, skill_name TEXT, skill_version TEXT,
            event_type TEXT, occurred_at TEXT)""",
        """CREATE TABLE tb_ai_skill_promotion_candidate (
            candidate_id TEXT PRIMARY KEY, cluster_key TEXT UNIQUE, title TEXT, proposed_skill_name TEXT,
            category TEXT, status TEXT, summary TEXT, draft_content TEXT,
            distinct_owner_count INTEGER, member_count INTEGER, usage_count_30d INTEGER,
            min_similarity REAL, similarity_method TEXT, reviewed_by TEXT, review_note TEXT,
            reviewed_at TEXT, published_skill_id TEXT, published_version TEXT,
            create_time TEXT DEFAULT CURRENT_TIMESTAMP, update_time TEXT DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE tb_ai_skill_promotion_member (
            candidate_id TEXT, skill_id TEXT, skill_version TEXT, owner_hash TEXT,
            similarity_score REAL, redacted_summary TEXT, usage_count_30d INTEGER,
            create_time TEXT DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY(candidate_id, skill_id))""",
        """CREATE TABLE tb_ai_skill_promotion_review_action (
            action_id TEXT PRIMARY KEY, candidate_id TEXT, reviewer TEXT, action TEXT,
            before_status TEXT, after_status TEXT, note TEXT, create_time TEXT DEFAULT CURRENT_TIMESTAMP)""",
        """CREATE TABLE tb_ai_skill_release (
            release_id TEXT PRIMARY KEY, skill_id TEXT, version TEXT, source_candidate_id TEXT,
            status TEXT, published_by TEXT, published_at TEXT, create_time TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(skill_id, version))""",
        """CREATE TABLE tb_ai_skill_lifecycle_review (
            review_id TEXT PRIMARY KEY, skill_id TEXT, skill_version TEXT, reason TEXT, status TEXT,
            usage_count_30d INTEGER, last_used_at TEXT, reviewed_by TEXT, review_note TEXT,
            reviewed_at TEXT, create_time TEXT DEFAULT CURRENT_TIMESTAMP,
            update_time TEXT DEFAULT CURRENT_TIMESTAMP, UNIQUE(skill_id, skill_version, reason))""",
        """CREATE TABLE tb_ai_skill_governance_heartbeat (
            heartbeat_id TEXT PRIMARY KEY, status TEXT, metrics_json TEXT, error_message TEXT,
            started_at TEXT, finished_at TEXT, create_time TEXT DEFAULT CURRENT_TIMESTAMP)""",
    ]
    with engine.begin() as connection:
        for statement in statements:
            connection.exec_driver_sql(statement)
    engine.dispose()


def _skill(name: str, instruction: str) -> str:
    return (
        "---\n"
        f"name: {name}\n"
        f"description: Use when diagnosing a recurring loop boundary error. {instruction}\n"
        "---\n\n"
        "# Procedure\n\n"
        f"1. {instruction}\n"
        "2. Verify the corrected boundary.\n"
    )


def _write_profile(root: Path, user_id: int, name: str, instruction: str) -> None:
    skill_dir = root / "profiles" / f"syncode-u{user_id}" / "skills" / "debugging" / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(_skill(name, instruction), encoding="utf-8")


class FakeIndex:
    enabled = True

    def __init__(self):
        self.rows = []

    def upsert(self, rows):
        self.rows = list(rows)
        return len(self.rows)

    def replace_owner(self, owner_hash, rows):
        replacement = list(rows)
        self.rows = [row for row in self.rows if row.owner_hash != owner_hash] + replacement
        return len(replacement)

    def replace_all(self, rows):
        self.rows = list(rows)
        return len(self.rows)

    def neighbors(self, skill, *, limit=20):
        return [(row.skill_id, 0.04) for row in self.rows if row.owner_hash != skill.owner_hash][:limit]


class FakeSynthesizer:
    enabled = True

    def synthesize(self, members):
        return SynthesizedSkill(
            title="Loop Boundary Diagnosis",
            name="loop-boundary-diagnosis",
            category="debugging",
            summary="General procedure shared by several users.",
            content=_skill("loop-boundary-diagnosis", "Compare the loop condition with the valid index range."),
        )


class DisabledSynthesizer:
    enabled = False

    def synthesize(self, members):
        return None


def test_personal_skills_are_profile_scoped_and_versioned(monkeypatch, tmp_path):
    hermes_home = tmp_path / "hermes"
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.setenv("SYNCODE_PLATFORM_SKILL_STORE", str(hermes_home / "platform-skills"))
    _write_profile(hermes_home, 7, "loop-helper", "Inspect the left boundary.")
    _write_profile(hermes_home, 8, "loop-helper", "Inspect the right boundary.")
    store = HermesSkillStore()

    user7, errors7 = store.scan_personal(user_id="7", profile="syncode-u7")
    user8, errors8 = store.scan_personal(user_id="8", profile="syncode-u8")
    assert not errors7 and not errors8
    assert "left boundary" in user7[0].content
    assert "right boundary" not in user7[0].content
    assert "right boundary" in user8[0].content

    database_url = f"sqlite+pysqlite:///{tmp_path / 'governance.sqlite3'}"
    _schema(database_url)
    repository = SkillGovernanceRepository(database_url)
    try:
        first = repository.sync_personal_skills(user_id="7", profile="syncode-u7", documents=user7)
        assert first == {"created": 1, "versioned": 1, "unchanged": 0, "archived": 0}
        skill_file = hermes_home / "profiles/syncode-u7/skills/debugging/loop-helper/SKILL.md"
        skill_file.write_text(_skill("loop-helper", "Inspect both boundaries."), encoding="utf-8")
        changed, _ = store.scan_personal(user_id="7", profile="syncode-u7")
        second = repository.sync_personal_skills(user_id="7", profile="syncode-u7", documents=changed)
        assert second["versioned"] == 1
        versions = repository.list_personal_versions(user_id="7", skill_name="loop-helper")
        assert [row["version"] for row in versions] == ["1.0.1", "1.0.0"]
    finally:
        repository.close()


def test_personal_scan_excludes_bundled_and_hub_skills(monkeypatch, tmp_path):
    hermes_home = tmp_path / "hermes"
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.setenv("SYNCODE_PLATFORM_SKILL_STORE", str(hermes_home / "platform-skills"))
    skills_root = hermes_home / "profiles/syncode-u7/skills"
    for category, name in (
        ("builtins", "bundled-helper"),
        ("hub-installs", "hub-helper"),
        ("learned", "agent-helper"),
        ("learned", "taught-helper"),
        ("custom", "handwritten-helper"),
        ("legacy-installs", "stale-hub-helper"),
    ):
        skill_dir = skills_root / category / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(_skill(name, f"Run {name}."), encoding="utf-8")

    (skills_root / ".bundled_manifest").write_text("bundled-helper:sha256-value\n", encoding="utf-8")
    hub_dir = skills_root / ".hub"
    hub_dir.mkdir()
    (hub_dir / "lock.json").write_text(
        json.dumps(
            {
                "version": 1,
                "installed": {
                    "catalog/hub-helper": {"install_path": "hub-installs/hub-helper"},
                },
            }
        ),
        encoding="utf-8",
    )
    (skills_root / ".usage.json").write_text(
        json.dumps(
            {
                "agent-helper": {"created_by": "agent"},
                "taught-helper": {"created_by": "learn"},
                "stale-hub-helper": {"created_by": "installed"},
            }
        ),
        encoding="utf-8",
    )

    documents, errors = HermesSkillStore().scan_personal(user_id="7", profile="syncode-u7")

    assert not errors
    assert {document.name for document in documents} == {
        "agent-helper",
        "taught-helper",
        "handwritten-helper",
    }


def test_external_skills_never_form_cross_user_promotion_candidates(monkeypatch, tmp_path):
    hermes_home = tmp_path / "hermes"
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.setenv("SYNCODE_PLATFORM_SKILL_STORE", str(hermes_home / "platform-skills"))
    monkeypatch.setenv("SYNCODE_SKILL_GOVERNANCE_HASH_SECRET", "test-secret")
    for user_id in (7, 8, 9):
        skills_root = hermes_home / f"profiles/syncode-u{user_id}/skills"
        skill_dir = skills_root / "hub" / "same-downloaded-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            _skill("same-downloaded-skill", "Run the shared downloaded workflow."),
            encoding="utf-8",
        )
        hub_dir = skills_root / ".hub"
        hub_dir.mkdir()
        (hub_dir / "lock.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "installed": {
                        "same-downloaded-skill": {"install_path": "hub/same-downloaded-skill"},
                    },
                }
            ),
            encoding="utf-8",
        )

    database_url = f"sqlite+pysqlite:///{tmp_path / 'external.sqlite3'}"
    _schema(database_url)
    repository = SkillGovernanceRepository(database_url)
    index = FakeIndex()
    service = SkillGovernanceService(
        repository,
        store=HermesSkillStore(),
        index=index,
        synthesizer=FakeSynthesizer(),
    )
    try:
        result = service.heartbeat(min_distinct_owners=3)
        assert result["skills_scanned"] == 0
        assert result["clusters_found"] == 0
        assert result["candidates_created"] == 0
        assert not index.rows
        assert repository.list_promotion_candidates(status="reviewing") == []
    finally:
        repository.close()


def test_provenance_scan_failure_does_not_archive_known_personal_skills(monkeypatch, tmp_path):
    hermes_home = tmp_path / "hermes"
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.setenv("SYNCODE_PLATFORM_SKILL_STORE", str(hermes_home / "platform-skills"))
    _write_profile(hermes_home, 7, "loop-helper", "Inspect the boundary.")
    database_url = f"sqlite+pysqlite:///{tmp_path / 'scan-failure.sqlite3'}"
    _schema(database_url)
    repository = SkillGovernanceRepository(database_url)
    service = SkillGovernanceService(
        repository,
        store=HermesSkillStore(),
        index=FakeIndex(),
        synthesizer=FakeSynthesizer(),
    )
    try:
        service.sync_user(user_id="7", profile="syncode-u7")
        lock_dir = hermes_home / "profiles/syncode-u7/skills/.hub"
        lock_dir.mkdir()
        (lock_dir / "lock.json").write_text("{not-json", encoding="utf-8")

        result = service.sync_user(user_id="7", profile="syncode-u7")

        assert result["scanned"] == 0
        assert result["errors"]
        skills = repository.list_personal_skills(user_id="7")
        assert len(skills) == 1
        assert skills[0]["lifecycle_status"] == "active"
    finally:
        repository.close()


def test_heartbeat_promotes_cross_user_cluster_and_publishes_read_only_source(monkeypatch, tmp_path):
    hermes_home = tmp_path / "hermes"
    platform_root = hermes_home / "platform-skills"
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.setenv("SYNCODE_PLATFORM_SKILL_STORE", str(platform_root))
    monkeypatch.setenv("SYNCODE_SKILL_GOVERNANCE_HASH_SECRET", "test-secret")
    for user_id in (7, 8, 9):
        _write_profile(
            hermes_home,
            user_id,
            f"loop-helper-{user_id}",
            "Compare the loop condition with the valid index range.",
        )

    database_url = f"sqlite+pysqlite:///{tmp_path / 'promotion.sqlite3'}"
    _schema(database_url)
    repository = SkillGovernanceRepository(database_url)
    service = SkillGovernanceService(
        repository,
        store=HermesSkillStore(),
        index=FakeIndex(),
        synthesizer=FakeSynthesizer(),
    )
    try:
        result = service.heartbeat(min_distinct_owners=3)
        assert result["profiles"] == 3
        assert result["clusters_found"] == 1
        assert result["candidates_created"] == 1
        candidates = repository.list_promotion_candidates(status="reviewing")
        assert len(candidates) == 1
        candidate = repository.promotion_candidate(candidates[0]["candidate_id"])
        assert candidate["distinct_owner_count"] == 3
        assert len({member["owner_ref"] for member in candidate["members"]}) == 3
        assert all("skill_id" not in member and "owner_hash" not in member for member in candidate["members"])
        assert all("syncode-u" not in (member["redacted_summary"] or "") for member in candidate["members"])

        published = service.review_promotion(
            candidate_id=candidate["candidate_id"],
            reviewer="admin",
            decision="approve",
            note="Reusable across users.",
        )
        assert published["skill_id"] == "platform:loop-boundary-diagnosis"
        published_file = platform_root / "debugging/loop-boundary-diagnosis/SKILL.md"
        assert published_file.is_file()
        assert repository.list_promotion_candidates(status="published")[0]["published_version"] == "1.0.0"

        changed_content = _skill("loop-boundary-diagnosis", "This write must be rolled back.")
        with pytest.raises(ValueError, match="open promotion candidate"):
            service.review_promotion(
                candidate_id=candidate["candidate_id"],
                reviewer="admin",
                decision="approve",
                note="Duplicate review.",
                content=changed_content,
            )
        assert "This write must be rolled back" not in published_file.read_text(encoding="utf-8")
    finally:
        repository.close()


def test_discovered_candidate_can_be_rejected_without_ai_draft(monkeypatch, tmp_path):
    hermes_home = tmp_path / "hermes"
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.setenv("SYNCODE_PLATFORM_SKILL_STORE", str(hermes_home / "platform-skills"))
    monkeypatch.setenv("SYNCODE_SKILL_GOVERNANCE_HASH_SECRET", "test-secret")
    for user_id in (7, 8, 9):
        _write_profile(
            hermes_home,
            user_id,
            f"loop-helper-{user_id}",
            "Compare the loop condition with the valid index range.",
        )
    database_url = f"sqlite+pysqlite:///{tmp_path / 'discovered.sqlite3'}"
    _schema(database_url)
    repository = SkillGovernanceRepository(database_url)
    service = SkillGovernanceService(
        repository,
        store=HermesSkillStore(),
        index=FakeIndex(),
        synthesizer=DisabledSynthesizer(),
    )
    try:
        result = service.heartbeat(min_distinct_owners=3)
        assert result["clusters_waiting_for_synthesis"] == 1
        candidate = repository.list_promotion_candidates(status="discovered")[0]
        rejected = service.review_promotion(
            candidate_id=candidate["candidate_id"],
            reviewer="admin",
            decision="reject",
            note="Not reusable enough.",
        )
        assert rejected["status"] == "rejected"
    finally:
        repository.close()


def test_platform_archive_is_restored_when_review_persistence_fails(monkeypatch, tmp_path):
    hermes_home = tmp_path / "hermes"
    platform_root = hermes_home / "platform-skills"
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.setenv("SYNCODE_PLATFORM_SKILL_STORE", str(platform_root))
    database_url = f"sqlite+pysqlite:///{tmp_path / 'archive-compensation.sqlite3'}"
    _schema(database_url)
    repository = SkillGovernanceRepository(database_url)
    store = HermesSkillStore()
    store.publish_platform(
        name="loop-helper",
        category="debugging",
        package={"SKILL.md": _skill("loop-helper", "Inspect the boundary.")},
    )
    service = SkillGovernanceService(
        repository,
        store=store,
        index=FakeIndex(),
        synthesizer=FakeSynthesizer(),
    )
    monkeypatch.setattr(
        repository,
        "list_lifecycle_reviews",
        lambda **_kwargs: [{"review_id": "review-1", "skill_name": "loop-helper"}],
    )

    def fail_review(**_kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(repository, "finish_lifecycle_review", fail_review)
    try:
        with pytest.raises(RuntimeError, match="database unavailable"):
            service.review_lifecycle(
                review_id="review-1",
                reviewer="admin",
                decision="archive",
                note=None,
            )
        assert (platform_root / "debugging/loop-helper/SKILL.md").is_file()
    finally:
        repository.close()


def test_low_usage_platform_skill_enters_configurable_review_queue(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'low-usage.sqlite3'}"
    _schema(database_url)
    repository = SkillGovernanceRepository(database_url)
    try:
        with repository.engine.begin() as connection:
            connection.exec_driver_sql(
                """INSERT INTO tb_ai_skill (
                    skill_id, skill_name, display_name, scope, owner_user_id, lifecycle_status,
                    current_version, create_time, update_time
                ) VALUES (
                    'platform:rare-helper', 'rare-helper', 'Rare helper', 'platform', 0, 'active',
                    '1.0.0', datetime('now', '-40 days'), datetime('now', '-40 days')
                )"""
            )
            connection.exec_driver_sql(
                """INSERT INTO tb_ai_skill_usage_event (
                    event_id, user_id, skill_name, skill_version, event_type, occurred_at
                ) VALUES ('event-1', 7, 'rare-helper', '1.0.0', 'skill.invoked', CURRENT_TIMESTAMP)"""
            )

        assert repository.refresh_lifecycle_reviews(stale_days=30, max_usage=0) == 0
        assert repository.refresh_lifecycle_reviews(stale_days=30, max_usage=1) == 1
        reviews = repository.list_lifecycle_reviews(status="pending")
        assert reviews[0]["usage_count_30d"] == 1
        assert "At most 1" in reviews[0]["reason"]
    finally:
        repository.close()


def test_governance_heartbeat_rejects_concurrent_runs(tmp_path):
    database_url = f"sqlite+pysqlite:///{tmp_path / 'heartbeat-lock.sqlite3'}"
    _schema(database_url)
    repository = SkillGovernanceRepository(database_url)
    service = SkillGovernanceService(
        repository,
        store=HermesSkillStore(),
        index=FakeIndex(),
        synthesizer=FakeSynthesizer(),
    )
    service._heartbeat_lock.acquire()
    try:
        with pytest.raises(ValueError, match="already running"):
            service.heartbeat()
    finally:
        service._heartbeat_lock.release()
        repository.close()


def test_personal_archive_restore_and_rollback(monkeypatch, tmp_path):
    hermes_home = tmp_path / "hermes"
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.setenv("SYNCODE_PLATFORM_SKILL_STORE", str(hermes_home / "platform-skills"))
    _write_profile(hermes_home, 7, "loop-helper", "Inspect the original boundary.")
    database_url = f"sqlite+pysqlite:///{tmp_path / 'lifecycle.sqlite3'}"
    _schema(database_url)
    repository = SkillGovernanceRepository(database_url)
    service = SkillGovernanceService(repository, store=HermesSkillStore(), index=FakeIndex(), synthesizer=FakeSynthesizer())
    try:
        service.sync_user(user_id="7", profile="syncode-u7")
        skill_file = hermes_home / "profiles/syncode-u7/skills/debugging/loop-helper/SKILL.md"
        skill_file.write_text(_skill("loop-helper", "Inspect the changed boundary."), encoding="utf-8")
        service.sync_user(user_id="7", profile="syncode-u7")
        service.rollback_user_skill(user_id="7", profile="syncode-u7", name="loop-helper", version="1.0.0")
        restored = next((hermes_home / "profiles/syncode-u7/skills").rglob("loop-helper/SKILL.md"))
        assert "original boundary" in restored.read_text(encoding="utf-8")
        service.archive_user_skill(user_id="7", profile="syncode-u7", name="loop-helper")
        assert repository.list_personal_skills(user_id="7")[0]["lifecycle_status"] == "archived"
        service.restore_user_skill(user_id="7", profile="syncode-u7", name="loop-helper")
        assert repository.list_personal_skills(user_id="7")[0]["lifecycle_status"] == "active"
    finally:
        repository.close()


def test_bundled_skill_upgrade_respects_declared_versions(monkeypatch, tmp_path):
    hermes_home = tmp_path / "hermes"
    platform_root = hermes_home / "platform-skills"
    source_root = tmp_path / "bundled"
    monkeypatch.setenv("HERMES_HOME", str(hermes_home))
    monkeypatch.setenv("SYNCODE_PLATFORM_SKILL_STORE", str(platform_root))

    source_skill = source_root / "education" / "memory-helper" / "SKILL.md"
    source_skill.parent.mkdir(parents=True)
    source_skill.write_text(
        "---\nname: memory-helper\ndescription: Recall learning history.\nversion: 1.0.0\n---\n\nOld instructions.\n",
        encoding="utf-8",
    )
    store = HermesSkillStore()
    assert store.seed_platform_skills(source_root) == 1

    source_skill.write_text(
        "---\nname: memory-helper\ndescription: Recall learning history.\nversion: 1.1.0\n---\n\nNew instructions.\n",
        encoding="utf-8",
    )
    assert store.seed_platform_skills(source_root) == 1
    deployed = platform_root / "education" / "memory-helper" / "SKILL.md"
    assert "New instructions" in deployed.read_text(encoding="utf-8")

    deployed.write_text(
        "---\nname: memory-helper\ndescription: Administrator-owned content.\n---\n\nKeep this content.\n",
        encoding="utf-8",
    )
    source_skill.write_text(
        "---\nname: memory-helper\ndescription: Recall learning history.\nversion: 1.2.0\n---\n\nBundled update.\n",
        encoding="utf-8",
    )
    assert store.seed_platform_skills(source_root) == 0
    assert "Keep this content" in deployed.read_text(encoding="utf-8")
