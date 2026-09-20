# AgentEval — Google Stitch copy-paste prompts

> **How to use:** Stitch → **Web** → paste **one** prompt → Generate → refine with follow-ups → next prompt.  
> **MCP:** Agent-driven flow → [STITCH_MCP_SETUP.md](STITCH_MCP_SETUP.md) (Cursor MCP must show `stitch` tools).  
> **Onboarding stepper (canonical):** 1 Name agent → 2 Requirements & endpoint → 3 Preview pack → 4 Freeze suite → 5 Run & CI gate.  
> **Demo data (everywhere):** `demo-refund-agent`, max refund **$100**, failure **$250**, **8** frozen tests, Staging URL `https://staging.acme.com/v1/chat`.

---

## Prompt 01 — Marketing landing

```
Design a desktop marketing landing page for agenteval.app.

Hero: headline "Test AI agents before production." Subheadline: "Deterministic evidence, frozen regression suites, and release gating for tool-calling agents—no vibes, no prod APM."

Primary CTA button purple: "Start free". Secondary outline: "Read docs".

Three feature columns with icons (simple line icons):
1) "Requirements → test pack" — set-cover optimizer from PRD
2) "Freeze & regress" — baseline diff on every run
3) "Replay & audit" — jump-to-fail trajectory + HTML report

Small code-style strip example: PASS / FAIL / UNVERIFIABLE badges.

Footer: minimal links Terms, Privacy, GitHub. No robot stock photos, no chat bubble hero, no gradient blobs.

Style: B2B developer SaaS. Light canvas #f8f9fa, white cards, subtle gray borders #adb5bd, royal purple primary #7C3AED, Inter font, JetBrains Mono for code snippets. Flat UI, minimal shadows. NOT a consumer chat app.
```

---

## Prompt 02 — Sign up + create workspace

```
Design a desktop sign-up screen for AgentEval (agenteval.app).

Split layout:
LEFT panel (40%): dark charcoal #1a1b1e with white text. Headline: "Deterministic testing & release gating for autonomous AI agents." Three trust bullets with checkmarks: "BYOA — HTTP/MCP, zero agent code changes", "Frozen regression suites for CI", "Exportable HTML audit reports". No heavy purple gradient.

RIGHT panel (60%): white card titled "Create your workspace".
- SSO buttons full width: "Continue with GitHub", "Continue with Google"
- Divider "Or continue with work email"
- Fields: Full name, Work email, Password (hint min 12 chars) with strength meter
- Workspace name input "Acme AI Core" with live slug preview: app.agenteval.app/acme-ai-core
- Checkbox: agree to Terms of Service and Privacy Policy
- Primary purple full width: "Create workspace & continue"
- Footer link: "Already have an account? Sign in"

Style: Inter UI, purple primary #7C3AED, clean borders, professional dev-tool aesthetic. NOT playful consumer app.
```

---

## Prompt 03 — Sign in

```
Design a desktop sign-in screen for AgentEval matching the sign-up brand.

Centered white card on #f8f9fa background. Logo AgentEval top. Title "Sign in". Subtitle "Welcome back to Acme AI Core workspace."

Fields: Work email, Password with show/hide. Link "Forgot password?" right-aligned.

Primary purple button "Sign in". SSO buttons GitHub and Google below divider.

Link at bottom: "New here? Create a workspace"

Style: Inter, royal purple #7C3AED, flat cards, minimal shadow. Developer SaaS tone.
```

---

## Prompt 04 — Verify email

```
Design desktop "Verify your email" screen for AgentEval post-signup.

Centered card on soft gray #f8f9fa. Logo + title "Check your inbox". Body text: we sent a verification link to maya@acme.com.

Illustration: simple envelope icon, not cartoonish.

Buttons: outline "Resend email", disabled gray "Continue" until verified.

Link: "Wrong email? Change address"

Show alternate success state in a second variant frame: green check "Email verified" with enabled purple button "Continue to onboarding".

Style: Inter, purple #7C3AED, minimal, professional.
```

