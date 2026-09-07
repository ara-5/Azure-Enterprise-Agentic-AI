# CI/CD setup

`ci.yml` needs nothing beyond checkout — it lints, unit-tests and builds images locally without touching Azure.

`cd.yml` and `evaluation.yml` need OIDC access to your Azure subscription plus a handful of repo variables. One-time setup:

## 1. Create a Microsoft Entra app + federated credential for GitHub Actions

```bash
az ad app create --display-name "eaap-github-actions" --query appId -o tsv
# save the output as APP_ID

az ad sp create --id $APP_ID

az ad app federated-credential create --id $APP_ID --parameters '{
  "name": "github-main-branch",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:ara-5/Azure-Enterprise-Agentic-AI:ref:refs/heads/main",
  "audiences": ["api://AzureADTokenExchange"]
}'
```

## 2. Grant it deploy + data-plane roles

```bash
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
RG=rg-eaap-dev

# Deploy-time roles (push images, update Container Apps)
az role assignment create --assignee $APP_ID --role "Contributor" --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RG"
az role assignment create --assignee $APP_ID --role "AcrPush" --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RG/providers/Microsoft.ContainerRegistry/registries/<acrName>"

# Data-plane roles, only needed for evaluation.yml
az role assignment create --assignee $APP_ID --role "Cognitive Services OpenAI User" --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RG/providers/Microsoft.CognitiveServices/accounts/<openAiName>"
az role assignment create --assignee $APP_ID --role "Search Index Data Reader" --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RG/providers/Microsoft.Search/searchServices/<searchName>"
```

## 3. Repo secrets (Settings → Secrets and variables → Actions → Secrets)

| Secret | Value |
|---|---|
| `AZURE_CLIENT_ID` | the `$APP_ID` above |
| `AZURE_TENANT_ID` | `az account show --query tenantId -o tsv` |
| `AZURE_SUBSCRIPTION_ID` | `az account show --query id -o tsv` |

## 4. Repo variables (same page, "Variables" tab)

| Variable | Value |
|---|---|
| `AZURE_RESOURCE_GROUP` | e.g. `rg-eaap-dev` |
| `AZURE_ACR_NAME` | from `infra/deploy.sh` output |
| `BACKEND_CONTAINER_APP_NAME` | `<baseName>-api` |
| `FRONTEND_CONTAINER_APP_NAME` | `<baseName>-web` |
| `VITE_ENTRA_CLIENT_ID`, `VITE_ENTRA_TENANT_ID`, `VITE_API_SCOPE`, `VITE_API_BASE_URL` | from `infra/register_entra_apps.sh` + `deploy` outputs |
| `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_CHAT_DEPLOYMENT`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`, `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_INDEX_NAME` | from `deploy` outputs, only needed for `evaluation.yml` |

Also create a GitHub **environment** named `production` (Settings → Environments) if you want manual-approval gating on deploys/evaluation — both workflows already target `environment: production`.
