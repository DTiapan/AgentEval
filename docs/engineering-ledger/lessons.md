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
| LL-010 | Out-of-Order Test Completion and Deterministic Suite Report Invariants | logged | project | architecture / testing |
| LL-011 | HTTP Transport Migration: Event Hooks for Redirect-Resistant SSRF and Connection Pool Sizing | logged | project | security / performance |
| LL-012 | In-Process Background Task Traps: SQLite Thread Affinity and FastAPI Route Masking | logged | project | architecture / threading |
| LL-013 | Streaming Persistence Prevents Catastrophic Test Preemption in Containerized Runtimes | logged | project | architecture / database |
| LL-014 | Structured JSON Logging in Containerized Cloud Runtimes: Severity Mappings, Contextvars, and Evaluator Attribution | logged | project | observability / architecture |

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
---

## LL-010: Out-of-Order Test Completion and Deterministic Suite Report Invariants

- **Date**: 2026-10-04
- **Scope**: project
- **Context**: When introducing concurrent execution in test runners (`concurrent.futures.ThreadPoolExecutor`), worker threads complete in non-deterministic order depending on variable agent response latencies and judge inference times. As tests finish, iterating through `as_completed(futures)` appends results in completion order rather than candidate test specification order.
- **Root Cause**: Downstream consumers—including `diff_suite_runs`, git diffs of frozen test reports, console UI table listings, and Allure-class HTML report sections—rely on invariant canonical test ordering (`[test-0, test-1, test-2, ...]`). When tests complete out-of-order, sequential runs of the exact same suite produce diff churn, visual jumping in UI test lists, and false-positive ordering discrepancies in regression diffs.
- **Lesson / Rule**: Always decouple the execution topology from the result presentation topology. In concurrent test runners, maintain a canonical index mapping from the source test pack (`order = {test.id: i for i, test in enumerate(pack.tests)}`) and explicitly sort the collected results by canonical index (`results.sort(key=lambda r: order.get(r.test_id, 0))`) before constructing the final `SuiteRunReport`. This guarantees 100% deterministic report outputs regardless of worker scheduling or completion jitter.

---

## LL-011: HTTP Transport Migration: Event Hooks for Redirect-Resistant SSRF and Connection Pool Sizing

- **Date**: 2026-10-04
- **Scope**: project
- **Context**: Migrating from standard library `urllib.request` to `httpx.Client` introduces connection pooling and Keep-Alive across concurrent worker threads, reducing TLS handshake latency. However, high-level HTTP client libraries typically follow HTTP 3xx redirects automatically (`follow_redirects=True`) without re-running application-level security policies against redirected destination URLs. Furthermore, if connection pool limits (`max_connections`) are set lower than worker pool concurrency, worker threads experience connection starvation and blocking pool queue timeouts.
- **Root Cause**: In standard `httpx.Client(follow_redirects=True)`, the initial request URL may be validated, but a malicious server responding with `302 Found -> Location: http://169.254.169.254` can cause the client to blindly follow the redirect to cloud metadata. Additionally, unit tests that previously patched `urllib.request.urlopen` will silently fail or make unwanted network calls when transports migrate to `httpx`.
- **Lesson / Rule**: Use `httpx` request event hooks (`event_hooks={"request": [ssrf_hook]}`) to enforce security policies. Because `httpx` executes the `request` event hook for *every* outbound request—including each individual redirect hop—the hook intercepts and evaluates the new `Location` URL *before* any socket or TLS handshake is initiated. Sizing connection limits (`Limits(max_connections=50, max_keepalive_connections=20)`) to match or exceed the runner's worker pool ceiling prevents pool contention. In test suites, use `httpx.MockTransport` and client dependency injection rather than monkeypatching global network libraries.

## LL-012: Multi-Threaded In-Process Background Jobs: SQLite Thread Affinity and FastAPI Route Precedence

- **Date**: 2026-10-04
- **Scope**: project
- **Context**: Introducing in-process asynchronous task management (`RunJobManager` via `ThreadPoolExecutor`) decoupled long-running test suite runs from HTTP request lifecycles. However, two non-obvious architecture traps emerged during implementation: Python's standard `sqlite3.connect()` default thread affinity check, and Starlette/FastAPI route matching order for wildcard path parameters.
- **Root Cause**:
  1. **SQLite Thread Affinity Error**: `sqlite3.connect()` defaults to `check_same_thread=True`. When a `SuiteWorkflow` instance initialized on the main FastAPI request thread is passed to a background thread in `ThreadPoolExecutor`, saving the run report triggers `sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread`. Under WAL mode, concurrent reads and serialized writes are safe across threads when configuring `sqlite3.connect(path, timeout=30.0, check_same_thread=False)`.
  2. **FastAPI Route Masking**: Declaring `@app.get("/v1/suites/{agent_id}/runs/{run_id}")` before `@app.get("/v1/suites/{agent_id}/runs/latest")` causes FastAPI to route `/runs/latest` to the parameterized handler with `run_id="latest"`, returning an erroneous 404 because `"latest"` is treated as a literal run ID.