---

## Prompt 05 — Onboarding 1/5 — First agent

```
Design AgentEval onboarding step 1 of 5 (desktop web, authenticated).

Top horizontal stepper: 1 filled, 2-5 empty. Workspace context chip: "Acme AI Core".

Title: "Name your first agent". Subtitle: "You can add more agents later in this workspace."

Form card:
- Agent display name: "Refund Assistant"
- Agent ID (slug): demo-refund-agent (editable with validation hint)
- Optional description textarea

Footer actions: Back (disabled), primary purple "Continue".

Right column optional simple diagram: Requirements → Test pack → Run (thin lines, no 3D).

Style: #f8f9fa canvas, white cards, purple primary, Inter + JetBrains Mono for agent id field.
```

---

## Prompt 06 — Onboarding 2/5 — Requirements

```
Design AgentEval onboarding step 2 of 5 (desktop).

Stepper step 2 active. Title "Paste your requirements". Subtitle "We derive capabilities and tests from this—no scenario YAML."

Large textarea with monospace PRD sample about refund agent: max $100 without manager approval, Stripe refund tool, no PII in logs.

Below textarea: purple chip "6 capabilities detected". Links: "Upload .md file", "Use example PRD".

Back button, purple Continue.

Style: developer SaaS, light gray background, white card, Inter UI.
```

---

## Prompt 07 — Onboarding 3/5 — Endpoint & probe

```
Design AgentEval onboarding step 3 of 5 (desktop).

Title "Connect staging endpoint". Subtitle "Black-box tests call your agent URL—we never modify your code."

Environment pills: Local | Staging (selected) | CI

Fields:
- Endpoint URL: https://staging.acme.com/v1/chat
- Auth header (optional) masked secret field

Purple "Probe" button. Green inline result: "200 OK · 18ms"

Show error variant on same layout: amber banner "Unreachable — check URL, auth, or VPN"

Continue button disabled until probe succeeds. Back button.

Style: Inter, purple #7C3AED, flat professional UI.
```

---

## Prompt 08 — Onboarding 4/5 — Preview & freeze

```
Design AgentEval onboarding step 4 of 5 (desktop).

Title "Preview optimized pack". Optimizer slider with labels Fast (3), Balanced (10 selected), Thorough (25).

Stats line: "38 candidates → 8 tests · 78% compression · mandatory floors retained"

Scrollable preview list (4 visible rows):
- [01] core refund flow — badge functional
- [02] ceiling-breach — badge mandatory floor rose outline
- [03] prompt injection — badge security
- [04] invalid input — badge edge case

Mandatory floors checklist with green checks: Authorization ceiling, Prompt injection resistance.

Back, primary purple "Freeze suite & continue".

Style: data-dense but clean, Inter, purple primary.
```

---

## Prompt 09 — Onboarding 5/5 — First run

```
Design AgentEval onboarding step 5 of 5 (desktop).

Title "Run assurance". Summary card: Agent demo-refund-agent · 8 frozen tests · Environment Staging.

Large purple "Execute run" button.

Progress section showing run in progress: spinner on test 3 of 8 "test-ceiling-breach".

Completed state below: KPI row — Pass rate 87% (7/8), 1 failure rose, 0 unverifiable amber, avg 24ms.

Links: text "View failure in replay", purple button "Open Assurance Runs".

No confetti. Professional engineering tone.

Style: AgentEval light theme, purple CTAs.
```

---

## Prompt 10 — App header (component)

```
Design ONLY the sticky top application header for AgentEval authenticated desktop app. No page body.

Height 56px, white bar with subtle bottom border and light backdrop blur.

Left: shield logo + bold "AgentEval" + small pill "Pre-Release"

Center: segmented control tabs — "Studio & Planner" | "Assurance Runs" with numeric badge 8 on second tab.

Right: dropdown "demo-refund-agent v1", environment badge "Staging", sun/moon theme toggle, green dot label "Engine connected".

Below header optional thin bar: workspace name "Acme AI Core" with chevron.

Style: Inter, royal purple active tab #7C3AED, gray #f8f9fa page peek below header.
```

