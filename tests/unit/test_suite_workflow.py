"""Library suite workflow (shared by CLI and API)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from agenteval.planning.models import ObservationBundle, SuiteRunReport, TestCaseResult
from agenteval.services.suite_workflow import SuiteWorkflow

SAMPLE_PRD = """# Demo Agent

## Functional requirements

1. The agent must greet the user by name when asked.
"""


def test_run_suite_requires_endpoint(tmp_path: Path) -> None:
    workflow = SuiteWorkflow(suite_root=tmp_path / "suites")
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
    workflow = SuiteWorkflow(suite_root=tmp_path / "suites")
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
