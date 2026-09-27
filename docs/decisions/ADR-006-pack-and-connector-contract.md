# ADR-006: Domain pack and connector contract

**Status:** Accepted; protocol + fintech v0 pack shipped (checks/connectors pending)  
**Date:** 2026-09-27  
**Context:** [ADR-005](ADR-005-backbone-domain-packs-source-of-truth.md), [pack-interface.md](../design/pack-interface.md), FR-P-01..06

## Context

Domain logic must not live in the backbone (NFR-B-07), but packs and connectors
were only described in prose in ADR-005. Implementers need a stable contract before
writing fintech or connector registration code.

## Decision

1. **Normative interface doc:** [docs/design/pack-interface.md](../design/pack-interface.md)
   defines pack slots, entry point groups (`agenteval.domain_packs`,
   `agenteval.pack_checks`, `agenteval.connectors`), and the `DomainPack` protocol.

2. **Connectors are not packs.** Transport and evidence sources are configured per
   workspace and referenced by `Target`.

3. **Checks are registered**, not hardcoded in backbone scorers, except for
   built-in `blackbox_observable` and harness builtins until packs ship.

4. **v1 packs** ship as Python packages in-repo; no customer pack authoring.

## Consequences

- Fintech pack work starts by implementing `agenteval_packs.fintech` against the protocol.
- Backbone adds `agenteval/packs/protocol.py` (types only) before any pack code.
- CI will eventually grep for forbidden domain strings in `agenteval/` excluding `agenteval_packs/`.

## Alternatives considered

| Option | Why not |
|--------|---------|
| YAML pack configs only | Cannot run deterministic checks or evidence interpreters safely |
| Packs as DB-only rows | No versioned code for scorers; poor reproducibility |
