"""Persist frozen regression suites under .agenteval/suites/ (DR-010)."""

import json
from datetime import UTC, datetime
from pathlib import Path

from agenteval.planning.models import (
    CandidateTest,
    SuiteManifest,
    SuiteRunReport,
    TestPack,
)


class SuiteExistsError(FileExistsError):
    """Raised when suite init would overwrite without force."""


class SuiteStore:
    """Filesystem layout for one agent suite."""

    def __init__(self, root: Path | str = ".agenteval/suites") -> None:
        self.root = Path(root)

    def agent_dir(self, agent_id: str) -> Path:
        return self.root / agent_id

    def init_suite(
        self,
        manifest: SuiteManifest,
        pool: list[CandidateTest],
        pack: TestPack,
        *,
        force: bool = False,
    ) -> Path:
        directory = self.agent_dir(manifest.agent_id)
        if directory.exists() and not force:
            raise SuiteExistsError(
                f"Suite already exists at {directory}. Use --force-new-version to replace."
            )
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "suite.manifest.json").write_text(
            manifest.model_dump_json(indent=2), encoding="utf-8"
        )
        (directory / "candidate_pool.json").write_text(
            json.dumps([t.model_dump() for t in pool], indent=2), encoding="utf-8"
        )
        (directory / "test_pack.json").write_text(pack.model_dump_json(indent=2), encoding="utf-8")
        return directory

    def load_manifest(self, agent_id: str) -> SuiteManifest:
        path = self.agent_dir(agent_id) / "suite.manifest.json"
        return SuiteManifest.model_validate_json(path.read_text(encoding="utf-8"))

    def load_pack(self, agent_id: str) -> TestPack:
        path = self.agent_dir(agent_id) / "test_pack.json"
        return TestPack.model_validate_json(path.read_text(encoding="utf-8"))

    def load_pool(self, agent_id: str) -> list[CandidateTest]:
        path = self.agent_dir(agent_id) / "candidate_pool.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [CandidateTest.model_validate(item) for item in raw]

    def save_run(self, agent_id: str, report: SuiteRunReport) -> Path:
        runs = self.agent_dir(agent_id) / "runs"
        runs.mkdir(parents=True, exist_ok=True)
        out = runs / f"{report.run_id}.json"
        out.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        latest = self.agent_dir(agent_id) / "latest_run.json"
        latest.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        return out

    def load_latest_run(self, agent_id: str) -> SuiteRunReport | None:
        path = self.agent_dir(agent_id) / "latest_run.json"
        if not path.exists():
            return None
        return SuiteRunReport.model_validate_json(path.read_text(encoding="utf-8"))

    @staticmethod
    def new_manifest(
        agent_id: str,
        requirements_fingerprint: str,
        endpoint_profile: str,
        version: int = 1,
    ) -> SuiteManifest:
        return SuiteManifest(
            agent_id=agent_id,
            version=version,
            requirements_fingerprint=requirements_fingerprint,
            created_at=datetime.now(UTC).isoformat(),
            endpoint_profile=endpoint_profile,
        )
