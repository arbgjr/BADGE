import pyodbc
from . import helpers
from flask import current_app

class Database:
    def __init__(self):
        self.conn_str = helpers.get_app_config_setting('SqlConnectionString')

    def connect(self):
        try:
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

