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

function Stop-AzureFunction {
	param (
		[string]$functionAppName,
		[string]$resourceGroupName
	)

	try {
		# Parar a Azure Function
		az functionapp stop --name $functionAppName --resource-group $resourceGroupName
		Write-Host "A Azure Function '$functionAppName' foi parada com sucesso." -ForegroundColor Green
	} catch {
		Show-ErrorMessage "Falha ao parar a Azure Function."
		exit
	}
}

function Remove-AzureFunction {
	param (
		[string]$functionAppName,
		[string]$resourceGroupName
	)

	try {
		# Remova a Azure Function
		az functionapp delete --name $functionAppName --resource-group $resourceGroupName --yes
		Write-Host "A Azure Function '$functionAppName' foi removida com sucesso." -ForegroundColor Green
		Remove-RegistryValue -Name "functionAppName"
	} catch {
		Show-ErrorMessage "Falha ao remover a Azure Function."
		exit
	}
}

function Remove-AzureStorageAccount {
	param (
		[string]$storageAccountName,
		[string]$resourceGroupName
	)

	try {
		# Remova a conta de armazenamento
		az storage account delete --name $storageAccountName --resource-group $resourceGroupName --yes
		Write-Host "A conta de armazenamento '$storageAccountName' foi removida com sucesso." -ForegroundColor Green
		Remove-RegistryValue -Name "storageAccountName"
	} catch {
		Show-ErrorMessage "Falha ao remover a conta de armazenamento."
		exit
	}
}

function Remove-AzureResourceGroup {
	param (
		[string]$resourceGroupName
	)

	try {
		# Remova o grupo de recursos
		az group delete --name $resourceGroupName --yes
		Write-Host "O grupo de recursos '$resourceGroupName' foi removido com sucesso." -ForegroundColor Green
		Remove-RegistryValue -Name "resourceGroupName"
	} catch {
		Show-ErrorMessage "Falha ao remover o grupo de recursos."
		exit
	}
}

function Remove-AzureSubscription {
	param (
		[string]$subscriptionId
	)

	try {
		az account remove --subscription $subscriptionId
		Write-Host "Assinatura com ID '$subscriptionId' removida com sucesso." -ForegroundColor Green
		Remove-RegistryValue -Name "subscriptionName"
		Remove-RegistryValue -Name "subscriptionId"
	} catch {
		Show-ErrorMessage "Falha ao remover a assinatura."
		exit
	}
}
