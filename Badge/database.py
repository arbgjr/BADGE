import traceback
from datetime import datetime, timedelta
from pymongo import MongoClient
from pilmoji import Pilmoji
import logging

from . import azure
from . import logger

class Database:
    def __init__(self):
        self.logger = logger
        
        # Configuração do cliente Azure
        azure_client = azure.Azure()

        self.logger.log(logging.INFO, f"[database] Obter dados de conexão com o banco.")
        conn_str_orig = azure_client.get_key_vault_secret('CosmosDBConnectionString')
        self.conn_str = self._transform_connection_string(conn_str_orig)

    def _transform_connection_string(self, original_conn_str):
        # Não é necessário transformar a string de conexão para o CosmosDB
        return original_conn_str
                              
    def connect(self):
        try:
            self.logger.log(logging.INFO, f"[database] Conectando com o banco.")
            client = MongoClient(self.conn_str)
            return client
        except Exception as e:
            stack_trace = traceback.format_exc()
            self.logger.log(logging.ERROR, f"Erro de conexão com o banco de dados: {e}\nStack Trace:\n{stack_trace}")
            raise

    def get_badge_template(self, issuer_name, area_name):
        try:
            with self.connect() as client:
                db = client['dbBadges']
                templates_collection = db['Templates']

                # Buscar o template baseado no nome do emissor e na área
                template_data = templates_collection.find_one({
                    "IssuerName": issuer_name,
                    "AreaDetails.AreaName": area_name
                })

                # Verificar se o template foi encontrado
                if template_data:
                    # Preparar os dados do template para retornar
                    template_info = {
                        "BlobUrl": template_data.get("BlobUrl"),
                        "AreaDetails": template_data.get("AreaDetails", {}),
                        "ContentDetails": template_data.get("ContentDetails", {})
                    }
                    return template_info
                else:
                    self.logger.log(logging.WARNING, f"Nenhum template encontrado para o emissor '{issuer_name}' na área '{area_name}'.")
                    return None
        except Exception as e:
            stack_trace = traceback.format_exc()
            self.logger.log(logging.ERROR, f"Erro ao obter template do badge: {e}\nStack Trace:\n{stack_trace}")
            return None
        
    def get_badge_image(self, badge_guid):
        try:
            with self.connect() as client:
                db = client['dbBadges']
                badges_collection = db['Badges']
                return badges_collection.find_one({"GUID": badge_guid})["BadgeData"]
        except Exception as e:
            stack_trace = traceback.format_exc()
            self.logger.log(logging.ERROR, f"Erro ao obter imagem do badge: {e}\nStack Trace:\n{stack_trace}")
            return None

    def insert_badge(self, badge_guid, badge_data):
        try:
            with self.connect() as client:
                db = client['dbBadges']
                badges_collection = db['Badges']
                self.logger.log(logging.INFO, f"[database] Inserindo dados no banco.")
                badges_collection.insert_one(badge_data)
            return True
        except Exception as e:
            stack_trace = traceback.format_exc()
            self.logger.log(logging.ERROR, f"Erro ao inserir badge no banco de dados: {e}\nStack Trace:\n{stack_trace}")
            return False

    def insert_badge_json(self, badge_json):
        try:
            with self.connect() as client:
                db = client['dbBadges']
                badges_collection = db['Badges'] 

                # Insira o JSON diretamente na coleção
                result = badges_collection.insert_one(badge_json)

                if result.inserted_id:
                    return str(result.inserted_id)
                else:
                    return result
        except Exception as e:
            stack_trace = traceback.format_exc()
            self.logger.log(logging.ERROR, f"Erro ao inserir JSON da insígnia no banco de dados: {e}\nStack Trace:\n{stack_trace}")
            return None

    def create_badge_json_v1(self, badge_id, name, description, issuer_id, issuer_name, issuer_email, issuer_phone, holder_id, holder_name, holder_email, category_main, category_sub, template_id, template_url, badge_image_url, issued_date, expiry_date, additional_info, verification_link):
        badge_json = {
            "badgeId": badge_id,
            "name": name,
            "description": description,
            "issuer": {
                "issuerId": issuer_id,
                "name": issuer_name,
                "contactInfo": {
                    "email": issuer_email,
                    "phone": issuer_phone,
                }
            },
            "holder": {
                "holderId": holder_id,
                "name": holder_name,
                "email": holder_email,
            },
            "category": {
                "mainCategory": category_main,
                "subCategory": category_sub,
            },
            "template": {
                "templateId": template_id,
                "templateUrl": template_url,
            },
            "generatedBadge": {
                "badgeImageUrl": badge_image_url,
                "metadata": {
                    "issuedDate": issued_date,
                    "expiryDate": expiry_date,
                    "additionalInfo": additional_info,
                }
            },
            "verificationLink": verification_link,
        }

        return badge_json
