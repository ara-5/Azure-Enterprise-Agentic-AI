@description('Base name used to derive all resource names, e.g. "eaap-dev".')
@minLength(3)
@maxLength(12)
param baseName string

param location string = resourceGroup().location

@description('Entra ID tenant hosting both the API and SPA app registrations.')
param entraTenantId string
param entraApiClientId string
param entraApiAudience string
param entraAllowedGroups string = ''

@description('Placeholder images used on the very first deploy, before CI/CD has pushed real ones (see .github/workflows/cd.yml).')
param backendImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'
param frontendImage string = 'mcr.microsoft.com/azuredocs/containerapps-helloworld:latest'

param costBudgetMonthlyUsd string = '200'

var suffix = uniqueString(resourceGroup().id, baseName)
var storageAccountName = toLower('${take(replace(baseName, '-', ''), 11)}st${take(suffix, 8)}')
var acrName = toLower('${take(replace(baseName, '-', ''), 11)}acr${take(suffix, 8)}')
var keyVaultName = toLower('${take(baseName, 12)}-kv-${take(suffix, 6)}')
var searchName = toLower('${baseName}-search-${take(suffix, 6)}')
var openAiName = toLower('${baseName}-aoai-${take(suffix, 6)}')

module identity 'modules/identity.bicep' = {
  name: 'identity'
  params: {
    name: '${baseName}-identity'
    location: location
  }
}

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring'
  params: {
    name: baseName
    location: location
  }
}

module keyVault 'modules/keyvault.bicep' = {
  name: 'keyvault'
  params: {
    name: keyVaultName
    location: location
    tenantId: entraTenantId
    principalIdToGrantAccess: identity.outputs.principalId
  }
}

module storage 'modules/storage.bicep' = {
  name: 'storage'
  params: {
    name: storageAccountName
    location: location
    principalIdToGrantAccess: identity.outputs.principalId
    documentsContainerName: 'documents'
    costContainerName: 'cost-exports'
  }
}

module search 'modules/search.bicep' = {
  name: 'search'
  params: {
    name: searchName
    location: location
    principalIdToGrantAccess: identity.outputs.principalId
  }
}

module openAi 'modules/openai.bicep' = {
  name: 'openai'
  params: {
    name: openAiName
    location: location
    principalIdToGrantAccess: identity.outputs.principalId
  }
}

module acr 'modules/acr.bicep' = {
  name: 'acr'
  params: {
    name: acrName
    location: location
    principalIdToGrantAccess: identity.outputs.principalId
  }
}

module containerApps 'modules/containerapps.bicep' = {
  name: 'containerapps'
  params: {
    namePrefix: baseName
    location: location
    logAnalyticsWorkspaceName: '${baseName}-law'
    userAssignedIdentityId: identity.outputs.id
    userAssignedIdentityClientId: identity.outputs.clientId
    acrLoginServer: acr.outputs.loginServer
    backendImage: backendImage
    frontendImage: frontendImage
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
    keyVaultUri: keyVault.outputs.uri
    azureOpenAiEndpoint: openAi.outputs.endpoint
    azureOpenAiChatDeployment: 'gpt-4o'
    azureOpenAiEmbeddingDeployment: 'text-embedding-3-large'
    azureSearchEndpoint: search.outputs.endpoint
    azureSearchIndexName: 'enterprise-rag-index'
    azureStorageAccountUrl: storage.outputs.blobEndpoint
    azureStorageContainerDocuments: 'documents'
    azureStorageContainerCost: 'cost-exports'
    entraTenantId: entraTenantId
    entraApiClientId: entraApiClientId
    entraApiAudience: entraApiAudience
    entraAllowedGroups: entraAllowedGroups
    costBudgetMonthlyUsd: costBudgetMonthlyUsd
  }
}

output resourceGroupName string = resourceGroup().name
output acrLoginServer string = acr.outputs.loginServer
output acrName string = acr.outputs.name
output backendUrl string = 'https://${containerApps.outputs.backendFqdn}'
output frontendUrl string = 'https://${containerApps.outputs.frontendFqdn}'
output azureOpenAiName string = openAi.outputs.name
output azureSearchName string = search.outputs.name
output storageAccountName string = storage.outputs.name
output keyVaultName string = keyVault.outputs.name
output appInsightsName string = monitoring.outputs.appInsightsName
output managedIdentityClientId string = identity.outputs.clientId
