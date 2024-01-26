$randomIdentifier="999999"
$resourceGroupName="rg-badges-$randomIdentifier"
$functionAppName="func-badges-$randomIdentifier"
$storageAccountName = "blobbadges$randomIdentifier"
$azappconfigName="appconfig-badges-$randomIdentifier"
$keyVaultName = "kv-badges-$randomIdentifier"

$BadgeContainerName="badges"
$FontsContainerName="fonts"
$nosqlDBName="nosqlengagement"
$databaseName="dbBadges"
$AzKVUri = "https://$keyVaultName.vault.azure.net/"
$BadgeVerificationUrl="https://www.qualquerurl.com"
LinkedInPost = @"
Estou muito feliz em compartilhar que acabei de conquistar um novo badge: {badge_name}!\r\nEsta conquista representa {additional_info}.\r\nVocê pode verificar a autenticidade do meu badge aqui: {validation_url}\r\n#Conquista #Badge #DesenvolvimentoProfissional
"@

Clear-Host

Write-Host "Recuperando keys do database: $databaseName" -ForegroundColor Green
$keys = az cosmosdb keys list --name $nosqlDBName --resource-group $resourceGroupName --query "primaryMasterKey" -o tsv

Write-Host "Recuperando connection string da storage account: $storageAccountName" -ForegroundColor Green
$blobConnectionString = az storage account show-connection-string --name $storageAccountName --resource-group $resourceGroupName --query "connectionString" -o tsv

Write-Host "Criando connection string do database: $nosqlDBName.$databaseName" -ForegroundColor Green
$nosqlConnectionString = "mongodb://${nosqlDBName}:${keys}@${nosqlDBName}.mongo.cosmos.azure.com:10255/?ssl=true&replicaSet=globaldb&retrywrites=false&maxIdleTimeMS=120000&appName=@${nosqlDBName}@"

Write-Host "Criando connection string do App Config: $azappconfigName" -ForegroundColor Green
$appconfigConnectionString = az appconfig credential list --name $azappconfigName --resource-group $resourceGroupName --query "[0].connectionString" -o tsv

$appconfigConnectionString = $appconfigConnectionString.Trim()
$connectionStrings = @{
    "AppConfigConnectionString" = @{
        "Value" = $appconfigConnectionString
        "Type" = "Custom"
    }
}
Set-AzWebApp -ResourceGroupName $resourceGroupName -Name $functionAppName -ConnectionStrings $connectionStrings

Write-Host "Gerando URL SAS do template a e da fonts da storage account  $storageAccountName" -ForegroundColor Green
$blobFiles = @(
    @{ContainerName=$BadgeContainerName; BlobName='Badge.png'; BlobUrlVariableName='blobUrlTemplateBadge'},
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
    @{Caminho=".\template.json"; ValorAntigo="<blobUrlNotoColorEmoji>"; ValorNovo=$blobUrlNotoColorEmoji}
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
