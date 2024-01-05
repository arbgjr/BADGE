# Script de Configuração e Instalação para o Projeto BADGE
Clear-Host
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$timestamp = Get-Date -Format "yyyyMMdd.HHmm"
$version = "v$timestamp"
Write-Host "Script version: $version" -ForegroundColor Magenta

# Verificar se o script está sendo executado com privilégios de administrador
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
	Write-Host "Este script precisa ser executado com privilégios de administrador." -ForegroundColor Red
	Write-Host "Reinicie o PowerShell como Administrador e tente novamente." -ForegroundColor Yellow
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

enum ScriptSteps {
	NotStarted
	AzureCLIInstalled
	FunctionCoreToolsAppInstalled
	AzureFunctionsCoreToolsChecked
	GitInstalled
	GitConfigured
	RepoCloned
	FuncInitialized
	AzureCLILoginExecuted
	SetSubsTenantCreated
	RGCreated
	StorageCreated
	AzFuncCreated
	AzFuncPublished
	AzSQLCreated
	AzSQLDatabaseCreated
	AzAppConfigCreated
	AzFuncEnvCreated
	AzAppConfigEnvCreated
}

Function NumLastStep {
	param ([int]$step)
	return [array]::IndexOf([Enum]::GetValues([ScriptSteps]), [ScriptSteps]$step) + 1
}

$lastStep = [ScriptSteps]::NotStarted
$intLastStep = NumLastStep $lastStep

$registryPath = "HKCU:\Software\$REPO_NAME\Install"
$currentPath = Get-Location

Function Save-ScriptProgress {
	param ([int]$step)
	try {
		Set-RegistryValue -Name "LastStep" -Value ([int]$step)
		$lastStep = Get-LastCompletedStep
		$intLastStep = NumLastStep $lastStep
	} catch {
		Write-Host "Erro ao salvar o progresso no registro. Certifique-se de que o script está sendo executado com privilégios de administrador." -ForegroundColor Red
		exit
	}
}

Function Get-LastCompletedStep {
	try {
		$lastStepValue = Get-RegistryValue -Name "LastStep"
		if ($lastStepValue -ne $null) {
			return [ScriptSteps]$lastStepValue
		}
	} catch {
		Write-Host "Erro ao ler o progresso do registro. Certifique-se de que o script está sendo executado com privilégios de administrador." -ForegroundColor Red
		exit
	}
	return [ScriptSteps]::NotStarted
}

function Clear-ScriptProgress {

	# Verificar se o caminho existe antes de tentar removê-lo
	if (Test-Path -Path $registryPath) {
		Remove-Item -Path $registryPath -Force
		Write-Host "Progresso do script removido com sucesso." -ForegroundColor Green
	} else {
		Write-Host "Nenhum progresso do script encontrado para remover." -ForegroundColor Yellow
	}
}

Function Read-HostWithCancel {
	param (
		[string]$prompt,
		[string]$registryValueName = $null,
		[string]$defaultValue = ""
	)

	# Defina uma variável para controlar se a função deve continuar ou sair
	$continueLoop = $true

	while ($continueLoop) {
		if (-not [string]::IsNullOrWhiteSpace($defaultValue)) {
			$fullPrompt = "$prompt (ou 'cancelar' para sair) [default: $defaultValue]: "
		} else {
			$fullPrompt = "$prompt (ou 'cancelar' para sair): "
		}

		# Verificar e obter o valor salvo apenas se o nome da chave do registro for fornecido
		if ($registryValueName) {
			$savedInput = Get-RegistryValue -Name $registryValueName
			if ($savedInput) {
				Write-Host $prompt
				$confirmation = Read-Host "Usar valor salvo '$savedInput'? (S/N, 'cancelar' para sair)"
				if ($confirmation -eq 'S' -or $confirmation -eq 's') {
					return $savedInput
				} elseif ($confirmation -eq 'cancelar') {
					Write-Host "Operação cancelada pelo usuário no passo $lastStep." -ForegroundColor Red
					Ask-Clear-ScriptProgress
					exit
				}
			}
		}

		Write-Host $fullPrompt -NoNewline
		$input = Read-Host
		if ($input -eq 'cancelar') {
			Write-Host "Operação cancelada pelo usuário no passo $lastStep." -ForegroundColor Red
			Ask-Clear-ScriptProgress
			exit
		} elseif ([string]::IsNullOrWhiteSpace($input)) {
			$input = $defaultValue
			Write-Host "Valor definido: $input" -ForegroundColor Green
		}

		# Salvar o valor no registro, seja ele digitado pelo usuário ou o valor padrão
		if ($registryValueName -and -not [string]::IsNullOrWhiteSpace($input)) {
			Set-RegistryValue -Name $registryValueName -Value $input
		}
		
		$continueLoop = $false
	}

	return $input
}

Function Ask-Clear-ScriptProgress {
	try {
		$clearProgress = Read-HostWithCancel "Deseja limpar o progresso do script no registro? Isso pode causar problemas se o script for executado novamente. (S/N)"
		if ($clearProgress -eq 'S' -or $clearProgress -eq 's') {
			try {
				Clear-ScriptProgress
				Write-Host "Progresso do script limpo com sucesso." -ForegroundColor Green
			} catch {
				Write-Host "Falha ao limpar o progresso do script." -ForegroundColor Red
			}
		} else {
			Write-Host "O progresso do script foi mantido." -ForegroundColor Yellow
		}
	} catch {
		Write-Host "Erro ao limpar o progresso do registro. Certifique-se de que o script está sendo executado com privilégios de administrador." -ForegroundColor Red
		exit
	}
}

Function Set-RegistryValue {
	param (
		[string]$Name,
		[string]$Value
	)
	try {
		# Verificar se o caminho no registro existe, se não, criá-lo
		if (-not (Test-Path $registryPath)) {
			New-Item -Path $registryPath -Force | Out-Null
		}

		# Definir a propriedade no registro
		Set-ItemProperty -Path $registryPath -Name $Name -Value $Value
	} catch {
		Write-Host "Erro ao salvar no registro: $_" -ForegroundColor Red
	}
}

Function Get-RegistryValue {
	param (
		[string]$Name
	)
	try {
		if (Test-Path $registryPath) {
			return (Get-ItemProperty -Path $registryPath -Name $Name -ErrorAction SilentlyContinue).$Name
		}
	} catch {
		Write-Host "Erro ao ler do registro. Certifique-se de que o script está sendo executado com privilégios de administrador." -ForegroundColor Red
	}
	return $null
}

