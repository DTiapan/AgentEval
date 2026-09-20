"""Filesystem → SQLite suite import."""

from pathlib import Path

from agenteval.db.import_suites import import_suites_from_filesystem
from agenteval.db.suite_repository import SuiteRepository
from agenteval.planning.execution_trace import build_blackbox_trajectory
from agenteval.planning.models import ObservationBundle, SuiteRunReport, TestCaseResult
from agenteval.planning.suite_store import SuiteStore


def test_import_suites_from_filesystem(tmp_path: Path) -> None:
    suite_root = tmp_path / "suites"
    db_path = tmp_path / "agenteval.db"
    store = SuiteStore(suite_root)
    manifest = SuiteStore.new_manifest("import-me", "fp", "http://127.0.0.1/chat")

    from agenteval.planning.models import CandidateTest, TestPack

    test = CandidateTest(
        id="t1",
        capability_id="c",
        persona_id="p",
        name="n",
        user_prompt="hi",
        expected_behavior="ok",
    )
    pack = TestPack(
        agent_id="import-me",
        version=1,
        tests=[test],
        candidate_count=1,
        requirements_fingerprint="fp",
    )
    store.init_suite(manifest, [test], pack, force=True)

    obs = ObservationBundle(
        test_id="t1",
        user_prompt="hi",
        response_text="hey",
        http_status=200,
        latency_ms=1.0,
    )
    trajectory = build_blackbox_trajectory(obs, "PASS", "ok")
    report = SuiteRunReport(
        agent_id="import-me",
        run_id="run-import",
        suite_version=1,
        results=[
            TestCaseResult(
                test_id="t1",
                verdict="PASS",
                observation=obs,
                trajectory=trajectory,
            )
        ],
        passed=1,
        failed=0,
        unverifiable=0,
    )
    store.save_run("import-me", report)

    result = import_suites_from_filesystem(suite_root, db_path)
    assert result.agents_imported == 1
    assert result.runs_imported == 1
    assert result.execution_steps_imported == len(trajectory)
    assert result.errors == []

    repo = SuiteRepository(db_path)
    loaded = repo.load_run("import-me", "run-import")
    repo.close()
    assert loaded is not None
    assert len(loaded.results[0].trajectory) == len(trajectory)


def test_import_backfills_legacy_runs_without_trajectory(tmp_path: Path) -> None:
    suite_root = tmp_path / "suites"
    db_path = tmp_path / "agenteval.db"
    store = SuiteStore(suite_root)
    from agenteval.planning.models import CandidateTest, TestPack

    test = CandidateTest(
        id="t1",
        capability_id="c",
        persona_id="p",
        name="n",
        user_prompt="hi",
        expected_behavior="ok",
    )
    pack = TestPack(
        agent_id="legacy",
        version=1,
        tests=[test],
        candidate_count=1,
        requirements_fingerprint="fp",
    )
    manifest = SuiteStore.new_manifest("legacy", "fp", "http://127.0.0.1/chat")
    store.init_suite(manifest, [test], pack, force=True)

    legacy_json = """{
      "agent_id": "legacy",
      "run_id": "legacy-run",
      "suite_version": 1,
      "results": [{
        "test_id": "t1",
        "verdict": "PASS",
        "observation": {
          "test_id": "t1",
          "user_prompt": "hi",
          "response_text": "hey",
          "http_status": 200,
          "latency_ms": 2.0
        },
        "rationale": "ok"
      }],
      "passed": 1,
      "failed": 0,
      "unverifiable": 0
    }"""
    runs = store.agent_dir("legacy") / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    (runs / "legacy-run.json").write_text(legacy_json, encoding="utf-8")

    result = import_suites_from_filesystem(suite_root, db_path)
    assert result.execution_steps_imported > 0
    repo = SuiteRepository(db_path)
    loaded = repo.load_run("legacy", "legacy-run")
    repo.close()
    assert loaded is not None
    assert len(loaded.results[0].trajectory) > 0
