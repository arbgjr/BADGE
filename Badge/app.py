import logging
import os
import io
import base64
import uuid
import hashlib
import pyodbc
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import qrcode
import gnupg
import azure.functions as func
from azf_wsgi import AzureFunctionsWsgi 
from flask import Flask, jsonify, request
from azure.identity import DefaultAzureCredential
from azure.appconfiguration import AzureAppConfigurationClient
from . import helpers
from werkzeug.exceptions import HTTPException
import flask, werkzeug
from flask_restx import Resource, Api
from . import helpers

# Criação da aplicação Flask
application = Flask(__name__)

# Configurações da aplicação
# Ativar a propagação de exceções para garantir que os erros sejam tratados de maneira adequada
application.config['PROPAGATE_EXCEPTIONS'] = True

# Inicializar a API REST com Flask-RESTx
# doc='/doc/' habilita a documentação Swagger em /doc/
api = Api(application, doc='/doc/')

# Inicialização do GnuPG para criptografia
# Certifique-se de que o caminho para o diretório GPG está correto e acessível
gpg_home = os.getenv('GPG_HOME', '/path/to/.gnupg')
gpg = gnupg.GPG(gnupghome=gpg_home)

# Verificar se o GnuPG está configurado corretamente
if not gpg.list_keys():
    raise EnvironmentError("GPG não está configurado corretamente ou não tem chaves disponíveis.")

@api.route("/hello")
class Hello(Resource):
    @api.doc(
        params={'owner_name': 'Nome do proprietário da requisição'},
        responses={
            200: 'Success',
            400: 'Validation Error'
        }
    )
    def get(self):
        # Parser para parâmetros de consulta
        parser = reqparse.RequestParser()
        parser.add_argument('owner_name', required=True, help="Nome do proprietário não pode ser vazio")
        args = parser.parse_args()

        user = args['owner_name']
        return jsonify({"message": f"Hello Azure Function {user}"})

api.add_resource(Hello, "/hello")


class Ping(Resource):
    @api.doc(
        description="Verifica se a API está ativa e respondendo.",
        responses={
            200: "API ativa",
            500: "Erro interno do servidor"
        }
    )
    def get(self):
        """Endpoint para verificar a saúde da API."""
        return jsonify({"message": "back"}), 200

api.add_resource(Ping, "/ping")


# Modelo de dados para a documentação Swagger
badge_model = api.model('BadgeData', {
    'owner_name': fields.String(required=True, description='Nome do proprietário do badge'),
    'issuer_name': fields.String(required=True, description='Nome do emissor do badge')
})

class EmitBadge(Resource):
    @api.doc(
        description="Emitir um novo badge.",
        responses={
            200: "Badge emitido com sucesso",
            400: "Erro de validação",
            500: "Erro interno do servidor"
        }
    )
    @api.expect(badge_model, validate=True)
    def post(self):
        """Endpoint para emitir um novo badge."""
        data = request.json
        result = helpers.generate_badge(data)
        return jsonify(result)

api.add_resource(EmitBadge, '/emit_badge')


# Parser para parâmetros de consulta
parser = reqparse.RequestParser()
parser.add_argument('badge_guid', type=str, required=True, help="GUID do badge é obrigatório")

class GetBadgeImage(Resource):
    @api.doc(
        description="Obter a imagem de um badge específico.",
        params={'badge_guid': 'GUID do badge a ser buscado'},
        responses={
            200: "Badge encontrado",
            404: "Badge não encontrado",
            500: "Erro interno do servidor"
        }
    )
    @api.expect(parser)
    def get(self):
        """Endpoint para obter a imagem de um badge específico."""
        args = parser.parse_args()
        badge_guid = args['badge_guid']
        
        conn_str = helpers.get_app_config_setting('SqlConnectionString')
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT BadgeBase64 FROM Badges WHERE GUID = ?", badge_guid)
            row = cursor.fetchone()
        
        if row:
            return jsonify({"badge_image": row[0]})
        else:
            return jsonify({"error": "Badge não encontrado"}), 404

api.add_resource(GetBadgeImage, '/get_badge_image')


# Parser para parâmetros de consulta
parser = reqparse.RequestParser()
parser.add_argument('data', type=str, required=True, help="Dados criptografados são obrigatórios")

