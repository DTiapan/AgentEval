# ADR-007: Production Database Architecture — SQLite-on-GCS Evaluation and Dual-Engine Persistence Strategy

**Status:** Accepted  
**Date:** 2026-10-04  
**Context:** [ADR-004](ADR-004-sqlite-local-persistence.md) (SQLite for local and single-tenant persistence), [DR-020](../engineering-ledger/decisions.md) (SQLite v1 schema), [DR-029](../engineering-ledger/decisions.md) (Turnkey GCP Deployment), [DR-039](../engineering-ledger/decisions.md) (Drop Dual Persistence)

---

## Context

In [ADR-004](ADR-004-sqlite-local-persistence.md), AgentEval established SQLite as the embedded default persistence engine, replacing legacy filesystem JSON files. In [DR-029](../engineering-ledger/decisions.md), AgentEval introduced turnkey Google Cloud Platform deployment scripts (`deploy/gcp/deploy.sh`) targeting Google Cloud Run Gen2, mounting persistent storage via Cloud Storage FUSE:
```bash
--add-volume="name=agenteval-data,type=cloud-storage,bucket=${GCS_DATA_BUCKET}"
--add-volume-mount="volume=agenteval-data,mount-path=/app/data"
```

While this setup allows database files (`agenteval.db`) to survive Cloud Run container redeployments, running SQLite over Cloud Storage FUSE (`gcsfuse`) in an autoscaling container runtime introduces fundamental architectural hazards:

1. **Absence of Distributed POSIX Advisory Locks:**
   SQLite relies on POSIX advisory byte-range locking (`fcntl()` / `flock()`) within the operating system kernel to serialize concurrent writes. Google Cloud Storage is an HTTP object store, not a POSIX filesystem. GCS has no centralized lock manager. When Cloud Run autoscales to $\ge 2$ instances (or during zero-downtime rolling revision deployments), multiple containers mount the same bucket and write concurrently. Neither container sees the other's locks. Concurrent flushes overwrite pages in GCS, corrupting the database file (`sqlite3.DatabaseError: database disk image is malformed`).

2. **Shared Memory (`.shm`) and WAL Mode Incompatibility:**
   High-performance SQLite concurrency depends on Write-Ahead Logging (WAL) and memory-mapped shared memory (`agenteval.db-shm` via `mmap()`). Network object storage drivers do not support cross-machine shared memory. Attempting to run WAL mode over GCS FUSE risks transaction coordination failures and process crashes.

3. **High Write Latency and API Amplification:**
   Because Cloud Storage objects are immutable, every transactional `fsync` executed by SQLite forces `gcsfuse` to upload the database file over HTTPS to Google's API. This inflates commit latency from sub-millisecond local NVMe speeds to 50–250ms per transaction and incurs substantial GCS Class A operation fees during incremental result streaming.

4. **Official Google Cloud Architectural Guidance:**
   Google explicitly states in Cloud Run and GCS FUSE documentation:
   > *"Cloud Storage FUSE is not POSIX-compliant and does not support file locking. Do not use Cloud Storage FUSE for databases such as SQLite, MySQL, or PostgreSQL."*

We need a definitive persistence architecture that guarantees data safety and horizontal scalability in production cloud environments while preserving frictionless, zero-configuration local execution for open-source developers.

---

## Alternatives Considered

### Option A: Retain SQLite on GCS FUSE with Single-Instance Pinning
- **Mechanism:** Enforce `max-instances: 1` (`--max-instances=1`) in Cloud Run configuration and use rollback journals (`journal_mode = DELETE` or `TRUNCATE`) or periodic snapshot backups.
- **Pros:** Zero new infrastructure required; low monthly cost.
- **Cons:** Caps throughput to a single container; high write latency (50-250ms per fsync); vulnerable to silent corruption during rolling revision deployments if two revisions briefly overlap.
- **Verdict:** Acceptable only as an immediate emergency operational guardrail; rejected as a production architecture.

### Option B: SQLite with Litestream Replication to GCS + Local Ephemeral Disk
- **Mechanism:** Store `agenteval.db` on Cloud Run's local ephemeral NVMe/RAM disk (`/tmp/agenteval.db`). Run Litestream as a companion process that continuously streams WAL frames to `gs://${GCS_DATA_BUCKET}`. On container startup, Litestream restores the database from GCS in <1s.
- **Pros:** Retains SQLite (0 query code changes); sub-millisecond local disk write speeds; low cost.
- **Cons:** Strictly single-writer. If Cloud Run scales to 2 instances, multiple writers cause split-brain replica corruption. Cloud Run must remain permanently pinned to `max-instances: 1`.
- **Verdict:** Viable for dedicated single-tenant appliances, but does not provide a path for multi-tenant SaaS scaling.

