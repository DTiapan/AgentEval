# Lessons learned (LL)

Blameless capture of surprises, failed approaches, and reusable principles.

## Active index

| ID | Title | Status | Scope | Category |
|----|-------|--------|-------|----------|
| LL-001 | Rich Terminal Bracket Escaping and Pydantic Model Reordering | logged | project | architecture / tooling |
| LL-002 | Disk-Cached Persona Synthesis for Sub-50ms CLI Startup and Zero-Token Re-runs | logged | project | performance / architecture |
| LL-003 | Operational Tier Stack-Ranking & Multi-Vendor LLM Gateway via LiteLLM | logged | project | architecture / llm |

---

## LL-003: Operational Tier Stack-Ranking & Multi-Vendor LLM Gateway via LiteLLM

- **Date**: 2026-09-20
- **Scope**: project
- **Context**: Static persona catalogs suffer from maintenance burden and cannot capture bespoke customer niches. Pointing raw LLMs at persona generation produces unstructured, unranked lists that vary wildly across vendors.
- **Root Cause**: Without standard operational tiers and unified API abstractions, teams end up hardcoding vendor SDKs (OpenAI, Anthropic, Gemini) and testing dozens of low-value edge personas.
- **Lesson / Rule**: Use `litellm` as the universal provider gateway. Constrain dynamic persona generation to 5 operational tiers (Frequent Users, Power Users, Adversaries, Novice, Security Auditors) with strict Pydantic JSON schema validation and `--top-personas` windowing to control test suite breadth.

---

## LL-002: Disk-Cached Persona Synthesis for Sub-50ms CLI Startup and Zero-Token Re-runs

- **Date**: 2026-09-20
- **Scope**: project
- **Context**: When running `agenteval plan --endpoint ...` or `agenteval run --endpoint ...`, generating complete persona specifications via LLM on every CLI invocation adds 1-3 seconds of network latency and token costs.
- **Root Cause**: Personas for standardized roles (e.g. SRE, Frontend, DBRE, Security Auditor) are largely invariant once generated for a specific agent archetype.
- **Lesson / Rule**: Store generated persona markdown in `.agenteval/personas/{slug}.md` with frontmatter, identity, core mission, and critical invariants. Check local cache before remote generation. On cache hit, load instantly (<1ms); on miss, synthesize, persist to disk, and display `[SYNTHESIZED]` vs `[CACHED]` status in the CLI.

---

## LL-001: Rich Terminal Bracket Escaping and Pydantic Model Reordering

- **Date**: 2026-09-20
- **Scope**: project
- **Context**: During CLI live streaming and TraceReplayer unit test implementation, bracketed tokens like `[key=xyz]` or `[ΔS mutated]` were being interpreted by Rich as markup/style tags and silently stripped when rendering to plain or unstyled consoles. Furthermore, in Pydantic v2 domain models, cross-referencing types (`ReliabilityScorecard` inside `ExecutionTrace`) requires either forward reference updates or strict topological definition ordering.
- **Root Cause**: Rich treats all single square brackets `[...]` as markup instructions unless escaped as `\[...]`. Pydantic models referencing each other fail static type evaluation if dependent models are defined after the parent without postponed annotations.
- **Lesson / Rule**: Always escape literal brackets in Rich console render strings (`\[key=...]`). Structure Pydantic domain models in bottom-up topological dependency order.

<!-- New entries above ## Archive -->

## Archive

<!-- Resolved lessons optionally summarized here -->
