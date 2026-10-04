"""Lightweight procedure / workflow sketch from PRD text (B2′ v0)."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field


class WorkflowNode(BaseModel):
    """Single inferred workflow step or policy constraint."""

    model_config = ConfigDict(extra="forbid")

    node_id: str
    label: str
    kind: str = Field(default="policy", description="policy | workflow | guard")


class ProcedureSketch(BaseModel):
    """Bounded graph summary from requirements text."""

    model_config = ConfigDict(extra="forbid")

    nodes: list[WorkflowNode] = Field(default_factory=list)


_POLICY_PATTERNS: list[tuple[str, str, str]] = [
    (r"without\s+.{0,40}order\s+id", "need_order_id", "guard"),
    (r"escalat", "escalate", "workflow"),
    (r"\$\s*50|50\s*\$|above\s+\$?\d+", "amount_threshold", "policy"),
    (r"refund", "refund_flow", "workflow"),
    (r"pii|personal", "no_pii", "guard"),
    (r"irrevers", "irreversible", "guard"),
]


def sketch_from_prd(prd_text: str | None) -> ProcedureSketch:
    """Rule-based extraction of workflow/policy nodes (no LLM)."""
    if not prd_text or not prd_text.strip():
        return ProcedureSketch()
    lower = prd_text.lower()
    nodes: list[WorkflowNode] = []
    seen: set[str] = set()
    for pattern, node_id, kind in _POLICY_PATTERNS:
        if re.search(pattern, lower) and node_id not in seen:
            seen.add(node_id)
            label = node_id.replace("_", " ")
            nodes.append(WorkflowNode(node_id=node_id, label=label, kind=kind))
    return ProcedureSketch(nodes=nodes)
