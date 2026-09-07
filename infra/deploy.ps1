# Provisions every Azure resource for the platform via infra/main.bicep.
# Prerequisite: infra/register_entra_apps.ps1 has been run once (or its
# outputs supplied manually) so entraApiClientId/entraApiAudience are known.
#
# Usage:
#   ./infra/deploy.ps1 -ResourceGroup rg-eaap-dev -Location eastus -BaseName eaap-dev `
#       -EntraTenantId <tenant-id> -EntraApiClientId <client-id>

param(
    [string]$ResourceGroup = "rg-eaap-dev",
    [string]$Location = "eastus",
    [string]$BaseName = "eaap-dev",
    [Parameter(Mandatory = $true)][string]$EntraTenantId,
    [Parameter(Mandatory = $true)][string]$EntraApiClientId,
    [string]$CostBudgetMonthlyUsd = "200"
)

$ErrorActionPreference = "Stop"

Write-Host "Creating resource group '$ResourceGroup' in '$Location'..."
az group create --name $ResourceGroup --location $Location | Out-Null

Write-Host "Deploying infra/main.bicep..."
$deployment = az deployment group create `
    --resource-group $ResourceGroup `
    --template-file infra/main.bicep `
    --parameters baseName=$BaseName `
                 location=$Location `
                 entraTenantId=$EntraTenantId `
                 entraApiClientId=$EntraApiClientId `
                 entraApiAudience="api://$EntraApiClientId" `
                 costBudgetMonthlyUsd=$CostBudgetMonthlyUsd `
    --query properties.outputs -o json | ConvertFrom-Json

Write-Host "`nDeployment complete. Key outputs:"
Write-Host "  ACR:              $($deployment.acrLoginServer.value)"
Write-Host "  Backend URL:      $($deployment.backendUrl.value)"
Write-Host "  Frontend URL:     $($deployment.frontendUrl.value)"
Write-Host "  Azure OpenAI:     $($deployment.azureOpenAiName.value)"
Write-Host "  Azure AI Search:  $($deployment.azureSearchName.value)"
Write-Host "  Key Vault:        $($deployment.keyVaultName.value)"
Write-Host "`nNext steps:"
Write-Host "  1. Build & push images, then update the Container Apps (see .github/workflows/cd.yml for the automated path)."
Write-Host "  2. Run scripts/seed_sample_data.py to load demo content into AI Search."
Write-Host "  3. Save these outputs as GitHub Actions repo variables/secrets for CI/CD (see docs/cicd-setup.md)."
