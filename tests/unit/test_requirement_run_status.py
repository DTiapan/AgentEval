"""FR-B-17 rollup helper."""

from agenteval.services.requirement_run_status import _criterion_status, _worst_status


def test_criterion_status_mapping() -> None:
    assert _criterion_status("PASS") == "proven"
    assert _criterion_status("FAIL") == "failing"
    assert _criterion_status("UNVERIFIABLE") == "unverifiable"
    assert _criterion_status(None) == "untested"


def test_worst_status_prefers_failing() -> None:
    assert _worst_status(["proven", "failing"]) == "failing"
