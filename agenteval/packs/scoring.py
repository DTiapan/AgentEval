"""Score acceptance criteria using pack checks or blackbox mirror."""

from agenteval.packs.check_registry import discover_pack_checks, resolve_check_by_kind
from agenteval.packs.protocol import CriterionVerdictDraft

CHECK_KIND_BLACKBOX = "blackbox_observable"


def score_criterion(
    *,
    check_kind: str,
    test_verdict: str,
    test_rationale: str,
    criterion_stable_id: str,
    criterion_description: str,
    evidence_items: list[dict[str, str]],
) -> CriterionVerdictDraft:
    if check_kind == CHECK_KIND_BLACKBOX:
        return CriterionVerdictDraft(
            verdict=test_verdict,
            rationale=test_rationale,
            evidence_item_ids=[
                e["id"] for e in evidence_items if test_verdict in ("PASS", "FAIL")
            ],
        )

    checks = discover_pack_checks()
    check_fn = resolve_check_by_kind(check_kind, checks)
    if check_fn is None:
        return CriterionVerdictDraft(
            verdict="UNVERIFIABLE",
            rationale=f"No pack check registered for check_kind '{check_kind}'.",
            evidence_item_ids=[],
        )

    return check_fn(
        criterion_stable_id=criterion_stable_id,
        criterion_description=criterion_description,
        evidence_items=evidence_items,
    )
