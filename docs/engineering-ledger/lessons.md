# Lessons learned (LL)

Blameless capture of surprises, failed approaches, and reusable principles.

## Active index

| ID | Title | Status | Scope | Category |
|----|-------|--------|-------|----------|
| LL-001 | Rich Terminal Bracket Escaping and Pydantic Model Reordering | logged | project | architecture / tooling |
| LL-002 | Disk-Cached Persona Synthesis for Sub-50ms CLI Startup and Zero-Token Re-runs | logged | project | performance / architecture |
| LL-003 | Operational Tier Stack-Ranking & Multi-Vendor LLM Gateway via LiteLLM | logged | project | architecture / llm |
| LL-004 | Python Reserved Keywords in Tool Schema Bridges (Pydantic Aliasing) and Dynamic OSS Extra Loading | logged | project | architecture / typing |
| LL-005 | Strict Suite Sync Prefixing and Capability Association for Red-Team/Adversarial Inferred Tests | logged | project | architecture / sync |
| LL-006 | Playwright Driver CDN 404 in IDE Environment and Offline Mirror Restoration | logged | project | tooling / browser |

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


---

## LL-005: Strict Suite Sync Prefixing and Capability Association for Red-Team/Adversarial Inferred Tests

- **Date**: 2026-09-27
- **Scope**: project
- **Context**: When synthetic adversarial tests or red-team candidate tests are generated from external bridges (e.g. PromptFoo bridge or LLM red-teaming), test names often take the form `RedTeam [prompt-injection] ...`. During suite re-synchronization (`SuiteSynchronizer.compute_sync`), `_normalize_pool_capability_ids` parses capability names by splitting on colon (`test.name.split(":", 1)[0].strip()`). If the test name does not prefix the associated capability, the sync engine re-links all red-team tests to an arbitrary first capability or drops them as orphan capabilities.
- **Root Cause**: The suite synchronization engine relies on the convention that candidate test names begin with `{primary_capability.name}: ...` to preserve capability associations across PRD edits and version upgrades.
- **Lesson / Rule**: Always prefix generated candidate test names with `{primary_capability.name}: <Descriptor>` (e.g. `{cap.name}: RedTeam [{plugin}] {hypothesis}`). This ensures deterministic capability matching during suite synchronization and capability-targeted gap closing.

---

## LL-004: Python Reserved Keywords in Tool Schema Bridges (Pydantic Aliasing) and Dynamic OSS Extra Loading

- **Date**: 2026-09-27
- **Scope**: project
- **Context**: Interfacing with external tool formats such as PromptFoo YAML specifications requires generating keys named `assert`, which is a reserved keyword in Python. In Pydantic v2, defining fields like `assert_list: list[PromptFooAssertion] = Field(default_factory=list, alias="assert")` handles serialization, but direct keyword initialization `PromptFooTestCase(assert=...)` triggers a Python `SyntaxError`. Furthermore, importing optional third-party packages like `deepeval` must not fail in environments where those extras are not installed.
- **Root Cause**: Python's AST prohibits using reserved keywords as keyword arguments. Static type checkers (`mypy --strict`) reject direct imports of uninstalled optional packages unless handled dynamically or typed with stubs.
- **Lesson / Rule**: For models with reserved keyword aliases, instantiate via `Model.model_validate({"assert": ..., ...})` to ensure both runtime validity and static typing without `# type: ignore` comments. For optional OSS packages, use `importlib.import_module()` with fallback handling to preserve zero-dependency lightweight operation while remaining 100% compliant with strict linting and typing constraints.

---

## LL-006: Playwright Driver CDN 404 in IDE Environment and Offline Mirror Restoration

- **Date**: 2026-10-02
- **Scope**: project
- **Context**: During live browser verification of the Web Studio UI via the Antigravity IDE browser subagent, the underlying Playwright manager failed to launch the browser with `got non 200 status code: 404 (404 Not Found) from https://playwright.azureedge.net/builds/driver/playwright-1.57.0-mac-arm64.zip`.
- **Root Cause**: The IDE's internal browser automation manager is hardcoded to download Playwright driver version `1.57.0` for `mac-arm64`. Microsoft Azure CDN endpoints return HTTP 404 for this zip package. The initial automated attempt left an empty folder at `~/Library/Caches/ms-playwright-go/1.57.0/`.
- **Lesson / Rule**: When internal IDE tool dependencies experience upstream CDN deprecation/404s, perform offline manual recovery by downloading the exact artifact from an active archive/mirror (e.g. `https://cdn.npmmirror.com/binaries/playwright/builds/driver/playwright-1.57.0-mac-arm64.zip`), extracting into `~/Library/Caches/ms-playwright-go/1.57.0/`, setting executable permissions on `./node`, and bootstrapping the browser binaries via `./node package/cli.js install chromium`.

<!-- New entries above ## Archive -->

## Archive

<!-- Resolved lessons optionally summarized here -->
