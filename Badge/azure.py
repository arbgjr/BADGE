import traceback
from azure.identity import DefaultAzureCredential
from azure.appconfiguration import AzureAppConfigurationClient
from azure.keyvault.secrets import SecretClient
import os
from . import logger 

# Classe principal
class Azure:
    def __init__(self):
        self.logger = logger

        self.credential = DefaultAzureCredential()
        self.app_config_client = self._initialize_app_config_client()
        self.secret_client = self._initialize_key_vault_client()

    def _initialize_app_config_client(self):
        connection_string = os.getenv("CUSTOMCONNSTR_AppConfigConnectionString")
        if not connection_string:
            self.logger.log('error', "A variável de ambiente 'AppConfigConnectionString' não está definida.")
            raise ValueError("AppConfigConnectionString não está definida.")
        return AzureAppConfigurationClient.from_connection_string(connection_string)

    def _initialize_key_vault_client(self):
        key_vault_url = self.get_app_config_setting("AzKVURI", )
        if key_vault_url is None:
            self.logger.log('error', "A URL do Azure Key Vault não foi encontrada na configuração.")
            raise ValueError("A URL do Azure Key Vault não foi encontrada.")

        if not key_vault_url.startswith("https://") or ".vault.azure.net" not in key_vault_url:
            self.logger.log('error', "URL do Azure Key Vault fornecida está incorreta")
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
            self.logger.log('error', f"Erro ao obter a configuração para a chave '{key}': {str(e)}\nStack Trace:\n{stack_trace}")
            return None

    def get_key_vault_secret(self, secret_name):
        try:
            secret = self.secret_client.get_secret(secret_name)
            return secret.value
        except Exception as e:
            stack_trace = traceback.format_exc()
            self.logger.log('error', f"Erro ao obter o segredo '{secret_name}' do Azure Key Vault: {str(e)}\nStack Trace:\n{stack_trace}")
            return None

