# ADR-002: Dynamic Persona Synthesis, Stack-Ranking & Multi-Vendor LiteLLM Gateway

- **Status**: Accepted
- **Date**: 2026-09-20
- **Decision Makers**: @ajas.bakran
- **Tags**: architecture, personas, litellm, llm-gateway, evaluation-scoping

## Context

In early designs, AgentEval maintained a static catalog of candidate personas (35–50+ markdown files). As real-world evaluation workflows were tested, three severe architectural bottlenecks became apparent:

1. **Maintenance Toil & Semantic Drift**: Manually creating, updating, and maintaining hundreds of static personas across ever-shifting agent capabilities is unsustainable.
2. **Domain Mismatch**: Pre-canned personas (e.g., generic SRE or Sales) fail to capture company-specific schemas, private APIs, customer tiers, and bespoke tool constraints.
3. **Evaluation Bloat & Token Waste**: Testing an agent against dozens of irrelevant personas causes combinatorial explosion in test suite runtimes and token costs.
4. **LLM Provider Fragmentation**: Different teams and CI runners use different model providers (OpenAI, Anthropic Claude, Google Gemini, Ollama for local runs, AWS Bedrock, or Azure OpenAI). Hardcoding vendor-specific client libraries creates vendor lock-in and repetitive wrapper code.

## Decision

We make four architectural decisions:

### 1. Adopt LiteLLM as the Unified Multi-Vendor LLM Gateway
Instead of building custom SDK wrappers for OpenAI, Anthropic, Gemini, Bedrock, and Ollama, AgentEval adopts **`litellm`** as its official LLM provider abstraction layer.
- Provides a unified `litellm.completion()` / `litellm.acompletion()` API across 100+ LLM backends.
- Standardizes authentication via standard environment variables (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, etc.).
- Native support for structured JSON schema outputs and Pydantic validation.

### 2. On-the-Fly Dynamic Persona Discovery
Given an agent under test (its description, tool definitions, API specification, customer end, or PRD), AgentEval prompts the LLM to dynamically invent and formulate targeted user and adversary personas tailored specifically to the agent's exact operational context.

### 3. Persona Stack-Ranking & Top-K Windowing (`--top-personas`)
Candidate personas are stack-ranked into 5 operational tiers based on frequency and risk:
- **Tier 1 (Frequent Operations, ~70% volume)**: The primary daily user performing intended workflows.
- **Tier 2 (Power Users & Edge Cases, ~20% volume)**: High-load, bulk actions, and boundary conditions.
- **Tier 3 (Adversarial / Red-Team, ~5% volume)**: Deliberate fuzzing, prompt injections, and malformed inputs.
- **Tier 4 (Confused / Novice)**: Missing context and ambiguous prompts to evaluate agent disambiguation.
- **Tier 5 (Compliance & Security Auditor)**: Permission escalation and data boundary stress-testing.

To prevent evaluation overkill, the CLI provides a configurable `--top-personas K` flag (default: `3`), executing only the highest-signal personas.

### 4. Layered Air-Gapped Fallback & Disk Caching
- **Cache**: Generated personas are stored in `.agenteval/personas/{slug}.md` for instant (<1ms) repeat CLI runs with zero token costs.
- **Fallback**: If no LLM API key is present or the environment is air-gapped, AgentEval falls back automatically to `Jev` (TypeSafe AI) and the curated static registry.

## Consequences

### Positive
- **Zero Friction**: Developers can point AgentEval at any agent endpoint or PRD and get calibrated, tailored evaluation personas without writing a single line of YAML or markdown.
- **Vendor Agnostic**: Seamlessly switches between Claude 3.5 Sonnet, GPT-4o, Gemini 1.5 Pro, and local Ollama models with a single model string or environment variable.
- **Controlled Cost & Runtime**: Top-K windowing keeps test runs fast and budget-friendly while retaining high test yield.
- **Local-First & Air-Gapped Safe**: Caching and local deterministic fallbacks ensure tests never fail because of transient network outages.

### Negative / Trade-offs
- Additional runtime dependency on `litellm`.
- LLM non-determinism during initial synthesis (mitigated by strict Pydantic schema validation and local disk caching).

## Implementation status (2026-09-24)

- LiteLLM persona synthesis, `.agenteval/personas/` caching and the local
  heuristic fallback are implemented (`personas/dynamic.py`,
  `personas/synthesizer.py`, `recommender/jev_client.py`).
- `--top-personas` exists on the CLI only; the Web UI and `/v1/suites/*` do not
  expose it, although they are the default product path (DR-021).
- The Jev endpoint (`TYPESAFE_API_URL`, default `https://api.typesafe.ai/v1/classify`)
  has not been verified against a live service; the local heuristic may be the
  path that runs in practice.
- Under ADR-005, personas become a contribution from domain plugins rather than
  a backbone concern.

## References
- [LiteLLM Documentation](https://docs.litellm.ai/)
- [AgentEval Product Roadmap (Plane 0 & Plane 5)](../ROADMAP.md)
