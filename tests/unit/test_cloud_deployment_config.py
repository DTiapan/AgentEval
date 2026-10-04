"""Unit tests verifying deployment configuration consistency and timeout safety (Slice 3)."""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_deploy_sh_timeout_baseline() -> None:
    deploy_sh = REPO_ROOT / "deploy" / "gcp" / "deploy.sh"
    assert deploy_sh.is_file(), f"Missing {deploy_sh}"
    content = deploy_sh.read_text(encoding="utf-8")

    match = re.search(r'TIMEOUT="?\$\{TIMEOUT:-(\d+)\}"?', content)
    assert match is not None, "deploy.sh missing TIMEOUT default assignment"
    timeout_val = int(match.group(1))
    assert timeout_val >= 1800, (
        f"deploy.sh default TIMEOUT is {timeout_val}s; must be >= 1800s to prevent Cloud Run "
        "premature HTTP 504 timeouts on full evaluation suites."
    )


def test_service_yaml_timeout_baseline() -> None:
    service_yaml = REPO_ROOT / "deploy" / "gcp" / "service.yaml"
    assert service_yaml.is_file(), f"Missing {service_yaml}"
    content = service_yaml.read_text(encoding="utf-8")

    match = re.search(r'timeoutSeconds:\s*(\d+)', content)
    assert match is not None, "service.yaml missing spec.template.spec.timeoutSeconds"
    timeout_val = int(match.group(1))
    assert timeout_val >= 1800, (
        f"service.yaml timeoutSeconds is {timeout_val}s; must be >= 1800s for Cloud Run Gen2."
    )


def test_cloudbuild_yaml_timeout_baseline() -> None:
    cloudbuild_yaml = REPO_ROOT / "cloudbuild.yaml"
    assert cloudbuild_yaml.is_file(), f"Missing {cloudbuild_yaml}"
    content = cloudbuild_yaml.read_text(encoding="utf-8")

    # Either a direct flag or a substitution variable must enforce >= 1800
    sub_match = re.search(r'_TIMEOUT:\s*"?(\d+)"?', content)
    flag_match = re.search(r'--timeout="?(\d+)"?', content)
    timeout_val = int(sub_match.group(1)) if sub_match else (int(flag_match.group(1)) if flag_match else 0)

    assert timeout_val >= 1800, (
        f"cloudbuild.yaml deployment step timeout is {timeout_val}s; must be >= 1800s."
    )


def test_env_gcp_example_timeout_baseline() -> None:
    env_example = REPO_ROOT / ".env.gcp.example"
    assert env_example.is_file(), f"Missing {env_example}"
    content = env_example.read_text(encoding="utf-8")

    match = re.search(r'^TIMEOUT=(\d+)', content, re.MULTILINE)
    assert match is not None, ".env.gcp.example missing TIMEOUT setting"
    timeout_val = int(match.group(1))
    assert timeout_val >= 1800, (
        f".env.gcp.example TIMEOUT is {timeout_val}; must be >= 1800."
    )


def test_sqlite_gcs_max_instances_guardrail_in_deploy_sh() -> None:
    """Verify deploy.sh enforces MAX_INSTANCES=1 for SQLite on GCS FUSE safety (ADR-007)."""
    deploy_sh = REPO_ROOT / "deploy" / "gcp" / "deploy.sh"
    content = deploy_sh.read_text(encoding="utf-8")

    match = re.search(r'MAX_INSTANCES="?\$\{MAX_INSTANCES:-(\d+)\}"?', content)
    assert match is not None, "deploy.sh missing MAX_INSTANCES default assignment"
    max_val = int(match.group(1))
    assert max_val == 1, (
        f"deploy.sh default MAX_INSTANCES is {max_val}; must be 1 to prevent multi-instance "
        "split-brain corruption with SQLite on GCS FUSE (ADR-007)."
    )

    # Verify active guardrail check exists
    assert "MAX_INSTANCES=1" in content, "deploy.sh missing active MAX_INSTANCES=1 clamp"
    assert "SQLite on GCS FUSE does not support multi-instance writes" in content, (
        "deploy.sh missing ADR-007 safety warning message"
    )


def test_sqlite_gcs_max_scale_guardrail_in_service_yaml() -> None:
    """Verify service.yaml clamps maxScale to 1 for SQLite on GCS FUSE safety (ADR-007)."""
    service_yaml = REPO_ROOT / "deploy" / "gcp" / "service.yaml"
    content = service_yaml.read_text(encoding="utf-8")

    match = re.search(r'autoscaling\.knative\.dev/maxScale:\s*"(\d+)"', content)
    assert match is not None, "service.yaml missing autoscaling.knative.dev/maxScale"
    max_scale = int(match.group(1))
    assert max_scale == 1, (
        f"service.yaml maxScale is {max_scale}; must be 1 while using SQLite on GCS FUSE (ADR-007)."
    )


def test_sqlite_gcs_max_instances_in_env_gcp_example() -> None:
    """Verify .env.gcp.example defaults MAX_INSTANCES=1 (ADR-007)."""
    env_example = REPO_ROOT / ".env.gcp.example"
    content = env_example.read_text(encoding="utf-8")

    match = re.search(r'^MAX_INSTANCES=(\d+)', content, re.MULTILINE)
    assert match is not None, ".env.gcp.example missing MAX_INSTANCES setting"
    max_val = int(match.group(1))
    assert max_val == 1, (
        f".env.gcp.example MAX_INSTANCES is {max_val}; must be 1 for SQLite on GCS FUSE (ADR-007)."
    )


def test_deploy_sh_postgres_horizontal_scaling_unlocked() -> None:
    """Verify deploy.sh unlocks horizontal scaling when DATABASE_URL is set (ADR-007)."""
    deploy_sh = REPO_ROOT / "deploy" / "gcp" / "deploy.sh"
    content = deploy_sh.read_text(encoding="utf-8")

    assert "PostgreSQL backend detected (DATABASE_URL configured)" in content, (
        "deploy.sh must log when PostgreSQL backend is detected"
    )
    assert 'POSTGRES_MAX_INSTANCES:-10' in content, (
        "deploy.sh must default MAX_INSTANCES to at least 10 when PostgreSQL is active"
    )
    assert "--add-cloudsql-instances" in content, (
        "deploy.sh must support binding Cloud SQL instances via --add-cloudsql-instances"
    )


def test_env_gcp_example_documents_postgres_and_cloud_sql() -> None:
    """Verify .env.gcp.example documents PostgreSQL and Cloud SQL configurations."""
    env_example = REPO_ROOT / ".env.gcp.example"
    content = env_example.read_text(encoding="utf-8")

    assert "DATABASE_URL=postgresql://" in content
    assert "CLOUD_SQL_INSTANCE=" in content
    assert "POSTGRES_MAX_INSTANCES=10" in content


def test_service_yaml_documents_cloud_sql_instances() -> None:
    """Verify service.yaml contains documented Cloud SQL instance annotations."""
    service_yaml = REPO_ROOT / "deploy" / "gcp" / "service.yaml"
    content = service_yaml.read_text(encoding="utf-8")

    assert "run.googleapis.com/cloudsql-instances" in content

