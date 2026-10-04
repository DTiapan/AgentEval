# Domain pack and connector interface

> **Status:** Contract + fintech v0 implemented (2026-09-27). Enable pack at freeze via env; audit evidence via `AGENTEVAL_AUDIT_LOG_DB_PATH`.
> **ADR:** [ADR-006](../decisions/ADR-006-pack-and-connector-contract.md)
> **Traces to:** FR-P-01..06, FR-B-21..23; [domain-model.md](domain-model.md).

## Separation

| | Domain pack | Connector |
|---|-------------|-----------|
| **Purpose** | Domain rules, terms, mandatory reqs, compliance mapping | Transport to agent or **evidence source** |
| **Examples** | Fintech, insurance, EU AI Act mapping | `http_transport`, `db_diff`, `audit_log` |
| **Depends on domain?** | Yes | **No** (backbone) |
| **Shipped by** | AgentEval maintainer (v1) | Customer config + backbone builtins |

Backbone code **must not** import pack modules (NFR-B-07). Discovery is **entry points**
(same pattern as [Inspect AI](https://inspect.ai-safety-institute.org.uk/) extensions).

## Pack manifest (installed row + package metadata)

Python package exposes entry point group: `agenteval.domain_packs`

```toml
# pyproject.toml (pack project)
[project.entry-points."agenteval.domain_packs"]
fintech = "agenteval_packs.fintech:FintechPack"
```

**`PackManifest`** (Pydantic, stored in `packs.manifest_json`):

| Field | Type | Required |
|-------|------|----------|
| `name` | str | yes |
| `version` | str | yes |
| `display_name` | str | yes |
| `description` | str | no |
| `slots_filled` | list[str] | yes — subset of slot ids below |

## Eight slots (any subset)

| Slot id | Provides | Consumed at |
|---------|----------|-------------|
| `options` | JSON schema for Studio toggles | Suite freeze → `suite_pack_selections.options_json` |
| `terms` | Glossary + extraction hints | PRD ingest |
| `mandatory_requirements` | `Requirement` drafts (`source_kind=pack`) | Freeze |
| `scenarios` | Extra `TestCase` seeds | Pool generation |
| `personas` | Persona definitions | Pool generation |
| `synthetic_test_data` | Frozen into `test_cases.test_data_json` | Freeze |
| `evidence_interpreters` | Map raw probe → `EvidenceItem` kinds | Run |
| `checks` | `check_kind` + scorer entry points | Run |
| `compliance_mappings` | `ComplianceControl` + links to criteria | Report (FR-B-23) |

## Pack protocol (Python ABC, target location `agenteval/packs/protocol.py`)

```python
class DomainPack(Protocol):
    manifest: PackManifest

    def contribute_options(self) -> dict[str, object]: ...
    def extraction_hints(self) -> list[ExtractionHint]: ...
    def mandatory_requirements(self, options: dict) -> list[RequirementDraft]: ...
    def compliance_controls(self) -> list[ComplianceControlDraft]: ...
    def register_checks(self) -> list[CheckRegistration]: ...

    # optional slot methods return empty defaults
```

**`CheckRegistration`:** `check_kind: str`, `evidence_kinds: list[str]`, entry point
to callable `(criterion, evidence_items) -> CriterionVerdictDraft`.

Entry point group for checks: `agenteval.pack_checks`

## Connector protocol

Entry point group: `agenteval.connectors`

| `kind` (DB) | Role |
|-------------|------|
| `http_transport` | Invoke agent (Solver) |
| `mcp_transport` | MCP agent |
| `db_diff` | Pre/post DB snapshot |
| `audit_log` | Query append-only audit table |
| `trace` | OTel / Inspect log ingest |

**`ConnectorConfig`** stored in `connectors.config_json`, validated per kind.

**Target** = one `transport_connector` + zero or more `target_evidence_connectors`
(see persistence schema).

## Suite freeze recording (FR-P-05)

`suite_pack_selections` + `suite_versions` must record:

- pack name + version per enabled pack
- connector ids + versions (or config hash) for target used on runs

## Fintech pack v0 (first implementation target)

| Slot | v0 scope |
|------|----------|
| `mandatory_requirements` | 2–3 disclosure / limit rules (no backbone wording) |
| `compliance_mappings` | Map to named control keys (not legal advice) |
| `checks` | One deterministic check against sample `audit_log` connector |
| `synthetic_test_data` | Order ids / amounts for refund sample agent |

**Enablement (v0):** `AGENTEVAL_ENABLED_DOMAIN_PACKS=fintech` at freeze; optional `AGENTEVAL_AUDIT_LOG_DB_PATH` at run for audit evidence.

## Out of scope (v1)

- Customer-authored packs
- Pack marketplace
- Runtime download of packs without install
