param location string = 'australiaeast'
param namePrefix string = 'pdfocr${uniqueString(resourceGroup().id)}'

@description('Storage account name')
var storageName = toLower('${namePrefix}st')

@description('Static Web App name')
var swaName = '${namePrefix}-swa'

@description('Document Intelligence name')
var docIntelName = '${namePrefix}-docint'

// ---------------------------
// Storage Account
// ---------------------------
resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
  }
}

// Blob containers
resource uploads 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: '${storage.name}/default/uploads'
}

resource outputs 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: '${storage.name}/default/outputs'
}

// Table storage (for job tracking)
resource tableService 'Microsoft.Storage/storageAccounts/tableServices@2023-01-01' = {
  name: '${storage.name}/default'
}

resource jobsTable 'Microsoft.Storage/storageAccounts/tableServices/tables@2023-01-01' = {
  name: '${storage.name}/default/OcrJobs'
}

// ---------------------------
// Document Intelligence
// ---------------------------
resource docIntel 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: docIntelName
  location: location
  kind: 'FormRecognizer'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: docIntelName
  }
}

// ---------------------------
// Static Web App
// ---------------------------
resource staticWebApp 'Microsoft.Web/staticSites@2025-03-01' = {
  name: swaName
  location: 'eastasia'
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
  properties: {
    buildProperties: {
      appLocation: 'app'
      apiLocation: 'api'
      outputLocation: 'dist'
      skipGithubActionWorkflowGeneration: true
    }
  }
}

// ---------------------------
// Outputs
// ---------------------------
output storageAccountName string = storage.name
output docIntelEndpoint string = docIntel.properties.endpoint
output staticWebAppName string = staticWebApp.name
