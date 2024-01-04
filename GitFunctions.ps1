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

function Remove-GitConfiguration {
	try {
		# Remova as configurações globais de nome de usuário e email no Git
		git config --global --unset-all user.name
		git config --global --unset-all user.email

		Write-Host "Configurações globais de nome de usuário e email do Git removidas com sucesso." -ForegroundColor Green
	} catch {
		Show-ErrorMessage "Falha ao remover as configurações globais do Git."
		exit
	}
}
