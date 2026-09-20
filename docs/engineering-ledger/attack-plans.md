# Attack plans

## Active index

| ID | Title | Status |
|----|-------|--------|
| AP-001 | Platform Architecture, Pluggable BYOA Harness & Trajectory Assurance Engine | active |

---

## AP-001: Platform Architecture, Pluggable BYOA Harness & Trajectory Assurance Engine

- **Owner**: Craft / Dev
- **Status**: active
- **Goal**: Establish core pluggable agent evaluation platform with universal agent adapters (HTTP, MCP, CLI, Python callable), trajectory-first verification engine, sandbox side-effect assertions, telemetry collector, and CLI test runner.

### Steps
1. [x] Adopt Craft framework in repository (`craft.project.yaml`, `AGENTS.md`, 52 domain skills installed in `.agents/skills`).
2. [x] Connect local git repository with remote `https://github.com/DTiapan/AgentEval.git`.
3. [x] Research TestMu AI Assurance, competitive landscape, and define implementation blueprint.
4. [ ] Scaffold core Python package (`agenteval/core`, `agenteval/adapters`, `agenteval/evaluators`, `agenteval/sandbox`, `agenteval/replay`, `agenteval/telemetry`, `agenteval/cli`).
5. [ ] Implement Universal Agent Adapters (`HTTPAdapter`, `MCPAdapter`, `CallableAdapter`, `CLIAdapter`).
6. [ ] Implement Trajectory & Tool Call Evaluators (Schema correctness, loop detection, state diff verification).
7. [ ] Implement Real-Time Live Streamer & Interactive Trajectory Replay (`agenteval run --live`, `agenteval replay <run-id>`, step scrubbing, `--jump-to-fail`).
8. [ ] Implement OpenTelemetry / OpenInference tracing and metrics exporter.
9. [ ] Implement Self-evolving Golden Dataset synthesizer & production log miner.
10. [ ] Implement CLI and CI/CD quality gate reporter (`agenteval run`, `agenteval gate`).
11. [ ] Build high-impact modern developer dashboard with visual scrubber, flame graphs, and dataset curation.

---

## Archive

<!-- Move cancelled/superseded AP summaries here -->
