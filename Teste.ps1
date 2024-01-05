$moduleFiles = @(
	"AzureFunctions.ps1",
	"GitFunctions.ps1",
	"RegistryFunctions.ps1",
	"MyTools.ps1"
)

foreach ($moduleFile in $moduleFiles) {
	$modulePath = Join-Path -Path $PSScriptRoot -ChildPath $moduleFile
	Import-Module $modulePath -Force
}

## Script de Configuração e Instalação para o Projeto BADGE
Initialize-Script

# Verificar se o script está sendo executado com privilégios de administrador
$isAdmin = Test-AdminPrivileges
if (-not $isAdmin) {
	exit
}

Set-Variable -Name "GITHUB_REPO" -Value "https://github.com/arbgjr/BADGE.git" -Option ReadOnly
Set-Variable -Name "REPO_NAME" -Value "Badge" -Option ReadOnly

$OS = Get-WmiObject -Class Win32_OperatingSystem
$osName = $OS.Caption
$osVersion = $OS.Version

Remove-Variable -Name "IsWindows" -Force -ErrorAction SilentlyContinue
$IsWindows = $OS.Caption -like "*Windows*"
Remove-Variable -Name "IsMacOS" -Force -ErrorAction SilentlyContinue
$IsMacOS = $OS.Caption -like "*Mac OS*"
Remove-Variable -Name "IsLinux" -Force -ErrorAction SilentlyContinue
$IsLinux = $OS.Caption -like "*Linux*"

Write-Host "Sistema Operacional: $osName"
Write-Host "Versão: $osVersion"

$registryPath = "HKCU:\Software\$REPO_NAME\Install"
$currentPath = Get-Location

# Recupera configurações salvas
$AzFuncEnv = Get-RegistryValue -Name "AzFuncEnv"
$defaultHostName = Get-RegistryValue -Name "defaultHostName"
$functionAppName = Get-RegistryValue -Name "functionAppName"
$storageAccountName = Get-RegistryValue -Name "storageAccountName"
$resourceGroupName = Get-RegistryValue -Name "resourceGroupName"
$location = Get-RegistryValue -Name "location"
$subscriptionName = Get-RegistryValue -Name "subscriptionName"
$subscriptionId = Get-RegistryValue -Name "subscriptionId"
$userName = Get-RegistryValue -Name "userName"
$repoUrl = Get-RegistryValue -Name "repoUrl"
$fullRepoPath = Get-RegistryValue -Name "repoPath"
$gitUserName = Get-RegistryValue -Name "gitUserName"
$gitUserEmail = Get-RegistryValue -Name "gitUserEmail"
$serverName = Get-RegistryValue -Name "serverName"
$databaseName = Get-RegistryValue -Name "databaseName"
$bdConnectionString = Get-RegistryValue -Name "bdConnectionString"
$azAppConfigName = Get-RegistryValue -Name "azAppConfigName"
$azAppConfigStrConn = Get-RegistryValue -Name "azAppConfigStrConn"
$AzKeyVaultName = Get-RegistryValue -Name "AzKeyVaultName"
$AzKVUri = Get-RegistryValue -Name "AzKVUri"
$AzFuncPrincipalId = Get-RegistryValue -Name "AzFuncPrincipalId"


# INSIRA ABAIXO O SCRIPT A SER TESTADO.

# Azure Functions
# 	AppConfigConnectionString
# Azure SQL Database: 
# Azure App Configuration: 
# 	AzKVURI
#	GpgKeyId
#	BadgeTemplateBase64
#	BadgeVerificationUrl
#	SqlConnectionString
# Azure Key Vault: 