function Show-ErrorMessage {
	param (
		[string]$ErrorMessage,
		[int]$ErrorLine
	)

	Write-Host "ERRO na linha $ErrorLine : $ErrorMessage" -ForegroundColor Red
}

Function Set-AzureAccount {
	param (
		[string]$Mensagem
	)

	while ($true) {
		Write-Host $Mensagem -ForegroundColor Yellow
		try {
			$azLoginResult = az login
			$errorCode = $LASTEXITCODE
			if ($errorCode -eq 0) {
				# O código de retorno zero indica que o login foi bem-sucedido
				$azAccountJson = az account show --output json | Out-String
				if ([string]::IsNullOrWhiteSpace($azAccountJson)) {
					Write-Host "Erro ao obter informações da conta Azure." -ForegroundColor Red
					exit
				}

				try {
					$azAccount = ConvertFrom-Json $azAccountJson
					$usuario = $azAccount.user.name
					Write-Host "Logado na Azure CLI com a conta: $usuario" -ForegroundColor Green
				} catch {
					Write-Host "Erro ao analisar o JSON da conta Azure." -ForegroundColor Red
					$usuario = ""
				}

				$confirmation = Read-HostWithCancel "As informações da conta estão corretas? (S/N)"
				if ($confirmation -eq 'S' -or $confirmation -eq 's') {
					break
				}
			} else {
				Write-Host "Falha ao fazer login na Azure CLI: $errorCode" -ForegroundColor Red
				Ask-Clear-ScriptProgress
				exit
			}
		} catch {
			Write-Host "Erro inesperado ao fazer login na Azure CLI." -ForegroundColor Red
			exit
		}
	}
}

Function Set-AzureSubscription {
	param (
		[string]$Mensagem
	)
	while ($true) {
		Write-Host $Mensagem -ForegroundColor Yellow
		az account list --output table

		$subscriptionNameOrId = Read-HostWithCancel "Insira o nome ou ID da assinatura" "subscriptionNameOrId"
		az account set --subscription $subscriptionNameOrId

		az account show
		$confirmation = Read-HostWithCancel "As informações da assinatura estão corretas? (S/N)"
		if ($confirmation -eq 'S' -or $confirmation -eq 's') {
			break
		}
	}
}

Function Set-GitConfiguration {
	$userName = Read-HostWithCancel "Insira o seu nome" "userName"
	git config --global user.name $userName

	$userEmail = Read-HostWithCancel "Insira o seu email" "userEmail"
	git config --global user.email $userEmail
}

Function Clone-GitRepository {
	param (
		[string]$path,
		[string]$url
	)
	git clone $url
	Set-Location -Path $path
	Write-Host "Repositório '$url' clonado com sucesso em '$path'." -ForegroundColor Green
}

Function Publish-AzureFunction {
	$repoPath = Get-RegistryValue -Name "repoPath"
	Set-Location -Path $repoPath
	func azure functionapp publish $functionAppName
	Write-Host "Azure Function '$functionAppName' publicada com sucesso." -ForegroundColor Green
}

Function Update-EnvFuncSetting {
	param (
		[string]$appName,
		[string]$resourceGroup,
		[string]$settingName
	)
 
 	$settingValue = Read-HostWithCancel "Insira o valor da sua variável de ambiente '$settingName':" "settingValue"
	az functionapp config appsettings set --name $functionAppName --resource-group $resourceGroupName --settings $settingName=$settingValue
	Write-Host "Configuração: '$settingName' atualizada com sucesso na Azure Function '$functionAppName' com o valor '$settingValue'." -ForegroundColor Green
}

function Get-SqlServerName {
    do {
        $serverName = Read-HostWithCancel "12 - Insira o nome do servidor SQL" "serverName"
        if ([string]::IsNullOrWhiteSpace($serverName)) {
            Write-Host "O nome do servidor SQL é obrigatório." -ForegroundColor Green
        } elseif (-not ($serverName -match '^[a-z0-9-]+$') -or ($serverName -match '^-$|-$')) {
            Write-Host "O nome do servidor SQL deve conter apenas letras minúsculas 'a'-'z', números 0-9 e hífen (-). O hífen não pode ser o único caractere." -ForegroundColor Red
        }
    } while ([string]::IsNullOrWhiteSpace($serverName) -or (-not ($serverName -match '^[a-z0-9-]+$') -or ($serverName -match '^-$|-$')))

    return $serverName
}

