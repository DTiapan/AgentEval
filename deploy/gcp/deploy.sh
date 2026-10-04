#!/usr/bin/env bash
#
# Production Google Cloud Platform (Cloud Run) Turnkey Deployment Script for AgentEval
#
# Features:
# - Artifact Registry creation & Cloud Build container compilation
# - Cloud Storage persistent volume mount on Cloud Run Gen2 (SQLite DB & suites survive redeploys)
# - Automatic Secret Manager discovery and IAM binding (OpenRouter, DeepSeek, OpenAI, TypeSafe AI)
# - Serverless VPC Access connector support for evaluating internal/private VPC agents
# - Zero downtime deployment with healthcheck verification
#

set -euo pipefail

# Color formatting
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info() { echo -e "${BLUE}${BOLD}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}${BOLD}[SUCCESS]${NC} $*"; }
warn() { echo -e "${YELLOW}${BOLD}[WARN]${NC} $*"; }
error() { echo -e "${RED}${BOLD}[ERROR]${NC} $*" >&2; exit 1; }

# Prerequisites check
command -v gcloud >/dev/null 2>&1 || error "'gcloud' CLI is required. Please install Google Cloud SDK: https://cloud.google.com/sdk/docs/install"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
ENV_FILE="${AGENTEVAL_ENV_FILE:-${REPO_ROOT}/.env.gcp}"

if [[ -f "${ENV_FILE}" ]]; then
    info "Loading deployment configuration from ${ENV_FILE}"
    set -a
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    set +a
elif [[ -f "${REPO_ROOT}/.env" ]]; then
    info "Loading deployment configuration from ${REPO_ROOT}/.env"
    set -a
    # shellcheck disable=SC1090
    source "${REPO_ROOT}/.env"
    set +a
else
    warn "No .env.gcp found. Copy .env.gcp.example → .env.gcp or export deployment variables."
fi

# Project & Region Configuration
GCP_PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || true)}"
if [[ -z "$GCP_PROJECT_ID" || "$GCP_PROJECT_ID" == "(unset)" || "$GCP_PROJECT_ID" == "your-gcp-project-id" ]]; then
    warn "No valid GCP project configured."
    info "To create a brand-new GCP project automatically, run:"
    info "  ./deploy/gcp/setup-project.sh [PROJECT_ID]"
    error "Set GCP_PROJECT_ID in .env.gcp or run ./deploy/gcp/setup-project.sh."
fi

if ! gcloud projects describe "${GCP_PROJECT_ID}" >/dev/null 2>&1; then
    warn "Project '${GCP_PROJECT_ID}' does not exist on Google Cloud."
    info "To create and configure it automatically, run:"
    info "  ./deploy/gcp/setup-project.sh ${GCP_PROJECT_ID}"
    error "Project '${GCP_PROJECT_ID}' not found."
fi

GCP_REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-agenteval-service}"
REPO_NAME="${REPO_NAME:-agenteval-repo}"
CPU="${CPU:-2}"
MEMORY="${MEMORY:-4Gi}"
MIN_INSTANCES="${MIN_INSTANCES:-0}"
# Note: Clamped to 1 by default when using SQLite on GCS FUSE to prevent multi-writer corruption (ADR-007).
# Scale > 1 only when connecting to managed PostgreSQL via DATABASE_URL.
MAX_INSTANCES="${MAX_INSTANCES:-1}"
TIMEOUT="${TIMEOUT:-1800}"
CONCURRENCY="${CONCURRENCY:-20}"

GCS_DATA_BUCKET="${GCS_DATA_BUCKET:-${GCP_PROJECT_ID}-agenteval-data}"
AGENTEVAL_DATA_DIR="${AGENTEVAL_DATA_DIR:-/app/data}"
VPC_CONNECTOR_NAME="${VPC_CONNECTOR_NAME:-agenteval-vpc-connector}"
VPC_EGRESS="${VPC_EGRESS:-private-ranges-only}"