---

## Prompt 11 — Studio & Planner (full page)

```
Design full desktop page "Studio & Planner" for AgentEval including the sticky header (Studio tab active).

Two-column resizable layout with gap between floating white cards on #f8f9fa canvas.

LEFT COLUMN cards:
1) Preset chips: Customer Refund, Order Swarm, Code Bot
2) Agent ID demo-refund-agent, Endpoint URL + outline "Probe" showing green 200 OK 18ms
3) PRD markdown editor with "6 capabilities detected"
4) Slider "Optimizer ceiling" Fast 3, Balanced 10, Thorough 25
5) Button row: "Preview pack" outline, "Freeze suite" solid purple

RIGHT COLUMN dark terminal inspector (#1a1b1e):
- Traffic light window dots, filename test-pack.yaml
- Toggle Card view | Monaco, button Copy prompt
- Tabs [01 core-behav] [02 ceiling-breach] [03 injection]
- Badges: cap:refund_process, persona:adversary, mandatory floor
- Box "Sent prompt" monospace
- Purple left border box "Invariant: agent must not approve refund over $100 without manager approval"
- Bottom drawer: progress bars Persona coverage, Failure surface, Capability coverage; text "Candidate pool 38 → Pack 8"

NOT a chat UI. Developer testing console.

Style: Inter + JetBrains Mono, purple #7C3AED primary, flat borders, minimal shadow.
```

**Follow-up (optional):** `Add empty state: PRD textarea placeholder and disabled Freeze suite button.`

---

## Prompt 12 — Assurance Runs (full page)

```
Design full desktop page "Assurance Runs" for AgentEval. Header with Assurance Runs tab active (badge 8).

Row of 5 KPI cards:
- Pass rate 87% (7/8) — amber because not 100%
- Pack tests: 8 frozen
- Failures: 1 rose
- Unverifiable: 0
- Avg latency 24ms, subtext p95 42ms

Rose alert banner full width: "⚠ 2 regressions vs v1.1 baseline" with buttons "Jump to failing test" (purple) and "Compare baselines" (outline).

Master-detail split ~55/45:

LEFT: search box, filter pills ALL PASS FAIL UNVERIFIABLE. Table columns Verdict, Test ID, Prompt snippet, Capability, ms. One FAIL row selected with purple left border: test-ceiling-breach.

RIGHT: Execution evidence inspector — HTTP 200 OK pill, Sent prompt, Agent response text agreeing to $250 refund, section Invariant check FAILED rose background explaining $250 exceeds $100 cap. Toggle Card | JSON. Buttons: purple "Execute run", outline "Open standalone report".

Style: data-dense engineering dashboard, Inter, JetBrains Mono in inspector, purple brand.
```

**Follow-up (optional):** `Replace regression banner with emerald "✓ 0 regressions vs v1.1 baseline".`

---

## Prompt 13 — Trajectory replay (full page)

```
Design desktop "Trajectory replay" page for AgentEval for failed test test-ceiling-breach.

Top: back link "← Assurance Runs", title with FAIL rose badge.

Playback bar: buttons First Prev Play Next Last, label "Turn 3 of 7", prominent outline button "Jump to fail".

Horizontal timeline with nodes: User message, Tool call refund, Observation, Invariant fail (highlighted red).

Three equal panels below with dark headers:
- Thought: agent reasoning excerpt
- Action: tool name process_refund, JSON args amount 250
- Observation: mock Stripe response success

Light page background, dark panel headers, monospace in action/observation.

Style: Inter UI, purple accents on primary actions, professional debugger aesthetic NOT video player consumer UI.
```

---

## Prompt 14 — HTML report modal

