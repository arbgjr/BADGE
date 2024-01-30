# INICIO DE ONDE VOCÊ PRECISA MODIFICAR
$issuerName="Acme Industries"
$areaName="AsPoNe"
$caminhoDoTemplateDoBadge="C:\New folder"
$caminhoDaFonteNotoColorEmoji="C:\New folder\Fonts"
$caminhoDaFonteRubikBold="C:\New folder\Fonts"
$caminhoDaFonteRubikRegular="C:\New folder\Fonts"
$BadgeVerificationUrl="https://www.qualquerurl.com"
$LinkedInPost = @"
Estou muito feliz em compartilhar que acabei de conquistar um novo badge: {badge_name}!\r\nEsta conquista representa {additional_info}.\r\nVocê pode verificar a autenticidade do meu badge aqui: {validation_url}\r\n#Conquista #Badge #DesenvolvimentoProfissional
"@
# FIM DE ONDE VOCÊ PRECISA MODIFICAR 
# DAQUI PRA BAIXO É POR SUA CONTA E RISCO.

Clear-Host
$environmentTag = "Dev"
$productTag = "Badges"
$criadoem = Get-Date -Format "yyyy-MM-ddTHH:mm:ss"
$labelValue="Badge"

$randomIdentifier = Get-Random -Maximum 1000000
$resourceGroupName="rg-badges-$randomIdentifier"
$location="eastus2"
$functionAppName="func-badges-$randomIdentifier"
$functionsVersion="4"
$pythonVersion="3.11"
$storageAccountName = "blobbadges$randomIdentifier"
if ($storageAccountName.Length -gt 24) {
    $storageAccountName = $storageAccountName.Substring(0, 24)
}
$skuStorage="Standard_LRS"
$BadgeContainerName="badges"
$FontsContainerName="fonts"
$nosqlDBName="nosql-badges-$randomIdentifier"
$databaseName="dbBadges"
$azappconfigName="appconfig-badges-$randomIdentifier"
$keyVaultName = "kv-badges-$randomIdentifier"

Write-Host "Criando grupo de recursos: $resourceGroupName" -ForegroundColor Green
az group create --name $resourceGroupName --location "$location" --tags Environment=$environmentTag Product=$productTag CriadoEm=$criadoem

Write-Host "Criando storage account: $storageAccountName" -ForegroundColor Green
az storage account create --name $storageAccountName --location "$location" --resource-group $resourceGroupName --sku $skuStorage --tags Environment=$environmentTag Product=$productTag CriadoEm=$criadoem CriadoEm=$criadoem
Write-Host "Recuperando connection string da storage account: $storageAccountName" -ForegroundColor Green
$blobConnectionString = az storage account show-connection-string --name $storageAccountName --resource-group $resourceGroupName --query "connectionString" -o tsv
Write-Host "Criando containers $FontsContainerName da storage account: $storageAccountName" -ForegroundColor Green
az storage container create --name $FontsContainerName --account-name $storageAccountName --connection-string $blobConnectionString
Write-Host "Criando containers $BadgeContainerName da storage account: $storageAccountName" -ForegroundColor Green
az storage container create --name $BadgeContainerName --account-name $storageAccountName --connection-string $blobConnectionString

Write-Host "Criando function: $functionAppName" -ForegroundColor Green
az functionapp create --name $functionAppName --storage-account $storageAccountName --consumption-plan-location "$location" --resource-group $resourceGroupName --os-type Linux --runtime python --runtime-version $pythonVersion --functions-version $functionsVersion --tags Environment=$environmentTag Product=$productTag CriadoEm=$criadoem
Write-Host "Ativando a Identidade Gerenciada para a Function: $functionAppName" -ForegroundColor Green
az functionapp identity assign --name $functionAppName --resource-group $resourceGroupName
$AzFuncPrincipalId = $(az functionapp identity show --name $functionAppName --resource-group $resourceGroupName --query "principalId" -o tsv)

Write-Host "Criando CosmosDB: $nosqlDBName" -ForegroundColor Green
az cosmosdb create --name $nosqlDBName --resource-group $resourceGroupName --default-consistency-level Session  --locations regionName="$location" failoverPriority=0 isZoneRedundant=False --kind MongoDB --tags Environment=$environmentTag Product=$productTag CriadoEm=$criadoem

Write-Host "Criando database: $databaseName" -ForegroundColor Green
az cosmosdb mongodb database create --account-name $nosqlDBName --name $databaseName --resource-group $resourceGroupName
Write-Host "Recuperando keys do database: $databaseName" -ForegroundColor Green
$keys = az cosmosdb keys list --name $nosqlDBName --resource-group $resourceGroupName --query "primaryMasterKey" -o tsv
Write-Host "Criando connection string do database: $databaseName" -ForegroundColor Green
$nosqlConnectionString = "mongodb://${nosqlDBName}:${keys}@${nosqlDBName}.mongo.cosmos.azure.com:10255/?ssl=true&replicaSet=globaldb&retrywrites=false&maxIdleTimeMS=120000&appName=@${nosqlDBName}@"