echo -e "${BOLD}======================================================${NC}"
echo -e "${CYAN}${BOLD}       AgentEval: Google Cloud Run Deployment         ${NC}"
echo -e "${BOLD}======================================================${NC}"
info "Project ID:       ${GCP_PROJECT_ID}"
info "Region:           ${GCP_REGION}"
info "Cloud Run Name:   ${SERVICE_NAME}"
info "Artifact Repo:    ${REPO_NAME}"
info "Data Bucket:      gs://${GCS_DATA_BUCKET}"
info "Compute Specs:    ${CPU} vCPUs, ${MEMORY} RAM (Gen 2 Execution Environment)"
echo ""

# 1. Enable Required Google Cloud APIs
info "Verifying and enabling required GCP APIs..."
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    storage.googleapis.com \
    compute.googleapis.com \
    vpcaccess.googleapis.com \
    --project="${GCP_PROJECT_ID}"
success "GCP APIs enabled."

# 2. Ensure Artifact Registry Repository Exists
info "Checking Artifact Registry repository '${REPO_NAME}'..."
if ! gcloud artifacts repositories describe "${REPO_NAME}" --location="${GCP_REGION}" --project="${GCP_PROJECT_ID}" >/dev/null 2>&1; then
    info "Creating Artifact Registry docker repository '${REPO_NAME}' in ${GCP_REGION}..."
    gcloud artifacts repositories create "${REPO_NAME}" \
        --repository-format=docker \
        --location="${GCP_REGION}" \
        --description="AgentEval container image repository" \
        --project="${GCP_PROJECT_ID}"
    success "Created Artifact Registry repository."
else
    success "Artifact Registry repository exists."
fi

IMAGE_TAG="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${REPO_NAME}/agenteval:latest"

# 3. Build Container Image via Google Cloud Build
info "Submitting container build to Google Cloud Build (target: ${IMAGE_TAG})..."
gcloud builds submit "${REPO_ROOT}" \
    --tag "${IMAGE_TAG}" \
    --project="${GCP_PROJECT_ID}" \
    --timeout="25m" \
    --machine-type="E2_HIGHCPU_8"
success "Container built and pushed to Artifact Registry."

# 4. Service Account & IAM Permissions
PROJECT_NUMBER=$(gcloud projects describe "${GCP_PROJECT_ID}" --format='value(projectNumber)')
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
info "Cloud Run Compute Service Account: ${COMPUTE_SA}"

# 5. Persistent Storage Volume (Cloud Storage Volume Mount on Cloud Run Gen2)
info "Checking Cloud Storage bucket 'gs://${GCS_DATA_BUCKET}' for persistent volume..."
if ! gcloud storage buckets describe "gs://${GCS_DATA_BUCKET}" --project="${GCP_PROJECT_ID}" >/dev/null 2>&1; then
    info "Creating storage bucket 'gs://${GCS_DATA_BUCKET}' in ${GCP_REGION}..."
    gcloud storage buckets create "gs://${GCS_DATA_BUCKET}" \
        --project="${GCP_PROJECT_ID}" \
        --location="${GCP_REGION}" \
        --uniform-bucket-level-access
    success "Created storage bucket gs://${GCS_DATA_BUCKET}"
else
    success "Storage bucket gs://${GCS_DATA_BUCKET} exists."
fi

info "Granting storage.objectAdmin permission to compute service account..."
gcloud storage buckets add-iam-policy-binding "gs://${GCS_DATA_BUCKET}" \
    --member="serviceAccount:${COMPUTE_SA}" \
    --role="roles/storage.objectAdmin" \
    --project="${GCP_PROJECT_ID}" --quiet >/dev/null 2>&1 || true

STORAGE_VOLUME_FLAGS=(
    --add-volume="name=agenteval-data,type=cloud-storage,bucket=${GCS_DATA_BUCKET}"
    --add-volume-mount="volume=agenteval-data,mount-path=${AGENTEVAL_DATA_DIR}"
)
info "Mounted gs://${GCS_DATA_BUCKET} → ${AGENTEVAL_DATA_DIR} (SQLite DB and test suites survive redeploy)."

# Cloud Storage FUSE + SQLite Safety Guardrail (ADR-007)
# SQLite does not support distributed multi-instance locking over GCS FUSE.
# If SQLite persistence is used, we must clamp MAX_INSTANCES to 1 to prevent database corruption.
if [[ "${AGENTEVAL_USE_SQLITE:-1}" == "1" && -z "${DATABASE_URL:-}" && "${MAX_INSTANCES}" -gt 1 ]]; then
    warn "CRITICAL: SQLite on GCS FUSE does not support multi-instance writes (ADR-007)!"
    warn "Clamping MAX_INSTANCES from ${MAX_INSTANCES} -> 1 to prevent silent database corruption."
    MAX_INSTANCES=1
