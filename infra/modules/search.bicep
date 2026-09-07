@description('Azure AI Search service backing the RAG knowledge base (hybrid vector + keyword + semantic ranking). The Managed Identity gets both control-plane and data-plane roles so it can create/manage the index and read/write documents.')
param name string
param location string
param principalIdToGrantAccess string
param sku string = 'basic'

resource search 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: name
  location: location
  sku: {
    name: sku
  }
  properties: {
    replicaCount: 1
    partitionCount: 1
    hostingMode: 'default'
    semanticSearch: 'standard'
    disableLocalAuth: true
  }
}

var searchIndexDataContributorRoleId = '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
var searchServiceContributorRoleId = '7ca78c08-252a-4471-8644-bb5ff32d4ba0'

resource indexDataContributorAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, principalIdToGrantAccess, searchIndexDataContributorRoleId)
  scope: search
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchIndexDataContributorRoleId)
    principalId: principalIdToGrantAccess
    principalType: 'ServicePrincipal'
  }
}

resource serviceContributorAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, principalIdToGrantAccess, searchServiceContributorRoleId)
  scope: search
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchServiceContributorRoleId)
    principalId: principalIdToGrantAccess
    principalType: 'ServicePrincipal'
  }
}

output name string = search.name
output endpoint string = 'https://${search.name}.search.windows.net'
