#!/usr/bin/env bash
# Provisions every Azure resource for the platform via infra/main.bicep.
# Prerequisite: infra/register_entra_apps.sh has been run once (or its
# outputs supplied manually) so ENTRA_API_CLIENT_ID is known.
#
# Usage:
#   ./infra/deploy.sh -g rg-eaap-dev -l eastus -n eaap-dev -t <tenant-id> -c <api-client-id>
set -euo pipefail

RESOURCE_GROUP="rg-eaap-dev"
LOCATION="eastus"
BASE_NAME="eaap-dev"
COST_BUDGET="200"

while getopts "g:l:n:t:c:b:" opt; do
  case $opt in
    g) RESOURCE_GROUP="$OPTARG" ;;
    l) LOCATION="$OPTARG" ;;
    n) BASE_NAME="$OPTARG" ;;
    t) ENTRA_TENANT_ID="$OPTARG" ;;
    c) ENTRA_API_CLIENT_ID="$OPTARG" ;;
    b) COST_BUDGET="$OPTARG" ;;
    *) echo "Unknown option"; exit 1 ;;
  esac
done

: "${ENTRA_TENANT_ID:?Pass -t <entra tenant id>}"
: "${ENTRA_API_CLIENT_ID:?Pass -c <entra api app registration client id>}"

echo "Creating resource group '$RESOURCE_GROUP' in '$LOCATION'..."
az group create --name "$RESOURCE_GROUP" --location "$LOCATION" >/dev/null

echo "Deploying infra/main.bicep..."
az deployment group create \
  --resource-group "$RESOURCE_GROUP" \
  --template-file infra/main.bicep \
  --parameters baseName="$BASE_NAME" \
               location="$LOCATION" \
               entraTenantId="$ENTRA_TENANT_ID" \
               entraApiClientId="$ENTRA_API_CLIENT_ID" \
               entraApiAudience="api://$ENTRA_API_CLIENT_ID" \
               costBudgetMonthlyUsd="$COST_BUDGET" \
  --query properties.outputs -o json | tee infra/last-deploy-outputs.json

echo ""
echo "Deployment complete. Outputs saved to infra/last-deploy-outputs.json"
echo "Next: build/push images (or let .github/workflows/cd.yml do it), then run scripts/seed_sample_data.py."
