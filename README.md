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
- Utiliza Flask para o backend, integrado com Azure Functions.
- Armazenamento de dados com Azure SQL Database.
- Segurança reforçada através do Azure Key Vault e criptografia PGP.

## Como Começar
1. Configure o ambiente Azure (Azure Functions, Azure SQL Database, Azure App Configuration).
2. Clone o repositório e instale as dependências necessárias.
3. Configure as variáveis de ambiente conforme a documentação.

## Instalação Automatizada com `install.ps1` para o BADGE

### Pré-Requisitos
- **PowerShell v7+**: Certifique-se de ter o PowerShell v7 ou superior instalado. Para macOS e Linux, [siga as instruções de instalação do PowerShell](https://docs.microsoft.com/pt-br/powershell/scripting/install/installing-powershell).

### Passos para Windows
1. **Abrir PowerShell como Administrador**: Clique com o botão direito no menu Iniciar e selecione "Windows PowerShell (Admin)".
2. **Baixe o script com o comando**:
   ```powershell
   curl -L -o install.ps1 https://raw.githubusercontent.com/arbgjr/BADGE/dev/install.ps1
   ```
3. Execute o script abaixo é siga as instruções na tela:
   ```powershell
   .\install.ps1
   ```

#### Para Usuários de macOS
1. Abra o Terminal.
2. Baixe o script com:
   ```bash
   curl -L -o install.ps1 https://raw.githubusercontent.com/arbgjr/BADGE/dev/install.ps1
   ```
3. Dê permissão de execução e execute o script com:
   ```bash
   chmod +x install.ps1
   sudo ./install.ps1
   ```

#### Para Usuários de Linux
1. Abra o Terminal.
2. Baixe o script com:
   ```bash
   wget -O install.ps1 https://raw.githubusercontent.com/arbgjr/BADGE/dev/install.ps1
   ```
3. Dê permissão de execução e execute o script com:
   ```bash
   chmod +x install.ps1
   sudo ./install.ps1
   ```

Siga as instruções no script para configurar seu ambiente Azure e clonar o repositório do projeto BADGE.

## Contribuições
Contribuições são bem-vindas! Para contribuir, siga as diretrizes de contribuição no repositório.

## Licença 
Vide LICENSE.
