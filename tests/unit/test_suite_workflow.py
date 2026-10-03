"""Library suite workflow (shared by CLI and API)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from agenteval.db.suite_repository import SuiteRepository
from agenteval.ingest.requirements import RequirementsIngestor
from agenteval.planning.models import ObservationBundle, SuiteRunReport, TestCaseResult
from agenteval.services.suite_workflow import SuiteWorkflow

SAMPLE_PRD = """# Demo Agent

## Functional requirements

1. The agent must greet the user by name when asked.
"""


def test_run_suite_requires_endpoint(tmp_path: Path) -> None:
    workflow = SuiteWorkflow(suite_root=tmp_path / "suites", use_sqlite=False)
    workflow.init_from_prd_text(
        SAMPLE_PRD,
        agent_id="demo-agent",
        force_new_version=True,
    )
    try:
        workflow.run_suite("demo-agent")
    except ValueError as exc:
        assert "endpoint" in str(exc).lower()
    else:
        raise AssertionError("expected ValueError")


@patch("agenteval.services.suite_workflow.BlackboxRunner")
def test_run_suite_saves_latest(mock_runner_cls: MagicMock, tmp_path: Path) -> None:
    workflow = SuiteWorkflow(suite_root=tmp_path / "suites", use_sqlite=False)
    workflow.init_from_prd_text(
        SAMPLE_PRD,
        agent_id="demo-agent",
        endpoint_url="http://127.0.0.1:9/chat",
        force_new_version=True,
    )

    observation = ObservationBundle(
        test_id="t1",
        user_prompt="hi",
        response_text="hello",
    )
    mock_runner_cls.return_value.run_pack.return_value = SuiteRunReport(
        agent_id="demo-agent",
        run_id="run-abc",
        suite_version=1,
        results=[
            TestCaseResult(
                test_id="t1",
                verdict="PASS",
                observation=observation,
            )
        ],
        passed=1,
        failed=0,
        unverifiable=0,
    )

    report = workflow.run_suite("demo-agent")
    assert report.run_id == "run-abc"
    latest = workflow.latest_run("demo-agent")
    assert latest is not None
    assert latest.run_id == "run-abc"


@patch("agenteval.services.suite_workflow.BlackboxRunner")
def test_sqlite_primary_skips_filesystem_on_init_and_run(
    mock_runner_cls: MagicMock, tmp_path: Path
) -> None:
    db_path = tmp_path / "agenteval.db"
    workflow = SuiteWorkflow(
        suite_root=tmp_path / "suites",
        use_sqlite=True,
        db_path=db_path,
    )
    workflow.init_from_prd_text(
        SAMPLE_PRD,
        agent_id="demo-agent",
        endpoint_url="http://127.0.0.1:9/chat",
        force_new_version=True,
    )

    observation = ObservationBundle(
        test_id="t1",
        user_prompt="hi",
        response_text="hello",
    )
    mock_runner_cls.return_value.run_pack.return_value = SuiteRunReport(
        agent_id="demo-agent",
        run_id="run-sql",
        suite_version=1,
        results=[
            TestCaseResult(
                test_id="t1",
                verdict="PASS",
                observation=observation,
            )
        ],
        passed=1,
        failed=0,
        unverifiable=0,
    )

    suite_dir = tmp_path / "suites" / "demo-agent"
    assert not (suite_dir / "suite.manifest.json").exists()

    workflow.run_suite("demo-agent")
    repo = SuiteRepository(db_path)
    loaded = repo.load_latest_run("demo-agent")
    assert loaded is not None
    assert loaded.run_id == "run-sql"
    assert repo.load_requirements_text("demo-agent") == SAMPLE_PRD
    repo.close()
    assert not (suite_dir / "latest_run.json").exists()


PRD_TWO_CAPS = """# Sync Agent

## Capabilities
- Issue Refund: Refund orders for customers
- Lookup Order: Find order status by id
"""

PRD_ONE_CAP = """# Sync Agent