# Função para gerar uma senha complexa e aleatória
function Generate-RandomPassword {
    param (
        [int]$length = 16,
        [bool]$includeNumbers = $true,
        [bool]$includeLowercase = $true,
        [bool]$includeUppercase = $true,
        [bool]$beginWithLetter = $true,
        [string]$includeSymbols = "!@#$%^&*()_-+=<>?/[]{}|"
    )

    $validChars = @()

    if ($includeUppercase) { $validChars += 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' }
    if ($includeLowercase) { $validChars += 'abcdefghijklmnopqrstuvwxyz' }
    if ($includeNumbers) { $validChars += '0123456789' }
    if ($includeSpecialChars) { $validChars += '!@#$%^&*()_-+=<>?/[]{}|' }

    if ($validChars.Count -eq 0) {
        Write-Host "Pelo menos uma categoria de caracteres deve ser selecionada." -ForegroundColor Red
        return $null
    }

    $password = ""

    for ($i = 0; $i -lt $length; $i++) {
        $randomCategoryIndex = Get-Random -Minimum 0 -Maximum $validChars.Count
        $randomCategory = $validChars[$randomCategoryIndex]
        $randomCharIndex = Get-Random -Minimum 0 -Maximum $randomCategory.Length
        $randomChar = $randomCategory[$randomCharIndex]
        $password += $randomChar
    }

    return $password
}

function Get-SqlDatabaseName {
    param (
        [string]$repoName
    )

    do {
        $databaseName = Read-HostWithCancel "13 - Insira o nome do banco de dados SQL" "databaseName" $repoName
        if ([string]::IsNullOrWhiteSpace($databaseName)) {
            Write-Host "O nome do banco de dados SQL é obrigatório." -ForegroundColor Red
        }
    } while ([string]::IsNullOrWhiteSpace($databaseName))

    return $databaseName
}

function Get-ValidInstallerLink {
    param (
        [string]$installScriptUrl
    )

    $validLink = $false
    while (-not $validLink) {
        $installScriptUrl = Read-HostWithCancel "Insira o link para o instalador desejado" "installScriptUrl"

        try {
            Invoke-WebRequest -Uri $installScriptUrl -OutFile "Installer.exe" -UseBasicParsing
            $validLink = $true
        } catch {
            Write-Host "O link fornecido não é válido. Certifique-se de que é um link direto para o instalador." -ForegroundColor Red
            $validLink = $false
        }
    }

    return $installScriptUrl
}

function Get-AzAppConfigName {
    do {
        $azAppConfigName = Read-HostWithCancel "Digite o nome do Azure App Configuration" "azAppConfigName"
        if ([string]::IsNullOrWhiteSpace($azAppConfigName)) {
            Write-Host "O nome do Azure App Configuration é obrigatório." -ForegroundColor Green
        } elseif (-not ($azAppConfigName -match '^[a-z0-9-]+$') -or ($azAppConfigName -match '^-$|-$')) {
            Write-Host "O nome do Azure App Configuration deve conter apenas letras minúsculas 'a'-'z', números 0-9 e hífen (-). O hífen não pode ser o único caractere." -ForegroundColor Red
        }
    } while ([string]::IsNullOrWhiteSpace($azAppConfigName) -or (-not ($azAppConfigName -match '^[a-z0-9-]+$') -or ($azAppConfigName -match '^-$|-$')))

    return $azAppConfigName
}


function Set-AppConfigKeyValue {
    param (
        [string]$azAppConfigName,
        [string]$settingName,
        [string]$settingValue,
        [string]$tag
    )

    if ([string]::IsNullOrWhiteSpace($settingName)) {
        Write-Host "O nome da configuração é obrigatório." -ForegroundColor Red
        return
    }

    if ([string]::IsNullOrWhiteSpace($settingValue)) {
        $settingValue = $null
    }

    # Defina o valor padrão do Content-Type como texto simples
    $contentType = "text/plain;charset=utf-8"

    # Avalie o Content-Type com base na extensão do nome da chave
    if ($settingName -match "\.(json|JSON)$") {
        $contentType = "application/json;charset=utf-8"
    } elseif ($settingName -match "\.(xml|XML)$") {
        $contentType = "application/xml;charset=utf-8"
    }

    # Defina o content-type com base na avaliação acima
    az appconfig kv set --name $azAppConfigName --key $settingName --value $settingValue --yes --label $tag --content-type $contentType
}

$confirmRun = Read-HostWithCancel "Deseja efetuar a configuração do ambiente de forma automatizada? (S/N)"
if ($confirmRun -eq 'N' -or $confirmRun -eq 'n') {
	break
}

# Recupera de onde o script parou a execução
$lastStep = Get-LastCompletedStep

try {
	if ($lastStep -le [ScriptSteps]::NotStarted) {
		# Instalar a Azure CLI
		try {
			# Para a Azure CLI, capturando a saída e formatando
			$azureCliInfo = az --version
			Write-Host "1 - Azure CLI já está instalada." -ForegroundColor Green
			Write-Host "Informações da Azure CLI:" -ForegroundColor Green
			
			foreach ($line in $azureCliInfo) {
				$formattedLine = "`t" + ($line -replace '\s+', ' ')
				Write-Host $formattedLine -ForegroundColor Green
			}
		} catch {
			try {
				Write-Host "1 - Instalando Azure CLI..." -ForegroundColor Yellow
				if ($IsWindows) {
					# Preferir Winget no Windows
					winget install --id Microsoft.AzureCLI -e --source winget
				} elseif ($IsMacOS) {
					# Usar Homebrew no macOS
					brew update
					if ($?) { brew install azure-cli }

				} elseif ($IsLinux) {
					# Usar apt-get para sistemas baseados em Debian/Ubuntu
					bash -c "curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
				} else {
					Show-ErrorMessage "Sistema operacional não suportado."
					exit
				}
			} catch {
				Show-ErrorMessage "Falha ao instalar Azure CLI."
				exit
			}
		}
		Save-ScriptProgress -step ([int][ScriptSteps]::AzureCLIInstalled)
	} else {
		$azureCliInfo = az --version
		Write-Host "1 - Azure CLI já está instalada." -ForegroundColor Green
		foreach ($line in $azureCliInfo) {
			$formattedLine = "`t" + ($line -replace '\s+', ' ')
			Write-Host $formattedLine -ForegroundColor Green
		}
	}

	if ($lastStep -le [ScriptSteps]::AzureCLIInstalled) {
		# Instalar o Azure Functions Core Tools
		try {
			$funcVersion = func --version
			Write-Host "2 - Azure Functions Core Tools já está instalado. Versão: $funcVersion" -ForegroundColor Green
		} catch {
			try {
				Write-Host "2 - Instalando Azure Functions Core Tools..." -ForegroundColor Yellow
				if ($IsWindows) {
					# Preferir Winget no Windows
					winget install --id Microsoft.AzureFunctionsCoreTools -e --source winget
				} elseif ($IsMacOS) {
					# Usar Homebrew no macOS
					brew tap azure/functions
					if ($?) { brew install azure-functions-core-tools }
				} elseif ($IsLinux) {
					# Usar apt-get para sistemas baseados em Debian/Ubuntu
					bash -c "wget -q https://packages.microsoft.com/config/ubuntu/20.04/packages-microsoft-prod.deb && sudo dpkg -i packages-microsoft-prod.deb && sudo apt-get update && sudo apt-get install azure-functions-core-tools-3"
				} else {
					Show-ErrorMessage "Sistema operacional não suportado."
					exit
				}
				$funcVersion = func --version
			} catch {
				Show-ErrorMessage "Falha ao instalar Azure Functions Core Tools."
				exit
			}
		}
		Save-ScriptProgress -step ([int][ScriptSteps]::FunctionCoreToolsAppInstalled)
	} else {
		$funcVersion = func --version
		Write-Host "2 - Azure Functions Core Tools já está instalado. Versão: $funcVersion" -ForegroundColor Green
	}

	if ($lastStep -le [ScriptSteps]::FunctionCoreToolsAppInstalled) {
		# Instalar o Git
		 try {
			$gitVersion = git --version
			Write-Host "3 - Git já está instalado. Versão: $gitVersion" -ForegroundColor Green
		} catch {
			try {
				Write-Host "3 - Instalando Git..." -ForegroundColor Yellow
				if ($IsWindows) {
					# Preferir Winget no Windows
					winget install --id Git.Git -e --source winget
				} elseif ($IsMacOS) {
					# Usar Homebrew no macOS
					brew install git
				} elseif ($IsLinux) {
					# Usar apt-get para sistemas baseados em Debian/Ubuntu
					sudo apt-get update
					if ($?) { sudo apt-get install git }
				} else {
					Show-ErrorMessage "Sistema operacional não suportado."
					exit
				}
			} catch {
				Show-ErrorMessage "Falha ao instalar Git."
				exit
			}
		}
		Save-ScriptProgress -step ([int][ScriptSteps]::GitInstalled)
	} else {
		$gitVersion = git --version
		Write-Host "3 - Git já está instalado. Versão: $gitVersion" -ForegroundColor Green
	}

	if ($lastStep -le [ScriptSteps]::GitInstalled) {
		try {
			$gitUserName = git config --global user.name
			$gitUserEmail = git config --global user.email

			if ($gitUserName -and $gitUserEmail) {
				Write-Host "4 - Configuração atual do Git: Nome de usuário: '$gitUserName', Email: '$gitUserEmail'" -ForegroundColor Green
				$changeGitConfig = Read-HostWithCancel "Deseja alterar a configuração do Git? (S/N)"
				if ($changeGitConfig -ne 'S' -and $changeGitConfig -ne 's') {
					Write-Host "Continuando com a configuração atual do Git." -ForegroundColor Green
				} else {
					Set-GitConfiguration
				}
			} else {
				Set-GitConfiguration
			}
			Set-RegistryValue -Name "gitUserName" -Value $gitUserName
			Set-RegistryValue -Name "gitUserEmail" -Value $gitUserEmail
		} catch {
			Show-ErrorMessage "Falha ao configurar Git."
			exit
		}
		Save-ScriptProgress -step ([int][ScriptSteps]::GitConfigured)
	} else {
		$gitUserName = Get-RegistryValue -Name "gitUserName"
		$gitUserEmail = Get-RegistryValue -Name "gitUserEmail"
		Write-Host "4 - Configuração atual do Git: Nome de usuário: '$gitUserName', Email: '$gitUserEmail'" -ForegroundColor Green
	}

	if ($lastStep -le [ScriptSteps]::GitConfigured) {
		try {
			$repoPath = Read-HostWithCancel "5 - Insira o caminho para clonar o repositório" "repoPath" $currentPath
			$repoUrl = Read-HostWithCancel "Insira a URL do repositório: " "repoUrl" $GITHUB_REPO
			$fullRepoPath = Join-Path $repoPath $REPO_NAME
			Set-RegistryValue -Name "repoPath" -Value $fullRepoPath
			
			if (Test-Path $fullRepoPath) {
				Write-Host "O repositório '$repoUrl' já existe em '$fullRepoPath'." -ForegroundColor Green
				$cloneAgain = Read-HostWithCancel "Deseja clonar o repositório novamente? (S/N)"
				if ($cloneAgain -eq 'S' -or $cloneAgain -eq 's') {
					Remove-Item -Recurse -Force $fullRepoPath
					Clone-GitRepository $fullRepoPath $repoUrl
				} else {
					Write-Host "Usando o repositório existente." -ForegroundColor Green
				}
			} else {
				Clone-GitRepository $fullRepoPath $repoUrl
			}
		} catch {
			Show-ErrorMessage "Falha ao clonar o repositório."
			exit
		}
		Save-ScriptProgress -step ([int][ScriptSteps]::RepoCloned)
	} else {
		$url = Get-RegistryValue -Name "repoUrl"
		$path = Get-RegistryValue -Name "repoPath"
		Write-Host "5 - Repositório '$url' clonado em '$path'." -ForegroundColor Green
	}

	if ($lastStep -le [ScriptSteps]::RepoCloned) {
		Write-Host "6 - Verificando se a função já foi inicializada em disco..." -ForegroundColor Yellow

		# Verifique se o arquivo 'host.json' existe no diretório atual
		if (Test-Path -Path "host.json") {
			Write-Host "'host.json' já existe. O comando 'func init' já foi executado." -ForegroundColor Green
		} else {
			# Execute o comando 'func init' se 'host.json' não existe
			Write-Host "Executando 'func init'..." -ForegroundColor Yellow
			func init . --worker-runtime python
		}

		# Verifique se o diretório da função existe
		if (Test-Path -Path $REPO_NAME -PathType Container) {
			Write-Host "O diretório '$REPO_NAME' já existe. O comando 'func new' já foi executado." -ForegroundColor Green
		} else {
			# Execute o comando 'func new' se a pasta não existe
			Write-Host "Executando 'func new'..." -ForegroundColor Yellow
			func new --name $REPO_NAME --template "HttpTrigger"
		}
		Save-ScriptProgress -step ([int][ScriptSteps]::FuncInitialized)
	} else {
		Write-Host "6 - A função já foi inicializada em disco..." -ForegroundColor Yellow
	}

	if ($lastStep -le [ScriptSteps]::FuncInitialized) {
		$azAccountJson = az account show --output json | Out-String
		if (-not $azAccountJson -or $azAccountJson -eq "") {
			Write-Host "Não está logado." -ForegroundColor Green
			$userName = ""
		} else {
			try {
				$azAccount = ConvertFrom-Json $azAccountJson
				$userName = $azAccount.user.name
				Write-Host "7 - Já está logado na Azure CLI com a conta: $userName" -ForegroundColor Green
				$changeAccount = Read-HostWithCancel "Deseja CONTINUAR com a conta atual? (S/N)"
				if ($changeAccount -eq 'S' -and $changeAccount -eq 's') {
					Write-Host "Continuando com a conta atual." -ForegroundColor Green
				} else {
					Set-AzureAccount "Definindo a conta correta..."
				}
			} catch {
				Write-Host "Erro ao analisar o JSON da conta Azure." -ForegroundColor Red
				$userName = ""
			}
		}

		if ([string]::IsNullOrWhiteSpace($userName)) {
			Set-AzureAccount "7 - Fazendo login na Azure CLI..."
		}
		
		Set-RegistryValue -Name "userName" -Value $userName
		
		Save-ScriptProgress -step ([int][ScriptSteps]::AzureCLILoginExecuted)
	} else {
		$userName = Get-RegistryValue -Name "userName"
		Write-Host "7 - Já está logado na Azure CLI com a conta: $userName" -ForegroundColor Green
	}

	if ($lastStep -le [ScriptSteps]::AzureCLILoginExecuted) {
		$currentSubscriptionJson = az account show --query "{name:name, id:id}" --output json | Out-String
		if (-not $currentSubscriptionJson -or $currentSubscriptionJson -eq "") {
			Write-Host "Assinatura não definida" -ForegroundColor Green
			$currentSubscription = ""
		} else {
			try {
				$currentSubscription = ConvertFrom-Json $currentSubscriptionJson
				$subscriptionName = $currentSubscription.name
				$subscriptionId = $currentSubscription.id
				Write-Host "8 - Assinatura atual: $subscriptionName (ID: $subscriptionId)" -ForegroundColor Green
				$changeSubscription = Read-HostWithCancel "Deseja CONTINUAR com a assinatura atual? (S/N)"
				if ($changeSubscription -eq 'S' -and $changeSubscription -eq 's') {
					Write-Host "Continuando com a assinatura atual." -ForegroundColor Green
				} else {
					Set-AzureSubscription "Definindo a assinatura e o diretório corretos..."
				}
			} catch {
				Write-Host "Erro ao analisar o JSON da assinatura atual." -ForegroundColor Red
				exit
			}
		}
		
		if ([string]::IsNullOrWhiteSpace($currentSubscription)) {
			try {
				Set-AzureSubscription "Definindo a assinatura e o diretório..."
			} catch {
				if ($_ -match "User cancelled the Accounts Control Operation") {
					Write-Host "Definição de Assinatura cancelada pelo usuário. A execução do script foi cancelada." -ForegroundColor Red
					exit
				} else {
					Show-ErrorMessage "Falha ao definir a assinatura na Azure CLI."
					exit
				}
			}
		}
		
		Set-RegistryValue -Name "subscriptionName" -Value $currentSubscription.name
		Set-RegistryValue -Name "subscriptionId" -Value $currentSubscription.id
		
		Save-ScriptProgress -step ([int][ScriptSteps]::SetSubsTenantCreated)
	} else{
		$subscriptionName = Get-RegistryValue -Name "subscriptionName"
		$subscriptionId = Get-RegistryValue -Name "subscriptionId"
		Write-Host "8 - Assinatura atual: $subscriptionName (ID: $subscriptionId)" -ForegroundColor Green
	}
	
	if ($lastStep -le [ScriptSteps]::SetSubsTenantCreated) {
		# Criar um Novo Grupo de Recursos
		$resourceGroupName = Read-HostWithCancel "9 - Insira o nome do grupo de recursos" "resourceGroupName"
		$existingResourceGroup = az group exists --name $resourceGroupName

		while ($existingResourceGroup -eq 'true') {
			$useExistingRG = Read-HostWithCancel "O grupo de recursos '$resourceGroupName' já existe. Deseja utilizá-lo? (S/N)"
			if ($useExistingRG -eq 'S' -or $useExistingRG -eq 's') {
				$location = az group show --name $resourceGroupName --query location -o tsv
				Write-Host "Usando o grupo de recursos '$resourceGroupName' existente, localizado em '$location'." -ForegroundColor Green
				break
			} else {
				$resourceGroupName = Read-HostWithCancel "Insira um novo nome para o grupo de recursos" "resourceGroupName"
				$existingResourceGroup = az group exists --name $resourceGroupName
			}
		}

		if ($existingResourceGroup -eq 'false') {
			try {
				# Obter a lista de localizações disponíveis
				$locations = az account list-locations --query "[].name" | ConvertFrom-Json

				while ($true) {
					$location = Read-HostWithCancel "Insira a localização (ex: eastus2)" "location"

					# Verificar se a localização é válida
					if ($locations -contains $location) {
						# Criar o grupo de recursos se a localização for válida
						az group create --name $resourceGroupName --location $location
						Write-Host "Criado o novo grupo de recursos '$resourceGroupName' localizado em '$location'." -ForegroundColor Green
						break
					} else {
						Write-Host "Localização inválida. Por favor, insira uma localização válida." -ForegroundColor Red
					}
				}
			} catch {
				Show-ErrorMessage "Falha ao criar o grupo de recursos."
				exit
			}
		}
		
		Set-RegistryValue -Name "location" -Value $location
		
		Save-ScriptProgress -step ([int][ScriptSteps]::RGCreated)
	} else {
		$resourceGroupName = Get-RegistryValue -Name "resourceGroupName"
		$location = Get-RegistryValue -Name "location"
		Write-Host "9 - Usando o grupo de recursos '$resourceGroupName' existente, localizado em '$location'." -ForegroundColor Green
	}

	if ($lastStep -le [ScriptSteps]::RGCreated) {
		# Criar uma conta de armazenamento para Azure Functions
		$storageAccountName = Read-HostWithCancel "10 - Insira o nome da conta de armazenamento" "storageAccountName"
		$existingStorageAccount = az storage account check-name --name $storageAccountName --query 'nameAvailable'

		while ($existingStorageAccount -eq 'false') {
			$useExistingStorage = Read-HostWithCancel "A conta de armazenamento '$storageAccountName' já existe. Deseja utilizá-la? (S/N)"
			if ($useExistingStorage -eq 'S' -or $useExistingStorage -eq 's') {
				Write-Host "Usando a conta de armazenamento existente: '$storageAccountName'." -ForegroundColor Green
				break
			} else {
				$storageAccountName = Read-Host "Insira um novo nome para a conta de armazenamento" "storageAccountName"
				$existingStorageAccount = az storage account check-name --name $storageAccountName --query 'nameAvailable'
			}
		}

		if ($existingStorageAccount -eq 'true') {
			try {
				az storage account create --name $storageAccountName --location $location --resource-group $resourceGroupName --sku Standard_LRS
				Write-Host "Conta de armazenamento criada: '$storageAccountName'." -ForegroundColor Green
			} catch {
				Show-ErrorMessage "Falha ao criar a conta de armazenamento."
				exit
			}
		}
		Save-ScriptProgress -step ([int][ScriptSteps]::StorageCreated)
	} else {
		$storageAccountName = Get-RegistryValue -Name "storageAccountName"
		Write-Host "10 - Usando a conta de armazenamento existente: '$storageAccountName'." -ForegroundColor Green
	}

	if ($lastStep -le [ScriptSteps]::StorageCreated) {
		# Criar uma Azure Function
		$functionAppName = Read-HostWithCancel "11 - Insira o nome da sua Azure Function" "functionAppName"
		$existingFunctionApp = az functionapp show --name $functionAppName --query 'state' --resource-group $resourceGroupName 2>&1

		while ($existingFunctionApp) {
			$useExistingFunctionApp = Read-HostWithCancel "A Azure Function '$functionAppName' já existe. Deseja utilizá-la? (S/N)"
			if ($useExistingFunctionApp -eq 'S' -or $useExistingFunctionApp -eq 's') {
				Write-Host "Usando a Azure Function existente: '$functionAppName'." -ForegroundColor Green
				break
			} else {
				$functionAppName = Read-HostWithCancel "Insira um novo nome para a Azure Function" "functionAppName"
				$existingFunctionApp = az functionapp show --name $functionAppName --query 'state'
			}
		}

		if (-not $existingFunctionApp) {
			try {
				az functionapp create --consumption-plan-location $location --name $functionAppName --os-type Linux --resource-group $resourceGroupName --runtime python --storage-account $storageAccountName --functions-version 4
				Write-Host "Azure Function criada: '$functionAppName'." -ForegroundColor Green
			} catch {
				Show-ErrorMessage "Falha ao criar a Azure Function."
				exit
			}
		}
		Save-ScriptProgress -step ([int][ScriptSteps]::AzFuncCreated)
	} else {
		$functionAppName = Get-RegistryValue -Name "functionAppName"
		Write-Host "11 - Azure Function criada: '$functionAppName'." -ForegroundColor Green
	}

	if ($lastStep -le [ScriptSteps]::AzFuncCreated) {
		try {
			$functionAppInfo = az functionapp show --name $functionAppName  --resource-group $resourceGroupName --query "{state: state, defaultHostName: defaultHostName}" -o json | ConvertFrom-Json

			if ($functionAppInfo -and $functionAppInfo.state -eq "Running") {
				Write-Host "12 - A Azure Function '$functionAppName' já está publicada e em execução em: $($functionAppInfo.defaultHostName)" -ForegroundColor Green
				$publishAgain = Read-HostWithCancel "Deseja publicar a Azure Function novamente? (S/N)"
				if ($publishAgain -eq 'S' -or $publishAgain -eq 's') {
					Publish-AzureFunction
				} else {
					Write-Host "Usando a Azure Function publicada existente." -ForegroundColor Green
				}
			} else {
				Publish-AzureFunction
			}
			
			Set-RegistryValue -Name "defaultHostName" -Value $functionAppInfo.defaultHostName
			
		} catch {
			Show-ErrorMessage "Falha ao publicar a Azure Function."
			exit
		}
		Save-ScriptProgress -step ([int][ScriptSteps]::AzFuncPublished)
	} else {
		$defaultHostName = Get-RegistryValue -Name "defaultHostName"
		Write-Host "12 - Azure Function publicada e em execução em: '$defaultHostName'." -ForegroundColor Green
	}

	if ($lastStep -le [ScriptSteps]::AzFuncPublished) {
		# Criar um Azure SQL
		$serverName = Get-SqlServerName
		
		# Verificar se o servidor SQL existe
		try {
			$existingServer = az sql server show --name $serverName --resource-group $resourceGroupName --query 'name'
			while ($existingServer -eq $serverName) {
				$useExistingServer = Read-HostWithCancel "O Azure SQL '$serverName' já existe. Deseja utilizá-la? (S/N)"
				if ($useExistingServer -eq 'S' -or $useExistingServer -eq 's') {
					Write-Host "Usando o Azure SQL existente: '$serverName'." -ForegroundColor Green
					break
				} else {
					$serverName = Get-SqlServerName
					$existingServer = az sql server show --name $serverName --resource-group $resourceGroupName --query 'name'
				}
			}
			
			if ($existingServer -eq $serverName) {
				try {
					Write-Host "Criando o servidor SQL Azure '$serverName'..." -ForegroundColor Green
					$password = Generate-RandomPassword -length 16 -includeNumbers $true -includeLowercase $true -includeUppercase $true -beginWithLetter $true -includeSymbols "!@#$%^&*()_-"
					az sql server create --location $location --resource-group $resourceGroupName --name $serverName --admin-user $userName  --admin-password $password --enable-public-network false
					if ($LASTEXITCODE -eq 0) {
						Write-Host "Servidor SQL Azure '$serverName' criado com sucesso." -ForegroundColor Green
						Write-Host "Login: ' $userName ' Senha: " $password -ForegroundColor Green
						Write-Host "ANOTE OS DADOS ACIMA, POIS ELES NÃO SERÃO SALVOS EM LUGAR NENHUM!" -ForegroundColor Green
						Read-Host "Pressione Enter para continuar..." -ForegroundColor Green
					} else {
						Show-ErrorMessage "Falha ao criar o servidor SQL Azure."
						exit
					}
				} catch {
					Show-ErrorMessage "Falha ao criar o Azure SQL."
					exit
				}
			}
		} catch {
			Show-ErrorMessage "Erro ao verificar a existência do servidor SQL."
			exit
		}		
		Save-ScriptProgress -step ([int][ScriptSteps]::AzSQLCreated)
	} else {
		$serverName = Get-RegistryValue -Name "serverName"
		Write-Host "12 - Azure SQL criado em: '$serverName'." -ForegroundColor Green
	}

	if ($lastStep -le [ScriptSteps]::AzSQLCreated) {
		# Criar um Azure SQL Database
		$databaseName = Get-SqlDatabaseName
		
		try {
			# Verifique se o banco de dados já existe
			$existingDatabase = az sql db show --name $databaseName --server $serverName --resource-group $resourceGroupName --query 'name'
			while ($existingDatabase -eq $databaseName) {
				$useExistingDatabase = Read-HostWithCancel "O Banco de Dados SQL Azure '$databaseName' já existe. Deseja utilizá-la? (S/N)"
				if ($useExistingDatabase -eq 'S' -or $useExistingDatabase -eq 's') {
					Write-Host "Usando o Banco de Dados SQL Azure existente: '$databaseName'." -ForegroundColor Green
					break
				} else {
					$databaseName = Get-SqlDatabaseName
					$existingDatabase = az sql db show --name $databaseName --server $serverName --resource-group $resourceGroupName --query 'name'
				}
			}
			
			if ($existingDatabase -eq $databaseName) {
				try {
					Write-Host "Criando o Banco de Dados SQL Azure '$databaseName'..." -ForegroundColor Green
					az sql db create --name $databaseName --server $serverName --resource-group $resourceGroupName --edition Free --zone-redundant false --collation SQL_Latin1_General_CP1_CI_AS
					if ($LASTEXITCODE -eq 0) {
						Write-Host "Banco de Dados SQL Azure criado com sucesso." -ForegroundColor Green
					} else {
						Write-Host "Falha ao criar o Banco de Dados SQL Azure." -ForegroundColor Green
					}
				} catch {
					Show-ErrorMessage "Falha ao criar o Banco de Dados SQL Azure."
					exit
				}
			}
		} catch {
			Show-ErrorMessage "Falha ao criar o Banco de Dados SQL Azure."
			exit
		}		
		Save-ScriptProgress -step ([int][ScriptSteps]::AzSQLDatabaseCreated)
	} else {
		$databaseName = Get-RegistryValue -Name "databaseName"
		Write-Host "13 - Banco de Dados SQL Azure criado em: '$databaseName'." -ForegroundColor Green
	}

	if ($lastStep -le [ScriptSteps]::AzSQLDatabaseCreated) {
		# Loop para garantir que o nome do arquivo do script SQL seja informado e exista
		do {
			$scriptFileName = Read-HostWithCancel "Insira o nome do arquivo de script SQL a ser executado (inclua o caminho completo, se necessário)" "scriptFileName" ".\$REPO_NAME.sql"

			# Verificar se o nome do arquivo de script foi fornecido
			if ([string]::IsNullOrWhiteSpace($scriptFileName)) {
				Write-Host "O nome do arquivo de script SQL é obrigatório. Por favor, informe o nome do arquivo." -ForegroundColor Green
				continue
			}

			# Verificar se o arquivo de script existe
			if (-not (Test-Path $scriptFileName)) {
				Write-Host "O arquivo de script SQL '$scriptFileName' não existe. Verifique o caminho e o nome do arquivo." -ForegroundColor Green
			}
			else {
				break  # Sair do loop somente se o arquivo existir
			}
		} while ($true)

		$bdConnectionString = az sql db show-connection-string --server "$serverName" --client ado.net --output tsv

		# Verificar se a string de conexão foi obtida com sucesso
		if (-not [string]::IsNullOrWhiteSpace($bdConnectionString)) {
			Write-Host "String de conexão do banco de dados Azure SQL obtida com sucesso:" -ForegroundColor Green
			$bdConnectionString = $bdConnectionString -replace "<username>", "$username@$serverName" -replace "<password>", $password
		
			# Instruções para executar o script 
			Write-Host "Para executar o script '$scriptFileName' no banco de dados, siga estas etapas:" -ForegroundColor Cyan
			Write-Host "1. Abra uma ferramenta de gerenciamento de banco de dados compatível com SQL, como o SQL Server Management Studio (SSMS) ou o Azure Data Studio." -ForegroundColor Cyan
			Write-Host "   Você pode baixar o SQL Server Management Studio (SSMS) em: https://docs.microsoft.com/en-us/sql/ssms/download-sql-server-management-studio-ssms" -ForegroundColor Cyan
			Write-Host "   Ou o Azure Data Studio em: https://docs.microsoft.com/en-us/sql/azure-data-studio/download-azure-data-studio" -ForegroundColor Cyan
			Write-Host "2. Use a seguinte string de conexão abaixo para se conectar ao banco de dados." -ForegroundColor Cyan
			Write-Host $bdConnectionString -ForegroundColor Yellow
			Set-RegistryValue -Name "bdConnectionString" -Value $bdConnectionString
			Write-Host "3. Edite o arquivo '$scriptFileName' e troque <databasename> por '$databaseName'." -ForegroundColor Cyan
			Write-Host "4. Abra o arquivo '$scriptFileName' na ferramenta de gerenciamento de banco de dados." -ForegroundColor Cyan
			Write-Host "5. Execute o script '$scriptFileName' no contexto do banco de dados para criar as tabelas e realizar as ações necessárias." -ForegroundColor Cyan
		} else {
			Write-Host "Falha ao obter a string de conexão do banco de dados Azure SQL." -ForegroundColor Green
			Write-Host "Certifique-se de que o servidor e o banco de dados informados estão corretos e que o Azure CLI está configurado corretamente." -ForegroundColor Green
		}
	}

	if ($lastStep -le [ScriptSteps]::AzSQLDatabaseCreated) {
		try {
			# Lista de configurações existentes
			$existingSettings = az functionapp config appsettings list --name $functionAppName --resource-group $resourceGroupName | ConvertFrom-Json

			# Inicialize um array para armazenar as configurações a serem adicionadas
			$newSettings = @()

			while ($true) {
				$settingName = Read-HostWithCancel "Insira um nome para a sua variável de ambiente (ou pressione Enter para sair)"

				if ([string]::IsNullOrWhiteSpace($settingName)) {
					# O usuário pressionou Enter para sair do loop
					break
				}

				$existingSetting = $existingSettings | Where-Object { $_.name -eq $settingName }

				if ($existingSetting) {
					Write-Host "A configuração '$settingName' já existe com o valor: $($existingSetting.value)" -ForegroundColor Green
					$updateSetting = Read-HostWithCancel "Deseja atualizar o valor? (S/N)"
					if ($updateSetting -ne 'S' -and $updateSetting -ne 's') {
						Write-Host "Mantendo a configuração existente." -ForegroundColor Green
					} else {
						$settingValue = Read-HostWithCancel "Insira o novo valor para '$settingName'"
						$newSettings += @{name=$settingName; value=$settingValue}
					}
				} else {
					$settingValue = Read-HostWithCancel "Insira o valor para '$settingName'"
					$newSettings += @{name=$settingName; value=$settingValue}
				}
			}

			# Adicione as novas configurações
			foreach ($setting in $newSettings) {
				az functionapp config appsettings set --name $functionAppName --resource-group $resourceGroupName --settings $setting.name=$setting.value
				Write-Host "Configuração: '$($setting.name)' adicionada com sucesso à Azure Function '$functionAppName' com o valor '$($setting.value)'." -ForegroundColor Green
			}
			
			Set-RegistryValue -Name "AzFuncEnv" -Value $newSettings
			
		} catch {
			Show-ErrorMessage "Falha ao adicionar ou atualizar as variáveis de ambiente à Azure Function."
			exit
		}
		Save-ScriptProgress -step ([int][ScriptSteps]::AzFuncEnvCreated)
	}

	if ($lastStep -le [ScriptSteps]::AzFuncEnvCreated) {

		try {
			# Lista de configurações existentes no Azure App Configuration
			$existingSettings = az appconfig kv list --name $azAppConfigName --output json | ConvertFrom-Json

			# Inicialize um array para armazenar as configurações a serem adicionadas
			$newSettings = @(
				@{name='GpgKeyId'; value=$null},
				@{name='BadgeTemplateBase64'; value=$null},
				@{name='BadgeVerificationUrl'; value=$null},
				@{name='AzKVURI'; value=$AzKVURI},
				@{name='SqlConnectionString'; value=$bdConnectionString}
			)

			while ($true) {
				$settingName = Read-HostWithCancel "Insira o nome da configuração (ou pressione Enter para sair)"

				if ([string]::IsNullOrWhiteSpace($settingName)) {
					# O usuário pressionou Enter para sair do loop
					break
				}

				$existingSetting = $existingSettings | Where-Object { $_.key -eq $settingName }

				if ($existingSetting) {
					Write-Host "A configuração '$settingName' já existe com o valor: $($existingSetting.value)" -ForegroundColor Green
					$updateSetting = Read-HostWithCancel "Deseja atualizar o valor? (S/N)"
					if ($updateSetting -ne 'S' -and $updateSetting -ne 's') {
						Write-Host "Mantendo a configuração existente." -ForegroundColor Green
					} else {
						$settingValue = Read-HostWithCancel "Insira o novo valor para '$settingName'"
						$newSettings += @{name=$settingName; value=$settingValue}
					}
				} else {
					$settingValue = Read-HostWithCancel "Insira o valor para '$settingName'"
					$newSettings += @{name=$settingName; value=$settingValue}
				}
			}

			# Adicione as novas configurações
			foreach ($setting in $newSettings) {
				Set-AppConfigKeyValue -azAppConfigName $azAppConfigName -settingName $setting.name -settingValue $setting.value -tag $REPO_NAME
				Write-Host "Configuração: '$($setting.name)' adicionada com sucesso ao Azure App Configuration '$azAppConfigName' com o valor '$($setting.value)'." -ForegroundColor Green
			}
			
			Set-RegistryValue -Name "AzAppConfigSet" -Value $newSettings
			Write-Host "As configurações foram adicionadas/atualizadas no Azure App Configuration '$azAppConfigName'." -ForegroundColor Green
			
			Save-ScriptProgress -step ([int][ScriptSteps]::AzAppConfigEnvCreated)
		} catch {
			Show-ErrorMessage "Falha ao adicionar ou atualizar as configurações no Azure App Configuration."
			exit
		}
	}

	# Verificar se o Azure Data Studio está instalado
	try {
		$adsVersionInfo = azuredatastudio --version
		$adsVersion = $adsVersionInfo[0]
		$adsCommitHash = $adsVersionInfo[1]
		$adsArchitecture = $adsVersionInfo[2]
		$formattedVersion = "$adsVersion $adsArchitecture ($adsCommitHash)"
		Write-Host "Azure Data Studio já está instalado. Versão: $formattedVersion" -ForegroundColor Green
	} catch {
		try {
			$installAzDataStudio = Read-HostWithCancel "[OPCIONAL] O Azure Data Studio não está instalado. Deseja instalá-lo? (S/N)"
			if ($installAzDataStudio -eq 'S' -or $installAzDataStudio -eq 's') {
				Write-Host "Instalando Azure Data Studio..." -ForegroundColor Yellow
				if ($IsWindows) {
					# Baixar o instalador do Azure Data Studio para Windows
					$installScriptUrl = Get-ValidInstallerLink "https://go.microsoft.com/fwlink/?linkid=2251733"
					Start-Process -FilePath ".\Installer.exe" -ArgumentList "/install /passive /norestart" -Wait
					Remove-Item -Path ".\Installer.exe" -Force
				} elseif ($IsMacOS) {
					# Usar Homebrew no macOS
					brew install --cask azure-data-studio
				} elseif ($IsLinux) {
					# Baixar o pacote do Azure Data Studio para Linux
					$installScriptUrl = "https://go.microsoft.com/fwlink/?linkid=2251643"
					wget -qO- $installScriptUrl | sudo bash
				} else {
					Show-ErrorMessage "Sistema operacional não suportado."
					exit
				}
				$adsVersion = sqlops --version
			} else {
				Write-Host "Caso deseje instalar Azure Data Studio baixe e instale-o de https://docs.microsoft.com/en-us/sql/azure-data-studio/download-azure-data-studio"
			}
		} catch {
			Show-ErrorMessage "Falha ao instalar o Azure Data Studio."
			exit
		}
	}

	# Verificar se o Azure Key Vault Explorer está instalado
	$installAzKVE = Read-HostWithCancel "[OPCIONAL] Deseja instalar o Azure Key Vault Explorer (S/N)"
	if ($installAzKVE -eq 'S' -or $installAzKVE -eq 's') {
		Write-Host "Instalando Azure Key Vault Explorer..." -ForegroundColor Yellow
		if ($IsWindows) {
			# Abrir o navegador padrão com o URL de download do Azure Key Vault Explorer
			Start-Process -FilePath "msedge" -ArgumentList "https://aka.ms/ve"
		} else {
			Show-ErrorMessage "Sistema operacional não suportado."
			exit
		}
	} else {
		Write-Host "Caso deseje instalar o Azure Key Vault Explorer, baixe e instale-o de https://aka.ms/ve" -ForegroundColor Green
	}

	# Verificar se o Azure Storage Explorer está instalado
	$installAzStorageExplorer = Read-HostWithCancel "[OPCIONAL] Deseja instalar o Azure Storage Explorer? (S/N)"
	if ($installAzStorageExplorer -eq 'S' -or $installAzStorageExplorer -eq 's') {
		Write-Host "Instalando Azure Storage Explorer..." -ForegroundColor Yellow
		if ($IsWindows) {
			# Baixar o instalador do Azure Storage Explorer para Windows
			$installScriptUrl = Get-ValidInstallerLink "https://go.microsoft.com/fwlink/?linkid=2216182&clcid=0x409"
			Start-Process -FilePath ".\Installer.exe" -ArgumentList "/install /passive /norestart" -Wait
			Remove-Item -Path ".\Installer.exe" -Force
		} elseif ($IsMacOS) {
			# Usar Homebrew no macOS https://go.microsoft.com/fwlink/?linkid=2216184&clcid=0x409
			brew install --cask azure-storage-explorer
		} elseif ($IsLinux) {
			# Baixar o pacote do Azure Storage Explorer para Linux
			$installScriptUrl = "https://go.microsoft.com/fwlink/?linkid=2216383&clcid=0x409"
			wget -qO- $installScriptUrl | sudo bash
		} else {
			Show-ErrorMessage "Sistema operacional não suportado."
			exit
		}
	} else {
		Write-Host "Caso deseje instalar Azure Storage Explorer baixe e instale-o de https://azure.microsoft.com/en-us/products/storage/storage-explorer/"
	}

} catch {
	Show-ErrorMessage -ErrorMessage $_.Exception.Message -ErrorLine $_.InvocationInfo.ScriptLineNumber
	exit
}

# No final do script, perguntar se deve limpar o progresso
Save-ScriptProgress -step ([int][ScriptSteps]::Finished)
Write-Host "Configuração e instalação concluídas." -ForegroundColor Green

Ask-Clear-ScriptProgress
