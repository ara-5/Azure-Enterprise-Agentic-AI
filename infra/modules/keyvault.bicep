@description('Key Vault using RBAC authorization (no access policies) -- the Managed Identity is granted "Key Vault Secrets User" below, nothing else gets a standing grant.')
param name string
param location string
param principalIdToGrantAccess string
param tenantId string

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: name
  location: location
  properties: {
    tenantId: tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    enablePurgeProtection: true
  }
}

var keyVaultSecretsUserRoleId = '4633458b-17de-408a-b874-0445c86b69e6'

resource secretsUserAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, principalIdToGrantAccess, keyVaultSecretsUserRoleId)
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', keyVaultSecretsUserRoleId)
    principalId: principalIdToGrantAccess
    principalType: 'ServicePrincipal'
  }
}

output name string = keyVault.name
output uri string = keyVault.properties.vaultUri
