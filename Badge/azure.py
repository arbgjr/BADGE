import os
import requests
import traceback
from azure.identity import DefaultAzureCredential
from azure.appconfiguration import AzureAppConfigurationClient
#from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.sql import SqlManagementClient
from azure.keyvault.secrets import SecretClient
import re
from . import logger, LogLevel
import inspect

# Classe principal
class Azure:
    def __init__(self):
        self.logger = logger

        self.credential = DefaultAzureCredential()
        self.app_config_client = self._initialize_app_config_client()
        self.secret_client = self._initialize_key_vault_client()
        
        self.frame = inspect.currentframe().f_back
        self.module_name = inspect.getmodule(self.frame).__name__
        self.class_name = self.frame.f_globals.get('__qualname__')
        function_name = self.frame.f_code.co_name
        self.caller_info = f"{self.module_name}.{self.class_name}.{function_name}"
        
        # Atualizar a regra de firewall para Azure SQL
        #self.update_firewall_rule()

    def _initialize_app_config_client(self):
        function_name = self.frame.f_code.co_name
        self.caller_info = f"{self.module_name}.{self.class_name}.{function_name}"
        connection_string = os.getenv("CUSTOMCONNSTR_AppConfigConnectionString")
        if not connection_string:
            self.logger.log(self.caller_info, LogLevel.ERROR, "A variável de ambiente 'AppConfigConnectionString' não está definida.")
            raise ValueError("AppConfigConnectionString não está definida.")
        return AzureAppConfigurationClient.from_connection_string(connection_string)

    def _initialize_key_vault_client(self):
        function_name = self.frame.f_code.co_name
        self.caller_info = f"{self.module_name}.{self.class_name}.{function_name}"
        key_vault_url = self.get_app_config_setting("AzKVURI", )
        if key_vault_url is None:
            self.logger.log(self.caller_info, LogLevel.ERROR, "A URL do Azure Key Vault não foi encontrada na configuração.")
            raise ValueError("A URL do Azure Key Vault não foi encontrada.")

        if not key_vault_url.startswith("https://") or ".vault.azure.net" not in key_vault_url:
            self.logger.log(self.caller_info, LogLevel.ERROR, "URL do Azure Key Vault fornecida está incorreta")
            raise ValueError("URL do Azure Key Vault fornecida está incorreta")

        return SecretClient(vault_url=key_vault_url, credential=self.credential)
    
    def get_app_config_setting(self, key, label="Badge"):
        function_name = self.frame.f_code.co_name
        self.caller_info = f"{self.module_name}.{self.class_name}.{function_name}"
        try:
            if label:
                config_setting = self.app_config_client.get_configuration_setting(key, label=label)
            else:
                config_setting = self.app_config_client.get_configuration_setting(key)
            return config_setting.value
        except Exception as e:
            stack_trace = traceback.format_exc()
            self.logger.log(self.caller_info, LogLevel.ERROR, f"Erro ao obter a configuração para a chave '{key}': {str(e)}\nStack Trace:\n{stack_trace}")
            return None

    def get_key_vault_secret(self, secret_name):
        function_name = self.frame.f_code.co_name
        self.caller_info = f"{self.module_name}.{self.class_name}.{function_name}"
        try:
            secret = self.secret_client.get_secret(secret_name)
            return secret.value
        except Exception as e:
            stack_trace = traceback.format_exc()
            self.logger.log(self.caller_info, LogLevel.ERROR, f"Erro ao obter o segredo '{secret_name}' do Azure Key Vault: {str(e)}\nStack Trace:\n{stack_trace}")
            return None

    def get_function_ip(self):
        function_name = self.frame.f_code.co_name
        self.caller_info = f"{self.module_name}.{self.class_name}.{function_name}"
        try:
            response = requests.get("https://ifconfig.me/ip")
            response.raise_for_status()  # Isso garantirá que erros HTTP sejam capturados como exceções
            return response.text.strip()
        except requests.RequestException as e:
            self.logger.log(self.caller_info, LogLevel.ERROR, f"Erro ao obter o IP da função: {e}")
            raise

    def update_firewall_rule(self):
        function_name = self.frame.f_code.co_name
        self.caller_info = f"{self.module_name}.{self.class_name}.{function_name}"
        try:
            function_ip = self.get_function_ip()
            self.logger.log(self.caller_info, LogLevel.DEBUG, f"Function IP: {function_ip}")
            resource_group = self.get_resource_group()
            self.logger.log(self.caller_info, LogLevel.DEBUG, f"Resource Group: {resource_group}")
            subscription_id = self.get_subscription_id()
            self.logger.log(self.caller_info, LogLevel.DEBUG, f"Subscription ID: {subscription_id}")
            
            # Extrair informações do servidor da string de conexão
            conn_str = self.get_key_vault_secret('SqlConnectionString')
            server_match = re.search(r"Server=tcp:([a-zA-Z0-9.-]+),(\d+);", conn_str)
            if not server_match:
                raise ValueError("Não foi possível extrair informações do servidor da string de conexão.")

            server = server_match.group(1)
            self.logger.log(self.caller_info, LogLevel.DEBUG, f"Az SQL Server: {server}")

            database_match = re.search(r"Initial Catalog=([a-zA-Z0-9]+);", conn_str)
            if not database_match:
                raise ValueError("Não foi possível extrair informações do banco da string de conexão.")

            database = database_match.group(1)
            self.logger.log(self.caller_info, LogLevel.DEBUG, f"Database: {database}")
            
            # Crie uma instância do SqlManagementClient
            credential = DefaultAzureCredential()
            sql_client = SqlManagementClient(credential, subscription_id)

            # Crie ou atualize a regra de firewall
            firewall_rule = sql_client.firewall_rules.create_or_update(
                resource_group_name=resource_group,
                server_name=server,
                firewall_rule_name="PermitirAcessoFunction",
                parameters={
                    "properties": {
                        "startIpAddress": function_ip,
                        "endIpAddress": function_ip
                    }
                }
            )
            
            self.logger.log(self.caller_info, LogLevel.DEBUG, f"Regra de firewall atualizada: {firewall_rule.name}")
        except Exception as e:
            self.logger.log(self.caller_info, LogLevel.ERROR, f"Erro ao atualizar a regra de firewall: {e}")
            raise

    def get_resource_group(self):
        function_name = self.frame.f_code.co_name
        self.caller_info = f"{self.module_name}.{self.class_name}.{function_name}"
        try:
            resource_group = os.environ["RESOURCE_GROUP_NAME"]

            if not resource_group:
                raise EnvironmentError("RESOURCE_GROUP_NAME não está definida em variáveis de ambiente.")

            return resource_group