- **Lesson / Rule**:
  1. In multi-threaded Python applications using SQLite persistence, configure `check_same_thread=False` and a generous lock timeout (`timeout=30.0`) in the connection factory to support safe thread hand-offs under WAL mode.
  2. In FastAPI / Starlette routing, always register literal static subpaths (such as `/latest`, `/status`, `/health`) *before* parameterized wildcard paths (such as `/{run_id}`) to prevent route shadowing.

## LL-013: Streaming Persistence Prevents Catastrophic Test Preemption in Containerized Runtimes

- **Date**: 2026-10-04
- **Scope**: project
- **Context**: Accumulating batch test results exclusively in memory until runner completion creates a severe vulnerability in containerized serverless runtimes (Cloud Run, Kubernetes, AWS ECS Fargate, spot instances). When horizontal autoscalers scale down or worker nodes are preempted mid-suite, all progress and multi-step execution step trajectories are permanently destroyed.
- **Root Cause**:
  1. **All-or-Nothing Batch Persistence**: In a batch model, state transitions directly from 0% persisted to 100% persisted only after the final test completes. If a crash or SIGTERM occurs at 98% completion, 100% of the execution work is lost.
  2. **Concurrent Write Collisions under ThreadPoolExecutor**: When streaming results as each test finishes across parallel worker threads (`max_workers=50`), multiple threads invoke the database simultaneously. Without serialization, SQLite under WAL mode can still encounter transient `busy` or `locked` conditions during concurrent write transactions.
  3. **Foreign Key Integrity with Mocked Test Reports**: When test suites mock `BlackboxRunner.run_pack()`, mock return values may supply hardcoded run IDs (e.g. `run-db`) that differ from the auto-generated execution run ID. If streaming persistence writes child results before the parent run row is initialized, SQLite raises `sqlite3.IntegrityError: FOREIGN KEY constraint failed`.
- **Lesson / Rule**:
  1. Always stream state transitions incrementally: initialize the parent entity record with `status = 'running'` *before* starting workers, flush each result and its execution trace immediately upon completion, and update running tallies via atomic SQL subqueries.
  2. Protect SQLite write operations with a re-entrant lock (`threading.RLock()`) to serialize concurrent thread flushes cleanly while allowing nested helper calls within the same thread.
  3. In `finalize_run`, check if the parent run row exists before writing results and initialize it on-demand to guarantee foreign key integrity even when third-party runners or test mocks supply custom run identifiers.
  4. Explicitly gate baseline lookups (`load_latest_run`) to filter for `(status IS NULL OR status = 'completed')` so that in-flight and failed runs are never mistaken for signed-off evaluation baselines.

## LL-014: Structured JSON Logging in Containerized Cloud Runtimes: Severity Mappings, Contextvars, and Evaluator Attribution

- **Date**: 2026-10-04
- **Scope**: project
- **Context**: In production cloud container environments (Google Cloud Run, GKE, AWS ECS, Datadog), application logs are ingested by automated log shippers that parse stdout/stderr as single-line JSON. Three critical observability requirements must be met: severity level recognition, request correlation, and evaluator fallback attribution.
- **Root Cause**:
  1. **Log Level Indexing Drift**: Standard Python logging and structlog emit log levels as lowercase strings under `"level"` (`"info"`, `"warning"`). Cloud log aggregators (specifically Google Cloud Logging) do not index `"level"`; they strictly require an uppercase `"severity"` field (`INFO`, `WARNING`, `ERROR`, `CRITICAL`). Without explicit severity mapping, critical warnings and exceptions are indexed as neutral informational entries and fail to trigger log-based alert metrics.
  2. **Asynchronous Request Tracing Gap**: When an HTTP request triggers background worker execution or multi-threaded evaluations, tracing the lifecycle of a single request across interleaved concurrent logs is impossible without a unique correlation identifier (`X-Request-ID`). Passing request IDs through method signatures pollutes domain interfaces; using `contextvars` (`structlog.contextvars`) allows zero-boilerplate contextual propagation across async and threaded boundaries.
  3. **Silent Evaluation Fallbacks (The "Phantom LLM" Problem)**: When an LLM judge encounters rate limits, timeouts, or API authentication failures and silently falls back to offline heuristic pattern matching, end users may mistakenly believe their agent was evaluated by a state-of-the-art LLM. Emitting an explicit `evaluator_provenance` tag and a structured `llm_judge_fallback_triggered` warning guarantees forensic transparency in production telemetry.
- **Lesson / Rule**:
  1. Always normalize log levels to GCP native `"severity"` field in JSON log processors (`add_gcp_severity`).
  2. Inject and preserve `X-Request-ID` at HTTP boundary middlewares (`RequestIdMiddleware`), expose it in CORS allowlists, and bind it to thread/async contextvars so downstream execution traces inherit correlation automatically.
  3. Never silently degrade evaluation engines; always stamp results with `evaluator_provenance` (`litellm-judge` vs `heuristic-fallback`) and emit structured warnings on fallback activation.
  4. Detect terminal TTY vs container environments dynamically: render human-readable colorized logs when running interactively on a developer terminal, and switch to strict single-line JSON (`JSONRenderer`) when redirected to pipes, log files, or production container runtimes.

<!-- New entries above ## Archive -->

## Archive


<!-- Resolved lessons optionally summarized here -->

