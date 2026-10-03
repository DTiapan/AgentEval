#!/usr/bin/env bash
#
# Create and Bootstrap a New Google Cloud Project for AgentEval
#
# What this script does:
# 1. Creates a brand-new, globally unique GCP project (e.g., agenteval-YYMMDDHHMM or custom name)
# 2. Auto-detects your active Google Cloud Billing Account and links it
# 3. Sets the new project as active in gcloud CLI configuration
# 4. Enables all required APIs (Cloud Run, Artifact Registry, Cloud Build, Secret Manager, Cloud Storage, VPC Access)
# 5. Generates or updates .env.gcp with the new project ID
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

command -v gcloud >/dev/null 2>&1 || error "'gcloud' CLI is required. Please install Google Cloud SDK: https://cloud.google.com/sdk/docs/install"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null || true)
[[ -z "${ACTIVE_ACCOUNT}" ]] && error "No active gcloud authentication found. Run: gcloud auth login"

# 1. Determine Project ID
SUGGESTED_ID="agenteval-$(date +%y%m%d%H%M)"
NEW_PROJECT_ID="${1:-${GCP_PROJECT_ID:-${SUGGESTED_ID}}}"

echo -e "${BOLD}======================================================${NC}"
echo -e "${CYAN}${BOLD}       AgentEval: Create New Google Cloud Project     ${NC}"
echo -e "${BOLD}======================================================${NC}"
info "Active Account:   ${ACTIVE_ACCOUNT}"
info "Target Project ID: ${NEW_PROJECT_ID}"
echo ""

# 2. Check if project already exists
if gcloud projects describe "${NEW_PROJECT_ID}" >/dev/null 2>&1; then
    warn "Project '${NEW_PROJECT_ID}' already exists."
else
    info "Creating new Google Cloud project '${NEW_PROJECT_ID}'..."
    gcloud projects create "${NEW_PROJECT_ID}" \
        --name="AgentEval Platform" \
        --set-as-default
    success "Project '${NEW_PROJECT_ID}' created successfully."
fi

# 3. Link Billing Account
info "Detecting active Google Cloud Billing Accounts..."
BILLING_ACCOUNT_ID=$(gcloud billing accounts list --filter="open=true" --format="value(ACCOUNT_ID)" 2>/dev/null | head -n 1 || true)

if [[ -n "${BILLING_ACCOUNT_ID}" ]]; then
    info "Found active billing account: ${BILLING_ACCOUNT_ID}"
    info "Linking billing account to project '${NEW_PROJECT_ID}'..."
    gcloud billing projects link "${NEW_PROJECT_ID}" \
        --billing-account="${BILLING_ACCOUNT_ID}" \
        --quiet
    success "Billing account linked."
else
    warn "No open billing account detected via gcloud CLI."
    warn "Please link billing in GCP Console: https://console.cloud.google.com/billing/linkedaccount?project=${NEW_PROJECT_ID}"
fi

# 4. Set gcloud configuration
gcloud config set project "${NEW_PROJECT_ID}" --quiet
success "Active gcloud project set to '${NEW_PROJECT_ID}'."

# 5. Enable Core Google Cloud APIs
info "Enabling required GCP APIs for Cloud Run & Build..."
gcloud services enable \
    run.googleapis.com \
    artifactregistry.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com \
    storage.googleapis.com \
    compute.googleapis.com \
    vpcaccess.googleapis.com \
    --project="${NEW_PROJECT_ID}"
success "All required GCP APIs enabled."

# 6. Update or Create .env.gcp
ENV_FILE="${REPO_ROOT}/.env.gcp"
EXAMPLE_ENV="${REPO_ROOT}/.env.gcp.example"

if [[ ! -f "${ENV_FILE}" ]] && [[ -f "${EXAMPLE_ENV}" ]]; then
    cp "${EXAMPLE_ENV}" "${ENV_FILE}"
fi

if [[ -f "${ENV_FILE}" ]]; then
    # Update GCP_PROJECT_ID in .env.gcp
    if grep -q "^GCP_PROJECT_ID=" "${ENV_FILE}"; then
        sed -i '' "s/^GCP_PROJECT_ID=.*/GCP_PROJECT_ID=${NEW_PROJECT_ID}/" "${ENV_FILE}" 2>/dev/null || \
        sed -i "s/^GCP_PROJECT_ID=.*/GCP_PROJECT_ID=${NEW_PROJECT_ID}/" "${ENV_FILE}"
    else
        echo "GCP_PROJECT_ID=${NEW_PROJECT_ID}" >> "${ENV_FILE}"
    fi
    success "Updated ${ENV_FILE} with GCP_PROJECT_ID=${NEW_PROJECT_ID}"
fi

echo ""
echo -e "${GREEN}${BOLD}======================================================${NC}"
echo -e "${GREEN}${BOLD}      New GCP Project Initialized and Ready!          ${NC}"
echo -e "${GREEN}${BOLD}======================================================${NC}"
echo -e "Project ID:        ${BOLD}${NEW_PROJECT_ID}${NC}"
echo -e "GCP Console URL:   https://console.cloud.google.com/welcome?project=${NEW_PROJECT_ID}"
echo -e "Configuration:     ${ENV_FILE}"
echo ""
echo -e "Next step: Store your secrets and deploy:"
echo -e "  ${BLUE}gcloud secrets create openrouter-api-key --data-file=- <<< \"sk-or-v1-...\"${NC}"
echo -e "  ${BLUE}./deploy/gcp/deploy.sh${NC}"
echo ""