Write-Host "Criando App Config: $azappconfigName" -ForegroundColor Green
az appconfig create --location "$location" --name $azappconfigName --resource-group $resourceGroupName --tags Environment=$environmentTag Product=$productTag CriadoEm=$criadoem
Write-Host "Criando connection string do App Config: $azappconfigName" -ForegroundColor Green
$appconfigConnectionString = az appconfig credential list --name $azappconfigName --resource-group $resourceGroupName --query "[0].connectionString" -o tsv
Write-Host "Definindo permissões no App Config $azappconfigName para a Identidade Gerenciada da Function $functionAppName" -ForegroundColor Green
az role assignment create --assignee $AzFuncPrincipalId --role "Contributor" --scope (az appconfig show --name $azAppConfigName --resource-group $resourceGroupName --query "id" -o tsv)

Write-Host "Criando Key Vault: $keyVaultName" -ForegroundColor Green
az keyvault create --name $keyVaultName --resource-group $resourceGroupName --location $location --tags Environment=$environmentTag Product=$productTag CriadoEm=$criadoem
$AzKVUri = "https://$keyVaultName.vault.azure.net/"
Write-Host "Definindo permissões no Key Vault $keyVaultName para a Identidade Gerenciada da Function $functionAppName" -ForegroundColor Green
az keyvault set-policy --name $keyVaultName --object-id $AzFuncPrincipalId --secret-permissions get list set delete --key-permissions get create delete list update --certificate-permissions get list update create delete

Write-Host "Setando contexto da Azure CLI com o Azure PowerShell..." -ForegroundColor Green
Read-Host "Em breve você será redirecionado para confirmar sua autenticação no browser..... (pressione qualquer tecla para continuar)"
$subscriptionInfo = az account show --output json | ConvertFrom-Json
Enable-AzContextAutosave
Connect-AzAccount -Subscription $subscriptionInfo.id -Tenant $subscriptionInfo.tenantId
Get-AzContext

Write-Host "Setando configurações..." -ForegroundColor Green

Write-Host "Definindo AppConfigConnectionString em $functionAppName" -ForegroundColor Green
$appconfigConnectionString = $appconfigConnectionString.Trim()
$connectionStrings = @{
    "AppConfigConnectionString" = @{
        "Value" = $appconfigConnectionString
        "Type" = "Custom"
    }
}
Set-AzWebApp -ResourceGroupName $resourceGroupName -Name $functionAppName -ConnectionStrings $connectionStrings

Write-Host "Fazendo upload do template a e da fonts para a storage account  $storageAccountName" -ForegroundColor Green
$blobUploadParameters = @(
    @{ContainerName=$BadgeContainerName; LocalFilePath="$caminhoDoTemplateDoBadge\template_badge.png"; BlobName="template_badge.png"},
    @{ContainerName=$BadgeContainerName; LocalFilePath=".\badge_data.schema.json"; BlobName="badge_data.schema.json"},
    @{ContainerName=$FontsContainerName; LocalFilePath="$caminhoDaFonteNotoColorEmoji\NotoColorEmoji-Regular.ttf"; BlobName="NotoColorEmoji-Regular.ttf"},
    @{ContainerName=$FontsContainerName; LocalFilePath="$caminhoDaFonteRubikBold\Rubik-Bold.ttf"; BlobName="Rubik-Bold.ttf"},
    @{ContainerName=$FontsContainerName; LocalFilePath="$caminhoDaFonteRubikRegular\Rubik-Regular.ttf"; BlobName="Rubik-Regular.ttf"}
)

$blobUploadParameters | ForEach-Object {
    az storage blob upload --container-name $_.ContainerName --file $_.LocalFilePath --name $_.BlobName --account-name $storageAccountName --connection-string $blobConnectionString
}

Write-Host "Gerando URL SAS do template a e da fonts da storage account  $storageAccountName" -ForegroundColor Green
$blobFiles = @(
    @{ContainerName=$BadgeContainerName; BlobName='template_badge.png'; BlobUrlVariableName='blobUrlTemplateBadge'},
    @{ContainerName=$BadgeContainerName; BlobName='badge_data.schema.json'; BlobUrlVariableName='BadgeDBSchemaURL'},
    @{ContainerName=$FontsContainerName; BlobName='NotoColorEmoji-Regular.ttf'; BlobUrlVariableName='blobUrlNotoColorEmoji'},
    @{ContainerName=$FontsContainerName; BlobName='Rubik-Bold.ttf'; BlobUrlVariableName='blobUrlRubikBold'},
    @{ContainerName=$FontsContainerName; BlobName='Rubik-Regular.ttf'; BlobUrlVariableName='blobUrlRubikRegular'}
)

