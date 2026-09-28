# Tactical decisions (DR)

Decisions reversible without a formal ADR. Promote to `docs/decisions/` when reversal cost is high.

## Active index

| ID | Title | Status | Date |
|----|-------|--------|------|
| ADR-001 | [Build on Inspect AI as Evaluation Engine Foundation](../decisions/ADR-001-build-on-inspect-ai.md) | Accepted | 2026-09-20 |
| ADR-002 | [Dynamic Persona Synthesis, Stack-Ranking & Multi-Vendor LiteLLM Gateway](../decisions/ADR-002-dynamic-persona-synthesis-litellm.md) | Accepted | 2026-09-20 |
| DR-001 | Adopt Jev (TypeSafe AI System One) as Tier 1 judge — 40–200x faster than LLM-as-a-Judge for typed classification scoring. Confidence gating pattern: escalate to Tier 2 LLM when Jev confidence < 0.7. Ships in v0.3. | Accepted | 2026-09-20 |
| DR-002 | Adopt pass^k (reliability floor) alongside pass@k (capability ceiling) as dual metrics. Research shows 60% pass@1 agents can drop to 25% pass^3. Ships in v0.2. | Accepted | 2026-09-20 |
| DR-003 | Implement FirstUnrecoverableStepScorer for compounding error root-cause attribution (inspired by AgentRx). Ships in v0.2. | Accepted | 2026-09-20 |
| DR-004 | Implement Real-Time & Interactive Trajectory Replay (`agenteval replay` & live streaming) as a core capability. Enables step-by-step playback, time-travel debugging, jump-to-failure spotlighting, and side-by-side golden vs failing diff. Ships starting in v0.1. | Accepted | 2026-09-20 |
| DR-005 | Adopt 8-Plane Agent Reliability & Chaos Engineering Architecture. Extends evaluation unit from (Prompt -> Response) to (Agent x Environment x Scenario x FaultPlan). Incorporates ToolFaultInjector, IdempotencyScorer (duplicate_side_effect_rate), and Process Crash/Recovery Harness. | Accepted | 2026-09-20 |
| DR-006 | Adopt Plane 0 (Agent Contract, Discovery & Requirement Engineering) and Archetype-Driven Metric Segregation with Jev Metric Router. Formalizes PRD-to-Scenario compilation, MCP/OpenAPI auto-introspection, and specialized profiles (Tool, RAG, Code, Support, Swarm). | Accepted | 2026-09-20 |
| DR-007 | Ingest Agency-Agents Persona Corpus, Support Live HTTP BYOA Endpoints, and Integrate TypeSafe AI / Jev Typed Classification with Air-Gapped Fallback. Eliminates metric selection friction by deriving evaluation suites, invariants, and chaos fault plans directly from persona/PRD specs. | Accepted | 2026-09-20 |
| DR-008 | On-the-Fly Dynamic Persona Synthesis, Jev Selection & Local Disk Caching. Maintain a 35+ candidate persona catalog across Engineering, SRE, Security, Data, and Support. Select top matching personas with sub-50ms typed Jev inference, synthesize complete persona specifications on the fly, and persist in `.agenteval/personas/{slug}.md` for zero-latency reuse. | Accepted | 2026-09-20 |
| DR-009 | **Black-box-first evaluation** for enterprise customers: default **`blackbox`** execution profile (endpoint-observable evidence only). Retain v0.1 **`harness`** profile (sandbox ΔS, fault injection) as opt-in for in-process BYOA. Product pipeline = understand → hypothesize → candidate pool → risk → **set-cover optimization** → execute pack → coverage → gap-targeted re-test. Formalized in [ADR-003](../decisions/ADR-003-black-box-test-intelligence-pipeline.md); implemented via [AP-003](attack-plans.md#ap-003-black-box-test-intelligence-pipeline-v02v03). | Accepted | 2026-09-20 |
| DR-010 | **Frozen regression suite:** On first bootstrap (requirements + endpoint), generate the optimized test pack **once** and persist under `.agenteval/suites/<agent_id>/` as the versioned source of truth. Subsequent runs **load and execute** that suite for regression (“what broke?”)—**no implicit regeneration** on `run` or CI. New generation only via explicit `suite regenerate` (new version) or append-only extend (gap loop). Spec: [Frozen regression suite](../design/black-box-test-intelligence-pipeline.md#frozen-regression-suite-generate-once-run-many). | Accepted | 2026-09-20 |
| DR-012 | **Minimum-friction entry (requirements-first):** Primary inputs = **functional requirements** (PRD/upload text) + optional **HTTP endpoint**; AgentEval derives personas, test pack, and runs—users do not author scenario YAML or AgentCard by default. **Delivery ordering superseded by [DR-021](#active-index)** (Web UI + API first). Harness scenario YAML remains **low-priority / advanced** framework path. | Superseded (ordering) | 2026-09-20 |
| DR-011 | **Suite pruning on capability removal:** When a capability is **removed** from requirements/manifest, drop (archive) regression tests **linked to that capability** on the next explicit `suite sync` / `regenerate` / `migrate` after spec update—never on plain `suite run`. Changelog records removed test IDs. Added capabilities use extend/regen append only. Spec: [Pruning when functionality is removed](../design/black-box-test-intelligence-pipeline.md#pruning-when-functionality-is-removed). | Accepted | 2026-09-20 |
| ADR-003 | [Black-Box Test Intelligence Pipeline & Dual Execution Profiles](../decisions/ADR-003-black-box-test-intelligence-pipeline.md) | Accepted | 2026-09-20 |
| DR-013 | **Modernized Web Console (SoftQA Pattern, Obsidian Palette, Multi-Tenant SaaS Ready):** Overhauled `web/` into a React 19 + Tailwind v4 + Shadcn-style developer console modeled after SoftQA reference templates: technical blueprint dotted grid, dark code & test inspector terminal with window dots, test candidate tabs, collapsible coverage/gaps tree, and micro-metric cards. Obsidian slate palette (`#080C14` / `#0F172A` / `#1E293B`) with indigo & emerald accents strictly eliminating dark teal. State architected via `WorkspaceContext` for seamless transition to cloud SaaS while compiling to standalone static assets (`web/dist/`) served natively by FastAPI (`agenteval serve --with-ui`). | Accepted | 2026-09-20 |
| DR-014 | **Persona-Driven UX Architecture (`ux-planner` Skill), Precision Neutral Dark Theme & Standalone Report Alignment:** Grounded in `msitarzewski/agency-agents` Design Division (`ArchitectUX`, `UI Designer`, `Persona Walkthrough Specialist`) and `ui-ux-pro-max`. Formulated 3-Persona Matrix (Alex Chen, Maya Patel, Marcus Vance) and complete wireframes in `docs/design/ux-wireframes.md`. Refactored console UI and Allure-class HTML report to strictly adhere to the matte neutral dark developer theme (`#09090B`, `#121214`, `#0D0E11`, `#27272A`, `#FAFAFA`), eliminating dotted grid noise and teal gradients. Implemented Wireframe 1-4 elements: split-pane column headers, clean test candidate tab slugs (`[01 refund-auth]`), test case capability badges (`cap: refund_process • 18ms`), instant 0-regression clean diff banners, and in-app standalone report modal viewer. | Accepted | 2026-09-20 |
| DR-015 | **True Shadcn UI Primitives & Radix Primitives Migration:** Integrated genuine Shadcn UI components into `web/src/components/ui/` (`Button`, `Card`, `Badge`, `Tabs`, `Dialog`, `Slider`, `Input`, `Textarea`, `Separator`, `Tooltip`) leveraging Radix UI primitives (`@radix-ui/react-slot`, `@radix-ui/react-tabs`, `@radix-ui/react-dialog`, `@radix-ui/react-slider`, `@radix-ui/react-separator`, `@radix-ui/react-tooltip`), `class-variance-authority`, `clsx`, and `tailwind-merge` with standard `@/*` path aliases. Upgraded `Studio.tsx`, `AssuranceView.tsx`, and `Header.tsx` to compose these accessible, fully typed primitives while preserving the pristine Linear / Vercel Pro neutral dark aesthetic (`#09090B` canvas, `#121214` surface cards, `#27272A` borders). | Accepted | 2026-09-20 |
| DR-016 | **Ready-Made Component Blocks Integration (Resizable Panels, Monaco Editor, Shadcn Data Table):** Integrated production-grade ready-made component blocks into `web/`: `react-resizable-panels` (`ResizablePanelGroup`, `ResizablePanel`, `ResizableHandle`) for draggable split-pane views in both Studio and Assurance Runs, `@monaco-editor/react` (`CodeViewer`) for VS Code syntax highlighting, line numbers, and search across TypeScript test specs and JSON evidence traces, and Shadcn `Table` for structured test case telemetry. | Accepted | 2026-09-20 |
| DR-017 | **Shadcn Custom Oklch Theme & Dynamic Light/Dark Mode Integration:** Applied the exact custom Shadcn design tokens provided by the user (`oklch` grayscale surfaces, light background `#f8f9fa` with crisp `#ffffff` cards and `#f1f3f5` inputs, dark background `#1a1b1e` with progressive dark surfaces, subtle borders, shadows set to 0, royal purple primary `--primary: oklch(0.5547 0.2503 297.0156)` matching reference templates, Inter/JetBrains Mono typography with `-0.011em` tracking). Integrated Sun/Moon theme switcher in Header with localStorage persistence. | Accepted | 2026-09-20 |
| DR-018 | **UI Theme Token Harmonization, Floating Card Layout & Production Bundle Rebuild:** Resolved root-cause visual regression where an unbuilt bundle was serving the old pitch-black canvas (`bg-[#09090B]`) and fused split-pane container. Refactored Studio and AssuranceView to render independent, floating `<Card>` primitives (`gap-6` grid) over the soft `#f8f9fa` / `#1a1b1e` canvas. Harmonized all Shadcn UI primitives (`card`, `tabs`, `slider`, `tooltip`, `dialog`, `resizable`, `separator`, `table`) to eliminate hardcoded `zinc` classes in favor of semantic CSS variables (`text-card-foreground`, `bg-muted`, `border-border`). Rebuilt `web/dist` cleanly (1.12s); full suite passes 113 tests at 86.16% coverage; 0 ruff/mypy errors. | Accepted | 2026-09-20 |
| DR-020 | **SQLite v1 persistence schema (ADR-004):** Relational model for workspaces, users, agents, frozen `suite_versions`, `assurance_runs`, `test_case_results`, and `execution_steps` (sealed trajectories). Default embedded DB at `.agenteval/agenteval.db`; JSON `SuiteStore` remains import/export path. DDL: `agenteval/db/schema.sql`; design: `docs/design/persistence-schema.md`. Postgres later with same logical schema. | Accepted | 2026-09-21 |
| DR-021 | **Web UI-first product delivery (supersedes DR-012 ordering):** Primary onboarding = **`agenteval serve`** + **Web Console** (Studio → freeze → Assurance → Replay) backed by **`SuiteWorkflow`** and **`/v1/suites/*`** with **SQLite-primary** persistence ([ADR-004](../decisions/ADR-004-sqlite-local-persistence.md)). New product slices ship API + UI first; **Typer** remains for `serve`, engineering `suite *`, harness `run`, and `db import-suites` — no new customer-facing flows CLI-only. Spec drift / sync targets **API + Studio**, not `agenteval suite sync` as the default path. | Accepted | 2026-09-21 |
| DR-022 | **Real-agent reference target (not keyword mocks):** Default sample for product learning is `examples/real-agent/` — LangChain/LangGraph ReAct + SQLite tools (`lookup_ticket`, `list_customer_tickets`, `update_ticket_status`, `delete_ticket`) on `POST /chat`. Rule-based `examples/blackbox/` mocks remain **fixtures** for CI without an API key, not the evaluation north star. Next slices: post-run ΔS on `.agenteval/real-agent-ops.db`, then **Jev as Tier-1 typed judge** (DR-001) on traces — not more mock agents. | Accepted | 2026-09-21 |
| DR-023 | **LangWatch OSS architecture lessons — assurance appliance, integrate don’t rebuild:** Category validation from [langwatch/langwatch](https://github.com/langwatch/langwatch) (control plane PG + data plane ClickHouse, event-sourced workers, LangEvals sidecar, connected-agent relay). AgentEval stays **library + FastAPI + SQLite**, **verdict-first** (`PASS`/`FAIL`/`UNVERIFIABLE`), **PRD → frozen set-cover pack**; **emit** OTel from runs, **do not** ingest at LangWatch scale. Selective pattern adoption only (run isolation, optional outbound connect, trace→gap with provenance). See full entry below. | Accepted | 2026-09-21 |
| DR-024 | **Rule-Based Failure Hypothesis Catalog Expansion (Floor Layer) & ObservableScorer Tier-0 Hardening:** Expanded hypothesis templates from 9 → 25 across Functional, Edge, Security, Reliability, and Abuse categories, achieving 100% coverage of all 8 `MandatoryCategory` floors (`DATA_ISOLATION`, `PRIVILEGE_ESCALATION`, `TOOL_OUTPUT_INJECTION`, `CRITICAL_INVARIANTS`, `AUTHORIZATION`, `PROMPT_INJECTION`, `SENSITIVE_DATA_LEAKAGE`, `IRREVERSIBLE_ACTIONS`). Added `CapabilitySignals` flags (`has_external_dependency`, `has_multi_step`, `has_rate_limit`, `has_concurrency`, `is_read_only`). Hardened `ObservableScorer` heuristic evaluation and fixed transport failure status detection. | Accepted | 2026-09-27 |
| DR-025 | **Production-Grade Assurance Appliance Architecture (Priority Tiering, PromptFoo Bridge, DeepEval Bridge, Inspect AI Sandbox & Deterministic State-Diff Hardening):** Formalized the 3-tier assurance hierarchy (`P0 Critical Floors`, `P1 Recommended Workflows`, `P2 Adversarial & Fuzzing`) backed by marginal coverage curves and interactive execution budget controls. Integrated PromptFoo red-team bridge synthesizing 7 OWASP attack vectors; DeepEval trajectory semantic metrics (`ToolCorrectness`, `PlanAdherence`, `TaskCompletion`, `Hallucination`) with offline deterministic fallbacks; Inspect AI Docker sandbox task builder & JSONL dataset exporter; and hardened deterministic multi-table state-diff ($\Delta S$) assertions emitting `UNVERIFIABLE` when mutation evidence is missing. | Accepted | 2026-09-27 |
| DR-026 | **3-Tier Test Generation & Selection Backbone (LLM Synthesizer + Jev Quality Scorer + Real Ops Agent Target):** Implemented Tier 2 LLMCandidateSynthesizer (LiteLLM/DeepSeek with deterministic fallback) and Tier 3 JevCandidateScorer (multi-axis evaluation across severity, novelty, flakiness risk, and execution cost with P0 floor enforcement). Wired live reference IT Ops agent with real SQLite tools and state mutations on `http://127.0.0.1:8770/chat`. Agent deletion and cascading cleanup preserved as deferred. | Accepted | 2026-09-27 |
| DR-027 | **Switchable Tier-2 LLM-as-a-Judge Evaluation Backbone & BlackboxRunner Escalation:** Implemented `LLMJudgeScorer` using LiteLLM (DeepSeek / OpenRouter / OpenAI) with deterministic offline fallback. Introduced `JudgeMode` (`HYBRID`, `DETERMINISTIC_ONLY`, `LLM_JUDGE`). In `HYBRID` mode (default), deterministic heuristics run first; if an open-ended candidate has no rule match, `BlackboxRunner` automatically escalates to `LLMJudgeScorer` instead of stalling at `UNVERIFIABLE`. Upgraded `DeepEvalBridge` to support LiteLLM/OpenRouter keys. Verified live against the real IT Ops Agent (`:8770/chat`). | Accepted | 2026-09-28 |


---

### DR-026 — 3-Tier Test Generation & Selection Backbone: LLM Candidate Synthesizer, Jev Quality Filter, and Real-Agent Verification Target

- **Date:** 2026-09-27
- **Status:** accepted
- **Context:** While rule-based templates provide a solid security floor, generating comprehensive assurance packs for arbitrary agent specifications requires synthesizing contextual edge cases without producing unvalidated AI slop or running hundreds of redundant, low-value tests. Furthermore, evaluations must be verified against genuine, tool-calling agents rather than keyword mocks.
- **Options:**
  1. **Run All Raw Generated Tests:** Send 200–500 unvalidated LLM prompts directly to the agent without quality filtering or set-cover optimization.
  2. **Rule-Only Floor:** Restrict testing strictly to static rule templates, omitting contextual reasoning edge cases.
  3. **3-Tier Generation & Selection Pipeline with Jev Quality Scorer:** (Tier 1) Rule-based hypothesis templates for mandatory floors; (Tier 2) LLM candidate synthesis powered by LiteLLM / DeepSeek; (Tier 3) Jev multi-axis quality filter (grading severity, novelty, flakiness, and cost) pruning slop before set-cover optimization. Tested against a live LiteLLM IT Ops agent mutating SQLite.
- **Decision:** **Option 3.**
  1. **Tier 2 LLM Candidate Synthesizer (`agenteval/planning/llm_candidate_synthesizer.py`):** Integrates LiteLLM to synthesize boundary, contradiction, whitespace/casing, and edge-case tests with DeepSeek reasoning content, backed by a deterministic heuristic generator for $0-cost airgapped CI.
  2. **Tier 3 Jev Candidate Scorer (`agenteval/planning/jev_candidate_scorer.py`):** Filters candidate pools using multi-axis scoring: Severity ($\ge 0.7$ for security/safety/critical), Novelty (token-level Jaccard uniqueness against existing pool), Flakiness Risk (vague words, underspecified expectations), and Execution Cost. Discards slop and duplicates ($Q < 0.35$ or Novelty $< 0.20$), while strictly preserving P0 mandatory security floors.
  3. **Real Agent Target (`examples/real-agent/ops_agent_server.py`):** Deployed a live IT Ops agent on `http://127.0.0.1:8770/chat` running LiteLLM with DeepSeek reasoning and 4 real SQLite tools mutating `.agenteval/real-agent-ops.db`.
  4. **Agent Deletion Scope Alignment:** Per user instruction, agent deletion and cascading database removal (`E-AGENT-05`) are kept on the roadmap and specification as deferred for future implementation.
- **Consequences:** Provides a complete, production-grade test intelligence backbone generating high-signal, slop-free test packs with verified real-agent tool execution. 206 tests passing at 86.71% coverage with clean typing and linting.

---

<!-- New entries above ## Archive -->

### DR-023 — LangWatch OSS architecture lessons (assurance appliance vs LLMOps platform)

- **Date:** 2026-09-21
- **Status:** accepted
- **Context:** LangWatch ships a large open-core monorepo (App + Workers + PostgreSQL + Redis + ClickHouse + S3 + LangEvals/NLP + optional AI Gateway). Agent Testing overlaps our surface (scenarios, suites, judges, CI). We need a durable guardrail so slices do not drift into rebuilding their data platform.
- **Options:**
  1. **Parity chase** — replicate observability lake, evaluator microservice, feature-map across CLI/MCP/SDK/UI.
  2. **Assurance appliance** — minimal deploy (single process + SQLite), integrate with customer or vendor OTel for traces; borrow only high-leverage patterns.
  3. **Fork/embed LangWatch** — reuse their stack for assurance runs.
- **Decision:** **(2) Assurance appliance.** Validate the category; **do not** chase LangWatch feature parity ([ROADMAP](../ROADMAP.md) competitive section). Promote **integrate/partner** for observability, prompt loops, and evaluator catalogs.
- **Rationale:** Their moat is **telemetry scale + loop engineering** (ingest → project → monitor → improve). Our moat is **sealed proof or honest `UNVERIFIABLE`**, **requirements-driven pack optimization**, and **BYOA black-box** with boring self-host ([DR-009](decisions.md#active-index), [DR-010](decisions.md#active-index), [DR-021](decisions.md#active-index)).
- **LangWatch architecture (reference, not target):**
  - **Control plane:** PostgreSQL (Prisma) — users, projects, prompts, suite config.
  - **Data plane:** ClickHouse — traces, analytics, event-sourcing events/projections.
  - **Processing:** Workers + custom Redis **GroupQueue** (per-aggregate FIFO for fold projections).
  - **Agent testing:** `@langwatch/scenario`, sandboxed child with prefetched data; **connected agents** via outbound WebSocket relay ([ADR-128](https://github.com/langwatch/langwatch/blob/main/dev/docs/adr/128-connected-agents.md) in upstream repo).
  - **Evaluators:** separate **LangEvals** Python service; online monitors and guardrails on trace stream.
  - **Commercial:** enterprise modules under `platform/app/ee/` (SSO, SCIM, billing, audit) — same artifact, license-gated.
- **Explicit non-goals (unless strategy changes):** full **LLM observability product**, **AI gateway / corp governance plane**, **prompt registry + Langy auto-PR loop**, **voice/multimodal simulation platform**, **LangEvals-scale built-in judge catalog**, **feature-map parity** across four product surfaces. Documented in [ROADMAP](../ROADMAP.md#competitive-landscape--positioning).
- **Selective adoption (when a slice needs it):**
  | Pattern | AgentEval use | Guardrail |
  |---------|---------------|-----------|
  | Multi-turn HTTP simulation | v0.3+ runner | Persist real `execution_steps` only ([no-demo-ui-data](../../.cursor/rules/no-demo-ui-data.mdc)) |
  | Connected-agent relay | Optional `connect` later | Same as HTTP black-box evidence rules |
  | Run isolation (child/prefetch) | Heavy sim workers | Security + cancel; not a second platform DB |
  | Trace → candidate test | v0.3–0.4 gap loop | Provenance `INFERRED`, cite source run id |
  | OTel | v0.5+ **export** from assurance runs | Customer’s Phoenix/LangWatch/LangSmith ingests; we do not replace CH |
  | LLM judge | Tier-2 overlay ([DR-001](decisions.md#active-index)) | Never invent side-effects; never downgrade `UNVERIFIABLE` |
- **Tradeoffs accepted:** No real-time trace explorer, instant evals at 10k rows/min, or enterprise SSO in core OSS v1 — by design.
- **Links:** [ROADMAP — Competitive Landscape](../ROADMAP.md#competitive-landscape--positioning), [LangWatch self-host architecture](https://langwatch.ai/docs/self-hosting/infrastructure/architecture.md), upstream [FEATURE_MAP.md](https://github.com/langwatch/langwatch/blob/main/FEATURE_MAP.md).

### DR-024 — Rule-Based Failure Hypothesis Catalog Expansion & ObservableScorer Tier-0 Hardening

- **Date:** 2026-09-27
- **Status:** accepted
- **Context:** AgentEval's black-box test generation previously generated candidates using only 9 hardcoded hypothesis templates in `hypothesis_catalog.py`, leaving 4 out of 8 `MandatoryCategory` safety floors completely unpopulated (`DATA_ISOLATION`, `PRIVILEGE_ESCALATION`, `TOOL_OUTPUT_INJECTION`, `CRITICAL_INVARIANTS`). Additionally, `CapabilitySignals` only evaluated 4 coarse flags, and `ObservableScorer` had heuristic rules for only 6 templates, misclassifying transport failures on HTTP 200 responses mentioning "timed out".
- **Decision:**
  1. Expand hypothesis template catalog from 9 → 25 templates across Functional, Edge, Security, Reliability, and Abuse categories.
  2. Achieve 100% population for all 8 `MandatoryCategory` safety floors.
  3. Expand `CapabilitySignals` with 5 new flags (`has_external_dependency`, `has_multi_step`, `has_rate_limit`, `has_concurrency`, `is_read_only`) with refined mutation-vs-read-only signal resolution.
  4. Expand `ObservableScorer` with deterministic heuristic rules for all 25 templates, checking false success claim tokens before keyword matching and fixing `_is_transport_failure` to require HTTP >= 500.
  5. Fix Session 28 `requirement_id` hash transition test expectations across test files.
- **Consequences:** Provides a rock-solid, deterministic rule-based floor (Layer 1 of 3-layer pipeline) before LLM-based generation (Layer 2) and Jev multi-axis scoring (Layer 3). Full suite passes with 166 tests and 86.19% coverage.


### DR-025 — Production-Grade Assurance Appliance Architecture: Priority Tiering and Pragmatic OSS Bridges

- **Date:** 2026-09-27
- **Status:** accepted
- **Context:** Enterprise users deploying agents against PRD specifications face two core dilemmas: (1) "Which metrics and test cases should I run without wasting budget running 500 tests?", and (2) "How do we leverage standard evaluation tools without locking into heavyweight external cloud dependencies or compromising deterministic evidence?"
- **Options:**
  1. **Monolithic custom evaluator expansion:** Build every evaluator, red-team fuzzer, and sandbox runner from scratch in-house.
  2. **External SaaS dependency:** Mandate cloud PromptFoo / DeepEval / Inspect SaaS accounts and API keys.
  3. **Zero-bloat OSS bridges with offline deterministic fallback + Priority Tiering:** Integrate PromptFoo (adversarial attacks), DeepEval (trajectory semantics), and Inspect AI (Docker container sandbox specifications) as pluggable bridges with 100% offline deterministic heuristic fallbacks and an interactive 3-tier marginal coverage optimizer.
- **Decision:** **Option 3.**
  1. **No Hardcoded Test Counts / No Blame:** Replace arbitrary cutoffs with a 3-tier hierarchy (`P0 Critical Floors`, `P1 Recommended Workflows`, `P2 Adversarial & Fuzzing`) backed by a greedy marginal coverage curve ($R(C)/N$) and dynamic budget projections.
  2. **Interactive Budget Controls in Studio UI:** Expose a budget ceiling slider dynamically bound to candidate pool size, allowing users to tune execution budget and inspect test tiers before freezing suites.
  3. **PromptFoo Adversarial Bridge:** Synthesize OWASP Top 10, jailbreak, BOLA, and PII leakage probes into candidate tests, exporting PromptFoo YAML configurations and providing deterministic offline generation.
  4. **DeepEval Trajectory Metric Bridge:** Support semantic metric evaluation (`ToolCorrectness`, `PlanAdherence`, `TaskCompletion`, `Hallucination`) with zero-dependency offline deterministic heuristic fallbacks for CI and airgapped environments.
  5. **Inspect AI Sandbox Bridge:** Provide Docker container sandbox specifications and Inspect AI Task / dataset JSONL exports for code/shell agents per ADR-001 & ADR-005.
  6. **Deterministic Evidence vs Self-Report:** Hardened multi-table state diffs ($\Delta S$); explicitly emits `UNVERIFIABLE` whenever environmental mutation proof is missing or unsealed.
- **Consequences:** Eliminates vendor lock-in and high cloud eval bills while giving users enterprise-grade test generation, transparent priority tiering, and sealed evidence sign-off reports.

---

### DR-027 — Switchable Tier-2 LLM-as-a-Judge Evaluation Backbone & BlackboxRunner Escalation

- **Date:** 2026-09-28
- **Status:** accepted
- **Context:** `BlackboxRunner` previously evaluated responses using only Tier-0 `ObservableScorer`, which checked 25 static heuristic templates. Synthesized open-ended or LLM-generated tests without static regex rules defaulted to `UNVERIFIABLE: No heuristic rule match for template; external evaluator or LLM judge required.`. Additionally, `DeepEvalBridge` was not wired into the blackbox runner and strictly checked for OpenAI/Anthropic keys instead of LiteLLM/OpenRouter.
- **Alternatives considered:**
  1. **Add regex rules for all prompts:** Impossible for open-ended LLM-synthesized scenarios.
  2. **Force all tests through an LLM judge:** High token cost and unnecessary latency for simple deterministic safety checks.
  3. **Tiered confidence gating with a configurable mode switch (Option 3):** Run fast Tier-0 deterministic heuristics first; if an open-ended candidate has no rule match, escalate to `LLMJudgeScorer` (LiteLLM / DeepSeek) with rich rubric evaluation. Support configurable modes: `HYBRID` (default), `DETERMINISTIC_ONLY`, and `LLM_JUDGE`.
- **Decision:** **Option 3.**
  1. Implemented `LLMJudgeScorer` (`agenteval/evaluators/llm_judge.py`) using LiteLLM with robust JSON extraction and offline deterministic fallbacks.
  2. Added `JudgeMode` (`HYBRID`, `DETERMINISTIC_ONLY`, `LLM_JUDGE`) to `BlackboxRunner`, `SuiteWorkflow.run_suite`, and API schemas (`SuiteRunRequest.judge_mode`).
  3. Upgraded `DeepEvalBridge` to recognize `OPENROUTER_API_KEY` and `DEEPSEEK_API_KEY`.
  4. Verified live against the real IT Ops Agent at `:8770/chat`: functional and adversarial probes evaluated with rich semantic rationales.
- **Consequences:** Eliminates premature `UNVERIFIABLE` verdicts on dynamic tests while preserving zero-cost deterministic fast-paths and full offline CI reproducibility.

---

<!-- New entries above ## Archive -->

## Archive

<!-- Superseded decisions moved here with Superseded-by link -->