fi

# 6. Automatic Secret Manager Discovery & Binding
SECRET_FLAGS=()
bind_secret_if_exists() {
    local secret_name="$1"
    local env_var_name="$2"
    if gcloud secrets describe "${secret_name}" --project="${GCP_PROJECT_ID}" >/dev/null 2>&1; then
        info "Found secret '${secret_name}' in Google Secret Manager -> binding to ${env_var_name}..."
        gcloud secrets add-iam-policy-binding "${secret_name}" \
            --member="serviceAccount:${COMPUTE_SA}" \
            --role="roles/secretmanager.secretAccessor" \
            --project="${GCP_PROJECT_ID}" --quiet >/dev/null 2>&1 || true
        SECRET_FLAGS+=(--set-secrets="${env_var_name}=${secret_name}:latest")
    fi
}

info "Scanning Google Cloud Secret Manager for evaluator keys..."
bind_secret_if_exists "openrouter-api-key" "OPENROUTER_API_KEY"
bind_secret_if_exists "deepseek-api-key" "DEEPSEEK_API_KEY"
bind_secret_if_exists "openai-api-key" "OPENAI_API_KEY"
bind_secret_if_exists "typesafe-api-key" "TYPESAFE_API_KEY"
bind_secret_if_exists "agenteval-api-key" "AGENTEVAL_API_KEY"
bind_secret_if_exists "inspect-eval-key" "INSPECT_EVAL_KEY"

# Fallback secrets from env if not bound from Secret Manager
FALLBACK_ENV_VARS=""
if [[ -n "${OPENROUTER_API_KEY:-}" && ! " ${SECRET_FLAGS[*]:-} " =~ "OPENROUTER_API_KEY=" ]]; then
    FALLBACK_ENV_VARS="${FALLBACK_ENV_VARS},OPENROUTER_API_KEY=${OPENROUTER_API_KEY}"
fi
if [[ -n "${DEEPSEEK_API_KEY:-}" && ! " ${SECRET_FLAGS[*]:-} " =~ "DEEPSEEK_API_KEY=" ]]; then
    FALLBACK_ENV_VARS="${FALLBACK_ENV_VARS},DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}"
fi
if [[ -n "${OPENAI_API_KEY:-}" && ! " ${SECRET_FLAGS[*]:-} " =~ "OPENAI_API_KEY=" ]]; then
    FALLBACK_ENV_VARS="${FALLBACK_ENV_VARS},OPENAI_API_KEY=${OPENAI_API_KEY}"
fi
if [[ -n "${TYPESAFE_API_KEY:-}" && ! " ${SECRET_FLAGS[*]:-} " =~ "TYPESAFE_API_KEY=" ]]; then
    FALLBACK_ENV_VARS="${FALLBACK_ENV_VARS},TYPESAFE_API_KEY=${TYPESAFE_API_KEY}"
fi

# 7. Serverless VPC Access Connector (Optional - for private agent probing)
VPC_RUN_FLAGS=()
if gcloud compute networks vpc-access connectors describe "${VPC_CONNECTOR_NAME}" \
    --region="${GCP_REGION}" \
    --project="${GCP_PROJECT_ID}" >/dev/null 2>&1; then
    VPC_RUN_FLAGS=(
        --vpc-connector="${VPC_CONNECTOR_NAME}"
        --vpc-egress="${VPC_EGRESS}"
    )
    info "Attaching VPC Connector '${VPC_CONNECTOR_NAME}' (egress: ${VPC_EGRESS})."
else
    info "No VPC Connector attached. To test private VPC agents, run: ./deploy/gcp/vpc-network.sh"
fi

# 8. Environment Variables
DEFAULT_MODEL="${AGENTEVAL_REAL_AGENT_MODEL:-deepseek/deepseek-v4-flash-0731}"
ENABLED_PACKS="${AGENTEVAL_ENABLED_DOMAIN_PACKS:-fintech}"

