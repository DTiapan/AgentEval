# Product Requirements Document (PRD) — AgentEval SaaS
## Pre-Release AI Agent Assurance & Evaluation Platform

> **Document Version:** 4.0.0  
> **Status:** Specification for UX generation & incremental build  
> **North Star:** [Black-Box Test Intelligence Pipeline](black-box-test-intelligence-pipeline.md) — requirements (+ optional URL) → optimized test pack → deterministic execution → coverage, gaps, and honest limitations ([DR-012](../engineering-ledger/decisions.md))  
> **Companion UX:** [ux-wireframes.md](ux-wireframes.md) (screen wireframes; personas & journeys authoritative in this PRD)  
> **Last updated:** 2026-09-20  

---

## Table of contents

1. [Executive summary](#1-executive-summary)
2. [Problem, vision & product boundaries](#2-problem-vision--product-boundaries)
3. [User ecosystem (who uses AgentEval)](#3-user-ecosystem-who-uses-agenteval)
4. [User personas](#4-user-personas)
5. [User journey maps](#5-user-journey-maps)
6. [SaaS platform: auth, orgs, onboarding](#6-saas-platform-auth-orgs-onboarding)
7. [Core product workflows](#7-core-product-workflows)
8. [Information architecture & navigation](#8-information-architecture--navigation)
9. [Functional requirements by epic](#9-functional-requirements-by-epic)
10. [Non-functional requirements](#10-non-functional-requirements)
11. [Out of scope & later phases](#11-out-of-scope--later-phases)
12. [Success metrics & release gates](#12-success-metrics--release-gates)
13. [Screen specifications (product console)](#13-screen-specifications-product-console)
14. [Design system & UX generator brief](#14-design-system--ux-generator-brief)

---

## 1. Executive summary

**AgentEval** is a **full SaaS** platform for teams that ship autonomous AI agents (tool-calling, multi-turn, side-effecting). It answers one question before production: *“Is this agent safe, correct, and non-regressive against our stated requirements?”*

Unlike chat-based “vibe checks” or opaque LLM-as-judge scores, AgentEval provides **pre-production software testing**: derive a minimal high-value test pack from requirements and an endpoint, execute against staging or CI, assert **observable evidence**, flag **UNVERIFIABLE** when proof is missing, and **gate releases** with frozen regression suites and baseline diffs.

**Primary commercial motion:** Individual engineer signs up → connects staging agent → pastes PRD → freezes suite → runs in UI or CI → shares HTML audit report with security and release stakeholders.

**Explicit non-goal for this PRD:** Live production monitoring, APM, or continuous in-prod agent telemetry (a future product line, not v1 SaaS).

---

## 2. Problem, vision & product boundaries

### 2.1 Problem

Teams deploy agents that can refund money, mutate databases, and call third-party APIs. Testing is manual, non-reproducible, and trusts agent self-reports. Regressions slip through prompt tweaks. Security reviewers lack exportable proof.

### 2.2 Vision

**Pre-release assurance console** + **API/CLI parity** so the same workflows work in the browser, in GitHub Actions, and locally.

### 2.3 Core tenets (product)

| # | Tenet | User-visible implication |
|---|--------|---------------------------|
| 1 | Pre-production testing, not prod APM | No “live agent dashboard” in v1; environments are *Local*, *Staging*, *CI* |
| 2 | Deterministic evidence vs self-report | Pass/fail from observable rules; `UNVERIFIABLE` when evidence is sealed |
| 3 | BYOA (zero agent code changes) | HTTP/OpenAPI/MCP/callable targets via configuration only |
| 4 | Requirements → suite intelligence | Paste/upload PRD; optimizer compresses candidate pool (set cover + mandatory floors) |
| 5 | Frozen regression suites | Freeze once; compare every run to baseline for release gating |
| 6 | Trajectory-first debugging | Multi-turn replay with jump-to-fail |

### 2.4 Dual delivery (SaaS + power users)

| Surface | Role |
|---------|------|
| **Web app** | Onboarding, studio, runs, replay, reports, team collaboration |
| **HTTP API** | Same Pydantic contracts as library ([DR-012](../engineering-ledger/decisions.md)) |
| **CLI** | Local dev, scripting, parity with API for CI runners |

---

## 3. User ecosystem (who uses AgentEval)

Before personas, map **every actor** that touches the product. Personas are composites of these roles.

```mermaid
flowchart LR
    subgraph Build["Build & test (daily)"]
        AIE[AI / agent engineer]
        SRE[Reliability / platform engineer]
        QA[QA / test automation engineer]
    end
    subgraph Govern["Govern & approve"]
        SEC[Security / GRC auditor]
        EM[Eng manager / release owner]
        PM[Product manager]
    end
    subgraph Operate["Operate the tenant"]
        ADM[Org / workspace admin]
        BIL[Billing owner - later]
    end
    subgraph Machine["Non-human"]
        CI[CI/CD pipeline service account]
        IDP[Identity provider - SSO later]
    end

    AIE --> AE[(AgentEval SaaS)]
    SRE --> AE
    QA --> AE
    SEC --> AE
    EM --> AE
    PM --> AE
    ADM --> AE
    CI --> AE
    IDP -.-> AE
```

### 3.1 Role summary

| Actor | Relationship to product | Typical frequency |
|-------|-------------------------|-------------------|
| **AI / agent engineer** | Authors agents; runs suites locally and in staging | Daily |
| **QA automation engineer** | Wires API tokens into CI; enforces pass gates on PRs | Daily (CI) |
| **Reliability / platform engineer** | Owns endpoints, secrets, environments; probes health | Weekly |
| **Security / compliance auditor** | Reviews mandatory floors, exports HTML/PDF evidence | Per release / audit |
| **Engineering manager / release owner** | Reads regression diff and pass rate; approves deploy | Per RC |
| **Product manager** | Supplies requirements text; validates capability coverage | Per feature |
| **Org / workspace admin** | Invites users, roles, API keys, environment URLs | Setup + ad hoc |
| **Executive / viewer** | Read-only run history and reports | Monthly |
| **CI service account** | `POST /v1/suites/run` with scoped token | Every PR |

---

## 4. User personas

Methodology: [ux-planner](../../.agents/skills/ux-planner/SKILL.md) — role, mental model, 5-second intent, fears, success threshold.

### Persona matrix (primary UX targets)

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    AGENTEVAL SAAS PERSONA MATRIX (v4)                                     │
├─────────────┬────────────────────┬────────────────────┬────────────────────┬──────────────────────────────┤
│ ALEX CHEN   │ SAM ORTIZ          │ MAYA PATEL         │ MARCUS VANCE       │ JORDAN KIM                   │
│ AI Reliab.  │ QA Automation      │ Security Auditor   │ Release Gatekeeper │ Workspace Admin              │
│ Engineer    │ Engineer           │ (GRC / SecOps)     │ (Eng Lead)         │ (Platform / IT)              │
│ PRIMARY     │ PRIMARY (CI)       │ PRIMARY (audit)    │ SECONDARY          │ SECONDARY (setup)            │
├─────────────┼────────────────────┼────────────────────┼────────────────────┼──────────────────────────────┤
│ Build &     │ Gate merges on     │ Prove floors       │ 0 regressions vs   │ Invite team,                 │
│ debug agent │ frozen suite       │ before prod auth   │ baseline; sign-off │ environments, API keys       │
├─────────────┼────────────────────┼────────────────────┼────────────────────┼──────────────────────────────┤
│ PRIYA SHARMA│ RILEY NGUYEN       │ (Machine) CI BOT   │                    │                              │
│ Product Mgr │ Exec Viewer        │ GHA / GitLab       │                    │                              │
│ SECONDARY   │ TERTIARY           │ SERVICE ACCOUNT    │                    │                              │
└─────────────┴────────────────────┴────────────────────┴────────────────────┴──────────────────────────────┘
```

### P1 — Alex Chen · Senior AI Reliability Engineer (primary builder)

| Dimension | Detail |
|-----------|--------|
| **Role & mental model** | Ships refund/support/code agents. Thinks in Postman, VS Code, git branches. Wants “tests from my PRD,” not YAML archaeology. |
| **5-second intent** | “Where do I paste requirements, point at staging, and run a pack?” |
| **Fears** | Flaky LLM judges; 100-test CI bloat; false greens when the agent lies about tool use. |
| **Success threshold** | Preview → 8 tests cover capabilities → freeze → run → one failure → replay jump-to-fail → fix → green. |

### P2 — Sam Ortiz · QA Automation Engineer (CI primary)

| Dimension | Detail |
|-----------|--------|
| **Role & mental model** | Owns GitHub Actions / GitLab CI. Treats AgentEval as a **test job** like unit tests. |
| **5-second intent** | “What API call and secret do I add so PR #42 fails if regressions exist?” |
| **Fears** | Non-deterministic CI; missing docs for tokens; suite drift between dev and CI. |
| **Success threshold** | Docs copy-paste workflow; CI posts regression summary; merge blocked on fail. |

### P3 — Maya Patel · AI Safety & Security Auditor

| Dimension | Detail |
|-----------|--------|
| **Role & mental model** | Signs off before prod. Needs **proof**, not screenshots of chat. |
| **5-second intent** | “Are mandatory security floors green, and can I export evidence?” |
| **Fears** | Silent privilege escalation; injection bypass; unprovable “I checked role” claims. |
| **Success threshold** | Mandatory floors checklist ✓; HTML report with SHA256 suite hash; `UNVERIFIABLE` clearly labeled. |

### P4 — Marcus Vance · Engineering Lead / Release Gatekeeper

| Dimension | Detail |
|-----------|--------|
| **Role & mental model** | Approves release candidates; cares about trend and regressions, not test authoring. |
| **5-second intent** | “0 regressions vs last baseline and acceptable pass rate?” |
| **Fears** | Silent capability breakage; latency creep; no audit trail. |
| **Success threshold** | Regression banner green; one-click report link for leadership. |

### P5 — Jordan Kim · Workspace / Org Admin

| Dimension | Detail |
|-----------|--------|
| **Role & mental model** | Sets up tenant: users, roles, staging base URLs, API keys, (later) SSO. |
| **5-second intent** | “Invite my team and lock down who can freeze suites vs view-only.” |
| **Fears** | Shadow IT agents tested without governance; leaked API keys. |
| **Success threshold** | RBAC roles assigned; rotation-friendly API keys; audit log of freeze/run actions. |

### P6 — Priya Sharma · Product Manager

| Dimension | Detail |
|-----------|--------|
| **Role & mental model** | Owns requirements doc; validates that tests reflect user stories and policies ($100 refund cap). |
| **5-second intent** | “Does the generated pack cover the capabilities I wrote?” |
| **Fears** | Engineering-only jargon; no visibility into what was tested. |
| **Success threshold** | Capability coverage map matches PRD sections; can comment or flag missing capability (later). |

### P7 — Riley Nguyen · Executive / Viewer

| Dimension | Detail |
|-----------|--------|
| **Role & mental model** | Non-technical stakeholder; needs assurance summary. |
| **5-second intent** | “Did we test this agent, and what was the outcome?” |
| **Fears** | Overwhelming technical UI. |
| **Success threshold** | Read-only dashboard tile: pass rate, last run date, link to HTML report. |

### P8 — CI Bot · Service account (non-human persona)

| Dimension | Detail |
|-----------|--------|
| **Role** | Scoped token; runs frozen suite ID against `CI` environment URL from secrets. |
| **Success threshold** | Idempotent run API; JSON summary for PR comment integration (later). |

---

## 5. User journey maps

Stages: **Discover → Sign up → Onboard → Configure → Plan → Freeze → Run → Debug → Report → Gate → Admin**.

### 5.1 Journey A — Alex: first value in one session (happy path)

```mermaid
sequenceDiagram
    autonumber
    actor Alex as Alex (Engineer)
    participant Web as AgentEval Web
    participant API as AgentEval API
    participant Agent as Staging agent

    Alex->>Web: Sign up / log in
    Web->>Alex: Onboarding wizard
    Alex->>Web: Create workspace + agent shell
    Alex->>Web: Paste PRD markdown
    Alex->>Web: Set endpoint URL + Probe
    Web->>API: Probe target
    API->>Agent: Health / sample invoke
    Agent-->>API: 200 + latency
    API-->>Web: Reachable
    Alex->>Web: Preview pack (optimizer k=10)
    API-->>Web: Candidates + coverage + floors
    Alex->>Web: Freeze suite
    Alex->>Web: Execute run
    API->>Agent: Test pack execution
    Agent-->>API: Traces + responses
    API-->>Web: Pass/fail + evidence
    Alex->>Web: Open replay (jump-to-fail if needed)
    Alex->>Web: Export HTML report link
```

| Step | Alex thinks | Trust Δ |
|------|-------------|---------|
| Probe success | “It can reach my agent.” | ↑ |
| Set-cover stats | “8 tests, not 80.” | ↑ |
| UNVERIFIABLE on one case | “Honest product.” | ↑ |
| Replay | “I see the exact turn that broke.” | ↑ |

### 5.2 Journey B — Sam: CI gate on pull request

```mermaid
flowchart TD
    A[PR opened] --> B[CI job: AGENTEVAL_API_KEY]
    B --> C[Run frozen suite ID against CI env URL]
    C --> D{Regression diff vs baseline}
    D -->|0 regressions + pass threshold| E[✓ Merge allowed]
    D -->|Regressions or fail rate| F[✗ Block merge + link to run]
    F --> G[Alex opens Assurance Runs in UI]
```

### 5.3 Journey C — Maya: security sign-off

1. Log in (Auditor role) → **Assurance Runs** (read + export).
2. Filter **Mandatory floors** / security-tagged tests.
3. Drill into failure or `UNVERIFIABLE` — inspect raw observation.
4. **Open standalone HTML report** → download for compliance folder.
5. Optional: attach report to ticket (manual v1; integration later).

### 5.4 Journey D — Marcus: release candidate review

1. Notification or link from Sam/Alex (Slack/email later).
2. Land on **Runs** with **Regression diff banner** vs `v1.1 baseline`.
3. Scan KPI strip (pass %, failures, unverifiable, latency).
4. Approve verbally / in Jira; no suite editing required.

### 5.5 Journey E — Jordan: tenant setup (day 0)

```mermaid
flowchart LR
    J1[Create org] --> J2[Create workspace]
    J2 --> J3[Invite Alex, Sam, Maya, Marcus]
    J3 --> J4[Define environments: Local, Staging, CI URLs]
    J4 --> J5[Issue API keys scoped to workspace]
    J5 --> J6[Assign roles: Engineer vs Auditor vs Viewer]
```

### 5.6 Journey F — Priya: requirements alignment

1. Upload or paste PRD in **Studio** (or Spec hub).
2. Review **capability extractor** output vs her doc sections.
3. Request engineer run **Thorough** pack before major launch (communication outside tool v1).

### 5.7 Cognitive walkthrough — signup landing (all personas)

| Look | Think | Do | Trust |
|------|-------|-----|-------|
| Headline: “Test agents before production” | “This is for engineers like me.” | Start free / Sign up | ↑ if social proof + clear BYOA |
| Purple CTA “Create workspace” | “Not another chat playground.” | Click | ↑ |
| Empty state in Studio | “What do I paste?” | Guided checklist: PRD → URL → Probe | ↑ or ↓ if vague |

---

## 6. SaaS platform: auth, orgs, onboarding

### 6.1 Tenancy model

```
Organization (billing entity - later)
└── Workspace (team boundary; secrets & suites)
    ├── Members + roles
    ├── Environments (Local | Staging | CI) → base URL + auth profile
    ├── Agents (logical target: id, description, linked endpoint per env)
    ├── Specifications (PRD uploads, OpenAPI)
    ├── Suites (draft preview | frozen)
    └── Runs (execution history, baselines, reports)
```

### 6.2 Authentication & account

| Requirement ID | Requirement | Priority |
|----------------|-------------|----------|
| AUTH-01 | Email + password sign up with verification email | P0 |
| AUTH-02 | Log in / log out / forgot password | P0 |
| AUTH-03 | OAuth: GitHub + Google | P1 |
| AUTH-04 | Session management (secure HTTP-only cookies or bearer for API) | P0 |
| AUTH-05 | SSO (SAML/OIDC) for enterprise | P2 (later) |

### 6.3 Authorization (RBAC)

| Role | Studio edit | Freeze suite | Execute run | View runs | Export report | Admin settings |
|------|-------------|--------------|-------------|-----------|---------------|----------------|
| **Owner** | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| **Engineer** | ✓ | ✓ | ✓ | ✓ | ✓ | — |
| **Auditor** | — | — | — (optional run in sandbox) | ✓ | ✓ | — |
| **Viewer** | — | — | — | ✓ | ✓ (read) | — |

### 6.4 Onboarding wizard (first login)

**Goal:** Time-to-first-run &lt; 15 minutes for Alex.

| Step | UI copy intent | Validation |
|------|----------------|------------|
| 1. Welcome | “Assure agents before production” | — |
| 2. Workspace name | Team or project name | Unique slug |
| 3. First agent | Agent display name + ID | Non-empty |
| 4. Requirements | Paste markdown or upload `.md` | Min length / parse ok |
| 5. Endpoint | Staging URL + optional auth header secret | **Probe** required to continue (soft skip with warning) |
| 6. First preview | Default optimizer **Balanced (10)** | Show candidate count |
| 7. CTA | **Freeze & run** or **Run preview once** | Lands on Assurance Runs |

**Empty states** after skip: persistent banner “Complete setup: probe endpoint.”

### 6.5 Settings surfaces

| Area | Contents |
|------|----------|
| **Profile** | Name, email, password, theme |
| **Workspace → Members** | Invite email, role, remove |
| **Workspace → API keys** | Create, revoke, last used, scopes (`run:read`, `suite:run`, `suite:write`) |
| **Workspace → Environments** | URL templates, default headers (secrets vault) |
| **Workspace → Agents** | Registry list, link specs, per-env endpoint overrides |
| **Org → Billing** | Placeholder “Coming soon” in v1 SaaS UI | P2 |

### 6.6 Notifications (v1 minimal)

- In-app: run completed, regression detected (banner on next visit).
- Email: invite to workspace; optional run failure (P1).

---

## 7. Core product workflows

Aligned with North Star pipeline: **Spec → Understand → Optimize → Freeze → Execute → Score → Coverage/Gaps → Report**.

| Workflow | Primary persona | Key outcome |
|----------|-----------------|-------------|
| **Author & optimize** | Alex, Priya | Preview pack + coverage + mandatory floors |
| **Freeze regression** | Alex, Sam | Immutable suite version for CI |
| **Execute assurance run** | Alex, Sam, CI Bot | Verdicts + traces |
| **Replay & debug** | Alex | Jump-to-fail trajectory |
| **Baseline & regression diff** | Marcus, Sam | vs previous green run |
| **Audit export** | Maya, Marcus | Standalone HTML (+ PDF certificate P1) |
| **Curate golden tests** | Alex | Promote failure trace to new case (P1) |

---

## 8. Information architecture & navigation

### 8.1 Authenticated app shell

```
AgentEval SaaS
├── Marketing (public): /, /pricing (later), /docs
├── Auth: /login, /signup, /forgot-password, /verify-email
├── Onboarding: /onboarding (wizard)
└── App (authenticated)
    ├── Home / Fleet overview (agents + last run status)     [P1]
    ├── Studio & Planner                                    [P0]
    ├── Assurance Runs                                      [P0]
    ├── Replay (deep link: /runs/:id/replay)                [P0]
    ├── Spec & uploads hub                                  [P1]
    ├── Reports library                                     [P1]
    └── Settings (profile, workspace, members, keys, envs)  [P0 members/keys P1 rest]
```

### 8.2 Mode switcher (in-app header)

Primary builder loop uses two modes (existing console pattern):

- **Studio & Planner** — spec, probe, optimizer, freeze  
- **Assurance Runs** — execute, regression diff, evidence, report  

Global context: **Workspace**, **Agent**, **Environment**, **Engine connection** status.

### 8.3 Fleet overview (home) — P1

Card per agent: last run pass %, regression badge, link to latest report. Serves Marcus, Riley, Jordan.

---

## 9. Functional requirements by epic

Priority: **P0** (MVP SaaS), **P1** (fast follow), **P2** (later).

### Epic E-ORG — Organization & workspace

| ID | Requirement | P |
|----|-------------|---|
| E-ORG-01 | User can create a workspace on first signup | P0 |
| E-ORG-02 | User can invite members by email with role | P0 |
| E-ORG-03 | User can list/remove members (Owner/Admin) | P0 |
| E-ORG-04 | Workspace isolates suites, runs, secrets | P0 |

### Epic E-AUTH — Authentication

| ID | Requirement | P |
|----|-------------|---|
| E-AUTH-01 | Sign up, login, logout | P0 |
| E-AUTH-02 | Email verification gate for new accounts | P0 |
| E-AUTH-03 | Password reset flow | P0 |
| E-AUTH-04 | OAuth GitHub/Google | P1 |

### Epic E-AGENT — Agent registry & environments

| ID | Requirement | P |
|----|-------------|---|
| E-AGENT-01 | CRUD agent records (id, name, description) | P0 |
| E-AGENT-02 | Per-environment endpoint URL + auth secret | P0 |
| E-AGENT-03 | **Probe** reachability with latency and status | P0 |
| E-AGENT-04 | Link agent to active specification | P0 |

### Epic E-SPEC — Requirements & ingest

| ID | Requirement | P |
|----|-------------|---|
| E-SPEC-01 | Paste markdown PRD in studio | P0 |
| E-SPEC-02 | Upload `.md` / OpenAPI (yaml/json) | P1 |
| E-SPEC-03 | Display extracted capabilities with counts | P0 |
| E-SPEC-04 | Spec version history | P2 |

### Epic E-STUDIO — Preview & optimize

| ID | Requirement | P |
|----|-------------|---|
| E-STUDIO-01 | Preview pack without persisting (in-memory) | P0 |
| E-STUDIO-02 | Optimizer slider Fast 3 / Balanced 10 / Thorough 25 | P0 |
| E-STUDIO-03 | Show set-cover compression stats | P0 |
| E-STUDIO-04 | Mandatory floors checklist UI | P0 |
| E-STUDIO-05 | Test candidate inspector (prompt, invariant, metadata) | P0 |
| E-STUDIO-06 | Presets (refund bot, order swarm, code agent) | P1 |

### Epic E-SUITE — Freeze & sync

| ID | Requirement | P |
|----|-------------|---|
| E-SUITE-01 | Freeze suite to immutable version | P0 |
| E-SUITE-02 | List suite versions; CI references suite ID + version | P0 |
| E-SUITE-03 | Regenerate/sync when PRD changes ([DR-011](../engineering-ledger/decisions.md)) | P1 |

### Epic E-RUN — Execute & score

| ID | Requirement | P |
|----|-------------|---|
| E-RUN-01 | Execute frozen suite against selected environment | P0 |
| E-RUN-02 | Stream or poll run progress in UI | P0 |
| E-RUN-03 | Verdicts: PASS, FAIL, UNVERIFIABLE | P0 |
| E-RUN-04 | Execution evidence inspector (observation, response, rule) | P0 |
| E-RUN-05 | Set baseline run for regression comparisons | P0 |
| E-RUN-06 | Regression diff banner (new fail, fixed, unchanged) | P0 |

### Epic E-REPLAY — Trajectory debugger

| ID | Requirement | P |
|----|-------------|---|
| E-REPLAY-01 | Open replay from failed test row | P0 |
| E-REPLAY-02 | Step timeline + transport controls | P0 |
| E-REPLAY-03 | Jump-to-fail | P0 |
| E-REPLAY-04 | Thought / action / observation panes | P0 |
| E-REPLAY-05 | Environmental state diff when harness profile available | P1 |

### Epic E-REPORT — Reports & compliance

| ID | Requirement | P |
|----|-------------|---|
| E-REPORT-01 | Generate standalone HTML report per run | P0 |
| E-REPORT-02 | In-app modal viewer for HTML report | P0 |
| E-REPORT-03 | Shareable read-only link (tokenized) | P1 |
| E-REPORT-04 | PDF compliance certificate with suite hash | P1 |
| E-REPORT-05 | OpenTelemetry / OpenInference JSON export | P1 |

### Epic E-API — Developer & CI

| ID | Requirement | P |
|----|-------------|---|
| E-API-01 | REST parity: preview, init/freeze, run, get run, report | P0 |
| E-API-02 | Workspace-scoped API keys | P0 |
| E-API-03 | CLI uses same API optionally (`agenteval login`) | P1 |
| E-API-04 | Webhook on run complete | P2 |

### Epic E-AUDIT — Governance

| ID | Requirement | P |
|----|-------------|---|
| E-AUDIT-01 | Audit log: freeze, run, key created/revoked | P1 |
| E-AUDIT-02 | Export audit log CSV | P2 |

---

## 10. Non-functional requirements

| Category | Target (v1 SaaS) |
|----------|------------------|
| **Availability** | 99.5% monthly (excludes customer agent downtime) |
| **Run UI feedback** | Run status updates ≤ 3s polling or SSE |
| **Probe timeout** | 10s default, configurable |
| **Data residency** | Single region (US) MVP; EU later |
| **Secrets** | Encrypted at rest; never echo in UI after save |
| **Multi-tenancy** | Hard workspace isolation on all queries |
| **Performance** | Studio preview ≤ 60s for k=25 (depends on LLM gateway) |
| **Accessibility** | WCAG 2.1 AA for core flows (signup, studio, runs table) |
| **Browser support** | Last 2 Chrome, Firefox, Safari, Edge |

---

## 11. Out of scope & later phases

| Item | Rationale |
|------|-----------|
| **Live production monitoring / APM** | Different product; pre-release only |
| **In-prod agent tracing ingestion** | Deferred |
| **Scenario YAML harness as default path** | Advanced/low priority ([DR-012](../engineering-ledger/decisions.md)) |
| **Built-in LLM hosting** | Customer brings agent endpoint |
| **Full billing & plans** | UI stub; manual early access |
| **Marketplace of test packs** | P2+ |
| **Real-time multi-user co-editing** | P2 |
| **Mobile native apps** | Web responsive only |

**Phase hint:** v1 SaaS = Auth + workspace + Studio + Runs + Replay + HTML report + API keys. v1.1 = Fleet home, OAuth, share links, golden curation. v2 = SSO, billing, webhooks.

---

## 12. Success metrics & release gates

### 12.1 Product metrics

| Metric | Definition |
|--------|------------|
| **TTFV** | Median time signup → first completed run |
| **Freeze rate** | % previews that become frozen suites within 7d |
| **CI adoption** | Workspaces with ≥1 API key running weekly |
| **Regression catch** | Runs with ≥1 regression detected before prod deploy (survey) |
| **Report export** | HTML report opens per run |

### 12.2 UX acceptance (per persona)

| Persona | Acceptance test |
|---------|-----------------|
| Alex | Complete onboarding wizard + green run without reading docs |
| Sam | CI job fails when injecting known regression |
| Maya | Export HTML; all mandatory floors visible |
| Marcus | Understand regression banner in &lt; 10s |
| Jordan | Invite user with Auditor role who cannot freeze |

---

## 13. Screen specifications (product console)

The following screens are the **authenticated product core** (P0). Visual wireframes: [ux-wireframes.md](ux-wireframes.md).

### 13.1 Global application header

- **Height:** 56px sticky; `bg-card/95`, backdrop blur, bottom border.
- **Left:** Logo + **AgentEval** + version pill (`Pre-Release`).
- **Center:** Segmented control — **Studio & Planner** | **Assurance Runs** (badge: frozen test count).
- **Right:** Agent selector, Environment badge (Local / Staging / CI), theme toggle, **Engine** connection pulse.

### 13.2 Studio & Test Planner (`/studio`)

**Left (specification):**

1. Presets quick-fill (P1).
2. Agent ID, target endpoint, **Probe** (200 OK + ms or Unreachable).
3. PRD / capabilities markdown editor with capability counter.
4. Optimizer ceiling slider k=3…25 (Fast / Balanced / Thorough).
5. Actions: **Preview pack** (outline), **Freeze suite** (primary purple).

**Right (inspector):**

1. Terminal chrome: view toggle Card vs Monaco, copy prompt.
2. Test candidate tabs `[01]`…`[k]`.
3. Badges: capability, persona tier, category, mandatory floor.
4. Sent prompt + invariant criterion + hypothesis rationale.
5. Bottom drawer: persona / failure / capability coverage bars; mandatory floors checklist; set-cover stats.

### 13.3 Assurance Runs (`/runs`)

1. **KPI strip:** Pass rate, pack tests, failures, unverifiable, avg latency (p95).
2. **Regression diff banner** vs baseline (0 regressions emerald; regressions rose + jump).
3. **Master-detail:** filterable table + execution evidence inspector (card + Monaco JSON).
4. Actions: **Execute run**, **Open standalone report**.

### 13.4 Trajectory debugger (`/runs/:id/replay`)

Playback, jump-to-fail, timeline ribbon, thought / action / observation (+ state diff P1).

### 13.5 Spec & uploads hub (`/uploads`) — P1

Drag-drop PRD/OpenAPI; spec library; promote failure to golden test.

### 13.6 Standalone HTML report

Allure-class offline HTML; filters; latency charts; drill-down. Modal in app + download.

### 13.7 Auth & onboarding screens (new — UX to generate)

| Screen | Must include |
|--------|----------------|
| **Marketing landing** | Value prop, CTA signup, BYOA diagram |
| **Sign up / Log in** | Email/password; OAuth P1; link to docs |
| **Verify email** | Resend, continue to onboarding |
| **Onboarding wizard** | Steps in §6.4 with progress indicator |
| **Invite accept** | Join workspace, role shown |
| **Settings → Members** | Table + invite modal |
| **Settings → API keys** | Create with scopes, one-time display |
| **Fleet home** | Agent cards, last run, P1 |

---

## 14. Design system & UX generator brief

### 14.1 Tokens

**Oklch grayscale + royal purple** — see [design-system/agenteval/MASTER.md](../../design-system/agenteval/MASTER.md).

| Token | Usage |
|-------|--------|
| `--background` | Canvas `#f8f9fa` / dark `#1a1b1e` |
| `--primary` | Royal purple CTAs (Freeze, Execute) |
| `pass` / `fail` / `warn` | Emerald / rose / amber verdicts |

Typography: **Inter** UI, **JetBrains Mono** code. Flat surfaces, minimal shadow.

### 14.2 Prompt for UX Pilot / Figma AI

> Design **AgentEval SaaS** — pre-release AI agent testing for engineering teams.  
>  
> **Personas:** Alex (engineer, daily), Sam (CI), Maya (auditor), Marcus (release), Jordan (admin).  
>  
> **Flows:** Sign up → onboarding wizard (PRD + endpoint probe) → Studio (2-column, optimizer, freeze) → Assurance Runs (KPIs, regression banner, table + evidence) → Replay (jump-to-fail) → HTML report. Include **Settings**: members, API keys, environments.  
>  
> **Style:** Oklch grayscale, royal purple primary, developer-dense but clean cards, Monaco for JSON, resizable split panes.  
>  
> **Do not design:** Production APM dashboards or live traffic monitors.

---

## Document history

| Version | Change |
|---------|--------|
| 3.0.0 | Pre-release console screen specs |
| 4.0.0 | Full SaaS: user ecosystem, 8 personas, journeys, auth/onboarding/RBAC, epics, NFR, scope |
