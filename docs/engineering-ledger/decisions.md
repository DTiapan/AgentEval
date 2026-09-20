# Tactical decisions (DR)

Decisions reversible without a formal ADR. Promote to `docs/decisions/` when reversal cost is high.

## Active index

| ID | Title | Status | Date |
|----|-------|--------|------|
| ADR-001 | [Build on Inspect AI as Evaluation Engine Foundation](../decisions/ADR-001-build-on-inspect-ai.md) | Accepted | 2026-09-20 |
| DR-001 | Adopt Jev (TypeSafe AI System One) as Tier 1 judge — 40–200x faster than LLM-as-a-Judge for typed classification scoring. Confidence gating pattern: escalate to Tier 2 LLM when Jev confidence < 0.7. Ships in v0.3. | Accepted | 2026-09-20 |
| DR-002 | Adopt pass^k (reliability floor) alongside pass@k (capability ceiling) as dual metrics. Research shows 60% pass@1 agents can drop to 25% pass^3. Ships in v0.2. | Accepted | 2026-09-20 |
| DR-003 | Implement FirstUnrecoverableStepScorer for compounding error root-cause attribution (inspired by AgentRx). Ships in v0.2. | Accepted | 2026-09-20 |

---

<!-- New entries above ## Archive -->

## Archive

<!-- Superseded decisions moved here with Superseded-by link -->
