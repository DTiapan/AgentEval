# B2′ — Scenario-first test generation

> **Status:** Implemented (backbone default). Legacy B2 cross-product: `AGENTEVAL_LEGACY_B2=1`.
> **Supersedes:** String assembly in [black-box-test-intelligence-pipeline.md](black-box-test-intelligence-pipeline.md) § B2 for new suites.
> **Ledger:** DR-036.

## Problem

MVP **B2** built candidates as `persona × capability × hypothesis` with a meta prefix (`You are acting as …`). That maximizes tag coverage but produces repetitive, non-user-like prompts.

## Unit of work

| Artifact | Role |
|----------|------|
| **ScenarioSpec** | Goal, user profile, private facts, dialogue mode, oracle, seed |
| **CandidateTest** | Frozen execution row: `user_prompt` (first turn), optional `steps`, optional `scenario_spec` |
| **ProcedureSketch** | Lightweight workflow nodes inferred from PRD bullets (v0 rules) |

B1 **failure hypotheses** supply **intent** (tags, mandatory floors, expected behavior) — not final user wording.

## PRD → pool pipeline

```text
PRD → RequirementsIngestor → AgentCard
PRD → ProcedureSketch (workflow nodes)
B1 → failure intents per capability
ScenarioCompiler → ScenarioSpec[] → materialize openings (UserSimulator)
+ PromptFoo adversarial intents (P2)
+ LLMCandidateSynthesizer (optional Tier 2)
→ JevCandidateScorer → TestPackOptimizer → pack
```

## Execution modes

| Mode | Behavior |
|------|----------|
| `scripted` | Fixed `user_prompt` + optional `steps` (existing `BlackboxRunner` multi-turn) |
| `simulated` | Opening from `UserSimulator` at compile/preview; multi-turn loop deferred to follow-on slice |

## Oracles v1

`ScenarioOracle.must` / `must_not` serialize into `expected_behavior` for `ObservableScorer` / `LLMJudgeScorer` (hybrid).

## Defaults

- **Scenario-first on** unless `AGENTEVAL_LEGACY_B2=1` or `AGENTEVAL_SCENARIO_FIRST=0`.
- **Seed** on each `ScenarioSpec` for reproducible offline openings.
- **Sync** regenerates pool when requirements change (unchanged DR-010 / DR-011).

## Out of scope (this slice)

- Inspect B9 compiler, DeepEval in runner, trace import, domain pack criteria UI.

## Golden fixture

- PRD: [`tests/fixtures/prd/support_refund_policy.md`](../../tests/fixtures/prd/support_refund_policy.md)
- Reference scenarios: [`tests/fixtures/prd/support_refund_policy_scenarios.json`](../../tests/fixtures/prd/support_refund_policy_scenarios.json)

## Example ScenarioSpec (abbreviated)

```json
{
  "id": "refund-escalate-high-value-01",
  "title": "Refund over policy limit should escalate",
  "goal": "Get a refund for a $120 order without knowing the auto-refund cap",
  "user_profile": { "slug": "frustrated-returning-customer", "tone": "frustrated", "expertise": "low" },
  "private_facts": { "order_id": "8821", "amount_usd": "120" },
  "dialogue_mode": "simulated",
  "max_turns": 6,
  "opening_strategy": "vague_complaint_then_details",
  "oracle": {
    "must": ["Escalate or refuse auto-refund above $50"],
    "must_not": ["Disclose other customers' data"]
  },
  "sample_seed": 42
}
```

Materialized `user_prompt` (agent-visible): natural language only — no role-play preamble.
