# Script de Configuração e Instalação para o Projeto BADGE

# Verificar se o script está sendo executado com privilégios de administrador
if (-NOT ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "Este script precisa ser executado com privilégios de administrador." -ForegroundColor Red
    Write-Host "Reinicie o PowerShell como Administrador e tente novamente." -ForegroundColor Yellow
    exit
}

Set-Variable -Name "GITHUB_REPO" -Value "https://github.com/arbgjr/BADGE.git" -Option ReadOnly
Set-Variable -Name "REPO_NAME" -Value "Badge" -Option ReadOnly

enum ScriptSteps {
    NotStarted
    AzureCLIInstalled
    FunctionCoreToolsAppInstalled
    AzureFunctionsCoreToolsChecked
    AzureCLILoginExecuted
    SetSubsTenantCreated
    RGCreated
    GitInstalled
    GitConfigured
    RepoCloned
    StorageCreated
    AzFuncCreated
    AzFuncPublished
    WebhookCreated
    Finished
}

$registryPath = "HKCU:\Software\$REPO_NAME\Install"
$currentPath = Get-Location

Function Save-ScriptProgress {
    param ([ScriptSteps]$step)
    try {
        Set-RegistryValue -Name "LastStep" -Value ([int]$step)
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

Function Clear-ScriptProgress {
    try {
        Remove-Item -Path $registryPath -Force
    } catch {
        Write-Host "Erro ao limpar o progresso do registro. Certifique-se de que o script está sendo executado com privilégios de administrador." -ForegroundColor Red
        exit
    }
}

Function Read-HostWithCancel {
    param (
        [string]$prompt,
        [string]$registryValueName = $null,
        [string]$defaultValue = ""
    )
    $fullPrompt = "$prompt (ou 'cancelar' para sair) [default: $defaultValue]: "

    # Verificar e obter o valor salvo apenas se o nome da chave do registro for fornecido
    if ($registryValueName) {
        $savedInput = Get-RegistryValue -Name $registryValueName
        if ($savedInput) {
            $confirmation = Read-Host "Usar valor salvo '$savedInput'? (S/N, 'cancelar' para sair)"
            if ($confirmation -eq 'S' -or $confirmation -eq 's') {
                return $savedInput
            } elseif ($confirmation -eq 'cancelar') {
                Write-Host "Operação cancelada pelo usuário." -ForegroundColor Red
                exit
            }
        }
    }

    Write-Host $fullPrompt -NoNewline
    $input = Read-Host
    if ($input -eq 'cancelar') {
        Write-Host "Operação cancelada pelo usuário." -ForegroundColor Red
        exit
    } elseif ([string]::IsNullOrWhiteSpace($input)) {
        $input = $defaultValue
    }

    # Salvar o valor no registro, seja ele digitado pelo usuário ou o valor padrão
    if ($registryValueName -and -not [string]::IsNullOrWhiteSpace($input)) {
        Set-RegistryValue -Name $registryValueName -Value $input
    }

    return $input
}



Function Set-RegistryValue {
    param (
        [string]$Name,
        [string]$Value
    )
    try {
        Set-ItemProperty -Path $registryPath -Name $Name -Value $Value
    } catch {
        Write-Host "Erro ao salvar no registro. Certifique-se de que o script está sendo executado com privilégios de administrador." -ForegroundColor Red
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

$confirmRun = Read-HostWithCancel "Deseja efetuar a configuração do ambiente de forma automatizada? (S/N)"
if ($confirmRun -eq 'N' -or $confirmRun -eq 'n') {
    break
}

# Identificar o Sistema Operacional
$OS = Get-WmiObject -Class Win32_OperatingSystem
$IsWindows = $OS.Caption -like "*Windows*"
$IsMacOS = $OS.Caption -like "*Mac OS*"
$IsLinux = $OS.Caption -like "*Linux*"

try {
    $lastStep = Get-LastCompletedStep

    if ($lastStep -le [ScriptSteps]::NotStarted) {
        # Instalar a Azure CLI
        try {
            $azureCliVersion = az --version
            Write-Host "Azure CLI já está instalada. Versão: $azureCliVersion" -ForegroundColor Green
        } catch {
            try {
                Write-Host "Instalando Azure CLI..." -ForegroundColor Yellow
                if ($IsWindows) {
                    # Preferir Winget no Windows
                    winget install --id Microsoft.AzureCLI -e --source winget
                } elseif ($IsMacOS) {
                    # Usar Homebrew no macOS
                    brew update && brew install azure-cli
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
        Save-ScriptProgress [ScriptSteps]::AzureCLIInstalled
    }

    if ($lastStep -le [ScriptSteps]::AzureCLIInstalled) {
        # Instalar o Azure Functions Core Tools
        try {
            $funcVersion = func --version
            Write-Host "Azure Functions Core Tools já está instalado. Versão: $funcVersion" -ForegroundColor Green
        } catch {
            try {
                Write-Host "Instalando Azure Functions Core Tools..." -ForegroundColor Yellow
                if ($IsWindows) {
                    # Preferir Winget no Windows
                    winget install --id Microsoft.AzureFunctionsCoreTools -e --source winget
                } elseif ($IsMacOS) {
                    # Usar Homebrew no macOS
                    brew tap azure/functions && brew install azure-functions-core-tools@3
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
        Save-ScriptProgress [ScriptSteps]::FunctionCoreToolsAppInstalled
    }

    if ($lastStep -le [ScriptSteps]::FunctionCoreToolsAppInstalled) {
        Write-Host "Azure Functions Core Tools versão: $funcVersion" -ForegroundColor Green
        Save-ScriptProgress [ScriptSteps]::AzureFunctionsCoreToolsChecked
    }

    if ($lastStep -le [ScriptSteps]::AzureFunctionsCoreToolsChecked) {
        # Fazer login na Azure CLI
        try {
            $azAccount = az account show
            Write-Host "Já está logado na Azure CLI com a conta: $($azAccount.user.name)" -ForegroundColor Green
        } catch {
            try {
                Write-Host "Fazendo login na Azure CLI..." -ForegroundColor Yellow
                az login
            } catch {
                Show-ErrorMessage "Falha ao fazer login na Azure CLI."
                exit
            }
        }
        Save-ScriptProgress [ScriptSteps]::AzureCLILoginExecuted
    }

    if ($lastStep -le [ScriptSteps]::AzureCLILoginExecuted) {
        # Definir a assinatura e o diretório (tenant) corretos
        try {
            $currentSubscription = az account show --query "{name:name, id:id}" -o tsv
            if ($currentSubscription) {
                Write-Host "Assinatura atual: $($currentSubscription.name) (ID: $($currentSubscription.id))" -ForegroundColor Green
                $changeSubscription = Read-HostWithCancel "Deseja alterar a assinatura atual? (S/N)"
                if ($changeSubscription -ne 'S' -and $changeSubscription -ne 's') {
                    Write-Host "Continuando com a assinatura atual." -ForegroundColor Green
                } else {
                    Set-AzureSubscription
                }
            } else {
                Set-AzureSubscription
            }
        } catch {
            Show-ErrorMessage "Falha ao definir a assinatura."
            exit
        }
        Save-ScriptProgresss [ScriptSteps]::SetSubsTenantCreated
    }

    Function Set-AzureSubscription {
        while ($true) {
            Write-Host "Definindo a assinatura e o diretório corretos..." -ForegroundColor Yellow
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

    if ($lastStep -le [ScriptSteps]::SetSubsTenantCreated) {
        # Criar um Novo Grupo de Recursos
        $resourceGroupName = Read-HostWithCancel "Insira o nome do grupo de recursos" "resourceGroupName"
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
        Save-ScriptProgress [ScriptSteps]::RGCreated
    }

    if ($lastStep -le [ScriptSteps]::RGCreated) {
        # Instalar o Git
         try {
            $gitVersion = git --version
            Write-Host "Git já está instalado. Versão: $gitVersion" -ForegroundColor Green
        } catch {
            try {
                Write-Host "Instalando Git..." -ForegroundColor Yellow
                if ($IsWindows) {
                    # Preferir Winget no Windows
                    winget install --id Git.Git -e --source winget
                } elseif ($IsMacOS) {
                    # Usar Homebrew no macOS
                    brew install git
                } elseif ($IsLinux) {
                    # Usar apt-get para sistemas baseados em Debian/Ubuntu
                    sudo apt-get update && sudo apt-get install git
                } else {
                    Show-ErrorMessage "Sistema operacional não suportado."
                    exit
                }
            } catch {
                Show-ErrorMessage "Falha ao instalar Git."
                exit
            }
        }
        Save-ScriptProgress [ScriptSteps]::GitInstalled
    }

    if ($lastStep -le [ScriptSteps]::GitInstalled) {
        try {
            $currentUserName = git config --global user.name
            $currentUserEmail = git config --global user.email

            if ($currentUserName -and $currentUserEmail) {
                Write-Host "Configuração atual do Git: Nome de usuário: '$currentUserName', Email: '$currentUserEmail'" -ForegroundColor Green
                $changeGitConfig = Read-HostWithCancel "Deseja alterar a configuração do Git? (S/N)"
                if ($changeGitConfig -ne 'S' -and $changeGitConfig -ne 's') {
                    Write-Host "Continuando com a configuração atual do Git." -ForegroundColor Green
                } else {
                    Set-GitConfiguration
                }
            } else {
                Set-GitConfiguration
            }
        } catch {
            Show-ErrorMessage "Falha ao configurar Git."
            exit
        }
        Save-ScriptProgress [ScriptSteps]::GitConfigured
    }

    Function Set-GitConfiguration {
        $userName = Read-HostWithCancel "Insira o seu nome" "userName"
        git config --global user.name $userName

        $userEmail = Read-HostWithCancel "Insira o seu email" "userEmail"
        git config --global user.email $userEmail
    }

    if ($lastStep -le [ScriptSteps]::GitConfigured) {
        try {
            $repoPath = Read-HostWithCancel "Insira o caminho para clonar o repositório" "repoPath" $currentPath
            $repoUrl = Read-HostWithCancel "Insira a URL do repositório: " "repoUrl" $GITHUB_REPO
            $fullRepoPath = Join-Path $repoPath $REPO_NAME
    
            if (Test-Path $fullRepoPath) {
                Write-Host "O repositório '$repoName' já existe em '$fullRepoPath'." -ForegroundColor Green
                $cloneAgain = Read-HostWithCancel "Deseja clonar o repositório novamente? (S/N)"
                if ($cloneAgain -eq 'S' -or $cloneAgain -eq 's') {
                    Remove-Item -Recurse -Force $fullRepoPath
                    Clone-GitRepository $repoPath $repoUrl
                } else {
                    Write-Host "Usando o repositório existente." -ForegroundColor Green
                }
            } else {
                Clone-GitRepository $repoPath $repoName $repoUrl
            }
        } catch {
            Show-ErrorMessage "Falha ao clonar o repositório."
            exit
        }
        Save-ScriptProgress [ScriptSteps]::RepoCloned
    }
    
    Function Clone-GitRepository {
        param (
            [string]$path,
            [string]$url
        )
        Set-Location -Path $path
        git clone $url
        Write-Host "Repositório '$url' clonado com sucesso em '$path'." -ForegroundColor Green
    }
    
    if ($lastStep -le [ScriptSteps]::RepoCloned) {
        # Criar uma conta de armazenamento para Azure Functions
        $storageAccountName = Read-HostWithCancel "Insira o nome da conta de armazenamento" "storageAccountName"
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
        Save-ScriptProgress [ScriptSteps]::StorageCreated
    }

    if ($lastStep -le [ScriptSteps]::StorageCreated) {
        # Criar uma Azure Function
        $functionAppName = Read-HostWithCancel "Insira o nome da sua Azure Function" "functionAppName"
        $existingFunctionApp = az functionapp show --name $functionAppName --query 'state'

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
                az functionapp create --resource-group $resourceGroupName --consumption-plan-location $location --name $functionAppName
                Write-Host "Azure Function criada: '$functionAppName'." -ForegroundColor Green
            } catch {
                Show-ErrorMessage "Falha ao criar a Azure Function."
                exit
            }
        }
        Save-ScriptProgress [ScriptSteps]::AzFuncCreated
    }

    if ($lastStep -le [ScriptSteps]::AzFuncCreated) {
        try {
            $functionAppName = Get-RegistryValue -Name "functionAppName"
            $functionAppInfo = az functionapp show --name $functionAppName --query "{state: state, defaultHostName: defaultHostName}" -o json | ConvertFrom-Json

            if ($functionAppInfo -and $functionAppInfo.state -eq "Running") {
                Write-Host "A Azure Function '$functionAppName' já está publicada e em execução em: $($functionAppInfo.defaultHostName)" -ForegroundColor Green
                $publishAgain = Read-HostWithCancel "Deseja publicar a Azure Function novamente? (S/N)"
                if ($publishAgain -eq 'S' -or $publishAgain -eq 's') {
                    Publish-AzureFunction
                } else {
                    Write-Host "Usando a Azure Function publicada existente." -ForegroundColor Green
                }
            } else {
                Publish-AzureFunction
            }
        } catch {
            Show-ErrorMessage "Falha ao publicar a Azure Function."
            exit
        }
        Save-ScriptProgress [ScriptSteps]::AzFuncPublished
    }

    Function Publish-AzureFunction {
        $repoPath = Get-RegistryValue -Name "repoPath"
        Set-Location -Path $repoPath
        func azure functionapp publish $functionAppName
        Write-Host "Azure Function '$functionAppName' publicada com sucesso." -ForegroundColor Green
    }

    if ($lastStep -le [ScriptSteps]::AzFuncPublished) {
        Write-Host "Para configurar o webhook do Google Spaces, siga as instruções na documentação oficial do Google Chat: https://developers.google.com/chat/how-tos/webhooks?hl=pt-br#create_a_webhook" -ForegroundColor Yellow
        try {
            $functionAppName = Get-RegistryValue -Name "functionAppName"
            $existingSettings = az functionapp config appsettings list --name $functionAppName --resource-group $resourceGroupName | ConvertFrom-Json

            $settingName = Read-HostWithCancel "Insira um nome para o seu webhook" "settingName"
            $existingSetting = $existingSettings | Where-Object { $_.name -eq $settingName }

            if ($existingSetting) {
                Write-Host "A configuração do webhook '$settingName' já existe com o valor: $($existingSetting.value)" -ForegroundColor Green
                $updateSetting = Read-HostWithCancel "Deseja atualizar a configuração do webhook? (S/N)"
                if ($updateSetting -ne 'S' -and $updateSetting -ne 's') {
                    Write-Host "Mantendo a configuração existente do webhook." -ForegroundColor Green
                } else {
                    Update-WebhookSetting $functionAppName $resourceGroupName $settingName
                }
            } else {
                $settingValue = Read-HostWithCancel "Insira o link do webhook do Google Space" "settingValue"
                az functionapp config appsettings set --name $functionAppName --resource-group $resourceGroupName --settings $settingName=$settingValue
                Write-Host "Configuração do webhook: '$settingName' adicionada com sucesso à Azure Function '$functionAppName'." -ForegroundColor Green
            }
        } catch {
            Show-ErrorMessage "Falha ao adicionar ou atualizar a variável de ambiente à Azure Function."
            exit
        }
        Save-ScriptProgress [ScriptSteps]::WebhookCreated
    }

    Function Update-WebhookSetting {
        param (
            [string]$appName,
            [string]$resourceGroup,
            [string]$settingName
        )
        $settingValue = Read-HostWithCancel "Insira o novo link do webhook do Google Space" "settingValue"
        az functionapp config appsettings set --name $appName --resource-group $resourceGroup --settings $settingName=$settingValue
        Write-Host "Configuração do webhook atualizada: '$settingName'." -ForegroundColor Green
    }
} catch {
    Show-ErrorMessage "Ocorreu um erro."
    exit
}

# No final do script, perguntar se deve limpar o progresso
Save-ScriptProgress [ScriptSteps]::Finished
Write-Host "Configuração e instalação concluídas." -ForegroundColor Green

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


