"""Import frozen suites and run JSON from SuiteStore into SQLite."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from agenteval.db.suite_repository import SuiteRepository
from agenteval.planning.execution_trace import build_blackbox_trajectory
from agenteval.planning.models import SuiteRunReport, TestCaseResult
from agenteval.planning.suite_store import SuiteStore


class SuiteImportResult(BaseModel):
    """Outcome of a filesystem → SQLite import."""

    model_config = ConfigDict(extra="forbid")

    agents_imported: int = 0
    runs_imported: int = 0
    execution_steps_imported: int = 0
    agent_ids: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


def _backfill_trajectories(report: SuiteRunReport) -> SuiteRunReport:
    """Derive sealed steps for legacy run JSON that predates trajectory persistence."""
    results: list[TestCaseResult] = []
    for result in report.results:
        if result.trajectory:
            results.append(result)
            continue
        trajectory = build_blackbox_trajectory(
            result.observation,
            result.verdict,
            result.rationale,
        )
        results.append(result.model_copy(update={"trajectory": trajectory}))
    return report.model_copy(update={"results": results})


def _collect_run_reports(
    store: SuiteStore, agent_id: str
) -> list[SuiteRunReport]:
    seen: set[str] = set()
    reports: list[SuiteRunReport] = []

    runs_dir = store.agent_dir(agent_id) / "runs"
    if runs_dir.is_dir():
        for path in sorted(runs_dir.glob("*.json")):
            report = _backfill_trajectories(
                SuiteRunReport.model_validate_json(path.read_text(encoding="utf-8"))
            )
            if report.run_id in seen:
                continue
            seen.add(report.run_id)
            reports.append(report)

    latest = store.load_latest_run(agent_id)
    if latest is not None and latest.run_id not in seen:
        reports.append(_backfill_trajectories(latest))

    return reports


def import_suites_from_filesystem(
    suite_root: Path | str = ".agenteval/suites",
    db_path: Path | str | None = None,
    *,
    force: bool = True,
) -> SuiteImportResult:
    """Load every agent under ``suite_root`` into SQLite (ADR-004 migration)."""
    store = SuiteStore(suite_root)
    repo = SuiteRepository(db_path)
    result = SuiteImportResult()

    try:
        for agent_id in store.list_agent_ids():
            try:
                manifest = store.load_manifest(agent_id)
                pack = store.load_pack(agent_id)
                pool = store.load_pool(agent_id)
                card_path = store.agent_dir(agent_id) / "derived_agent_card.json"
                agent_card_json = (
                    card_path.read_text(encoding="utf-8")
                    if card_path.is_file()
                    else None
                )
                repo.init_suite(
                    manifest,
                    pool,
                    pack,
                    force=force,
                    agent_card_json=agent_card_json,
                )
                endpoint = manifest.endpoint_profile or "import://unknown"
                for report in _collect_run_reports(store, agent_id):
                    repo.save_run(agent_id, report, endpoint_url=endpoint)
                    result.runs_imported += 1
                    result.execution_steps_imported += sum(
                        len(r.trajectory) for r in report.results
                    )

                result.agents_imported += 1
                result.agent_ids.append(agent_id)
            except (OSError, ValueError, FileNotFoundError, ValidationError) as exc:
                result.errors.append(f"{agent_id}: {exc}")
    finally:
        repo.close()

    return result
