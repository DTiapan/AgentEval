"""Unit tests for Inspect AI task builder and Docker sandbox bridge."""

import ast
import json
from pathlib import Path

from agenteval.inspect_bridge.task_builder import (
    DockerSandboxSpec,
    InspectTaskBuilder,
)
from agenteval.planning.models import CandidateTest, MandatoryCategory, PriorityTier


def _sample_candidates() -> list[CandidateTest]:
    return [
        CandidateTest(
            id="test-code-1",
            capability_id="req-code-gen",
            persona_id="developer",
            name="Code Agent: Generate Fibonacci function",
            user_prompt="Write a Python script that computes the 10th Fibonacci number.",
            expected_behavior="Script must output 55.",
            coverage_tags=["coding", "python", "algorithms"],
            mandatory_categories=[MandatoryCategory.CRITICAL_INVARIANTS],
            category="coding",
            failure_mode="incorrect_recursion",
            rationale="Verify code execution correctness.",
            template_id="code-01",
            execution_cost=1.0,
            priority_tier=PriorityTier.P0_CRITICAL,
        ),
        CandidateTest(
            id="test-code-2",
            capability_id="req-shell-exec",
            persona_id="sysadmin",
            name="Shell Agent: Count file lines",
            user_prompt="Run wc -l on input.txt and print the line count.",
            expected_behavior="Process must exit code 0 and print integer line count.",
            coverage_tags=["shell", "bash", "cli"],
            mandatory_categories=[],
            category="shell",
            failure_mode="file_not_found",
            rationale="Verify shell tool execution.",
            template_id="shell-01",
            execution_cost=1.0,
            priority_tier=PriorityTier.P1_RECOMMENDED,
        ),
    ]


def test_inspect_task_builder_docker_availability_check() -> None:
    builder = InspectTaskBuilder()
    assert isinstance(builder.is_docker_available(), bool)


def test_build_task_converts_candidates() -> None:
    builder = InspectTaskBuilder()
    candidates = _sample_candidates()
    sandbox = DockerSandboxSpec(image="python:3.11-alpine", memory_limit="1g", cpu_limit=2.0)

    task = builder.build_task("code-agent", candidates, sandbox_spec=sandbox)

    assert task.task_id == "inspect-code-agent"
    assert len(task.samples) == 2
    assert task.sandbox.image == "python:3.11-alpine"
    assert task.sandbox.memory_limit == "1g"

    s1 = task.samples[0]
    assert s1.id == "test-code-1"
    assert s1.input == candidates[0].user_prompt
    assert s1.target == candidates[0].expected_behavior
    assert s1.metadata["priority_tier"] == "P0"
    assert s1.metadata["capability_id"] == "req-code-gen"

    s2 = task.samples[1]
    assert s2.metadata["priority_tier"] == "P1"


def test_export_dataset_jsonl(tmp_path: Path) -> None:
    builder = InspectTaskBuilder()
    task = builder.build_task("shell-agent", _sample_candidates())
    out_file = tmp_path / "dataset.jsonl"

    result_path = builder.export_dataset_jsonl(task, out_file)
    assert result_path.exists()

    lines = result_path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2

    parsed_sample = json.loads(lines[0])
    assert parsed_sample["id"] == "test-code-1"
    assert "target" in parsed_sample


def test_export_task_python_module() -> None:
    builder = InspectTaskBuilder()
    task = builder.build_task("code-agent", _sample_candidates())

    code = builder.export_task_python_module(task)
    assert "@task" in code
    assert "def inspect_code_agent()" in code
    assert "MemoryDataset" in code

    # Verify python syntax is valid AST
    parsed_ast = ast.parse(code)
    assert isinstance(parsed_ast, ast.Module)
