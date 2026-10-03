# Google Cloud Platform (Cloud Run) Deployment for AgentEval

Production turnkey deployment guide for **AgentEval: AI Agent Assurance & Evaluation Platform** on Google Cloud Platform, modeled after the battle-tested architecture in Recall.

---

## Architecture Overview

```
                                  ┌────────────────────────────────────────────────────────┐
                                  │ Google Cloud Platform                                  │
                                  │                                                        │
┌────────────────────────┐        │   ┌────────────────────────────────────────────────┐   │
│ Client / Browser / CI  │───────>│   │ Cloud Run (Gen2, 2 vCPUs, 4 GiB, CPU Boost)    │   │
│ (agenteval.app / web)  │  HTTPS │   │                                                │   │
└────────────────────────┘        │   │  • FastAPI REST API & Swagger docs (:8080)     │   │
                                  │   │  • Vite React Console served at /              │   │
                                  │   │  • Unprivileged runtime user (uid 10001)       │   │
                                  │   └──────┬──────────────────────┬─────────────┬────┘   │
                                  │          │                      │             │        │
                                  │          ▼                      ▼             │        │
                                  │   ┌───────────────┐     ┌───────────────┐     │        │
                                  │   │ Cloud Storage │     │ Secret        │     │        │
                                  │   │ Volume Mount  │     │ Manager       │     │        │
                                  │   │ (/app/data)   │     │ (API Keys)    │     │        │
                                  │   │               │     │               │     │        │
                                  │   │ • SQLite DB   │     │ • OpenRouter  │     │        │
                                  │   │ • Test Suites │     │ • DeepSeek    │     │        │
                                  │   │ • Run Reports │     │ • OpenAI      │     │        │
                                  │   │ • Traces & ΔS │     │ • TypeSafe AI │     │        │
                                  │   └───────────────┘     └───────────────┘     │        │
                                  │                                               ▼        │
                                  │                                     ┌────────────────┐ │
                                  │                                     │ Serverless VPC │ │
                                  │                                     │ Access (egress)│ │
                                  │                                     └───────┬────────┘ │
                                  │                                             │          │
                                  └─────────────────────────────────────────────┼──────────┘
                                                                                ▼
                                                                  ┌────────────────────────┐
                                                                  │ Evaluated Private      │
                                                                  │ Target Agents (VPC)    │
                                                                  │ (GCE / GKE / Private)  │
                                                                  └────────────────────────┘
```

---

## 1. Quickstart (Turnkey Deployment)

### Step 1: Create or Select Google Cloud Project

#### Option A: Create a brand-new GCP project automatically (Recommended)
You can create a new project, link your billing account, and enable all required APIs in one command directly from your terminal:
```bash
./deploy/gcp/setup-project.sh [NEW_PROJECT_ID]
```
*(If no project ID is provided, it auto-generates `agenteval-YYMMDDHHMM` and configures `.env.gcp` automatically).*

#### Option B: Use an existing GCP project
```bash
gcloud auth login
gcloud config set project <YOUR_GCP_PROJECT_ID>
cp .env.gcp.example .env.gcp
# Set GCP_PROJECT_ID=<YOUR_GCP_PROJECT_ID> in .env.gcp
```

### Step 3: Run Turnkey Deployment
```bash
./deploy/gcp/deploy.sh
```
This automated script will:
1. Enable all necessary GCP APIs (`run`, `artifactregistry`, `cloudbuild`, `secretmanager`, `storage`, `vpcaccess`).
2. Create an Artifact Registry Docker repository (`agenteval-repo`) if not present.
3. Build the multi-stage container image (compiling Web UI + Python environment) using Google Cloud Build.
4. Ensure the Google Cloud Storage bucket exists and grant `roles/storage.objectAdmin` to Cloud Run's compute service account.
5. Scan Secret Manager and automatically bind evaluator keys (`OPENROUTER_API_KEY`, `DEEPSEEK_API_KEY`, `OPENAI_API_KEY`, `TYPESAFE_API_KEY`).
6. Deploy to Google Cloud Run Gen2 with persistent volume mount at `/app/data`.
7. Output the live Web Console URL and health status.

---

## 2. Secrets Management (Google Secret Manager)

Store your LLM gateway and evaluator credentials in Google Cloud Secret Manager for zero plaintext exposure:

```bash
# OpenRouter API Key (Recommended default for LiteLLM & DeepEval)
gcloud secrets create openrouter-api-key --data-file=- <<< "sk-or-v1-..."

# DeepSeek Direct API Key (Optional)
gcloud secrets create deepseek-api-key --data-file=- <<< "sk-..."

# OpenAI API Key (Optional)
gcloud secrets create openai-api-key --data-file=- <<< "sk-..."

# TypeSafe AI Jev API Key (Optional)
gcloud secrets create typesafe-api-key --data-file=- <<< "ts-..."
```

`deploy.sh` automatically checks for these secret names, binds `roles/secretmanager.secretAccessor` to the Cloud Run service account, and injects them as environment variables into the container.

---

## 3. Persistent Volume (Surviving Redeploys)

AgentEval persists all regression suites, frozen baselines, execution traces, test candidate pools, and the SQLite database (`agenteval.db`) under `AGENTEVAL_DATA_DIR` (`/app/data`).

On Cloud Run Gen2, this directory is backed by a native **Cloud Storage Volume Mount**:
- **Bucket**: `gs://<PROJECT_ID>-agenteval-data`
- **Container Mount**: `/app/data`
- **Result**: Even when Cloud Run scales to zero or new versions are rolled out, your test suites, historical assurance runs, and SQLite records remain intact.

---

## 4. Evaluating Private VPC Agents (VPC Connector)

If the agents you need to evaluate run on private internal IPs inside your Google Cloud VPC (GCE VMs, GKE pods, or internal load balancers):

1. **Deploy the VPC Access Connector and Firewall**:
   ```bash
   ./deploy/gcp/vpc-network.sh
   ```
   This creates a Serverless VPC Access connector (`agenteval-vpc-connector`) with a dedicated `/28` subnet and opens firewall rules for evaluation ports (`80`, `443`, `8000`, `8080`, `8766`, `8770`).

2. **Deploy AgentEval with VPC Routing**:
   ```bash
   export VPC_CONNECTOR_NAME="agenteval-vpc-connector"
   ./deploy/gcp/deploy.sh
   ```
   With `--vpc-egress=private-ranges-only`, AgentEval routes internal agent requests (`10.x.x.x`, `172.16-31.x.x`, `192.168.x.x`) through the VPC while external LLM calls go direct.

---

## 5. Health Check & Diagnostics

Once deployed:
```bash
# Check service health and persistence configuration
curl -s https://<YOUR-CLOUD-RUN-URL>/health

# Sample response:
# {
#   "status": "ok",
#   "version": "0.1.0",
#   "persistence": {
#     "sqlite_enabled": true,
#     "database_path": "/app/data/agenteval.db",
#     "suite_root": "/app/data/suites"
#   }
# }
```
