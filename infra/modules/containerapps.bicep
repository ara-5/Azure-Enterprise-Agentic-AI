@description('Container Apps Environment plus the backend (FastAPI) and frontend (React/nginx) apps. Both apps run as the shared user-assigned Managed Identity -- zero secrets baked into images or set as plain env vars for anything Azure-AD-auth-capable.')
param namePrefix string
param location string
param logAnalyticsWorkspaceName string
param userAssignedIdentityId string
param userAssignedIdentityClientId string
param acrLoginServer string
param backendImage string
param frontendImage string
param appInsightsConnectionString string
param keyVaultUri string

param azureOpenAiEndpoint string
param azureOpenAiChatDeployment string
param azureOpenAiEmbeddingDeployment string
param azureSearchEndpoint string
param azureSearchIndexName string
param azureStorageAccountUrl string
param azureStorageContainerDocuments string
param azureStorageContainerCost string
param entraTenantId string
param entraApiClientId string
param entraApiAudience string
param entraAllowedGroups string
param costBudgetMonthlyUsd string
param costAlertWebhookSecretUri string = ''

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' existing = {
  name: logAnalyticsWorkspaceName
}

resource containerAppsEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${namePrefix}-env'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

resource backendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-api'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${userAssignedIdentityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
      }
      registries: [
        {
          server: acrLoginServer
          identity: userAssignedIdentityId
        }
      ]
      secrets: !empty(costAlertWebhookSecretUri) ? [
        {
          name: 'cost-alert-webhook-url'
          keyVaultUrl: costAlertWebhookSecretUri
          identity: userAssignedIdentityId
        }
      ] : []
    }
    template: {
      revisionSuffix: 'v1'
      scale: {
        minReplicas: 1
        maxReplicas: 3
        rules: [
          {
            name: 'http-scale'
            http: {
              metadata: {
                concurrentRequests: '30'
              }
            }
          }
        ]
      }
      containers: [
        {
          name: 'api'
          image: backendImage
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: concat([
            { name: 'APP_ENV', value: 'production' }
            { name: 'LOG_LEVEL', value: 'INFO' }
            { name: 'DISABLE_AUTH', value: 'false' }
            { name: 'DEMO_MODE', value: 'false' }
            { name: 'MANAGED_IDENTITY_CLIENT_ID', value: userAssignedIdentityClientId }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: appInsightsConnectionString }
            { name: 'AZURE_KEY_VAULT_URL', value: keyVaultUri }
            { name: 'AZURE_OPENAI_ENDPOINT', value: azureOpenAiEndpoint }
            { name: 'AZURE_OPENAI_CHAT_DEPLOYMENT', value: azureOpenAiChatDeployment }
            { name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT', value: azureOpenAiEmbeddingDeployment }
            { name: 'AZURE_SEARCH_ENDPOINT', value: azureSearchEndpoint }
            { name: 'AZURE_SEARCH_INDEX_NAME', value: azureSearchIndexName }
            { name: 'AZURE_STORAGE_ACCOUNT_URL', value: azureStorageAccountUrl }
            { name: 'AZURE_STORAGE_CONTAINER_DOCUMENTS', value: azureStorageContainerDocuments }
            { name: 'AZURE_STORAGE_CONTAINER_COST', value: azureStorageContainerCost }
            { name: 'ENTRA_TENANT_ID', value: entraTenantId }
            { name: 'ENTRA_API_CLIENT_ID', value: entraApiClientId }
            { name: 'ENTRA_API_AUDIENCE', value: entraApiAudience }
            { name: 'ENTRA_ALLOWED_GROUPS', value: entraAllowedGroups }
            { name: 'COST_BUDGET_MONTHLY_USD', value: costBudgetMonthlyUsd }
          ], !empty(costAlertWebhookSecretUri) ? [
            { name: 'COST_ALERT_WEBHOOK_URL', secretRef: 'cost-alert-webhook-url' }
          ] : [])
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8000
              }
              initialDelaySeconds: 10
              periodSeconds: 30
            }
          ]
        }
      ]
    }
  }
}

resource frontendApp 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-web'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${userAssignedIdentityId}': {}
    }
  }
  properties: {
    managedEnvironmentId: containerAppsEnv.id
    configuration: {
      ingress: {
        external: true
        targetPort: 80
        transport: 'auto'
      }
      registries: [
        {
          server: acrLoginServer
          identity: userAssignedIdentityId
        }
      ]
    }
    template: {
      revisionSuffix: 'v1'
      scale: {
        minReplicas: 1
        maxReplicas: 2
      }
      containers: [
        {
          name: 'web'
          image: frontendImage
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
        }
      ]
    }
  }
}

output backendFqdn string = backendApp.properties.configuration.ingress.fqdn
output frontendFqdn string = frontendApp.properties.configuration.ingress.fqdn
