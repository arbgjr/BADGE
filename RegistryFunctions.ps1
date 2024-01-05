enum ScriptSteps {
	NotStarted
	AzureCLIInstalled
	FunctionCoreToolsAppInstalled
	AzureFunctionsCoreToolsChecked
	GitInstalled
	GitConfigured
	RepoCloned
	AzureCLILoginExecuted
	SetSubsTenantCreated
	RGCreated
	StorageCreated
	AzFuncCreated
	AzFuncPublished
	AzFuncEnvCreated
}

Function NumLastStep {
	param ([int]$step)
	return [array]::IndexOf([Enum]::GetValues([ScriptSteps]), [ScriptSteps]$step) + 1
}

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

Function Ask-Clear-ScriptProgress {
	try {
		$clearProgress = Read-HostWithCancel "Deseja limpar o progresso do script no registro? Isso pode causar problemas se o script for executado novamente. (S/N)" "N"
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

Function Remove-RegistryValue {
	param (
		[string]$Name
	)
	try {
		if (Test-Path $registryPath) {
			return Remove-ItemProperty -Path $registryPath -Name $Name -ErrorAction SilentlyContinue
		}
	} catch {
		Write-Host "Erro ao ler do registro. Certifique-se de que o script está sendo executado com privilégios de administrador." -ForegroundColor Red
	}
	return $null
}
