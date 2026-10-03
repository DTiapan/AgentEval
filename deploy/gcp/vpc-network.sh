#!/usr/bin/env bash
#
# Serverless VPC Access Connector & Internal Firewall Setup for AgentEval
#
# Purpose:
# Allows AgentEval on Cloud Run to privately reach and evaluate AI agents
# running inside Google Cloud VPC (GCE instances, GKE services, internal Cloud Run)
# without exposing those agent endpoints to the public internet.
#

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

info() { echo -e "${BLUE}${BOLD}[INFO]${NC} $*"; }
success() { echo -e "${GREEN}${BOLD}[SUCCESS]${NC} $*"; }
warn() { echo -e "${YELLOW}${BOLD}[WARN]${NC} $*"; }
error() { echo -e "${RED}${BOLD}[ERROR]${NC} $*" >&2; exit 1; }

command -v gcloud >/dev/null 2>&1 || error "'gcloud' CLI is required."

GCP_PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || true)}"
[[ -z "$GCP_PROJECT_ID" || "$GCP_PROJECT_ID" == "(unset)" ]] && error "No GCP project active. Run 'gcloud config set project <PROJECT_ID>'."

GCP_REGION="${GCP_REGION:-us-central1}"
VPC_NETWORK="${VPC_NETWORK:-default}"
CONNECTOR_NAME="${VPC_CONNECTOR_NAME:-agenteval-vpc-connector}"
CONNECTOR_RANGE="${VPC_CONNECTOR_RANGE:-10.8.0.0/28}"
FIREWALL_RULE="${VPC_FIREWALL_RULE:-agenteval-allow-vpc-connector-egress}"

info "Project ID:      ${GCP_PROJECT_ID}"
info "Region:          ${GCP_REGION}"
info "VPC Network:     ${VPC_NETWORK}"
info "Connector Name:  ${CONNECTOR_NAME}"
info "Connector CIDR:  ${CONNECTOR_RANGE} (must not overlap with existing subnets)"

info "Enabling Compute & Serverless VPC Access APIs..."
gcloud services enable \
    compute.googleapis.com \
    vpcaccess.googleapis.com \
    --project="${GCP_PROJECT_ID}" \
    --quiet

info "Checking Serverless VPC Access Connector '${CONNECTOR_NAME}'..."
if ! gcloud compute networks vpc-access connectors describe "${CONNECTOR_NAME}" \
    --region="${GCP_REGION}" \
    --project="${GCP_PROJECT_ID}" >/dev/null 2>&1; then
    info "Creating VPC connector '${CONNECTOR_NAME}' in ${GCP_REGION} (this may take 3-5 minutes)..."
    gcloud compute networks vpc-access connectors create "${CONNECTOR_NAME}" \
        --project="${GCP_PROJECT_ID}" \
        --region="${GCP_REGION}" \
        --network="${VPC_NETWORK}" \
        --range="${CONNECTOR_RANGE}" \
        --min-instances=2 \
        --max-instances=3 \
        --machine-type=e2-micro
    success "VPC Access Connector created."
else
    success "VPC Access Connector '${CONNECTOR_NAME}' already exists."
fi

info "Checking firewall rule '${FIREWALL_RULE}'..."
if ! gcloud compute firewall-rules describe "${FIREWALL_RULE}" --project="${GCP_PROJECT_ID}" >/dev/null 2>&1; then
    info "Creating firewall rule '${FIREWALL_RULE}' allowing traffic from connector subnet..."
    gcloud compute firewall-rules create "${FIREWALL_RULE}" \
        --project="${GCP_PROJECT_ID}" \
        --network="${VPC_NETWORK}" \
        --direction=INGRESS \
        --action=ALLOW \
        --rules=tcp:80,tcp:443,tcp:8000,tcp:8080,tcp:8766,tcp:8770 \
        --source-ranges="${CONNECTOR_RANGE}" \
        --description="Allow AgentEval Cloud Run VPC connector to probe internal agent endpoints"
    success "Firewall rule created."
else
    success "Firewall rule '${FIREWALL_RULE}' already exists."
fi

echo ""
echo -e "${GREEN}${BOLD}======================================================${NC}"
echo -e "${GREEN}${BOLD}       VPC Networking Configured Successfully!        ${NC}"
echo -e "${GREEN}${BOLD}======================================================${NC}"
echo -e "Connector:  ${BOLD}${CONNECTOR_NAME}${NC} (${CONNECTOR_RANGE})"
echo -e "Network:    ${BOLD}${VPC_NETWORK}${NC}"
echo ""
echo -e "To deploy AgentEval with this VPC connector attached:"
echo -e "  ${BLUE}export VPC_CONNECTOR_NAME='${CONNECTOR_NAME}'${NC}"
echo -e "  ${BLUE}./deploy/gcp/deploy.sh${NC}"
echo ""
