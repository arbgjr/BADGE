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

function Show-ErrorMessage {
	param (
		[string]$ErrorMessage,
		[int]$ErrorLine
	)

	Write-Host "ERRO na linha $ErrorLine : $ErrorMessage" -ForegroundColor Red
}

function Test-AdminPrivileges {
    if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        Write-Host "Este script precisa ser executado com privilégios de administrador." -ForegroundColor Red
        Write-Host "Reinicie o PowerShell como Administrador e tente novamente." -ForegroundColor Yellow
        return $false
    }

    return $true
}

function Initialize-Script {
    Clear-Host
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $timestamp = Get-Date -Format "yyyyMMdd.HHmm"
    $version = "v$timestamp"
    Write-Host "Script version: $version" -ForegroundColor Magenta
}


<<<<<<< HEAD
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
        $installScript = Read-HostWithCancel "Insira o link para o instalador desejado" "installScriptUrl" $installScriptUrl

        try {
            Invoke-WebRequest -Uri $installScript -OutFile "Installer.exe" -UseBasicParsing
            $validLink = $true
        } catch {
            Write-Host "O link fornecido não é válido. Certifique-se de que é um link direto para o instalador." -ForegroundColor Red
            $validLink = $false
        }
    }

    return $installScriptUrl
}
<<<<<<< HEAD
=======

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

function Get-AzKeyVaultName {
    do {
        $keyVaultName = Read-HostWithCancel "Digite o nome do Azure Key Vault" "keyVaultName"
        if ([string]::IsNullOrWhiteSpace($keyVaultName)) {
            Write-Host "O nome do Azure Key Vault é obrigatório." -ForegroundColor Green
        } elseif (-not ($keyVaultName -match '^[a-z0-9-]+$') -or ($keyVaultName -match '^-$|-$')) {
            Write-Host "O nome do Azure Key Vault deve conter apenas letras minúsculas 'a'-'z', números 0-9 e hífen (-). O hífen não pode ser o único caractere." -ForegroundColor Red
        }
    } while ([string]::IsNullOrWhiteSpace($keyVaultName) -or (-not ($keyVaultName -match '^[a-z0-9-]+$') -or ($keyVaultName -match '^-$|-$')))

    return $keyVaultName
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
        $settingValue = "null"
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
>>>>>>> 39f11c4 ( On branch dev)
=======
>>>>>>> parent of f956466 ( On branch dev)
