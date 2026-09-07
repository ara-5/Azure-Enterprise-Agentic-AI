#!/usr/bin/env bash
# One-time Entra ID setup: registers the API app (exposes a scope + app
# roles) and the SPA app (the React frontend, public client using PKCE),
# and grants the SPA app permission to call the API.
#
# App registrations aren't Bicep-manageable resources (they're Microsoft
# Graph objects, not ARM), so this is a Graph-via-az-cli script, run once
# per environment before infra/deploy.sh.
#
# Usage: ./infra/register_entra_apps.sh "Enterprise Agentic AI"
set -euo pipefail

APP_BASENAME="${1:-Enterprise Agentic AI}"
TENANT_ID=$(az account show --query tenantId -o tsv)

echo "Tenant: $TENANT_ID"

echo "Creating API app registration..."
API_APP_ID=$(az ad app create --display-name "${APP_BASENAME} - API" --sign-in-audience AzureADMyOrg --query appId -o tsv)
API_OBJECT_ID=$(az ad app show --id "$API_APP_ID" --query id -o tsv)

az ad app update --id "$API_APP_ID" --identifier-uris "api://${API_APP_ID}"

echo "Defining 'access_as_user' delegated scope..."
SCOPE_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
az rest --method PATCH \
  --uri "https://graph.microsoft.com/v1.0/applications/${API_OBJECT_ID}" \
  --headers "Content-Type=application/json" \
  --body "{\"api\":{\"oauth2PermissionScopes\":[{\"id\":\"${SCOPE_ID}\",\"adminConsentDescription\":\"Allow the app to call the Agentic AI API on behalf of the signed-in user.\",\"adminConsentDisplayName\":\"Access Agentic AI API\",\"userConsentDescription\":\"Allow the app to call the Agentic AI API on your behalf.\",\"userConsentDisplayName\":\"Access Agentic AI API\",\"value\":\"access_as_user\",\"type\":\"User\",\"isEnabled\":true}]}}"

echo "Defining 'ingest' and 'admin' app roles..."
INGEST_ROLE_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
ADMIN_ROLE_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
az rest --method PATCH \
  --uri "https://graph.microsoft.com/v1.0/applications/${API_OBJECT_ID}" \
  --headers "Content-Type=application/json" \
  --body "{\"appRoles\":[{\"id\":\"${INGEST_ROLE_ID}\",\"allowedMemberTypes\":[\"User\",\"Application\"],\"description\":\"Can ingest documents into the knowledge base.\",\"displayName\":\"Ingest\",\"value\":\"ingest\",\"isEnabled\":true},{\"id\":\"${ADMIN_ROLE_ID}\",\"allowedMemberTypes\":[\"User\",\"Application\"],\"description\":\"Full administrative access, including evaluation reports.\",\"displayName\":\"Admin\",\"value\":\"admin\",\"isEnabled\":true}]}"

echo "Creating a service principal for the API app (required for role assignment/consent)..."
az ad sp create --id "$API_APP_ID" >/dev/null 2>&1 || true

echo "Creating SPA app registration (frontend)..."
SPA_APP_ID=$(az ad app create --display-name "${APP_BASENAME} - Web" --sign-in-audience AzureADMyOrg --query appId -o tsv)
az ad app update --id "$SPA_APP_ID" --set spa='{"redirectUris":["http://localhost:5173","https://REPLACE-WITH-YOUR-FRONTEND-FQDN"]}'
az ad sp create --id "$SPA_APP_ID" >/dev/null 2>&1 || true

echo "Granting the SPA app the API's access_as_user scope..."
az ad app permission add --id "$SPA_APP_ID" \
  --api "$API_APP_ID" \
  --api-permissions "${SCOPE_ID}=Scope"

cat <<EOF

Done. Save these values:

  ENTRA_TENANT_ID       = $TENANT_ID
  ENTRA_API_CLIENT_ID   = $API_APP_ID
  ENTRA_API_AUDIENCE    = api://$API_APP_ID
  VITE_ENTRA_CLIENT_ID  = $SPA_APP_ID
  VITE_ENTRA_TENANT_ID  = $TENANT_ID
  VITE_API_SCOPE        = api://$API_APP_ID/access_as_user

Remaining manual steps (Entra admin center, since these need interactive
admin consent / directory role assignment):
  1. Grant admin consent for the SPA app's API permission.
  2. Assign users/groups to the API app's "ingest" / "admin" app roles
     (Enterprise Applications > ${APP_BASENAME} - API > Users and groups).
  3. Once the frontend Container App is deployed, add its real FQDN as a
     SPA redirect URI (az ad app update --id $SPA_APP_ID --set spa.redirectUris=...).

Feed the ENTRA_* values into infra/deploy.sh / infra/main.parameters.json,
and the VITE_* values into frontend/.env / your CI build args.
EOF
