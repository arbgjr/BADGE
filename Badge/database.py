import logging
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.trace import config_integration
import os
import re
import pyodbc
from datetime import datetime, timedelta
from . import helpers
from flask import current_app
from . import azure

class Database:
    def __init__(self):
        self._configure_logging()

        # Configuração do cliente Azure
        azure_client = azure.Azure()

        logging.info(f"[database] Obter dados de conexão com o banco.")
        self.conn_str = self._transform_connection_string(azure_client.get_key_vault_secret('SqlConnectionString'))

    def _configure_logging(self):
        config_integration.trace_integrations(['logging'])
        self.logger = logging.getLogger(__name__)
        appinsights_key = os.environ.get("APPINSIGHTS_INSTRUMENTATIONKEY")
        if appinsights_key:
            handler = AzureLogHandler(connection_string=f'InstrumentationKey={appinsights_key}')
            self.logger.addHandler(handler)

    def _transform_connection_string(original_conn_str):
        # Extrair os componentes da string de conexão original
        server_match = re.search(r"Server=tcp:([a-zA-Z0-9.-]+),(\d+);", original_conn_str)
        database_match = re.search(r"Initial Catalog=([a-zA-Z0-9]+);", original_conn_str)
        user_id_match = re.search(r"User ID=([^;]+);", original_conn_str)
        password_match = re.search(r"Password=([^;]+);", original_conn_str)
        if not all([server_match, database_match, user_id_match, password_match]):
            raise ValueError("Formato de string de conexão inválido ou incompleto")

        server = server_match.group(1)
        port = server_match.group(2)
        database = database_match.group(1)
        user_id = user_id_match.group(1)
        password = password_match.group(1)

        # Montar a string de conexão para o pyodbc
        pyodbc_conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER=tcp:{server},{port};"
            f"DATABASE={database};"
            f"UID={user_id};"
            f"PWD={password};"
            "Encrypt=yes;"
            "TrustServerCertificate=no;"
            "Connection Timeout=30;"
        )

        return pyodbc_conn_str
                              
    def connect(self):
        try:
            logging.info(f"[database] Conectando com o banco.")
            return pyodbc.connect(self.conn_str)
        except pyodbc.Error as e:
            current_app.logger.error(f"Erro de conexão com o banco de dados: {e}")
            raise

    def get_badge_template(self, badge_id):
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT ImagemBase64 FROM Imagens WHERE Id = ?", badge_id)
                return cursor.fetchone()[0]
        except Exception as e:
            current_app.logger.error(f"Erro ao obter template do badge: {e}")
            return None

    def get_badge_image(self, badge_guid):
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT BadgeBase64 FROM Badges WHERE GUID = ?", badge_guid)
                return cursor.fetchone()
        except Exception as e:
            current_app.logger.error(f"Erro ao obter imagem do badge: {e}")
            return None

    def validate_badge(self, badge_guid, owner_name, issuer_name):
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM Badges WHERE GUID = ? AND OwnerName = ? AND IssuerName = ?", badge_guid, owner_name, issuer_name)
                return cursor.fetchone()
        except Exception as e:
            current_app.logger.error(f"Erro ao validar badge: {e}")
            return None

    def get_user_badges(self, user_id):
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT GUID, BadgeName FROM Badges WHERE UserID = ?", user_id)
                return cursor.fetchall()
        except Exception as e:
            current_app.logger.error(f"Erro ao obter badges do usuário: {e}")
            return None

    def get_badge_holders(self, badge_name):
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT UserName FROM Badges WHERE BadgeName = ?", badge_name)
                return cursor.fetchall()
        except Exception as e:
            current_app.logger.error(f"Erro ao obter detentores do badge: {e}")
            return None

    def get_badge_info_for_post(self, badge_guid):
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT BadgeName, AdditionalInfo FROM Badges WHERE GUID = ?", badge_guid)
                return cursor.fetchone()
        except Exception as e:
            current_app.logger.error(f"Erro ao obter informações do badge para postagem: {e}")
            return None

    def insert_badge(self, badge_guid, badge_hash, badge_data, owner_name, issuer_name, signed_hash, badge_base64):
        try:
            with self.connect() as conn:
                cursor = conn.cursor()
                logging.info(f"[database] Inserindo dados no banco.")
                cursor.execute(
                    "INSERT INTO Badges (GUID, BadgeHash, BadgeData, CreationDate, ExpiryDate, OwnerName, IssuerName, PgpSignature, BadgeBase64) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    badge_guid, badge_hash, badge_data, datetime.now(), datetime.now() + timedelta(days=365), owner_name, issuer_name, str(signed_hash), badge_base64
                )
                logging.info(f"[database] Comitando dados .")
                conn.commit()
            return True
        except Exception as e:
            current_app.logger.error(f"Erro ao inserir badge no banco de dados: {e}")
            return False
