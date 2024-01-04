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
if (-NOT Test-AdminPrivileges) {
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

$lastStep = [ScriptSteps]::NotStarted
$intLastStep = NumLastStep $lastStep

$registryPath = "HKCU:\Software\$REPO_NAME\Install"
$currentPath = Get-Location

$confirmRun = Read-HostWithCancel "Deseja efetuar a configuração do ambiente de forma automatizada? (S/N)"
if ($confirmRun -eq 'N' -or $confirmRun -eq 'n') {
	break
}

# Recupera de onde o script parou a execução
$lastStep = Get-LastCompletedStep

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

try {
	try {
		if (-not [string]::IsNullOrWhiteSpace($AzFuncEnv)) {
			foreach ($setting in $AzFuncEnv) {
				$deleteAzFuncEnv = Read-HostWithCancel "Deseja remover a configuração '$setting'? (S/N)"
				if ($deleteAzFuncEnv -eq 'S' -or $deleteAzFuncEnv -eq 's') {
					az functionapp config appsettings delete --name $functionAppName --resource-group $resourceGroupName --setting-name $setting
					Write-Host "Configuração: '$setting' removida com sucesso da Azure Function '$functionAppName'." -ForegroundColor Green
				} else {
					Write-Host "Mantendo a configuração '$setting'." -ForegroundColor Green
				}
			}
			Remove-RegistryValue -Name "AzFuncEnv"
		}
	} catch {
		Show-ErrorMessage "Falha ao remover as variáveis de ambiente da Azure Function."
		exit
	}

	try {
		$functionAppInfo = az functionapp show --name $functionAppName  --resource-group $resourceGroupName --query "{state: state, defaultHostName: defaultHostName}" -o json | ConvertFrom-Json

		if ($functionAppInfo -and $functionAppInfo.state -eq "Running") {
			Write-Host "A Azure Function '$functionAppName' está em execução em: $($functionAppInfo.defaultHostName)" -ForegroundColor Green
			$stopFunction = Read-HostWithCancel "Deseja parar a Azure Function? (S/N)"
			if ($stopFunction -eq 'S' -or $stopFunction -eq 's') {
				Stop-AzureFunction
			} else {
				Write-Host "Mantendo a Azure Function '$functionAppName' em execução." -ForegroundColor Green
			}
		} else {
			Write-Host "A Azure Function '$functionAppName' não está em execução." -ForegroundColor Green
		}
		
		Remove-RegistryValue -Name "defaultHostName"
		
	} catch {
		Show-ErrorMessage "Falha ao parar a Azure Function '$functionAppName'."
		exit
	}

	try {
		$existingFunctionApp = az functionapp show --name $functionAppName --query 'state' --resource-group $resourceGroupName

		if ($existingFunctionApp) {
			$functionAppState = $existingFunctionApp.Trim()

			if ($functionAppState -eq "Running") {
				Write-Host "A Azure Function '$functionAppName' existe, mas não está em execução." -ForegroundColor Green
				exit
			}

			$deleteFunctionApp = Read-HostWithCancel "Deseja remover a Azure Function '$functionAppName'? (S/N)"
			if ($deleteFunctionApp -eq 'S' -or $deleteFunctionApp -eq 's') {
				Remove-AzureFunction
			} else {
				Write-Host "Mantendo a Azure Function '$functionAppName' existente." -ForegroundColor Green
			}
		} else {
			Write-Host "A Azure Function '$functionAppName' não existe." -ForegroundColor Green
		}
	} catch {
		Show-ErrorMessage "Falha ao remover a Azure Function '$functionAppName'."
		exit
	}

	try {
		$existingStorageAccount = az storage account check-name --name $storageAccountName --query 'nameAvailable'

		if ($existingStorageAccount -eq 'true') {
			Write-Host "A conta de armazenamento '$storageAccountName' existe." -ForegroundColor Green
			$deleteStorageAccount = Read-HostWithCancel "Deseja remover a conta de armazenamento? (S/N)"
			if ($deleteStorageAccount -eq 'S' -or $deleteStorageAccount -eq 's') {
				Remove-AzureStorageAccount
			} else {
				Write-Host "Mantendo a conta de armazenamento '$storageAccountName' existente." -ForegroundColor Green
			}
		} else {
			Write-Host "A conta de armazenamento '$storageAccountName' não existe." -ForegroundColor Green
		}
	} catch {
		Show-ErrorMessage "Falha ao remover a conta de armazenamento '$storageAccountName'."
		exit
	}

	try {
		$existingResourceGroup = az group exists --name $resourceGroupName

		if ($existingResourceGroup -eq 'true') {
			Write-Host "O grupo de recursos '$resourceGroupName' existe." -ForegroundColor Green
			$deleteResourceGroup = Read-HostWithCancel "Deseja remover o grupo de recursos '$resourceGroupName'? (S/N)"
			if ($deleteResourceGroup -eq 'S' -or $deleteResourceGroup -eq 's') {
				Remove-AzureResourceGroup
			} else {
				Write-Host "Mantendo o grupo de recursos '$resourceGroupName' existente." -ForegroundColor Green
			}
		} else {
			Write-Host "O grupo de recursos '$resourceGroupName' não existe." -ForegroundColor Green
		}
	} catch {
		Show-ErrorMessage "Falha ao remover o grupo de recursos '$resourceGroupName'."
		exit
	}

	try {
		if ([string]::IsNullOrWhiteSpace($subscriptionName) -or [string]::IsNullOrWhiteSpace($subscriptionId)) {
			Write-Host "As informações de assinatura não estão definidas." -ForegroundColor Green
		} else {
			Write-Host "Assinatura atual: $subscriptionName (ID: $subscriptionId)" -ForegroundColor Green
			$restoreSubscription = Read-HostWithCancel "Deseja REMOVER a assinatura localmente (ela ainda existira no Portal Azure)? (S/N)"
			if ($restoreSubscription -eq 'S' -or $restoreSubscription -eq 's') {
				Remove-AzureSubscription
			} else {
				Write-Host "Mantendo a assinatura atual." -ForegroundColor Green
			}
		}
	} catch {
		Show-ErrorMessage "Falha ao remover as informações de assinatura."
		exit
	}

	try {
		$azAccountJson = az account show --output json | Out-String

		if (-not $azAccountJson -or $azAccountJson -eq "") {
			Write-Host "Você não está logado na Azure CLI." -ForegroundColor Green
		} else {
			$azAccount = ConvertFrom-Json $azAccountJson
			$userName = $azAccount.user.name
			$logoffAzureCLI = Read-HostWithCancel "Deseja fazer o logoff no Azure CLI da conta '$userName'? (S/N)"
			if ($logoffAzureCLI -eq 'S' -or $logoffAzureCLI -eq 's') {
				az logout
				Write-Host "Logoff da conta '$userName' bem-sucedido da Azure CLI. Você está desconectado da conta." -ForegroundColor Green
				Remove-RegistryValue -Name "userName"
			} else {
				Write-Host "Mantendo a conta '$userName' logada no Azure CLI." -ForegroundColor Green
			}
		}
	} catch {
		Show-ErrorMessage "Falha ao fazer logoff da conta na Azure CLI."
		exit
	}

	try {
		if ([string]::IsNullOrWhiteSpace($fullRepoPath)) {
			Write-Host "O caminho do repositório não está definido." -ForegroundColor Green
		} elseif (Test-Path $fullRepoPath) {
			Write-Host "O repositório em '$fullRepoPath' existe." -ForegroundColor Green
			$removeRepo = Read-HostWithCancel "Deseja REMOVER o repositório '$fullRepoPath'? (S/N)"
			if ($removeRepo -eq 'S' -or $removeRepo -eq 's') {
				Remove-Item -Recurse -Force $fullRepoPath
				Write-Host "Repositório '$fullRepoPath' removido com sucesso." -ForegroundColor Green
				Remove-RegistryValue -Name "fullRepoPath"
			} else {
				Write-Host "Mantendo o repositório '$fullRepoPath' existente." -ForegroundColor Green
			}
		} else {
			Write-Host "O repositório em '$fullRepoPath' não existe." -ForegroundColor Green
		}
	} catch {
		Show-ErrorMessage "Falha ao remover o repositório."
		exit
	}

	try {
		if ($gitUserName -and $gitUserEmail) {
			Write-Host "A configuração atual do Git é: Nome de usuário: '$gitUserName', Email: '$gitUserEmail'" -ForegroundColor Green
			$restoreGitConfig = Read-HostWithCancel "Deseja REMOVER a configuração atual do Git? (S/N)"
			if ($restoreGitConfig -eq 'S' -or $restoreGitConfig -eq 's') {
				Remove-GitConfiguration
				Write-Host "Configuração do Git removida com sucesso." -ForegroundColor Green
				Remove-RegistryValue -Name "gitUserName"
				Remove-RegistryValue -Name "gitUserEmail"
			} else {
				Write-Host "Mantendo a configuração atual do Git." -ForegroundColor Green
			}
		} else {
			Write-Host "A configuração do Git não está definida no registro." -ForegroundColor Green
		}
	} catch {
		Show-ErrorMessage "Falha ao verificar ou restaurar a configuração do Git."
		exit
	}

	try {
		$gitVersion = git --version 2>&1
		if ($LASTEXITCODE -eq 0) {
			$removeGit = Read-HostWithCancel "Deseja REMOVER o Git $gitVersion? (S/N)"
			if ($removeGit -eq 'S' -or $removeGit -eq 's') {
				Write-Host "Desinstalando Git..." -ForegroundColor Yellow
				if ($IsWindows) {
					# Desinstalar Git usando Winget no Windows
					winget uninstall --id Git.Git -e
				} elseif ($IsMacOS) {
					# Desinstalar Git usando Homebrew no macOS
					brew uninstall git
				} elseif ($IsLinux) {
					# Desinstalar Git usando apt-get em sistemas baseados em Debian/Ubuntu
					sudo apt-get remove --purge git
				} else {
					Show-ErrorMessage "Sistema operacional não suportado."
					exit
				}
				Write-Host "Git desinstalado com sucesso." -ForegroundColor Green
			}
		} else {
			Write-Host "Git não está instalado." -ForegroundColor Yellow
		}
	} catch {
		Show-ErrorMessage "Falha ao desinstalar Git."
		exit
	}

	try {
		$funcVersion = func --version 2>&1
		if ($LASTEXITCODE -eq 0) {
			$removeAzFuncCore = Read-HostWithCancel "Deseja REMOVER o Azure Functions Core Tools $funcVersion? (S/N)"
			if ($removeAzFuncCore -eq 'S' -or $removeAzFuncCore -eq 's') {
				Write-Host "Desinstalando Azure Functions Core Tools..." -ForegroundColor Yellow

				if ($IsWindows) {
					# Desinstalar Azure Functions Core Tools usando Winget no Windows
					winget uninstall --id Microsoft.AzureFunctionsCoreTools -e
				} elseif ($IsMacOS) {
					# Desinstalar Azure Functions Core Tools usando Homebrew no macOS
					brew uninstall azure-functions-core-tools
				} elseif ($IsLinux) {
					# Desinstalar Azure Functions Core Tools em sistemas baseados em Debian/Ubuntu
					sudo apt-get remove --purge azure-functions-core-tools-3
				} else {
					Show-ErrorMessage "Sistema operacional não suportado."
					exit
				}

				Write-Host "Azure Functions Core Tools desinstalado com sucesso." -ForegroundColor Green
			}
		} else {
			Write-Host "Azure Functions Core Tools não está instalado." -ForegroundColor Yellow
		}
	} catch {
		Show-ErrorMessage "Falha ao desinstalar Azure Functions Core Tools."
		exit
	}

	try {
		$azureCliInfo = az --version 2>&1
		if ($LASTEXITCODE -eq 0) {
			# A Azure CLI está instalada
			Write-Host "Azure CLI já está instalada." -ForegroundColor Green
			Write-Host "Desinstalando Azure CLI..." -ForegroundColor Yellow

			if ($IsWindows) {
				# Desinstalar Azure CLI usando Winget no Windows
				winget uninstall --id Microsoft.AzureCLI -e
			} elseif ($IsMacOS) {
				# Desinstalar Azure CLI usando Homebrew no macOS
				brew uninstall azure-cli
			} elseif ($IsLinux) {
				# Desinstalar Azure CLI em sistemas baseados em Debian/Ubuntu
				sudo apt-get remove --purge azure-cli
			} else {
				Show-ErrorMessage "Sistema operacional não suportado."
				exit
			}

			Write-Host "Azure CLI desinstalada com sucesso." -ForegroundColor Green
		} else {
			# A Azure CLI não está instalada
			Write-Host "Azure CLI não está instalada." -ForegroundColor Yellow
		}
	} catch {
		Show-ErrorMessage "Falha ao desinstalar Azure CLI."
		exit
	}

} catch {
	Show-ErrorMessage -ErrorMessage $_.Exception.Message -ErrorLine $_.InvocationInfo.ScriptLineNumber
	exit
}

# No final do script, perguntar se deve limpar o progresso
Write-Host "Desinstalações concluídas." -ForegroundColor Green

Ask-Clear-ScriptProgress