### Option C: Managed PostgreSQL Only (Complete Replacement of SQLite)
- **Mechanism:** Remove SQLite entirely and require PostgreSQL (Google Cloud SQL or serverless Neon/Supabase) for all environments.
- **Pros:** Complete ACID compliance, unlimited horizontal autoscaling, row-level locking, native `JSONB` for trajectory queries.
- **Cons:** Destroys frictionless onboarding for local developers, CLI evaluation (`agenteval run`), and air-gapped CI, requiring every user to run and manage a Postgres container.
- **Verdict:** Rejected as an exclusive solution due to high developer friction.

### Option D: Dual-Engine Persistence Strategy (Accepted)
- **Mechanism:** Decouple the database repository abstraction from the underlying SQL driver:
  1. **Local / CLI / CI / Single-Node Appliance:** Default to embedded **SQLite** (`.agenteval/agenteval.db`). Zero configuration, zero cost, air-gapped, sub-millisecond execution.
  2. **Cloud Run / Production Multi-Tenant SaaS:** Connect to **Managed PostgreSQL** (Cloud SQL / Neon / Supabase) via standard connection strings (`DATABASE_URL=postgresql://...`).
  3. **Immediate Cloud Run Safety Guardrail:** Until PostgreSQL is connected, clamp Cloud Run to `MAX_INSTANCES=1` to prevent GCS FUSE multi-writer corruption.
- **Verdict:** **Accepted.** Delivers enterprise cloud scalability without sacrificing the zero-friction developer experience.

---

## Decision

1. **Adopt Dual-Engine Persistence Strategy:**
   - **Engine 1 (SQLite):** Authoritative storage for local development, CLI workflows, air-gapped CI, and self-hosted single-node instances. Preserved under `agenteval/db/`.
   - **Engine 2 (PostgreSQL):** Authoritative storage for cloud-hosted multi-tenant SaaS deployments and autoscaling Cloud Run fleets. Configured dynamically whenever `DATABASE_URL` starts with `postgres://` or `postgresql://`.

2. **Schema & Relational Parity:**
   - Maintain strict relational schema parity between SQLite and PostgreSQL DDL (`workspaces`, `users`, `agents`, `suite_versions`, `assurance_runs`, `test_case_results`, `execution_steps`).
   - SQLite uses `TEXT` for JSON fields; PostgreSQL uses native `JSONB` with GIN indexing for fast trajectory and tool-call queries.

3. **Immediate Cloud Run Operational Guardrails:**
   - In `deploy/gcp/deploy.sh` and `deploy/gcp/service.yaml`, set default `MAX_INSTANCES=1` and `autoscaling.knative.dev/maxScale: "1"`.
   - When SQLite on GCS FUSE is detected, actively enforce `MAX_INSTANCES=1` to prevent multi-instance split-brain corruption.

---

## Consequences

### Positive
- **Data Integrity:** Eliminates the risk of catastrophic database corruption from concurrent Cloud Run instances writing to GCS FUSE.
- **Horizontal Scalability:** Clears the path for Cloud Run to scale to 10–100+ container instances once PostgreSQL is connected.
- **Preserved Developer Experience:** Local engineers and CI runners retain zero-dependency embedded SQLite with instant startup.
- **High-Performance Trajectory Analytics:** PostgreSQL `JSONB` enables indexing deep within execution traces and OTel spans.

### Negative / Trade-offs
- **Driver Maintenance:** The persistence layer must maintain compatibility across SQLite (`sqlite3`) and PostgreSQL (`asyncpg` / `psycopg3`).
- **Test Matrix:** Automated integration test suites will need to run against both SQLite and PostgreSQL backends in CI.

---

## Implementation Roadmap

- **Phase 1 (Immediate Guardrail — Slice 12):**
  - Publish ADR-007.
  - Enforce `MAX_INSTANCES=1` guardrails in `deploy.sh`, `service.yaml`, and `.env.gcp.example`.
  - Add automated regression tests in `test_cloud_deployment_config.py`.
- **Phase 2 (Repository Protocol & Driver Abstraction):**
  - Refactor `SuiteRepository` into a protocol / abstract base class.
  - Implement `PostgresSuiteRepository` leveraging `psycopg3` or `asyncpg`.
- **Phase 3 (Cloud SQL Production Integration):**
  - Add Cloud SQL connection proxy and VPC connector flags to `deploy.sh`.
  - Allow `MAX_INSTANCES` to scale up to 10–100 once PostgreSQL is active.

---

## References

- [ADR-004: SQLite for local and single-tenant persistence (v1)](ADR-004-sqlite-local-persistence.md)
- [DR-029: Turnkey Google Cloud Deployment Pipeline](../engineering-ledger/decisions.md#dr-029--turnkey-google-cloud-deployment-pipeline-cloud-run-gen2-gcs-volume-mount-secret-manager--serverless-vpc)
- [Google Cloud Storage FUSE Limitations](https://cloud.google.com/storage/docs/gcs-fuse)
- [Google Cloud Run Volume Mounts Overview](https://cloud.google.com/run/docs/configuring/services/volume-mounts)