class ValidateBadge(Resource):
    @api.doc(
        description="Validar a autenticidade de um badge.",
        params={'data': 'Dados criptografados do badge'},
        responses={
            200: "Badge válido",
            400: "Falha na descriptografia",
            404: "Badge não encontrado ou informações não correspondem",
            500: "Erro interno do servidor"
        }
    )
    @api.expect(parser)
    def get(self):
        """Endpoint para validar a autenticidade de um badge."""
        args = parser.parse_args()
        encrypted_data = args['data']
        decrypted_data = gpg.decrypt(encrypted_data)
        
        if not decrypted_data.ok:
            return jsonify({"error": "Falha na descriptografia"}), 400
        
        try:
            badge_guid, owner_name, issuer_name = decrypted_data.data.split("|")
        except ValueError:
            return jsonify({"error": "Dados decodificados inválidos"}), 400
        
        conn_str = helpers.get_app_config_setting('SqlConnectionString')
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM Badges WHERE GUID = ? AND OwnerName = ? AND IssuerName = ?", badge_guid, owner_name, issuer_name)
            badge = cursor.fetchone()
        
        if badge:
            return jsonify({"valid": True, "badge_info": badge})
        else:
            return jsonify({"valid": False, "error": "Badge não encontrado ou informações não correspondem"}), 404

api.add_resource(ValidateBadge, '/validate_badge')


# Parser para parâmetros de consulta
parser = reqparse.RequestParser()
parser.add_argument('user_id', type=str, required=True, help="ID do usuário é obrigatório")

class GetUserBadges(Resource):
    @api.doc(
        description="Obter a lista de badges de um usuário específico.",
        params={'user_id': 'ID do usuário para o qual os badges serão buscados'},
        responses={
            200: "Lista de badges retornada com sucesso",
            404: "Usuário não encontrado",
            500: "Erro interno do servidor"
        }
    )
    @api.expect(parser)
    def get(self):
        """Endpoint para obter a lista de badges de um usuário específico."""
        args = parser.parse_args()
        user_id = args['user_id']

        conn_str = helpers.get_app_config_setting('SqlConnectionString')
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT GUID, BadgeName FROM Badges WHERE UserID = ?", user_id)
            badges = cursor.fetchall()

        if not badges:
            return jsonify({"error": "Nenhum badge encontrado para o usuário"}), 404

        badge_list = []
        for badge in badges:
            badge_guid = badge[0]
            badge_name = badge[1]
            validation_url = f"https://yourdomain.com/validate?badge_guid={badge_guid}"
            badge_list.append({"name": badge_name, "validation_url": validation_url})

        return jsonify(badge_list)

api.add_resource(GetUserBadges, '/get_user_badges')


# Parser para parâmetros de consulta
parser = reqparse.RequestParser()
parser.add_argument('badge_name', type=str, required=True, help="Nome do badge é obrigatório")

class GetBadgeHolders(Resource):
    @api.doc(
        description="Obter a lista de usuários que possuem um badge específico.",
        params={'badge_name': 'Nome do badge para buscar os detentores'},
        responses={
            200: "Lista de detentores do badge retornada com sucesso",
            404: "Badge não encontrado",
            500: "Erro interno do servidor"
        }
    )
    @api.expect(parser)
    def get(self):
        """Endpoint para obter a lista de usuários que possuem um badge específico."""
        args = parser.parse_args()
        badge_name = args['badge_name']

        conn_str = helpers.get_app_config_setting('SqlConnectionString')
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT UserName FROM Badges WHERE BadgeName = ?", badge_name)
            badge_holders = cursor.fetchall()

        if not badge_holders:
            return jsonify({"error": "Nenhum detentor de badge encontrado para este nome de badge"}), 404

        users = [user[0] for user in badge_holders]
        return jsonify(users)

api.add_resource(GetBadgeHolders, '/get_badge_holders')


# Parser para parâmetros de consulta
parser = reqparse.RequestParser()
parser.add_argument('badge_guid', type=str, required=True, help="GUID do badge é obrigatório")

class GetLinkedInPost(Resource):
    @api.doc(
        description="Gerar um texto sugerido para postagem no LinkedIn sobre um badge.",
        params={'badge_guid': 'GUID do badge para gerar a postagem'},
        responses={
            200: "Postagem gerada com sucesso",
            404: "Badge não encontrado",
            500: "Erro interno do servidor"
        }
    )
    @api.expect(parser)
    def get(self):
        """Endpoint para gerar um texto sugerido para postagem no LinkedIn sobre um badge."""
        args = parser.parse_args()
        badge_guid = args['badge_guid']

        conn_str = helpers.get_app_config_setting('SqlConnectionString')
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT BadgeName, AdditionalInfo FROM Badges WHERE GUID = ?", badge_guid)
            badge = cursor.fetchone()

        if not badge:
            return jsonify({"error": "Badge não encontrado"}), 404

        badge_name, additional_info = badge

        # URL de validação do badge
        validation_url = f"https://yourdomain.com/validate?badge_guid={badge_guid}"
        
        # Texto sugerido para postagem
        post_text = (
            f"Estou muito feliz em compartilhar que acabei de conquistar um novo badge: {badge_name}! "
            f"Esta conquista representa {additional_info}. "
            f"Você pode verificar a autenticidade do meu badge aqui: {validation_url} "
            "#Conquista #Badge #DesenvolvimentoProfissional"
        )
        
        return jsonify({"linkedin_post": post_text})

api.add_resource(GetLinkedInPost, '/get_linkedin_post')
