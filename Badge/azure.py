import os
import requests
import traceback
from azure.identity import DefaultAzureCredential
from azure.appconfiguration import AzureAppConfigurationClient
from azure.mgmt.sql import SqlManagementClient
from azure.keyvault.secrets import SecretClient
from azure.storage.blob import BlobServiceClient, BlobClient, generate_blob_sas, BlobSasPermissions
from datetime import datetime, timedelta
import re
from PIL import Image
import io
from . import logger, LogLevel


# Classe principal
class Azure:
    def __init__(self):
        self.logger = logger

        self.credential = DefaultAzureCredential()
        self.app_config_client = self._initialize_app_config_client()
        self.secret_client = self._initialize_key_vault_client()
        self.blob_service_client = self._initialize_blob_service_client()

        # Atualizar a regra de firewall para Azure SQL
        #self.update_firewall_rule()

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
            self.logger.log(LogLevel.DEBUG, f"Function IP: {function_ip}")
            resource_group = self.get_resource_group()
            self.logger.log(LogLevel.DEBUG, f"Resource Group: {resource_group}")
            subscription_id = self.get_subscription_id()
            self.logger.log(LogLevel.DEBUG, f"Subscription ID: {subscription_id}")
            
            # Extrair informações do servidor da string de conexão
            conn_str = self.get_key_vault_secret('SqlConnectionString')
            server_match = re.search(r"Server=tcp:([a-zA-Z0-9.-]+),(\d+);", conn_str)
            if not server_match:
                raise ValueError("Não foi possível extrair informações do servidor da string de conexão.")

            server = server_match.group(1)
            self.logger.log(LogLevel.DEBUG, f"Az SQL Server: {server}")

            database_match = re.search(r"Initial Catalog=([a-zA-Z0-9]+);", conn_str)
            if not database_match:
                raise ValueError("Não foi possível extrair informações do banco da string de conexão.")

            database = database_match.group(1)
            self.logger.log(LogLevel.DEBUG, f"Database: {database}")
            
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
            
            self.logger.log(LogLevel.DEBUG, f"Regra de firewall atualizada: {firewall_rule.name}")
        except Exception as e:
            self.logger.log(LogLevel.ERROR, f"Erro ao atualizar a regra de firewall: {e}")
            raise

    def get_resource_group(self):
        try:
            resource_group = os.environ["RESOURCE_GROUP_NAME"]

            if not resource_group:
                raise EnvironmentError("RESOURCE_GROUP_NAME não está definida em variáveis de ambiente.")

            return resource_group
        except Exception as e:
            self.logger.log(LogLevel.ERROR, f"Erro geral: {e}")
            raise

    def get_subscription_id(self):
        try:
            subscription_id = os.environ["AZURE_SUBSCRIPTION_ID"]

            if not subscription_id:
                raise EnvironmentError("AZURE_SUBSCRIPTION_ID não está definida em variáveis de ambiente.")

            return subscription_id
        except Exception as e:
            self.logger.log(LogLevel.ERROR, f"Erro geral: {e}")
            raise

    def get_azure_function_name(self):
        azfunction_name = os.getenv('WEBSITE_SITE_NAME')
        
        if azfunction_name:
            return azfunction_name
        else:
            raise EnvironmentError("Nome da Azure Function não encontrado em variáveis de ambiente.")

    def _initialize_blob_service_client(self):
        try:
            storage_connection_string = self.get_key_vault_secret('BlobConnectionString') 
            if not storage_connection_string:
                raise ValueError("BlobConnectionString não está definida.")
            return BlobServiceClient.from_connection_string(storage_connection_string)
        except Exception as e:
            self.logger.log(LogLevel.ERROR, f"Erro ao inicializar o Blob Service Client: {str(e)}")
            raise

    def generate_sas_url(self, container_name, blob_name):
        try:
            container_client = self.blob_service_client.get_container_client(container_name)
            blob_client = container_client.get_blob_client(blob_name)

            # Define a data de expiração para 31 de dezembro do ano corrente às 23:59:59
            expiration_date = datetime(datetime.now().year, 12, 31, 23, 59, 59)
            
            # Define as permissões da URL SAS (leitura)
            sas_permissions = BlobSasPermissions(read=True)

            # Gera a URL SAS
            sas_url = generate_blob_sas(
                blob_client.account_name,
                blob_client.container_name,
                blob_client.blob_name,
                account_key=blob_client.credential.account_key,
                permission=sas_permissions,
                expiry=expiration_date
            )

            # Monta a URL completa
            full_url = f"{blob_client.url}?{sas_url}"
            return full_url
        except Exception as e:
            self.logger.log(LogLevel.ERROR, f"Erro ao gerar URL SAS: {str(e)}")
            raise
        
    def _create_container_if_not_exists(self, container_name):
        try:
            container_client = self.blob_service_client.get_container_client(container_name)
            if not container_client.exists():
                container_client.create_container()
        except Exception as e:
            self.logger.log(LogLevel.ERROR, f"Erro ao criar o contêiner: {str(e)}")
            raise

    def upload_blob(self, container_name, blob_name, file_path):
        try:
            self._create_container_if_not_exists(container_name)  # Verifica e cria o contêiner se não existir
            
            blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            with open(file_path, "rb") as data:
                blob_client.upload_blob(data)
            
            return True
        except Exception as e:
            self.logger.log(LogLevel.ERROR, f"Erro ao fazer upload do blob: {str(e)}")
            raise

    def upload_blob(self, container_name, blob_name, binary_data):
        try:
            self._create_container_if_not_exists(container_name)  # Verifica e cria o contêiner se não existir
            container_client = self.blob_service_client.get_container_client(container_name)
            container_client.upload_blob(blob_name, binary_data)
            
            return True
        except Exception as e:
            self.logger.log(LogLevel.ERROR, f"Erro ao fazer upload do blob: {str(e)}")
            raise

    def _container_exists(self, container_name):
        try:
            container_client = self.blob_service_client.get_container_client(container_name)
            return container_client.exists()
        except Exception as e:
            self.logger.log(LogLevel.ERROR, f"Erro ao verificar a existência do contêiner: {str(e)}")
            return False  # Em caso de erro, assume-se que o contêiner não existe

    def download_blob(self, container_name, blob_name, file_path):
        try:
            if not self._container_exists(container_name):  # Verifica se o contêiner existe
                self.logger.log(LogLevel.ERROR, f"O contêiner '{container_name}' não existe.")
                return  # Sai da função se o contêiner não existe
            blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=blob_name)
            with open(file_path, "wb") as download_file:
                download_file.write(blob_client.download_blob().readall())
        except Exception as e:
            self.logger.log(LogLevel.ERROR, f"Erro ao baixar o blob: {str(e)}")
            raise

    def return_blob_as_image(self, blob_url):
        try:
            # Faça uma solicitação HTTP para a URL SAS
            response = requests.get(blob_url)

            # Verifique se a solicitação foi bem-sucedida (código 200)
            if response.status_code == 200:
                # Lê o conteúdo da resposta e o converte em uma imagem PIL
                blob_data = response.content
                image = Image.open(io.BytesIO(blob_data))
                return image
            else:
                self.logger.log(LogLevel.ERROR, f"Erro ao baixar o blob. Código de resposta: {response.status_code}")
                return None
        except Exception as e:
            self.logger.log(LogLevel.ERROR, f"Erro ao baixar o blob: {str(e)}")
            raise

    def return_blob_as_binary(self, blob_url):
        try:
            response = requests.get(blob_url)
            if response.status_code == 200:
                font_data = response.content
                return io.BytesIO(font_data)
            else:
                self.logger.log(LogLevel.ERROR, f"Erro ao baixar a fonte. Código de resposta: {response.status_code}")
                return None
        except Exception as e:
            self.logger.log(LogLevel.ERROR, f"Erro ao baixar a fonte: {str(e)}")
            return None
        
    def return_blob_as_text(self, blob_url):
        try:
            response = requests.get(blob_url)
            if response.status_code == 200:
                data = response.content.decode('utf-8')  # Decodifica os bytes como texto UTF-8
                return data
            else:
                self.logger.log(LogLevel.ERROR, f"Erro ao baixar o blob. Código de resposta: {response.status_code}")
                return None
        except Exception as e:
            self.logger.log(LogLevel.ERROR, f"Erro ao baixar o blob: {str(e)}")
            return None

