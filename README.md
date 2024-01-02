# BADGE (Badge Authentication and Dynamic Grading Engine)

## Instalação
Antes de iniciar a configuração do BADGE, é necessário baixar e executar o script `install.ps1`. Este script automatiza a configuração do ambiente, incluindo a instalação de dependências necessárias e a configuração do projeto no Azure.

### Passos para a Execução do Script:
1. Baixe o script `install.ps1` do repositório do projeto BADGE.
2. Execute o script com privilégios de administrador no PowerShell.
3. Siga as instruções no script para configurar seu ambiente Azure e clonar o repositório do projeto.

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

## Contribuições
Contribuições são bem-vindas! Para contribuir, siga as diretrizes de contribuição no repositório.

## Licença 
Vide LICENSE.