$blobFiles | ForEach-Object {
    $expiryDate = (Get-Date -Year (Get-Date).Year -Month 12 -Day 31 -Hour 23 -Minute 59 -Second 59).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    $sasToken = az storage blob generate-sas --container-name $_.ContainerName --name $_.BlobName --permissions r --expiry $expiryDate --account-name $storageAccountName --connection-string $blobConnectionString --https-only --output tsv
    Set-Variable -Name $_.BlobUrlVariableName -Value ("https://$storageAccountName.blob.core.windows.net/$($_.ContainerName)/$($_.BlobName)?$sasToken")
}

Write-Host "Atualizando arquivos padrão..." -ForegroundColor Green
$arquivosEValores = @(
    @{Caminho=".\BadgeHeaderInfo.json"; ValorAntigo="<blobUrlRubikRegular>"; ValorNovo=$blobUrlRubikRegular},
    @{Caminho=".\template.json"; ValorAntigo="<issuerName>"; ValorNovo=$issuerName},
    @{Caminho=".\template.json"; ValorAntigo="<areaName>"; ValorNovo=$areaName},
    @{Caminho=".\template.json"; ValorAntigo="<blobUrlRubikBold>"; ValorNovo=$blobUrlRubikBold},
    @{Caminho=".\template.json"; ValorAntigo="<blobUrlNotoColorEmoji>"; ValorNovo=$blobUrlNotoColorEmoji},
    @{Caminho=".\template.json"; ValorAntigo="<blobUrlTemplateBadge>"; ValorNovo=$blobUrlTemplateBadge}
)
$arquivosEValores | ForEach-Object {
    $conteudoDoArquivo = Get-Content -Path $_.Caminho -Raw
    $conteudoDoArquivoAtualizado = $conteudoDoArquivo -replace $_.ValorAntigo, $_.ValorNovo
    Set-Content -Path $_.Caminho -Value $conteudoDoArquivoAtualizado
}

Write-Host "Setando valores no App Config $azappconfigName" -ForegroundColor Green
$newSettings = @(
    @{name='AzKVURI'; value=$AzKVURI},
    @{name='BadgeContainerName'; value=$BadgeContainerName},
    @{name='BadgeDBSchemaURL'; value=[System.Web.HttpUtility]::UrlEncode($BadgeDBSchemaURL)},
    @{name='BadgeVerificationUrl'; value=$BadgeVerificationUrl},
    @{name='LinkedInPost'; value=$LinkedInPost}
)

foreach ($setting in $newSettings) {
    az appconfig kv set --name $azappconfigName --key $setting.name --value $setting.value --content-type "text/plain;charset=utf-8" --label $labelValue
}

$contentBadgeHeaderInfo = Get-Content -Path ".\BadgeHeaderInfo.json" | Out-String | ConvertFrom-Json
$contentBadgeHeaderInfo = $contentBadgeHeaderInfo | ConvertTo-Json -Compress
$contentBadgeHeaderInfo = $contentBadgeHeaderInfo -replace '"', '\"'
az appconfig kv set --name $azappconfigName --key BadgeHeaderInfo --value "$contentBadgeHeaderInfo" --content-type "application/json;charset=utf-8" --label $labelValue

Write-Host "Setando segredos no Key Vault $keyVaultName" -ForegroundColor Green
$nosqlConnectionStrinURLEncoded=[System.Web.HttpUtility]::UrlEncode($nosqlConnectionString)

$keyVaultSecretParameters = @(
    @{SecretName="BlobConnectionString"; SecretValue=$blobConnectionString; ContentType="text/plain; charset=utf-8"},
    @{SecretName="CosmosDBConnectionString"; SecretValue=$nosqlConnectionStrinURLEncoded; ContentType="text/plain; charset=utf-8"}
)

$keyVaultSecretParameters | ForEach-Object {
    az keyvault secret set --vault-name $keyVaultName --name $_.SecretName --value $_.SecretValue --content-type $_.ContentType
}

Write-Host "Criando Collections Badges e Template detro do $nosqlDBName.$databaseName" -ForegroundColor Green
$collectionsParameters = @(
    @{CollectionName="Template"},
    @{CollectionName="Badges"}
)

$collectionsParameters | ForEach-Object {
    az cosmosdb mongodb collection create --account-name $nosqlDBName --database-name $databaseName  --name $_.CollectionName  --resource-group $resourceGroupName  --shard "_id"  --throughput "400"
}

Write-Host "Para inserir os dados mínimos no CosmosDB $nosqlDBName.$databaseName pegue o conteúdo do arquivo .\template.json e insira no banco. OBRIGATORIAMENTE deve ser criada uma collection de nome Template. Sem esse valor inicial a function não funcionará corretamente." -ForegroundColor Magenta

Write-Host "Publicando function $functionAppName" -ForegroundColor Green
func azure functionapp publish $functionAppName