## Capabilities
- Issue Refund: Refund orders for customers only
"""


def test_sqlite_sync_prunes_removed_capability(tmp_path: Path) -> None:
    db_path = tmp_path / "agenteval.db"
    workflow = SuiteWorkflow(
        suite_root=tmp_path / "suites",
        use_sqlite=True,
        db_path=db_path,
        max_tests=12,
    )
    workflow.init_from_prd_text(
        PRD_TWO_CAPS,
        agent_id="sync-agent",
        endpoint_url="http://127.0.0.1:9/chat",
        force_new_version=True,
    )
    before = workflow.get_suite("sync-agent")
    assert before.manifest.version == 1
    card_two = RequirementsIngestor.from_text(PRD_TWO_CAPS, agent_id="sync-agent")
    lookup_cap_id = card_two.capabilities[1].requirement_id()
    lookup_caps = [
        t.capability_id for t in before.optimized_pack.tests if t.capability_id == lookup_cap_id
    ]
    assert lookup_caps

    result = workflow.sync_from_prd_text(
        "sync-agent",
        PRD_ONE_CAP,
        endpoint_url="http://127.0.0.1:9/chat",
    )
    assert not result.noop
    assert lookup_cap_id in result.removed_capabilities
    assert result.new_version == 2

    after = workflow.get_suite("sync-agent")
    assert after.manifest.version == 2
    assert not any(t.capability_id == lookup_cap_id for t in after.optimized_pack.tests)
    assert after.requirements_text == PRD_ONE_CAP


@patch("agenteval.services.suite_workflow.BlackboxRunner")
def test_extend_gaps_from_latest_run_sqlite(mock_runner_cls: MagicMock, tmp_path: Path) -> None:
    db_path = tmp_path / "agenteval.db"
    workflow = SuiteWorkflow(
        suite_root=tmp_path / "suites",
        use_sqlite=True,
        db_path=db_path,
        max_tests=3,
    )
    workflow.init_from_prd_text(
        PRD_TWO_CAPS,
        agent_id="gap-wf",
        endpoint_url="http://127.0.0.1:9/chat",
        force_new_version=True,
    )
    pack_before = workflow.get_suite("gap-wf").optimized_pack
    observation = ObservationBundle(
        test_id=pack_before.tests[0].id,
        user_prompt="x",
        response_text="y",
    )
    mock_runner_cls.return_value.run_pack.return_value = SuiteRunReport(
        agent_id="gap-wf",
        run_id="run-gap",
        suite_version=1,
        results=[
            TestCaseResult(
                test_id=t.id,
                verdict="PASS",
                observation=observation,
            )
            for t in pack_before.tests
        ],
        passed=len(pack_before.tests),
        failed=0,
        unverifiable=0,
    )
    workflow.run_suite("gap-wf")

    extend = workflow.extend_gaps_from_latest_run("gap-wf", max_add=2)
    assert not extend.noop
    assert extend.new_version == 2
    after = workflow.get_suite("gap-wf")
    assert len(after.optimized_pack.tests) > len(pack_before.tests)


def test_init_persists_requirements_text_sqlite(tmp_path: Path) -> None:
    db_path = tmp_path / "agenteval.db"
    workflow = SuiteWorkflow(
        suite_root=tmp_path / "suites",
        use_sqlite=True,
        db_path=db_path,
    )
    workflow.init_from_prd_text(
        SAMPLE_PRD,
        agent_id="prd-agent",
        endpoint_url="http://127.0.0.1/chat",
        force_new_version=True,
    )
    detail = workflow.get_suite("prd-agent")
    assert detail.requirements_text == SAMPLE_PRD
    assert len(detail.optimized_pack.tests) >= 1


def test_delete_suite_filesystem(tmp_path: Path) -> None:
    suite_root = tmp_path / "suites"
    workflow = SuiteWorkflow(suite_root=suite_root, use_sqlite=False)
    workflow.init_from_prd_text(
        SAMPLE_PRD,
        agent_id="del-agent",
        endpoint_url="http://127.0.0.1/chat",
        force_new_version=True,
    )
    assert any(s.agent_id == "del-agent" for s in workflow.list_suites())
    assert workflow.delete_suite("del-agent") is True
    assert not any(s.agent_id == "del-agent" for s in workflow.list_suites())
    # Calling delete again raises FileNotFoundError
    import pytest

    with pytest.raises(FileNotFoundError):
        workflow.delete_suite("del-agent")


def test_delete_suite_sqlite(tmp_path: Path) -> None:
    suite_root = tmp_path / "suites"
    db_path = tmp_path / "test.db"
    workflow = SuiteWorkflow(suite_root=suite_root, use_sqlite=True, db_path=db_path)
    workflow.init_from_prd_text(
        SAMPLE_PRD,
        agent_id="sql-agent",
        endpoint_url="http://127.0.0.1/chat",
        force_new_version=True,
    )
    assert any(s.agent_id == "sql-agent" for s in workflow.list_suites())
    assert workflow.delete_suite("sql-agent") is True
    assert not any(s.agent_id == "sql-agent" for s in workflow.list_suites())
    import pytest

    with pytest.raises(FileNotFoundError):
        workflow.delete_suite("sql-agent")
