import logging
import pyodbc
from datetime import datetime, timedelta
from . import helpers
from flask import current_app

# Configurar o nível de log para INFO
logging.basicConfig(level=logging.INFO)

class Database:
    def __init__(self):
        logging.info(f"[database] Obter dados de conexão com o banco.")
        self.conn_str = helpers.get_app_config_setting('SqlConnectionString')

    def connect(self):
        try:
            logging.info(f"[database] Conectando com o banco.")
            return pyodbc.connect(self.conn_str)
        except pyodbc.Error as e:
            current_app.logger.error(f"Erro de conexão com o banco de dados: {e}")
            raise

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
