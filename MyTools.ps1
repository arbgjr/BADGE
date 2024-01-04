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