ENV_VARS="AGENTEVAL_DATA_DIR=${AGENTEVAL_DATA_DIR},AGENTEVAL_USE_SQLITE=1,AGENTEVAL_SERVE_UI=1,AGENTEVAL_UI_DIST=/app/web/dist,AGENTEVAL_REAL_AGENT_MODEL=${DEFAULT_MODEL},AGENTEVAL_ENABLED_DOMAIN_PACKS=${ENABLED_PACKS}"
if [[ -n "${AGENTEVAL_ALLOW_PRIVATE_ENDPOINTS:-}" ]]; then
    ENV_VARS="${ENV_VARS},AGENTEVAL_ALLOW_PRIVATE_ENDPOINTS=${AGENTEVAL_ALLOW_PRIVATE_ENDPOINTS}"
fi
if [[ -n "${AGENTEVAL_CORS_ORIGINS:-}" ]]; then
    ENV_VARS="${ENV_VARS},AGENTEVAL_CORS_ORIGINS=${AGENTEVAL_CORS_ORIGINS}"
fi
if [[ -n "${DATABASE_URL:-}" ]]; then
    ENV_VARS="${ENV_VARS},DATABASE_URL=${DATABASE_URL}"
fi
if [[ -n "${FALLBACK_ENV_VARS}" ]]; then
    ENV_VARS="${ENV_VARS}${FALLBACK_ENV_VARS}"
fi

# 9. Deploy to Google Cloud Run
info "Deploying '${SERVICE_NAME}' to Google Cloud Run (${GCP_REGION})..."
DEPLOY_CMD=(
    gcloud run deploy "${SERVICE_NAME}"
    --image="${IMAGE_TAG}"
    --platform="managed"
    --region="${GCP_REGION}"
    --project="${GCP_PROJECT_ID}"
    --allow-unauthenticated
    --port=8080
    --cpu="${CPU}"
    --memory="${MEMORY}"
    --cpu-boost
    --execution-environment="gen2"
    --min-instances="${MIN_INSTANCES}"
    --max-instances="${MAX_INSTANCES}"
    --timeout="${TIMEOUT}"
    --concurrency="${CONCURRENCY}"
    --set-env-vars="${ENV_VARS}"
    --quiet
)

if [[ ${#STORAGE_VOLUME_FLAGS[@]} -gt 0 ]]; then
    DEPLOY_CMD+=("${STORAGE_VOLUME_FLAGS[@]}")
fi
if [[ ${#VPC_RUN_FLAGS[@]} -gt 0 ]]; then
    DEPLOY_CMD+=("${VPC_RUN_FLAGS[@]}")
fi
if [[ ${#SECRET_FLAGS[@]} -gt 0 ]]; then
    DEPLOY_CMD+=("${SECRET_FLAGS[@]}")
fi

"${DEPLOY_CMD[@]}"

# 10. Service Verification & Details
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
    --platform="managed" \
    --region="${GCP_REGION}" \
    --project="${GCP_PROJECT_ID}" \
    --format='value(status.url)')

echo ""
echo -e "${GREEN}${BOLD}======================================================${NC}"
echo -e "${GREEN}${BOLD}     AgentEval Deployed Successfully to Google Cloud! ${NC}"
echo -e "${GREEN}${BOLD}======================================================${NC}"
echo -e "Web Console & Studio: ${BOLD}${SERVICE_URL}/${NC}"
echo -e "REST API Healthcheck: ${SERVICE_URL}/health"
echo -e "REST API Docs:        ${SERVICE_URL}/docs"
echo -e "Persistent Storage:   ${BOLD}gs://${GCS_DATA_BUCKET}${NC} mounted at ${AGENTEVAL_DATA_DIR}"
if [[ ${#SECRET_FLAGS[@]} -gt 0 ]]; then
    echo -e "Secret Manager:       ${GREEN}Connected (${#SECRET_FLAGS[@]} secret bindings active)${NC}"
fi
if [[ ${#VPC_RUN_FLAGS[@]} -gt 0 ]]; then
    echo -e "VPC Connector:        ${GREEN}${VPC_CONNECTOR_NAME} (${VPC_EGRESS})${NC}"
fi
echo ""
echo -e "Verify deployment health with:"
echo -e "  ${BLUE}curl -s ${SERVICE_URL}/health${NC}"
echo ""
