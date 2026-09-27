"""Persist Inspect-compatible run archive when inspect-ai extra is available (ADR-005 slice 5a)."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from agenteval.planning.models import SuiteRunReport, TestPack


def inspect_extra_available() -> bool:
    try:
        import importlib.util

        return importlib.util.find_spec("inspect_ai") is not None
    except ImportError:
        return False


def write_run_archive(
    report: SuiteRunReport,
    pack: TestPack,
    *,
    output_dir: Path,
) -> tuple[str, str]:
    """
    Write a minimal JSON archive for the run. Returns (absolute_path, sha256_hex).

    When inspect-ai is installed, tags the payload for future EvalLog import; otherwise
    stores an AgentEval-native sidecar (honest, not a fake Inspect file).
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "inspect_sidecar.json"
    payload = {
        "agenteval_version": "sidecar-5a",
        "inspect_ai_present": inspect_extra_available(),
        "generated_at": datetime.now(UTC).isoformat(),
        "run_id": report.run_id,
        "agent_id": report.agent_id,
        "suite_version": report.suite_version,
        "summary": {
            "passed": report.passed,
            "failed": report.failed,
            "unverifiable": report.unverifiable,
        },
        "samples": [
            {
                "test_id": r.test_id,
                "verdict": r.verdict,
                "rationale": r.rationale,
            }
            for r in report.results
        ],
        "pack_test_ids": [t.id for t in pack.tests],
    }
    body = json.dumps(payload, indent=2, sort_keys=True)
    path.write_text(body, encoding="utf-8")
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return str(path.resolve()), digest
