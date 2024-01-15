import os
import requests
import subprocess
import traceback
from azure.identity import DefaultAzureCredential
from azure.appconfiguration import AzureAppConfigurationClient
from azure.keyvault.secrets import SecretClient
import json
import re
from . import logger, LogLevel

# Classe principal
class Azure:
    def __init__(self):
        self.logger = logger

        self.credential = DefaultAzureCredential()
        self.app_config_client = self._initialize_app_config_client()
        self.secret_client = self._initialize_key_vault_client()

        # Atualizar a regra de firewall para Azure SQL
        self.update_firewall_rule()

    def _initialize_app_config_client(self):
        connection_string = os.getenv("CUSTOMCONNSTR_AppConfigConnectionString")
        if not connection_string:
            self.logger.log(LogLevel.ERROR, "A variável de ambiente 'AppConfigConnectionString' não está definida.")
            raise ValueError("AppConfigConnectionString não está definida.")
        return AzureAppConfigurationClient.from_connection_string(connection_string)

    def _initialize_key_vault_client(self):
        key_vault_url = self.get_app_config_setting("AzKVURI", )
        if key_vault_url is None:
            self.logger.log(LogLevel.ERROR, "A URL do Azure Key Vault não foi encontrada na configuração.")
            raise ValueError("A URL do Azure Key Vault não foi encontrada.")

        if not key_vault_url.startswith("https://") or ".vault.azure.net" not in key_vault_url:
            self.logger.log(LogLevel.ERROR, "URL do Azure Key Vault fornecida está incorreta")
            raise ValueError("URL do Azure Key Vault fornecida está incorreta")

        return SecretClient(vault_url=key_vault_url, credential=self.credential)
    
    def get_app_config_setting(self, key, label="Badge"):
        try:
            if label:
                config_setting = self.app_config_client.get_configuration_setting(key, label=label)
            else:
                config_setting = self.app_config_client.get_configuration_setting(key)
            return config_setting.value
        except Exception as e:
            stack_trace = traceback.format_exc()
            self.logger.log(LogLevel.ERROR, f"Erro ao obter a configuração para a chave '{key}': {str(e)}\nStack Trace:\n{stack_trace}")
            return None

    def get_key_vault_secret(self, secret_name):
        try:
            secret = self.secret_client.get_secret(secret_name)
            return secret.value
        except Exception as e:
            stack_trace = traceback.format_exc()
            self.logger.log(LogLevel.ERROR, f"Erro ao obter o segredo '{secret_name}' do Azure Key Vault: {str(e)}\nStack Trace:\n{stack_trace}")
            return None

    def get_function_ip(self):
        try:
            response = requests.get("https://ifconfig.me/ip")
            response.raise_for_status()  # Isso garantirá que erros HTTP sejam capturados como exceções
            return response.text.strip()
        except requests.RequestException as e:
            self.logger.log(LogLevel.ERROR, f"Erro ao obter o IP da função: {e}")
            raise

    def update_firewall_rule(self):
        try:
            function_ip = self.get_function_ip()
            resource_group = self.get_resource_group()
            server_match = re.search(r"Server=tcp:([a-zA-Z0-9.-]+),(\d+);", self.get_key_vault_secret('SqlConnectionString'))
            command = f"az sql server firewall-rule create --resource-group {resource_group} --server {server_match} --name PermitirAcessoFunction --start-ip-address {function_ip} --end-ip-address {function_ip}"
            self.logger.log(LogLevel.DEBUG, f"Executando comando: {command}")
            subprocess.run(command, shell=True, check=True)  # 'check=True' para capturar erros
        except subprocess.CalledProcessError as e:
            self.logger.log(LogLevel.ERROR, f"Erro ao atualizar a regra de firewall: {e}")
            raise

    def get_resource_group(self):
        try:
            function_name = self.get_azure_function_name()
            # O comando Azure CLI para obter as informações da função
            cmd = f"az functionapp show --name {function_name} --query resourceGroup -o json"
            self.logger.log(LogLevel.DEBUG, f"Executando comando: {cmd}")
            # Executa o comando e captura a saída
            output = subprocess.check_output(cmd, shell=True)
            rg_name = json.loads(output)
            
            return rg_name
        except subprocess.CalledProcessError as e:
            self.logger.log(LogLevel.ERROR, f"Erro ao recuperar o Resource Group: {e.output}")
            raise

    def get_azure_function_name(self):
        function_name = os.getenv('WEBSITE_SITE_NAME')
        
        if function_name:
            return function_name
        else:
            raise EnvironmentError("Nome da Azure Function não encontrado em variáveis de ambiente.")
