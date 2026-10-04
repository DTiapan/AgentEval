"""In-process asynchronous job manager for long-running assurance suite evaluations."""

from __future__ import annotations

import concurrent.futures
import threading
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from agenteval.planning.models import SuiteRunReport
    from agenteval.services.suite_workflow import SuiteWorkflow


class JobStatus(StrEnum):
    """Lifecycle status of a background assurance run job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RunProgress(BaseModel):
    """Observable progress of a test run execution."""

    model_config = ConfigDict(extra="forbid")

    completed: int = 0
    total: int = 0
    percent: float = 0.0


class RunJobInfo(BaseModel):
    """Metadata and execution state for an assurance suite job."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    agent_id: str
    status: JobStatus
    created_at: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    started_at: str | None = None
    completed_at: str | None = None
    progress: RunProgress = Field(default_factory=RunProgress)
    error: str | None = None


class RunJobManager:
    """Manages asynchronous background execution of assurance suite runs."""

    def __init__(self, max_concurrent_jobs: int = 4) -> None:
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=max_concurrent_jobs,
            thread_name_prefix="agenteval-job",
        )
        self._lock = threading.Lock()
        self._jobs: dict[str, RunJobInfo] = {}
        self._reports: dict[str, SuiteRunReport] = {}

    def submit_run(
        self,
        agent_id: str,
        workflow: SuiteWorkflow,
        *,
        endpoint_url: str | None = None,
        audit_log_db_path: str | None = None,
        judge_mode: str = "hybrid",
        max_concurrency: int | None = None,
    ) -> RunJobInfo:
        """Submit a suite run for asynchronous background execution and return job info."""
        run_id = uuid4().hex[:12]
        now_str = datetime.now(UTC).isoformat()
        job = RunJobInfo(
            run_id=run_id,
            agent_id=agent_id,
            status=JobStatus.PENDING,
            created_at=now_str,
            progress=RunProgress(),
        )

        with self._lock:
            self._jobs[run_id] = job

        self._executor.submit(
            self._execute_job,
            run_id=run_id,
            agent_id=agent_id,
            workflow=workflow,
            endpoint_url=endpoint_url,
            audit_log_db_path=audit_log_db_path,
            judge_mode=judge_mode,
            max_concurrency=max_concurrency,
        )
        return job

    def _execute_job(
        self,
        run_id: str,
        agent_id: str,
        workflow: SuiteWorkflow,
        endpoint_url: str | None,
        audit_log_db_path: str | None,
        judge_mode: str,
        max_concurrency: int | None,
    ) -> None:
        started_str = datetime.now(UTC).isoformat()
        with self._lock:
            if run_id in self._jobs:
                current_job = self._jobs[run_id]
                self._jobs[run_id] = current_job.model_copy(
                    update={"status": JobStatus.RUNNING, "started_at": started_str}
                )

        def on_progress(completed: int, total: int) -> None:
            pct = round((completed / total) * 100.0, 1) if total > 0 else 0.0
            with self._lock:
                if run_id in self._jobs:
                    cur = self._jobs[run_id]
                    self._jobs[run_id] = cur.model_copy(
                        update={
                            "progress": RunProgress(
                                completed=completed, total=total, percent=pct
                            )
                        }
                    )

        try:
            report = workflow.run_suite(
                agent_id,
                run_id=run_id,
                endpoint_url=endpoint_url,
                audit_log_db_path=audit_log_db_path,
                judge_mode=judge_mode,
                max_concurrency=max_concurrency,
                on_progress=on_progress,
            )
            completed_str = datetime.now(UTC).isoformat()
            total_tests = len(report.results)
            with self._lock:
                self._reports[run_id] = report
                if run_id in self._jobs:
                    cur = self._jobs[run_id]
                    self._jobs[run_id] = cur.model_copy(
                        update={
                            "status": JobStatus.COMPLETED,
                            "completed_at": completed_str,
                            "progress": RunProgress(
                                completed=total_tests,
                                total=total_tests,
                                percent=100.0,
                            ),
                        }
                    )
        except Exception as exc:
            failed_str = datetime.now(UTC).isoformat()
            with self._lock:
                if run_id in self._jobs:
                    cur = self._jobs[run_id]
                    self._jobs[run_id] = cur.model_copy(
                        update={
                            "status": JobStatus.FAILED,
                            "completed_at": failed_str,
                            "error": str(exc),
                        }
                    )

    def get_job(self, run_id: str) -> RunJobInfo | None:
        """Retrieve job metadata and progress by run_id."""
        with self._lock:
            return self._jobs.get(run_id)

    def get_report(self, run_id: str) -> SuiteRunReport | None:
        """Retrieve completed in-memory report by run_id."""
        with self._lock:
            return self._reports.get(run_id)

    def shutdown(self, wait: bool = False) -> None:
        """Shut down the background job executor."""
        self._executor.shutdown(wait=wait)


_global_job_manager: RunJobManager | None = None
_global_lock = threading.Lock()


def get_run_job_manager() -> RunJobManager:
    """Return the application singleton RunJobManager instance."""
    global _global_job_manager
    with _global_lock:
        if _global_job_manager is None:
            _global_job_manager = RunJobManager()
        return _global_job_manager
