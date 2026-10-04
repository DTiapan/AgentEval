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
| LL-007 | SSRF Defense-in-Depth: DNS Resolution, 3xx Redirect Traps, and Mock Compatibility in Test Harnesses | logged | project | security / testing |
| LL-008 | CORS Wildcard vs. Credentials Conflict and Drive-By Intranet Exploitation | logged | project | security / architecture |
| LL-009 | Serverless Ingress Timeouts vs. Synchronous AI Trajectory Runs: Deployment Drift and Incomplete Assurance | logged | project | architecture / deployment |

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

---

## LL-007: SSRF Defense-in-Depth: DNS Resolution, 3xx Redirect Traps, and Mock Compatibility in Test Harnesses

- **Date**: 2026-10-04
- **Scope**: project
- **Context**: When hardening BYOA agent endpoints against Server-Side Request Forgery (SSRF), naive URL validation (checking string prefix or parsing scheme and hostname) is trivially bypassed by HTTP 3xx redirects (e.g., public URL redirecting to `169.254.169.254`), alternative IPv6-mapped representations (`::ffff:169.254.169.254`), or DNS rebinding. Furthermore, replacing `urllib.request.urlopen` with custom `build_opener` instances can inadvertently break unit test fixtures that mock `urlopen` via `unittest.mock.patch`.
- **Root Cause**: Standard library `urllib.request.urlopen` follows up to 10 redirects by default without inspecting destination IP ranges. Link-local addresses (`169.254.0.0/16`) house cloud metadata credentials (GCP/AWS IMDS), which must be blocked unconditionally even when private RFC 1918 evaluation is enabled for VPC services. Additionally, `OpenerDirector.open()` does not route through `urllib.request.urlopen`, silently ignoring test patches and attempting live network calls.
- **Lesson / Rule**: Always pair initial URL validation with a `SafeRedirectHandler` that intercepts every 3xx redirect hop. Unconditionally block link-local and cloud metadata addresses regardless of private-network opt-in flags. In security transport wrapper functions (`safe_urlopen`), detect when `urlopen` has been replaced by a test mock (`hasattr(urllib.request.urlopen, "assert_called")`) and delegate to it after validation, preserving test determinism while enforcing strict production safety.

---

## LL-008: CORS Wildcard vs. Credentials Conflict and Drive-By Intranet Exploitation

- **Date**: 2026-10-04
- **Scope**: project
- **Context**: Setting `allow_origins=["*"]` is standard boilerplate in early FastAPI/Starlette development. However, combining `allow_origins=["*"]` with `allow_credentials=True` triggers W3C Fetch specification browser errors (`The value of the 'Access-Control-Allow-Origin' header in the response must not be the wildcard '*' when the request's credentials mode is 'include'`). Furthermore, local developer services listening on `localhost` or `127.0.0.1` without origin filtering are vulnerable to drive-by cross-origin attacks from arbitrary external websites.
- **Root Cause**: Browsers enforce the Same-Origin Policy (SOP), but CORS acts as an opt-in relaxation mechanism. If an internal developer tool exposes an unrestricted wildcard CORS API on `127.0.0.1`, any tab the engineer opens on the public internet can issue background `fetch("http://127.0.0.1:8766/v1/suites")` requests, stealing sensitive PRD contents, test traces, and agent credentials. Additionally, W3C standards strictly forbid credential sharing with wildcard origins.
- **Lesson / Rule**: Never deploy `allow_origins=["*"]` alongside `allow_credentials=True`. Restrict default CORS origins strictly to local development frontend ports (`localhost:5173`, `127.0.0.1:8766`). Make custom origins configurable via environment variables (`AGENTEVAL_CORS_ORIGINS`). Whenever a wildcard origin `*` is explicitly configured, dynamically enforce `allow_credentials=False` to maintain RFC compliance and protect developer workstations.

---

## LL-009: Serverless Ingress Timeouts vs. Synchronous AI Trajectory Runs: Deployment Drift and Incomplete Assurance

- **Date**: 2026-10-04
- **Scope**: project
- **Context**: In serverless container platforms such as Google Cloud Run, AWS App Runner, or Knative, the default HTTP request timeout is 300 seconds (5 minutes). While 300s is generous for standard microservices (REST CRUD APIs), AI agent evaluation workloads differ fundamentally: executing a 50-test assurance pack involves multi-turn agent network round-trips, tool execution latencies, and Tier-2 LLM judge completions (e.g. DeepSeek reasoning models), which cumulatively scale linearly to 10–25 minutes in synchronous execution mode.
- **Root Cause**: Hardcoding `TIMEOUT=300` across deployment scripts (`deploy.sh`), Knative manifests (`service.yaml`), and CI/CD templates (`cloudbuild.yaml`) causes the infrastructure ingress proxy to drop requests at second 300 with an ungraceful HTTP 504 Gateway Timeout. This severs the client connection, aborts in-flight execution, leaves run states unsealed, and risks partial database corruption during container de-scheduling. Furthermore, configuring timeout in only one deployment path (e.g. `deploy.sh`) causes subtle deployment drift when deploying through declarative Knative manifests or automated CI/CD triggers.
- **Lesson / Rule**: For platforms running synchronous long-duration evaluation workloads on Cloud Run Gen2, align all deployment channels to an explicit execution ceiling (`timeoutSeconds: 1800` / 30 minutes). Enforce cross-specification synchronization via automated unit tests (`test_cloud_deployment_config.py`) to prevent regressions until asynchronous background execution (e.g. `202 Accepted` job pools) can fully decouple the HTTP request lifecycle from batch evaluation runs.

<!-- New entries above ## Archive -->

## Archive

<!-- Resolved lessons optionally summarized here -->

