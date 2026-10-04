"""SQLite persistence mirroring SuiteStore for runs and frozen suites."""

import json
import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast
from urllib.parse import urlparse

if TYPE_CHECKING:
    from agenteval.services.requirement_run_status import AssuranceSignoffContext

from agenteval.db.config import (
    DEFAULT_WORKSPACE_ID,
    DEFAULT_WORKSPACE_NAME,
    DEFAULT_WORKSPACE_SLUG,
    database_path,
)
from agenteval.db.connection import connect, init_schema
from agenteval.db.normalized_suite import (
    count_criterion_verdicts_for_run,
    enrich_run_report,
    load_requirements_for_suite,
    load_suite_requirements_result,
    load_test_cases_for_suite,
    persist_normalized_suite,
    persist_run_evidence_and_verdicts,
)
from agenteval.domain.models import FrozenTestCaseRecord, RequirementRecord
from agenteval.planning.models import (
    CandidateTest,
    ExecutionStep,
    ObservationBundle,
    SuiteManifest,
    SuiteRequirementsResult,
    SuiteRunReport,
    TestCaseResult,
    TestPack,
)
from agenteval.planning.suite_store import SuiteExistsError
from agenteval.telemetry import start_span


class SuiteRepository:
    """Relational store for suite versions and assurance runs."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else database_path()
        self._conn = connect(self.db_path)
        self._write_lock = threading.RLock()
        init_schema(self._conn)
        self._ensure_default_workspace()

    def close(self) -> None:
        self._conn.close()

    def list_agent_ids(self) -> list[str]:
        rows = self._conn.execute(
            "SELECT id FROM agents WHERE workspace_id = ? ORDER BY id",
            (DEFAULT_WORKSPACE_ID,),
        ).fetchall()
        return [str(row["id"]) for row in rows]

    def delete_agent(self, agent_id: str) -> bool:
        exists = self._conn.execute(
            "SELECT 1 FROM agents WHERE id = ?",
            (agent_id,),
        ).fetchone()
        if exists is None:
            return False

        with self._conn:
            version_rows = self._conn.execute(
                "SELECT id FROM suite_versions WHERE agent_id = ?",
                (agent_id,),
            ).fetchall()
            version_ids = [str(r["id"]) for r in version_rows]

            self._conn.execute(
                "DELETE FROM assurance_runs WHERE agent_id = ?",
                (agent_id,),
            )

            if version_ids:
                placeholders = ",".join("?" for _ in version_ids)
                self._conn.execute(
                    f"DELETE FROM suite_pack_selections WHERE suite_version_id IN ({placeholders})",
                    version_ids,
                )
                self._conn.execute(
                    f"DELETE FROM test_cases WHERE suite_version_id IN ({placeholders})",
                    version_ids,
                )
                self._conn.execute(
                    f"DELETE FROM requirements WHERE suite_version_id IN ({placeholders})",
                    version_ids,
                )

            self._conn.execute(
                "DELETE FROM agents WHERE id = ?",
                (agent_id,),
            )
        return True

    def init_suite(
        self,
        manifest: SuiteManifest,
        pool: list[CandidateTest],
        pack: TestPack,
        *,
        force: bool = False,
        agent_card_json: str | None = None,
        requirements_text: str = "",
        enabled_domain_packs: list[str] | None = None,
    ) -> None:
        with start_span(
            "db.sqlite.operation",
            attributes={
                "db.system": "sqlite",
                "db.operation": "init_suite",
                "agenteval.agent_id": manifest.agent_id,
                "agenteval.force": force,
            },
        ):
            agent_id = manifest.agent_id
            exists = self._conn.execute(
                "SELECT 1 FROM agents WHERE id = ?",
                (agent_id,),
            ).fetchone()
            if exists is not None and not force:
                raise SuiteExistsError(
                    f"Suite already exists for agent '{agent_id}' in database. Use force to replace."
                )

            now = datetime.now(UTC).isoformat()
            with self._conn:
                self._ensure_default_workspace()
                self._conn.execute(
                    """
                    INSERT INTO agents (id, workspace_id, slug, display_name, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        display_name = excluded.display_name
                    """,
                    (
                        agent_id,
                        DEFAULT_WORKSPACE_ID,
                        agent_id,
                        agent_id,
                        now,
                    ),
                )
                suite_version_id = self._suite_version_id(agent_id, manifest.version)
                self._conn.execute(
                    """
                    INSERT INTO suite_versions (
                        id, agent_id, version, requirements_fingerprint,
                        requirements_text, endpoint_profile, pack_json,
                        candidate_pool_json, agent_card_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(agent_id, version) DO UPDATE SET
                        requirements_fingerprint = excluded.requirements_fingerprint,
                        requirements_text = excluded.requirements_text,
                        endpoint_profile = excluded.endpoint_profile,
                        pack_json = excluded.pack_json,
                        candidate_pool_json = excluded.candidate_pool_json,
                        agent_card_json = excluded.agent_card_json,
                        created_at = excluded.created_at
                    """,
                    (
                        suite_version_id,
                        agent_id,
                        manifest.version,
                        manifest.requirements_fingerprint,
                        requirements_text,
                        manifest.endpoint_profile,
                        pack.model_dump_json(),
                        json.dumps([t.model_dump() for t in pool]),
                        agent_card_json,
                        manifest.created_at or now,
                    ),
                )
                persist_normalized_suite(
                    self._conn,
                    suite_version_id,
                    pack,
                    agent_card_json=agent_card_json,
                    enabled_domain_packs=enabled_domain_packs,
                )

    def load_normalized_requirements(self, agent_id: str) -> list[RequirementRecord]:
        row = self._latest_suite_row(agent_id)
        if row is None:
            raise FileNotFoundError(f"No suite in database for agent '{agent_id}'")
        return load_requirements_for_suite(self._conn, str(row["id"]))

    def load_normalized_test_cases(self, agent_id: str) -> list[FrozenTestCaseRecord]:
        row = self._latest_suite_row(agent_id)
        if row is None:
            raise FileNotFoundError(f"No suite in database for agent '{agent_id}'")
        return load_test_cases_for_suite(self._conn, str(row["id"]))

    def load_requirements_result(self, agent_id: str) -> SuiteRequirementsResult | None:
        row = self._latest_suite_row(agent_id)
        if row is None:
            raise FileNotFoundError(f"No suite in database for agent '{agent_id}'")
        return load_suite_requirements_result(
            self._conn,
            agent_id,
            str(row["id"]),
            int(row["version"]),
        )

    def enrich_run_report(self, report: SuiteRunReport) -> SuiteRunReport:
        return enrich_run_report(self._conn, report)

    def load_signoff_context(
        self, agent_id: str, suite_version: int, run_id: str
    ) -> "AssuranceSignoffContext | None":
        from agenteval.services.requirement_run_status import build_assurance_signoff_context

        row = self._conn.execute(
            """
            SELECT id FROM suite_versions
            WHERE agent_id = ? AND version = ?
            """,
            (agent_id, suite_version),
        ).fetchone()
        if row is None:
            return None
        return build_assurance_signoff_context(self._conn, str(row["id"]), run_id)

    def load_agent_card_json(self, agent_id: str) -> str | None:
        row = self._latest_suite_row(agent_id)
        if row is None:
            return None
        raw = row["agent_card_json"]
        return str(raw) if raw else None

    def load_requirements_text(self, agent_id: str) -> str:
        row = self._latest_suite_row(agent_id)
        if row is None:
            raise FileNotFoundError(f"No suite in database for agent '{agent_id}'")
        return str(row["requirements_text"] or "")

    def load_manifest(self, agent_id: str) -> SuiteManifest:
        row = self._latest_suite_row(agent_id)
        if row is None:
            raise FileNotFoundError(f"No suite in database for agent '{agent_id}'")
        return SuiteManifest(
            agent_id=agent_id,
            version=int(row["version"]),
            requirements_fingerprint=str(row["requirements_fingerprint"]),
            created_at=str(row["created_at"]),
            endpoint_profile=str(row["endpoint_profile"] or ""),
        )

    def load_pack(self, agent_id: str) -> TestPack:
        row = self._latest_suite_row(agent_id)
        if row is None:
            raise FileNotFoundError(f"No suite in database for agent '{agent_id}'")
        return TestPack.model_validate_json(str(row["pack_json"]))

    def load_pool(self, agent_id: str) -> list[CandidateTest]:
        row = self._latest_suite_row(agent_id)
        if row is None:
            raise FileNotFoundError(f"No suite in database for agent '{agent_id}'")
        raw = row["candidate_pool_json"]
        if not raw:
            return []
        items = json.loads(str(raw))
        return [CandidateTest.model_validate(item) for item in items]

    def apply_sync(
        self,
        manifest: SuiteManifest,
        pool: list[CandidateTest],
        pack: TestPack,
        *,
        requirements_text: str = "",
        agent_card_json: str | None = None,
        enabled_domain_packs: list[str] | None = None,
    ) -> None:
        """Append a new frozen suite version after explicit spec drift sync (DR-011)."""
        agent_id = manifest.agent_id
        if self._latest_suite_row(agent_id) is None:
            raise FileNotFoundError(f"No suite in database for agent '{agent_id}'")

        now = datetime.now(UTC).isoformat()
        suite_version_id = self._suite_version_id(agent_id, manifest.version)
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO suite_versions (
                    id, agent_id, version, requirements_fingerprint,
                    requirements_text, endpoint_profile, pack_json,
                    candidate_pool_json, agent_card_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(agent_id, version) DO UPDATE SET
                    requirements_fingerprint = excluded.requirements_fingerprint,
                    requirements_text = excluded.requirements_text,
                    endpoint_profile = excluded.endpoint_profile,
                    pack_json = excluded.pack_json,
                    candidate_pool_json = excluded.candidate_pool_json,
                    agent_card_json = excluded.agent_card_json,
                    created_at = excluded.created_at
                """,
                (
                    suite_version_id,
                    agent_id,
                    manifest.version,
                    manifest.requirements_fingerprint,
                    requirements_text,
                    manifest.endpoint_profile,
                    pack.model_dump_json(),
                    json.dumps([t.model_dump() for t in pool]),
                    agent_card_json,
                    now,
                ),
            )
            persist_normalized_suite(
                self._conn,
                suite_version_id,
                pack,
                agent_card_json=agent_card_json,
                enabled_domain_packs=enabled_domain_packs,
            )

    def ensure_default_target(self, agent_id: str, endpoint_url: str) -> str | None:
        """
        Ensure a v002 HTTP transport target exists for ``endpoint_url``.

        Returns target id when the ``targets`` table exists; otherwise ``None``.
        """
        row = self._conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'targets'"
        ).fetchone()
        if row is None:
            return None

        existing = self._conn.execute(
            "SELECT id FROM targets WHERE agent_id = ? ORDER BY created_at LIMIT 1",
            (agent_id,),
        ).fetchone()
        if existing is not None:
            return str(existing["id"])

        parsed = urlparse(endpoint_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            endpoint_url = endpoint_url if endpoint_url.startswith("import://") else endpoint_url
        now = datetime.now(UTC).isoformat()
        connector_id = f"{agent_id}-http-transport"
        target_id = f"{agent_id}-default-target"
        config = json.dumps({"url": endpoint_url, "method": "POST"})
        with self._conn:
            self._ensure_default_workspace()
            self._conn.execute(
                """
                INSERT OR IGNORE INTO connectors (
                    id, workspace_id, slug, kind, config_json, created_at
                ) VALUES (?, ?, ?, 'http_transport', ?, ?)
                """,
                (
                    connector_id,
                    DEFAULT_WORKSPACE_ID,
                    f"{agent_id}-http",
                    config,
                    now,
                ),
            )
            self._conn.execute(
                """
                INSERT OR IGNORE INTO targets (
                    id, workspace_id, agent_id, environment_id,
                    display_name, transport_connector_id, created_at
                ) VALUES (?, ?, ?, NULL, ?, ?, ?)
                """,
                (
                    target_id,
                    DEFAULT_WORKSPACE_ID,
                    agent_id,
                    f"{agent_id} default",
                    connector_id,
                    now,
                ),
            )
        return target_id

    def initialize_run(
        self,
        agent_id: str,
        run_id: str,
        suite_version: int,
        *,
        endpoint_url: str,
    ) -> str:
        """Initialize an assurance run row in 'running' state with zero tallies."""
        row = self._conn.execute(
            """
            SELECT id FROM suite_versions
            WHERE agent_id = ? AND version = ?
            """,
            (agent_id, suite_version),
        ).fetchone()
        if row is None:
            raise FileNotFoundError(
                f"No suite version {suite_version} for agent '{agent_id}'"
            )
        suite_version_id = str(row["id"])
        now = datetime.now(UTC).isoformat()
        target_id = self.ensure_default_target(agent_id, endpoint_url)
        has_target_column = self._conn.execute(
            "SELECT 1 FROM pragma_table_info('assurance_runs') WHERE name = 'target_id'"
        ).fetchone()

        with self._write_lock, self._conn:
            if has_target_column is not None:
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO assurance_runs (
                        run_id, agent_id, suite_version_id, environment_id,
                        endpoint_url, started_at, finished_at,
                        passed, failed, unverifiable, run_diff_json, target_id, status
                    ) VALUES (?, ?, ?, NULL, ?, ?, ?, 0, 0, 0, NULL, ?, 'running')
                    """,
                    (
                        run_id,
                        agent_id,
                        suite_version_id,
                        endpoint_url,
                        now,
                        now,
                        target_id,
                    ),
                )
            else:
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO assurance_runs (
                        run_id, agent_id, suite_version_id, environment_id,
                        endpoint_url, started_at, finished_at,
                        passed, failed, unverifiable, run_diff_json
                    ) VALUES (?, ?, ?, NULL, ?, ?, ?, 0, 0, 0, NULL)
                    """,
                    (
                        run_id,
                        agent_id,
                        suite_version_id,
                        endpoint_url,
                        now,
                        now,
                    ),
                )
        return suite_version_id

    def save_partial_result(self, run_id: str, result: TestCaseResult) -> None:
        """Atomically persist a single test case result and trajectory, updating running tallies."""
        with start_span(
            "db.sqlite.operation",
            attributes={
                "db.system": "sqlite",
                "db.operation": "save_partial_result",
                "agenteval.run_id": run_id,
                "agenteval.test_id": result.test_id,
                "agenteval.verdict": result.verdict,
            },
        ):
            now = datetime.now(UTC).isoformat()
            result_id = f"{run_id}:{result.test_id}"
            with self._write_lock, self._conn:
                self._conn.execute(
                    """
                    INSERT OR REPLACE INTO test_case_results (
                        id, run_id, test_id, verdict, rationale, observation_json
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result_id,
                        run_id,
                        result.test_id,
                        result.verdict,
                        result.rationale,
                        result.observation.model_dump_json(),
                    ),
                )
                self._conn.execute(
                    "DELETE FROM execution_steps WHERE test_case_result_id = ?",
                    (result_id,),
                )
                self._insert_trajectory(result_id, result.trajectory)

                self._conn.execute(
                    """
                    UPDATE assurance_runs
                    SET passed = (SELECT count(*) FROM test_case_results WHERE run_id = ? AND verdict = 'PASS'),
                        failed = (SELECT count(*) FROM test_case_results WHERE run_id = ? AND verdict = 'FAIL'),
                        unverifiable = (SELECT count(*) FROM test_case_results WHERE run_id = ? AND verdict = 'UNVERIFIABLE'),
                        finished_at = ?
                    WHERE run_id = ?
                    """,
                    (run_id, run_id, run_id, now, run_id),
                )

    def finalize_run(
        self,
        agent_id: str,
        report: SuiteRunReport,
        *,
        endpoint_url: str,
    ) -> None:
        """Mark run as completed, update diff/tallies, and persist evidence and inspect sidecars."""
        with start_span(
            "db.sqlite.operation",
            attributes={
                "db.system": "sqlite",
                "db.operation": "finalize_run",
                "agenteval.agent_id": agent_id,
                "agenteval.run_id": report.run_id,
            },
        ):
            row = self._conn.execute(
                """
                SELECT id FROM suite_versions
                WHERE agent_id = ? AND version = ?
                """,
                (agent_id, report.suite_version),
            ).fetchone()
            if row is None:
                raise FileNotFoundError(
                    f"No suite version {report.suite_version} for agent '{agent_id}'"
                )
            suite_version_id = str(row["id"])
            now = datetime.now(UTC).isoformat()
            run_diff_json = json.dumps(report.run_diff) if report.run_diff is not None else None

            with self._write_lock, self._conn:
                run_row = self._conn.execute(
                    "SELECT 1 FROM assurance_runs WHERE run_id = ?",
                    (report.run_id,),
                ).fetchone()
                if run_row is None:
                    self.initialize_run(
                        agent_id,
                        report.run_id,
                        report.suite_version,
                        endpoint_url=endpoint_url,
                    )

                for result in report.results:
                    result_id = f"{report.run_id}:{result.test_id}"
                    exists = self._conn.execute(
                        "SELECT 1 FROM test_case_results WHERE id = ?",
                        (result_id,),
                    ).fetchone()
                    if exists is None:
                        self.save_partial_result(report.run_id, result)

                self._conn.execute(
                    """
                    UPDATE assurance_runs
                    SET status = 'completed',
                        finished_at = ?,
                        passed = ?,
                        failed = ?,
                        unverifiable = ?,
                        run_diff_json = ?
                    WHERE run_id = ?
                    """,
                    (
                        now,
                        report.passed,
                        report.failed,
                        report.unverifiable,
                        run_diff_json,
                        report.run_id,
                    ),
                )
                persist_run_evidence_and_verdicts(
                    self._conn,
                    report.run_id,
                    suite_version_id,
                    report.results,
                    captured_at=now,
                )
                self._persist_inspect_sidecar(suite_version_id, report)

    def mark_run_failed(self, run_id: str, error_message: str | None = None) -> None:
        """Mark run as failed upon unexpected error/exception."""
        now = datetime.now(UTC).isoformat()
        has_error_col = self._conn.execute(
            "SELECT 1 FROM pragma_table_info('assurance_runs') WHERE name = 'error_message'"
        ).fetchone()
        with self._write_lock, self._conn:
            if has_error_col is not None:
                self._conn.execute(
                    """
                    UPDATE assurance_runs
                    SET status = 'failed',
                        finished_at = ?,
                        error_message = ?
                    WHERE run_id = ?
                    """,
                    (now, error_message, run_id),
                )
            else:
                self._conn.execute(
                    """
                    UPDATE assurance_runs
                    SET status = 'failed',
                        finished_at = ?
                    WHERE run_id = ?
                    """,
                    (now, run_id),
                )

    def get_run_record(self, run_id: str) -> dict[str, Any] | None:
        """Return the raw assurance_runs row as a dict, including status and tallies."""
        row = self._conn.execute(
            "SELECT * FROM assurance_runs WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        return dict(row)

    def save_run(
        self,
        agent_id: str,
        report: SuiteRunReport,
        *,
        endpoint_url: str,
    ) -> None:
        """Batch persistence for a run report (backward-compatible)."""
        self.initialize_run(
            agent_id,
            report.run_id,
            report.suite_version,
            endpoint_url=endpoint_url,
        )
        for result in report.results:
            self.save_partial_result(report.run_id, result)
        self.finalize_run(agent_id, report, endpoint_url=endpoint_url)


    def _persist_inspect_sidecar(self, suite_version_id: str, report: SuiteRunReport) -> None:
        from agenteval.inspect_bridge.log_archive import inspect_extra_available, write_run_archive

        if not inspect_extra_available():
            return
        has_cols = self._conn.execute(
            "SELECT 1 FROM pragma_table_info('assurance_runs') WHERE name = 'inspect_log_path'"
        ).fetchone()
        if has_cols is None:
            return
        pack_row = self._conn.execute(
            "SELECT pack_json FROM suite_versions WHERE id = ?",
            (suite_version_id,),
        ).fetchone()
        if pack_row is None:
            return
        pack = TestPack.model_validate_json(str(pack_row["pack_json"]))
        out_dir = self.db_path.parent / "inspect_logs" / report.run_id
        log_path, digest = write_run_archive(report, pack, output_dir=out_dir)
        self._conn.execute(
            """
            UPDATE assurance_runs
            SET inspect_log_path = ?, inspect_log_sha256 = ?
            WHERE run_id = ?
            """,
            (log_path, digest, report.run_id),
        )

    def count_criterion_verdicts(self, run_id: str) -> int:
        return count_criterion_verdicts_for_run(self._conn, run_id)

    def load_latest_run(self, agent_id: str) -> SuiteRunReport | None:
        row = self._conn.execute(
            """
            SELECT run_id FROM assurance_runs
            WHERE agent_id = ? AND (status IS NULL OR status = 'completed')
            ORDER BY started_at DESC
            LIMIT 1
            """,
            (agent_id,),
        ).fetchone()
        if row is None:
            return None
        return self.load_run(agent_id, str(row["run_id"]))

    def load_run(self, agent_id: str, run_id: str) -> SuiteRunReport | None:
        run_row = self._conn.execute(
            """
            SELECT r.*, sv.version AS suite_version
            FROM assurance_runs r
            JOIN suite_versions sv ON sv.id = r.suite_version_id
            WHERE r.run_id = ? AND r.agent_id = ?
            """,
            (run_id, agent_id),
        ).fetchone()
        if run_row is None:
            return None

        result_rows = self._conn.execute(
            """
            SELECT id, test_id, verdict, rationale, observation_json
            FROM test_case_results
            WHERE run_id = ?
            ORDER BY test_id
            """,
            (run_id,),
        ).fetchall()

        results: list[TestCaseResult] = []
        for r in result_rows:
            observation = ObservationBundle.model_validate_json(str(r["observation_json"]))
            steps = self._load_steps(str(r["id"]))
            results.append(
                TestCaseResult(
                    test_id=str(r["test_id"]),
                    verdict=str(r["verdict"]),
                    observation=observation,
                    rationale=str(r["rationale"] or ""),
                    trajectory=steps,
                )
            )

        run_diff: dict[str, Any] | None = None
        if run_row["run_diff_json"]:
            run_diff = json.loads(str(run_row["run_diff_json"]))

        status = "completed"
        error_msg: str | None = None
        row_keys = run_row.keys()
        if "status" in row_keys and run_row["status"]:
            status = str(run_row["status"])
        if "error_message" in row_keys and run_row["error_message"]:
            error_msg = str(run_row["error_message"])

        report = SuiteRunReport(
            agent_id=agent_id,
            run_id=run_id,
            suite_version=int(run_row["suite_version"]),
            results=results,
            passed=int(run_row["passed"]),
            failed=int(run_row["failed"]),
            unverifiable=int(run_row["unverifiable"]),
            run_diff=run_diff,
            status=status,
            error=error_msg,
        )
        return enrich_run_report(self._conn, report)

    def _ensure_default_workspace(self) -> None:
        now = datetime.now(UTC).isoformat()
        self._conn.execute(
            """
            INSERT OR IGNORE INTO workspaces (id, slug, name, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (DEFAULT_WORKSPACE_ID, DEFAULT_WORKSPACE_SLUG, DEFAULT_WORKSPACE_NAME, now),
        )
        self._conn.commit()

    def _latest_suite_row(self, agent_id: str) -> sqlite3.Row | None:
        row = self._conn.execute(
            """
            SELECT * FROM suite_versions
            WHERE agent_id = ?
            ORDER BY version DESC
            LIMIT 1
            """,
            (agent_id,),
        ).fetchone()
        return cast(sqlite3.Row | None, row)

    @staticmethod
    def _suite_version_id(agent_id: str, version: int) -> str:
        return f"{agent_id}-v{version}"

    def _insert_trajectory(self, test_case_result_id: str, steps: list[ExecutionStep]) -> None:
        for index, step in enumerate(steps):
            step_pk = f"{test_case_result_id}:{index}"
            self._conn.execute(
                """
                INSERT INTO execution_steps (
                    id, test_case_result_id, step_index, step_id, kind, label,
                    thought, action_tool, action_args_json, observation,
                    http_status, latency_ms, is_failure
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    step_pk,
                    test_case_result_id,
                    index,
                    step.step_id,
                    step.kind,
                    step.label,
                    step.thought,
                    step.action_tool,
                    json.dumps(step.action_args),
                    step.observation,
                    step.http_status,
                    step.latency_ms,
                    1 if step.is_failure else 0,
                ),
            )

    def _load_steps(self, test_case_result_id: str) -> list[ExecutionStep]:
        rows = self._conn.execute(
            """
            SELECT * FROM execution_steps
            WHERE test_case_result_id = ?
            ORDER BY step_index
            """,
            (test_case_result_id,),
        ).fetchall()
        steps: list[ExecutionStep] = []
        for row in rows:
            args_raw = row["action_args_json"] or "{}"
            steps.append(
                ExecutionStep(
                    step_id=str(row["step_id"]),
                    kind=str(row["kind"]),
                    label=str(row["label"]),
                    thought=str(row["thought"] or ""),
                    action_tool=str(row["action_tool"] or ""),
                    action_args=json.loads(str(args_raw)),
                    observation=str(row["observation"] or ""),
                    http_status=row["http_status"],
                    latency_ms=row["latency_ms"],
                    is_failure=bool(row["is_failure"]),
                )
            )
        return steps
