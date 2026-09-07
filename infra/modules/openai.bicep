@description('Azure OpenAI resource with chat + embedding model deployments. disableLocalAuth is on -- the only way in is Entra ID / Managed Identity token auth.')
param name string
param location string
param principalIdToGrantAccess string
param chatDeploymentName string = 'gpt-4o'
param chatModelName string = 'gpt-4o'
param chatModelVersion string = '2024-08-06'
param chatCapacity int = 10
param embeddingDeploymentName string = 'text-embedding-3-large'
param embeddingModelVersion string = '1'
param embeddingCapacity int = 30

resource openAi 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: name
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: name
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: true
  }
}

resource chatDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openAi
  name: chatDeploymentName
  sku: {
    name: 'Standard'
    capacity: chatCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: chatModelName
      version: chatModelVersion
    }
  }
}

resource embeddingDeployment 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: openAi
  name: embeddingDeploymentName
  sku: {
    name: 'Standard'
    capacity: embeddingCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-large'
      version: embeddingModelVersion
    }
  }
  dependsOn: [
    chatDeployment
  ]
}

var cognitiveServicesOpenAiUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

resource openAiUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(openAi.id, principalIdToGrantAccess, cognitiveServicesOpenAiUserRoleId)
  scope: openAi
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', cognitiveServicesOpenAiUserRoleId)
    principalId: principalIdToGrantAccess
    principalType: 'ServicePrincipal'
  }
}

output name string = openAi.name
output endpoint string = openAi.properties.endpoint
