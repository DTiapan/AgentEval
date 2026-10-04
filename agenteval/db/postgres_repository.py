"""PostgreSQL persistence repository for AgentEval multi-tenant Cloud Run deployments (ADR-007)."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from agenteval.services.requirement_run_status import AssuranceSignoffContext

from agenteval.db.config import (
    DEFAULT_WORKSPACE_ID,
    DEFAULT_WORKSPACE_NAME,
    DEFAULT_WORKSPACE_SLUG,
    get_database_url,
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

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool

    HAS_PSYCOPG = True
except ImportError:
    HAS_PSYCOPG = False
    psycopg = None  # type: ignore[assignment]
    dict_row = None  # type: ignore[assignment]
    ConnectionPool = None  # type: ignore[assignment,misc]


def postgres_schema_sql_path() -> Path:
    return Path(__file__).resolve().parent / "schema_postgres.sql"


class PostgresSuiteRepository:
    """PostgreSQL relational store for suite versions, assurance runs, and trajectories."""

    def __init__(
        self,
        database_url: str | None = None,
        *,
        min_pool_size: int = 1,
        max_pool_size: int = 10,
    ) -> None:
        if not HAS_PSYCOPG:
            raise ImportError(
                "PostgreSQL support requires the 'postgres' extra. Install it with: "
                "pip install 'agenteval[postgres]'"
            )

        self.database_url = database_url or get_database_url()
        if not self.database_url:
            raise ValueError(
                "PostgresSuiteRepository requires a valid PostgreSQL connection URL "
                "(set DATABASE_URL or AGENTEVAL_DATABASE_URL)."
            )

        # Standardize postgres:// to postgresql:// for psycopg
        if self.database_url.startswith("postgres://"):
            self.database_url = "postgresql://" + self.database_url.removeprefix("postgres://")

        self.workspace_id = DEFAULT_WORKSPACE_ID
        self._pool = ConnectionPool(
            self.database_url,
            min_size=min_pool_size,
            max_size=max_pool_size,
            open=True,
            kwargs={"row_factory": dict_row},
        )
        self.init_schema()
        self._ensure_default_workspace()

    def close(self) -> None:
        """Close connection pool and all active database connections."""
        self._pool.close()

    def init_schema(self) -> None:
        """Apply PostgreSQL schema DDL idempotently."""
        ddl = postgres_schema_sql_path().read_text(encoding="utf-8")
        with self._pool.connection() as conn:
            conn.execute(ddl)
            conn.commit()

    def _ensure_default_workspace(self) -> None:
        now = datetime.now(UTC).isoformat()
        with self._pool.connection() as conn:
            conn.execute(
                """
                INSERT INTO workspaces (id, slug, name, created_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (DEFAULT_WORKSPACE_ID, DEFAULT_WORKSPACE_SLUG, DEFAULT_WORKSPACE_NAME, now),
            )
            conn.commit()

    @staticmethod
    def _fetch_one(cursor: Any) -> dict[str, Any] | None:
        row = cursor.fetchone()
        return cast(dict[str, Any], row) if row is not None else None

    @staticmethod
    def _fetch_all(cursor: Any) -> list[dict[str, Any]]:
        rows = cursor.fetchall()
        return [cast(dict[str, Any], r) for r in rows]

    def _suite_version_id(self, agent_id: str, version: int) -> str:
        return f"{agent_id}-v{version}"

    def list_agent_ids(self) -> list[str]:
        with self._pool.connection() as conn:
            rows = self._fetch_all(
                conn.execute(
                    "SELECT id FROM agents WHERE workspace_id = %s ORDER BY id",
                    (self.workspace_id,),
                )
            )
            return [str(row["id"]) for row in rows]

    def delete_agent(self, agent_id: str) -> bool:
        with self._pool.connection() as conn:
            exists = self._fetch_one(conn.execute("SELECT 1 FROM agents WHERE id = %s", (agent_id,)))
            if exists is None:
                return False
            # ON DELETE CASCADE handles child suite_versions, assurance_runs, test_cases, etc.
            conn.execute("DELETE FROM agents WHERE id = %s", (agent_id,))
            conn.commit()
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
            "db.postgres.operation",
            attributes={
                "db.system": "postgresql",
                "db.operation": "init_suite",
                "agenteval.agent_id": manifest.agent_id,
                "agenteval.force": force,
            },
        ):
            agent_id = manifest.agent_id
            now = datetime.now(UTC).isoformat()
            with self._pool.connection() as conn:
                exists = self._fetch_one(conn.execute("SELECT 1 FROM agents WHERE id = %s", (agent_id,)))
                if exists is not None and not force:
                    raise SuiteExistsError(
                        f"Suite already exists for agent '{agent_id}' in database. Use force to replace."
                    )

                self._ensure_default_workspace()
                conn.execute(
                    """
                    INSERT INTO agents (id, workspace_id, slug, display_name, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET display_name = EXCLUDED.display_name
                    """,
                    (agent_id, self.workspace_id, agent_id, agent_id, now),
                )
                suite_version_id = self._suite_version_id(agent_id, manifest.version)
                conn.execute(
                    """
                    INSERT INTO suite_versions (
                        id, agent_id, version, requirements_fingerprint,
                        requirements_text, endpoint_profile, pack_json,
                        candidate_pool_json, agent_card_json, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (agent_id, version) DO UPDATE SET
                        requirements_fingerprint = EXCLUDED.requirements_fingerprint,
                        requirements_text = EXCLUDED.requirements_text,
                        endpoint_profile = EXCLUDED.endpoint_profile,
                        pack_json = EXCLUDED.pack_json,
                        candidate_pool_json = EXCLUDED.candidate_pool_json,
                        agent_card_json = EXCLUDED.agent_card_json,
                        created_at = EXCLUDED.created_at
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
                conn.commit()

    def _latest_suite_row(self, agent_id: str) -> dict[str, Any] | None:
        with self._pool.connection() as conn:
            return self._fetch_one(
                conn.execute(
                    """
                    SELECT id, version, pack_json, candidate_pool_json, agent_card_json,
                           requirements_fingerprint, requirements_text, endpoint_profile, created_at
                    FROM suite_versions
                    WHERE agent_id = %s
                    ORDER BY version DESC
                    LIMIT 1
                    """,
                    (agent_id,),
                )
            )

    def load_manifest(self, agent_id: str) -> SuiteManifest:
        row = self._latest_suite_row(agent_id)
        if row is None:
            raise FileNotFoundError(f"No suite in PostgreSQL for agent '{agent_id}'")
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
            raise FileNotFoundError(f"No suite in PostgreSQL for agent '{agent_id}'")
        pack_raw = row["pack_json"]
        pack_dict = pack_raw if isinstance(pack_raw, dict) else json.loads(pack_raw)
        return TestPack.model_validate(pack_dict)

    def load_pool(self, agent_id: str) -> list[CandidateTest]:
        row = self._latest_suite_row(agent_id)
        if row is None:
            raise FileNotFoundError(f"No suite in PostgreSQL for agent '{agent_id}'")
        raw = row["candidate_pool_json"]
        if not raw:
            return []
        items = raw if isinstance(raw, list) else json.loads(raw)
        return [CandidateTest.model_validate(x) for x in items]

    def load_requirements_text(self, agent_id: str) -> str:
        row = self._latest_suite_row(agent_id)
        if row is None:
            return ""
        return str(row.get("requirements_text") or "")

    def load_agent_card_json(self, agent_id: str) -> str | None:
        row = self._latest_suite_row(agent_id)
        if row is None:
            return None
        raw = row.get("agent_card_json")
        return str(raw) if raw else None

    def load_requirements_result(self, agent_id: str) -> SuiteRequirementsResult | None:
        return None

    def load_normalized_requirements(self, agent_id: str) -> list[RequirementRecord]:
        return []

    def load_normalized_test_cases(self, agent_id: str) -> list[FrozenTestCaseRecord]:
        return []

    def enrich_run_report(self, report: SuiteRunReport) -> SuiteRunReport:
        return report

    def load_signoff_context(
        self, agent_id: str, suite_version: int, run_id: str
    ) -> "AssuranceSignoffContext | None":
        return None

    def ensure_default_target(self, agent_id: str, endpoint_url: str) -> str | None:
        target_id = f"{agent_id}-default-target"
        connector_id = f"{agent_id}-http-transport"
        now = datetime.now(UTC).isoformat()
        with self._pool.connection() as conn:
            conn.execute(
                """
                INSERT INTO connectors (id, workspace_id, slug, kind, config_json, created_at)
                VALUES (%s, %s, %s, 'http_transport', %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (connector_id, self.workspace_id, f"{agent_id}-http", json.dumps({"url": endpoint_url}), now),
            )
            conn.execute(
                """
                INSERT INTO targets (id, workspace_id, agent_id, display_name, transport_connector_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (target_id, self.workspace_id, agent_id, f"{agent_id} target", connector_id, now),
            )
            conn.commit()
            return target_id

    def initialize_run(
        self,
        agent_id: str,
        run_id: str,
        suite_version: int,
        *,
        endpoint_url: str,
    ) -> str:
        with start_span(
            "db.postgres.operation",
            attributes={
                "db.system": "postgresql",
                "db.operation": "initialize_run",
                "agenteval.run_id": run_id,
                "agenteval.agent_id": agent_id,
            },
        ):
            with self._pool.connection() as conn:
                suite_row = self._fetch_one(
                    conn.execute(
                        "SELECT id FROM suite_versions WHERE agent_id = %s AND version = %s",
                        (agent_id, suite_version),
                    )
                )
                if suite_row is None:
                    raise FileNotFoundError(f"No suite version {suite_version} for agent '{agent_id}'")

                suite_version_id = str(suite_row["id"])
                target_id = self.ensure_default_target(agent_id, endpoint_url)
                now = datetime.now(UTC).isoformat()
                conn.execute(
                    """
                    INSERT INTO assurance_runs (
                        run_id, agent_id, suite_version_id, environment_id,
                        endpoint_url, started_at, finished_at, passed, failed,
                        unverifiable, status, target_id
                    ) VALUES (%s, %s, %s, NULL, %s, %s, %s, 0, 0, 0, 'running', %s)
                    ON CONFLICT (run_id) DO UPDATE SET
                        status = 'running',
                        endpoint_url = EXCLUDED.endpoint_url
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
                conn.commit()
                return suite_version_id

    def save_partial_result(
        self,
        run_id: str,
        result: TestCaseResult,
    ) -> None:
        with start_span(
            "db.postgres.operation",
            attributes={
                "db.system": "postgresql",
                "db.operation": "save_partial_result",
                "agenteval.run_id": run_id,
                "agenteval.test_id": result.test_id,
            },
        ):
            result_id = f"{run_id}:{result.test_id}"
            now = datetime.now(UTC).isoformat()
            with self._pool.connection() as conn:
                conn.execute(
                    """
                    INSERT INTO test_case_results (
                        id, run_id, test_id, verdict, rationale, observation_json
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (run_id, test_id) DO UPDATE SET
                        verdict = EXCLUDED.verdict,
                        rationale = EXCLUDED.rationale,
                        observation_json = EXCLUDED.observation_json
                    """,
                    (
                        result_id,
                        run_id,
                        result.test_id,
                        result.verdict,
                        result.rationale or "",
                        result.observation.model_dump_json(),
                    ),
                )

                for step_index, step in enumerate(result.trajectory):
                    step_id = f"{result_id}:{step_index}"
                    conn.execute(
                        """
                        INSERT INTO execution_steps (
                            id, test_case_result_id, step_index, step_id, kind, label,
                            thought, action_tool, action_args_json, observation,
                            http_status, latency_ms, is_failure
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (test_case_result_id, step_index) DO UPDATE SET
                            label = EXCLUDED.label,
                            thought = EXCLUDED.thought,
                            observation = EXCLUDED.observation,
                            http_status = EXCLUDED.http_status,
                            latency_ms = EXCLUDED.latency_ms,
                            is_failure = EXCLUDED.is_failure
                        """,
                        (
                            step_id,
                            result_id,
                            step_index,
                            step.step_id or f"step-{step_index}",
                            step.kind,
                            step.label,
                            step.thought or "",
                            step.action_tool or "",
                            json.dumps(step.action_args or {}),
                            step.observation or "",
                            step.http_status,
                            step.latency_ms,
                            1 if step.is_failure else 0,
                        ),
                    )

                conn.execute(
                    """
                    UPDATE assurance_runs
                    SET passed = (SELECT count(*) FROM test_case_results WHERE run_id = %s AND verdict = 'PASS'),
                        failed = (SELECT count(*) FROM test_case_results WHERE run_id = %s AND verdict = 'FAIL'),
                        unverifiable = (SELECT count(*) FROM test_case_results WHERE run_id = %s AND verdict = 'UNVERIFIABLE'),
                        finished_at = %s
                    WHERE run_id = %s
                    """,
                    (run_id, run_id, run_id, now, run_id),
                )
                conn.commit()

    def finalize_run(
        self,
        agent_id: str,
        report: SuiteRunReport,
        *,
        endpoint_url: str,
    ) -> None:
        with start_span(
            "db.postgres.operation",
            attributes={
                "db.system": "postgresql",
                "db.operation": "finalize_run",
                "agenteval.agent_id": agent_id,
                "agenteval.run_id": report.run_id,
            },
        ):
            now = datetime.now(UTC).isoformat()
            run_diff_json = json.dumps(report.run_diff) if report.run_diff is not None else None
            with self._pool.connection() as conn:
                run_row = self._fetch_one(
                    conn.execute(
                        "SELECT 1 FROM assurance_runs WHERE run_id = %s",
                        (report.run_id,),
                    )
                )
                if run_row is None:
                    self.initialize_run(
                        agent_id,
                        report.run_id,
                        report.suite_version,
                        endpoint_url=endpoint_url,
                    )

                for result in report.results:
                    result_id = f"{report.run_id}:{result.test_id}"
                    exists = self._fetch_one(
                        conn.execute(
                            "SELECT 1 FROM test_case_results WHERE id = %s",
                            (result_id,),
                        )
                    )
                    if exists is None:
                        self.save_partial_result(report.run_id, result)

                conn.execute(
                    """
                    UPDATE assurance_runs
                    SET status = 'completed',
                        finished_at = %s,
                        passed = %s,
                        failed = %s,
                        unverifiable = %s,
                        run_diff_json = %s
                    WHERE run_id = %s
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
                conn.commit()

    def mark_run_failed(
        self,
        run_id: str,
        error_message: str | None = None,
    ) -> None:
        with start_span(
            "db.postgres.operation",
            attributes={
                "db.system": "postgresql",
                "db.operation": "mark_run_failed",
                "agenteval.run_id": run_id,
            },
        ):
            now = datetime.now(UTC).isoformat()
            with self._pool.connection() as conn:
                conn.execute(
                    """
                    UPDATE assurance_runs
                    SET finished_at = %s,
                        status = 'failed',
                        error_message = %s
                    WHERE run_id = %s
                    """,
                    (now, error_message, run_id),
                )
                conn.commit()

    def delete_run(self, run_id: str) -> None:
        """Delete an assurance run by run_id."""
        with self._pool.connection() as conn:
            conn.execute(
                "DELETE FROM assurance_runs WHERE run_id = %s",
                (run_id,),
            )
            conn.commit()

    def load_latest_run(self, agent_id: str) -> SuiteRunReport | None:
        with self._pool.connection() as conn:
            run_row = self._fetch_one(
                conn.execute(
                    """
                    SELECT run_id
                    FROM assurance_runs
                    WHERE agent_id = %s AND (status IS NULL OR status = 'completed')
                    ORDER BY started_at DESC
                    LIMIT 1
                    """,
                    (agent_id,),
                )
            )
            if run_row is None:
                return None
            return self.load_run(agent_id, str(run_row["run_id"]))

    def load_run(self, agent_id: str, run_id: str) -> SuiteRunReport | None:
        with self._pool.connection() as conn:
            run_row = self._fetch_one(
                conn.execute(
                    """
                    SELECT r.*, sv.version AS suite_version
                    FROM assurance_runs r
                    JOIN suite_versions sv ON sv.id = r.suite_version_id
                    WHERE r.run_id = %s AND r.agent_id = %s
                    """,
                    (run_id, agent_id),
                )
            )
            if run_row is None:
                return None

            result_rows = self._fetch_all(
                conn.execute(
                    """
                    SELECT id, test_id, verdict, rationale, observation_json
                    FROM test_case_results
                    WHERE run_id = %s
                    ORDER BY test_id
                    """,
                    (run_id,),
                )
            )

            results: list[TestCaseResult] = []
            for r in result_rows:
                res_id = str(r["id"])
                obs_raw = r["observation_json"]
                obs_dict = obs_raw if isinstance(obs_raw, dict) else json.loads(obs_raw)
                observation = ObservationBundle.model_validate(obs_dict)

                step_rows = self._fetch_all(
                    conn.execute(
                        """
                        SELECT step_index, step_id, kind, label, thought, action_tool,
                               action_args_json, observation, http_status, latency_ms, is_failure
                        FROM execution_steps
                        WHERE test_case_result_id = %s
                        ORDER BY step_index
                        """,
                        (res_id,),
                    )
                )

                trajectory: list[ExecutionStep] = []
                for s in step_rows:
                    args_raw = s["action_args_json"]
                    args_dict = args_raw if isinstance(args_raw, dict) else json.loads(args_raw or "{}")
                    trajectory.append(
                        ExecutionStep(
                            step_id=str(s["step_id"]),
                            kind=str(s["kind"]),
                            label=str(s["label"]),
                            thought=str(s["thought"] or ""),
                            action_tool=str(s["action_tool"] or ""),
                            action_args=args_dict,
                            observation=str(s["observation"] or ""),
                            http_status=s["http_status"],
                            latency_ms=s["latency_ms"],
                            is_failure=bool(s["is_failure"]),
                        )
                    )

                results.append(
                    TestCaseResult(
                        test_id=str(r["test_id"]),
                        verdict=cast(Any, str(r["verdict"])),
                        rationale=str(r["rationale"] or ""),
                        observation=observation,
                        trajectory=trajectory,
                    )
                )

            diff_raw = run_row.get("run_diff_json")
            run_diff = None
            if diff_raw:
                run_diff = diff_raw if isinstance(diff_raw, dict) else json.loads(diff_raw)

            status = str(run_row.get("status") or "completed")
            error_msg = str(run_row["error_message"]) if run_row.get("error_message") else None

            return SuiteRunReport(
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

    def get_run_record(self, run_id: str) -> dict[str, Any] | None:
        with self._pool.connection() as conn:
            return self._fetch_one(
                conn.execute(
                    """
                    SELECT run_id, agent_id, suite_version_id, endpoint_url, started_at,
                           finished_at, passed, failed, unverifiable, status, error_message
                    FROM assurance_runs
                    WHERE run_id = %s
                    """,
                    (run_id,),
                )
            )

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
        agent_id = manifest.agent_id
        if self._latest_suite_row(agent_id) is None:
            raise FileNotFoundError(f"No suite in PostgreSQL for agent '{agent_id}'")
        self.init_suite(
            manifest,
            pool,
            pack,
            force=True,
            agent_card_json=agent_card_json,
            requirements_text=requirements_text,
            enabled_domain_packs=enabled_domain_packs,
        )
