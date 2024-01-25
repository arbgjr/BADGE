# BADGE (Badge Authentication and Dynamic Grading Engine)

## Descrição

BADGE é um sistema inovador destinado a autenticar e classificar conquistas por meio de badges digitais. Este sistema permite que empresas e instituições de ensino emitam badges para reconhecer e validar habilidades, realizações e progressos de indivíduos.

## Características

- **Emissão de Badges**: Geração dinâmica de badges com informações personalizadas e QR Code para validação.
- **Validação de Badges**: Sistema seguro para autenticar a legitimidade dos badges emitidos.
- **Integração com Plataformas Sociais**: Facilidade para compartilhar conquistas em plataformas como LinkedIn.
- **Análise de Dados**: Dashboards para monitoramento do engajamento e progresso dos usuários.
- **Gamificação**: Elementos de gamificação para aumentar o engajamento e a motivação.

## Tecnologia

- Utiliza Flask para o backend, integrado com Azure Functions. (Não optei pelo Django pois preferi escolher quais funcionalidades meu sistema ia carregar.)
- Armazenamento de dados com Azure CosmosDB (as MongoDB).
- Armazenamento de arquivos com Azure Blob Storage
- Segurança reforçada através do Azure Key Vault.

## Como Começar

1. Configure o ambiente Azure (Azure Functions, Azure CosmosDB, Azure Blob Storage, Azure App Configuration, Azure Key Vault).
2. Clone o repositório e instale as dependências necessárias.
3. Configure as variáveis de ambiente conforme a documentação.

## Instalação do BADGE

### Pré-Requisitos

- **Windows 10 1709 (build 16299) ou posterior**: Caso possua sistema Linux ou MacOS, ainda é possível instalar o BADGE, basta verificar quais passos abaixo se aplicam e adapta-los a sua necessidade.

