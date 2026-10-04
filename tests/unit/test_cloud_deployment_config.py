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
