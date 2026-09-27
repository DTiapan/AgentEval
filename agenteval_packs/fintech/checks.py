"""Fintech pack deterministic checks (v0)."""

from agenteval.packs.protocol import CriterionVerdictDraft


def audit_refund_check(
    *,
    criterion_stable_id: str,
    criterion_description: str,
    evidence_items: list[dict[str, str]],
) -> CriterionVerdictDraft:
    audit_items = [e for e in evidence_items if e.get("kind") == "audit_log"]
    if not audit_items:
        return CriterionVerdictDraft(
            verdict="UNVERIFIABLE",
            rationale="No audit_log evidence captured for this case.",
            evidence_item_ids=[],
        )

    item = audit_items[-1]
    import json

    payload = json.loads(item.get("payload_json", "{}"))
    rows = payload.get("rows") or []
    expected = str(payload.get("expected_action") or "refund")
    matched = [r for r in rows if str(r.get("action", "")).lower() == expected.lower()]
    if matched:
        return CriterionVerdictDraft(
            verdict="PASS",
            rationale=f"Audit log contains action '{expected}'.",
            evidence_item_ids=[item["id"]],
        )
    if rows:
        actions = ", ".join(str(r.get("action")) for r in rows)
        return CriterionVerdictDraft(
            verdict="FAIL",
            rationale=f"Audit log rows present but none match expected action '{expected}' ({actions}).",
            evidence_item_ids=[item["id"]],
        )
    return CriterionVerdictDraft(
        verdict="FAIL",
        rationale="Audit log query returned no rows.",
        evidence_item_ids=[item["id"]],
    )