```
Design a large modal dialog over dimmed Assurance Runs page: "Standalone run report".

Modal ~90% viewport. Header: Run report run_8f3a2c · demo-refund-agent · Staging. Buttons Download HTML, Close X.

Report interior: summary pass/fail counts, small chart, filter chips ALL FAIL PASS UNVERIFIABLE, sortable test table with latency column. Clicked row shows detail snippet.

Use readable contrast; purple links; dark slate OR light report theme but keep AgentEval purple #7C3AED for links and primary actions.

Style: audit/compliance friendly, engineer-readable density.
```

---

## Prompt 15 — Settings: Members

```
Design AgentEval Settings page desktop. Left sidebar: Profile, Members (active), API Keys, Environments, Billing (gray "Soon").

Main panel Members:
- Title "Team members" subtitle "Manage who can freeze suites and run tests in Acme AI Core"
- Purple button "Invite member"
- Table: Name, Email, Role pill, Last active, menu dots
- Rows: Alex Chen alex@acme.com Engineer, Maya Patel maya@acme.com Auditor, Marcus Lee marcus@acme.com Viewer

Modal state "Invite member": email field, role select Engineer / Auditor / Viewer / Admin, Send invite purple button.

Include same top app header as AgentEval with Settings gear or user menu indicating settings context.

Style: Inter, white cards on #f8f9fa, purple primary.
```

---

## Prompt 16 — Settings: API keys

```
Design AgentEval Settings API Keys page desktop. Sidebar with API Keys active.

Intro one sentence: "Use keys in GitHub Actions to run frozen suites on every PR."

Table columns: Name, Scopes, Created, Last used, Revoke (destructive text).

Row: github-actions-pr · run:read, suite:run · Created Mar 1 · Last used 2h ago.

Purple "Create API key" opens modal: name input, checkboxes scopes, Create button.

After-create state: yellow callout "Copy this key now—it won't be shown again" with masked key field and copy icon.

Style: security-conscious dev SaaS, Inter, purple CTAs.
```

---

## Prompt 17 — Settings: Environments

```
Design AgentEval Settings Environments page desktop.

Three environment cards in a column:
- Local — base URL http://127.0.0.1:8765/chat — not default
- Staging — https://staging.acme.com/v1/chat — radio "Default for runs" selected
- CI — https://ci.internal.acme.com/agent — secret header configured checkmark

Each card: URL field, optional default headers secrets masked, Save outline button.

Help text: "Runs and probes use the default environment unless overridden."

Style: Inter, white cards, #f8f9fa background, purple Save primary on page bottom optional.
```

---

## Prompt 18 — Fleet home (dashboard)

```
Design AgentEval Home dashboard desktop for workspace Acme AI Core.

Include standard AgentEval header. Title "Agents". Purple button "Add agent".

Grid of 2-3 agent cards:
Card 1: demo-refund-agent, Staging, last run 2 hours ago, big pass 87%, rose chip "2 regressions", links View runs | Studio
Card 2: order-fulfillment-bot, CI, 100% pass, green "0 regressions"
Card 3 dashed empty state "Connect another agent"

Designed for engineering lead glanceable status, not executive fluff.

Style: Inter, purple accents, light theme cards on gray canvas.
```

---

## Quick refine prompts (use one at a time)

```
Switch entire screen to dark mode: background #1a1b1e, cards #222326, keep purple primary and emerald/rose verdict colors.
```

```
Increase data density: smaller table row height, more rows visible, keep accessibility contrast.
```

```
Make all primary buttons royal purple #7C3AED and remove cyan/teal accents everywhere.
```

```
Add keyboard focus rings on all interactive elements for WCAG visibility.
```

```
Remove decorative gradients and drop shadows; use 1px borders only.
```

---

## Recommended generation order

1. **02–03** Auth (skip if done)  
2. **10** Header  
3. **11–13** Core product (Studio, Runs, Replay)  
4. **05–09** Onboarding  
5. **14–18** Report modal + Settings + Home  
6. **01** Landing (optional polish)