- **Winget v1.6+**: Siga o [passo a passo indicado no site da Microsoft](https://learn.microsoft.com/pt-br/windows/package-manager/winget/#install-winget)

- **PowerShell v7+**: Certifique-se de ter o PowerShell v7 ou superior instalado. Para macOS e Linux, [siga as instruções de instalação do PowerShell](https://docs.microsoft.com/pt-br/powershell/scripting/install/installing-powershell).

- **Conta no Azure**: [Crie uma conta gratuita no Azure](https://azure.microsoft.com/pt-br/free/). Todos os recursos do Azure utilizados foram configurados para usar o minimo de custos possível.

- **Azure CLI v2.56+**: Todos os serviços do Azure serão instalados via CLI. Siga o passo a passo indicado no site da Microsoft para [instalar](https://learn.microsoft.com/pt-br/cli/azure/install-azure-cli) ou [atualizar](https://learn.microsoft.com/pt-br/cli/azure/update-azure-cli).

- **Azure Functions Core Tools v3+**: Siga o [passo a passo indicado no site da Microsoft](https://learn.microsoft.com/pt-br/azure/azure-functions/functions-run-local?tabs=windows%2Cisolated-process%2Cnode-v4%2Cpython-v2%2Chttp-trigger%2Ccontainer-apps&pivots=programming-language-powershell#install-the-azure-functions-core-tools)

- **Azure PowerShell v11.2+**: Siga o [passo a passo indicado no site da Microsoft](https://learn.microsoft.com/pt-br/powershell/azure/install-azps-windows?view=azps-11.2.0&tabs=powershell&pivots=windows-psgallery)

- **git v2.43+**: Siga o [passo a passo indicado no site do git](https://git-scm.com/book/pt-br/v2/Come%C3%A7ando-Instalando-o-Git)

### Instalação

- **Logar no Azure via CLI**: Todos os serviços do Azure serão instalados via CLI. Siga o [passo a passo indicado no site da Microsoft](https://learn.microsoft.com/pt-br/cli/azure/authenticate-azure-cli-interactively).

- **Caso possua mais de uma subscription, selecione a desejada**: Siga o [passo a passo indicado no site da Microsoft](https://learn.microsoft.com/pt-br/cli/azure/manage-azure-subscriptions-azure-cli?tabs=bash#change-the-active-tenant)

- **Configurar git**: Siga o [passo a passo indicado no site do git](https://git-scm.com/book/pt-br/v2/Come%C3%A7ando-Configura%C3%A7%C3%A3o-Inicial-do-Git)

- **Repo do Badges clonado**: Siga o [passo a passo indicado no site do git](https://git-scm.com/book/pt-br/v2/Fundamentos-de-Git-Obtendo-um-Reposit%C3%B3rio-Git#r_git_cloning) para clonar o repositorio [https://github.com/arbgjr/BADGE.git](https://github.com/arbgjr/BADGE.git).

- **Criar ou escolher um grupo de recursos no Azure para organização dos recursos que seão criados**: Siga o [passo a passo indicado no site da Microsoft](https://learn.microsoft.com/pt-br/cli/azure/manage-azure-groups-azure-cli#create-a-resource-group). Guarde o nome da grupo de recursos criado.

Ex.:
´´´powershell
$tagValue="Badge"
$randomIdentifier = Get-Random -Maximum 1000000
$resourceGroupName="rg-badges-$randomIdentifier"
$location="eastus2"
az group create --name $resourceGroupName --location "$location"
´´´

- **Criar uma Storage Account no Azure**: Siga o [passo a passo indicado no site da Microsoft](https://learn.microsoft.com/pt-br/azure/storage/common/storage-account-create?tabs=azure-cli#create-a-storage-account-1). Guarde o nome da Storage Account criada.
  - Para utilizar a Storage Account mais barata, recomendo que seja utilizado o parametro **--sku Standard_LRS**

Ex.:
´´´powershell
$storageAccountName="blob-badges-$randomIdentifier"
$skuStorage="Standard_LRS"
az storage account create --name $storageAccountName --location "$location" --resource-group $resourceGroupName --sku $skuStorage
´´´

- **Recuperar a connection string com o Storage Blob**.

Ex.:
´´´powershell
$blobConnectionString = az storage account show-connection-string --name $storageaccountName --resource-group $resourceGroupName --query "connectionString" -o tsv
´´´

- **Criar os containers para fonts e badges**:

Ex.:
´´´powershell
$BadgeContainerName="badges"
$FontsContainerName="fonts"
az storage container create --name $FontsContainerName --account-name $storageAccountName
az storage container create --name $BadgeContainerName --account-name $storageAccountName
´´´

- **Criar uma Azure Function Python**: Siga o [passo a passo indicado no site da Microsoft](https://learn.microsoft.com/pt-br/azure/azure-functions/scripts/functions-cli-create-serverless-python). Guarde o nome da Function criada.

Ex.:
´´´powershell
$functionAppName="func-badges-$randomIdentifier"
$functionsVersion="4"
$pythonVersion="3.11"
az functionapp create --name $functionAppName --storage-account $storageAccountName --consumption-plan-location "$location" --resource-group $resourceGroupName --os-type Linux --runtime python --runtime-version $pythonVersion --functions-version $functionsVersion
´´´

- **Ativar a Identidade Gerenciada para a Azure Function**:

Ex.:
´´´powershell
az functionapp identity assign --name $functionAppName --resource-group $resourceGroupName
$AzFuncPrincipalId = $(az functionapp identity show --name $functionAppName --resource-group $resourceGroupName --query "principalId" -o tsv)
´´´

- **Criar uma instância de um CosmosDB no Azure com compatibilidade do MongoDB**.

Ex.:
´´´powershell
$nosqlDBName="nosql-badges-$randomIdentifier"
az cosmosdb create --name $nosqlDBName --resource-group $resourceGroupName --default-consistency-level Session  --locations regionName="$location" failoverPriority=0 isZoneRedundant=False --kind MongoDB
´´´

- **Criar um banco MongoDB com nome "dbBadges" no CosmosDB**.

Ex.:
´´´powershell
$databaseName="dbBadges"
az cosmosdb mongodb database create --account-name $nosqlDBName --name $databaseName --resource-group $resourceGroupName
´´´

- **Recuperar a connection string com o "dbBadges"**.

Ex.:
´´´powershell
$keys = az cosmosdb keys list --name $nosqlDBName --resource-group $resourceGroupName --query "primaryMasterKey" -o tsv
$nosqlConnectionString = "mongodb://$nosqlDBName:`$keys@${nosqlDBName}.mongo.cosmos.azure.com:10255/?ssl=true&replicaSet=globaldb&retrywrites=false&maxIdleTimeMS=120000&appName=@${nosqlDBName}@"
´´´

- **Criar um Azure AppConfig**:

Ex.:
´´´powershell
$azappconfigName="appconfig-badges-$randomIdentifier"
az appconfig create --location "$location" --name $azappconfigName --resource-group $resourceGroupName
´´´

- **Recuperar a connection string com o Azure AppConfig**:

Ex.:
´´´powershell
$appconfigConnectionString = az appconfig credential list --name $appconfigName --resource-group $resourceGroupName --query "[0].connectionString" -o tsv
´´´

- **Definir permissões no Azure App Configuration para a Identidade Gerenciada do Azure Function**:

Ex.:
´´´powershell
az role assignment create --assignee $AzFuncPrincipalId --role "Contributor" --scope (az appconfig show --name $azAppConfigName --resource-group $resourceGroupName --query "id" -o tsv)
´´´

- **Criar um Azure Key Vault**:

Ex.:
´´´powershell
$keyVaultName = "kv-badges-$randomIdentifier"
az keyvault create --name $keyVaultName --resource-group $resourceGroupName --location $location
$AzKVUri = "https://$keyVaultName.vault.azure.net/"
´´´

- **Definir permissões no Azure Key Vault para a Identidade Gerenciada do Azure Function**:

Ex.:
´´´powershell
az keyvault set-policy --name $keyVaultName --object-id $AzFuncPrincipalId --secret-permissions get list set delete --key-permissions get create delete list update --certificate-permissions get list update create delete
´´´

- **Adicionar a string de conexão do App Config as configurações de connection string da Azure Function**:

Ex.:
´´´powershell
$appSettings = Get-AzWebApp -ResourceGroupName $resourceGroupName -Name $functionAppName
$connectionStringName = "AppConfigConnectionString"
$appSettings.SiteConfig.ConnectionStrings.Add((New-Object Microsoft.Azure.Management.WebSites.Models.ConnectionStringInfo -ArgumentList $connectionStringName, $appconfigConnectionString, "Custom"))
Set-AzWebApp -ResourceGroupName $resourceGroupName -Name $functionAppName -AppSettings $appSettings.SiteConfig.AppSettings
´´´

- **Fazer upload do template do Badge**: O template do Badge não pode ter fundo transparente, utilizo a premissa de fundo branco.

Ex.:
´´´powershell
az storage blob upload --container-name $BadgeContainerName --file "CaminhoDoTemplateDoBadge\template_badge.png" --name "template_badge.png" --account-name $storageAccountName
´´´

- **Baixar as fontes abaixo, e descompactar os arquivos baixados**:
  - [[OBRIGATÓRIA]]Not Color Emoji: https://fonts.google.com/noto/specimen/Noto+Color+Emoji
  - Outra Fonte do seu gosto, utilizo a Rubik: https://fonts.google.com/specimen/Rubik

- **Fazer upload dos arquivos para o blob storage**: Considero que o comando abaixo está sendo executado de dentro da pasta local do repo do BADGE

Ex.:
´´´powershell
$blobUploadParameters = @(
    @{ContainerName=$BadgeContainerName; LocalFilePath="CaminhoDoTemplateDoBadge\template_badge.png"; BlobName="template_badge.png"},
    @{ContainerName=$BadgeContainerName; LocalFilePath=".\badge_data.schema.json"; BlobName="badge_data.schema.json"},
    @{ContainerName=$FontsContainerName; LocalFilePath="CaminhoDaFonteNotoColorEmoji\NotoColorEmoji-Regular.ttf"; BlobName="NotoColorEmoji-Regular.ttf"},
    @{ContainerName=$FontsContainerName; LocalFilePath="CaminhoDaFonteRubikBold\Rubik-Bold.ttf"; BlobName="Rubik-Bold.ttf"},
    @{ContainerName=$FontsContainerName; LocalFilePath="CaminhoDaFonteRubikRegular\Rubik-Regular.ttf"; BlobName="Rubik-Regular.ttf"}
)

$blobUploadParameters | ForEach-Object {
    az storage blob upload --container-name $_.ContainerName --file $_.LocalFilePath --name $_.BlobName --account-name $storageAccountName
}
´´´

- **Gerar URL SAS dos arquivos enviados para o Blob Storage**:

Ex.:
´´´powershell
$blobFiles = @(
    @{ContainerName=$BadgeContainerName; BlobName='template_badge.png'; BlobUrlVariableName='blobUrlTemplateBadge'},
    @{ContainerName=$BadgeContainerName; BlobName='badge_data.schema.json'; BlobUrlVariableName='BadgeDBSchemaURL'},
    @{ContainerName=$FontsContainerName; BlobName='NotoColorEmoji-Regular.ttf'; BlobUrlVariableName='blobUrlNotoColorEmoji'},
    @{ContainerName=$FontsContainerName; BlobName='Rubik-Bold.ttf'; BlobUrlVariableName='blobUrlRubikBold'},
    @{ContainerName=$FontsContainerName; BlobName='Rubik-Regular.ttf'; BlobUrlVariableName='blobUrlRubikRegular'}
)

$blobFiles | ForEach-Object {
    $expiryDate = (Get-Date -Year (Get-Date).Year -Month 12 -Day 31 -Hour 23 -Minute 59 -Second 59).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
    $sasToken = az storage blob generate-sas --container-name $_.ContainerName --name $_.BlobName --permissions r --expiry $expiryDate --account-name $storageAccountName --https-only --output tsv
    Set-Variable -Name $_.BlobUrlVariableName -Value ("https://$storageAccountName.blob.core.windows.net/$($_.ContainerName)/$($_.BlobName)?$sasToken")
}
´´´

- **Atualizar arquivos com configurações padrão**: Caso queira

Ex.:
´´´powershell
$issuerName="Acme Industries"
$areaName="AsPoNe"

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
´´´

- **Adicionar configurações ao App Config**:

Ex.:
´´´powershell
$BadgeVerificationUrl="https://www.qualquerurl.com"
$LinkedInPost=""Estou muito feliz em compartilhar que acabei de conquistar um novo badge: {badge_name}!\r\nEsta conquista representa {additional_info}.\r\nVocê pode verificar a autenticidade do meu badge aqui: {validation_url}\r\n#Conquista #Badge #DesenvolvimentoProfissional"

$newSettings = @(
				@{name='AzKVURI'; value=$AzKVURI},
				@{name='BadgeContainerName'; value=$BadgeContainerName},
				@{name='BadgeDBSchemaURL'; value=$BadgeDBSchemaURL},
				@{name='BadgeVerificationUrl'; value=$BadgeVerificationUrl},
				@{name='LinkedInPost'; value=$LinkedInPost}
			)
$newSettings | ForEach-Object {Set-AppConfigKeyValue -azAppConfigName $azappconfigName -settingName $_.name -settingValue $_.value -ContentType "text/plain;charset=utf-8" -tag $tagValue}

$contentBadgeHeaderInfo = Get-Content -Path ".\BadgeHeaderInfo.json" -Raw
az appconfig kv set --name $azappconfigName --key BadgeHeaderInfo --value $content --content-type "application/json" --label $tagValue
´´´

- **Adicionar configurações ao Key Vault**:

Ex.:
´´´powershell
$keyVaultSecretParameters = @(
    @{SecretName="BlobConnectionString"; SecretValue=$blobConnectionString; ContentType="text/plain; charset=utf-8"},
    @{SecretName="CosmosDBConnectionString"; SecretValue=$nosqlConnectionString; ContentType="text/plain; charset=utf-8"}
)

$keyVaultSecretParameters | ForEach-Object {
    az keyvault secret set --vault-name $keyVaultName --name $_.SecretName --value $_.SecretValue --content-type $_.ContentType
}
´´´

- **Inserir no nosql os dados que serão inseridos no template**: Sugiro você recuperar o conteudo do arquivo Template.json e inserir diretamente no CosmosDB criado. O nome da Collection deve ser: Templates. E ela deve ficar dentro do dbBadges. A opção do script abaixo é passível de erros.

Ex.:
´´´powershell
$verb = "POST"
$resourceType = "docs"
$resourceLink = "dbs/$databaseName/colls/Templates"
$resourceKey = $keys # Chave primária do Cosmos DB
$date = [DateTime]::UtcNow.ToString("R")

$keyBytes = [System.Text.Encoding]::UTF8.GetBytes($resourceKey)
$hashAlgorithm = [System.Security.Cryptography.HMACSHA256]::new($keyBytes)
$stringToSign = $verb.ToLower() + "`n" + $resourceType.ToLower() + "`n" + $resourceLink + "`n" + $date.ToLower() + "`n" + "" + "`n"
$signatureBytes = $hashAlgorithm.ComputeHash([System.Text.Encoding]::UTF8.GetBytes($stringToSign))
$signature = [Convert]::ToBase64String($signatureBytes)

$authHeader = @{
    Authorization=("type=master&ver=1.0&sig=" + $signature)
    "x-ms-date"=$date
}

$uriCosmosDB = "https://$nosqlDBName.documents.azure.com:443/dbs/$databaseName/colls/Templates/docs"

$arquivoJson = ".\template.json"
$conteudoJson = Get-Content -Path $arquivoJson -Raw

$response = Invoke-RestMethod -Method Post -Uri $uriCosmosDB -Body $conteudoJson -Headers $authHeader -ContentType "application/json"

$response
´´´

- **Publicar a Function no Azure**: Siga o [passo a passo indicado no site da Microsoft](https://learn.microsoft.com/pt-br/azure/azure-functions/create-first-function-arc-cli?tabs=powershell%2Cwindows%2Cbrowser#deploy-the-function-project-to-azure)

## Contribuições

Contribuições são bem-vindas! Para contribuir, siga as diretrizes de contribuição no repositório.

## Licença

Vide LICENSE.