#            function_app_name = self.get_azure_function_name()
#            credential = DefaultAzureCredential()
#            subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]
#
#            if not subscription_id:
#                raise EnvironmentError("AZURE_SUBSCRIPTION_ID não está definida em variáveis de ambiente.")
#
#            client = ResourceManagementClient(credential, subscription_id)
#            self.logger.log(self.caller_info, LogLevel.DEBUG, f"Cliente ResourceManagementClient criado:{client}")
#
#            for function_app in client.resources.list():
#                if function_app.name == function_app_name and function_app.type == 'Microsoft.Web/sites':
#                    # O ID do recurso é no formato /subscriptions/{sub}/resourceGroups/{rg}/providers/...
#                    return function_app.id.split('/')[4]
#
#            raise ValueError(f"[{subscription_id}] Azure Function '{function_app_name}' não encontrada dentro de {client}.")
#        
        except Exception as e:
            self.logger.log(self.caller_info, LogLevel.ERROR, f"Erro geral: {e}")
            raise

    def get_subscription_id(self):
        function_name = self.frame.f_code.co_name
        self.caller_info = f"{self.module_name}.{self.class_name}.{function_name}"
        try:
            subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]

            if not subscription_id:
                raise EnvironmentError("AZURE_SUBSCRIPTION_ID não está definida em variáveis de ambiente.")

            return subscription_id
        except Exception as e:
            self.logger.log(self.caller_info, LogLevel.ERROR, f"Erro geral: {e}")
            raise

    def get_azure_function_name(self):
        function_name = self.frame.f_code.co_name
        self.caller_info = f"{self.module_name}.{self.class_name}.{function_name}"
        azfunction_name = os.getenv('WEBSITE_SITE_NAME')
        
        if azfunction_name:
            return azfunction_name
        else:
            raise EnvironmentError("Nome da Azure Function não encontrado em variáveis de ambiente.")
