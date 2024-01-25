from flask import Flask, jsonify, request 
import traceback
from flask_restx import Resource, Api, fields, reqparse
import logging

# Criação da aplicação Flask
application = Flask(__name__)

def format_exception(e):
    trace = traceback.format_exception(type(e), e, e.__traceback__)

    formatted_trace = []
    for line in trace:
        if " File" in line or " ^" in line:
            formatted_trace.append("\n" + line.strip())
        else:
            formatted_trace.append(line.strip())

    pretty_exception = "".join(formatted_trace)

    return pretty_exception

@application.errorhandler(Exception)
def handle_exception(e):
    formatted_error = format_exception(e)
    response = jsonify(message=str(e), formatted_error=formatted_error, type=type(e).__name__)
    response.status_code = 400
    return response

# Configurações da aplicação
# Ativar a propagação de exceções para garantir que os erros sejam tratados de maneira adequada
application.config['PROPAGATE_EXCEPTIONS'] = True

# Inicializar a API REST com Flask-RESTx
# doc='/doc/' habilita a documentação Swagger em /doc/
api = Api(application, doc='/doc/')

from . import logger
from . import business

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
            418: "Erro interno da aplicação"
        }
    )
    def get(self):
        """Endpoint para verificar a saúde da API."""
        return jsonify({"message": "back"}), 200

api.add_resource(Ping, "/ping")

class Configs(Resource):
    @api.doc(
        description="Recupera configurações para verificação se estão ok.",
        responses={
            200: "Retorno ok",
            418: "Erro interno da aplicação"
        }
    )
    def get(self):
        """Endpoint para recuperar configurações da API."""
        result = business.get_configs()
        return jsonify(result)

api.add_resource(Configs, "/configs")

# TODO: Payload compactado
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
            418: "Erro interno da aplicação"
        }
    )
    @api.expect(badge_model, validate=True)
    def post(self):
        """Endpoint para emitir um novo badge."""
        logger.log(logging.INFO, f"[app] Endpoint para emitir um novo badge.")
        data = request.json
        result = business.generate_badge(data)
        return jsonify(result)

api.add_resource(EmitBadge, '/emit_badge')


# Modelo de dados específico para GetBadgeImage
badge_image_model = api.model('BadgeImageRequest', {
    'badge_guid': fields.String(required=True, description='GUID do badge a ser buscado')
})

class GetBadgeImage(Resource):
    @api.doc(
        description="Obter a imagem de um badge específico via JSON.",
        responses={
            200: "Badge encontrado",
            400: "Dados inválidos",
            404: "Badge não encontrado",
            418: "Erro interno da aplicação"
        }
    )
    @api.expect(badge_image_model, validate=True)
    def get(self):
        """Endpoint para obter a imagem de um badge específico."""
        data = request.json
        result = business.badge_image(data)
        return jsonify(result)

api.add_resource(GetBadgeImage, '/get_badge_image')


# Modelo de dados para a documentação Swagger e validação
validate_badge_model = api.model('ValidateBadgeRequest', {
    'data': fields.String(required=True, description='Dados criptografados do badge')
})

class ValidateBadge(Resource):
    @api.doc(
        description="Validar a autenticidade de um badge.",
        responses={
            200: "Badge válido",
            400: "Falha na descriptografia ou dados inválidos",
            404: "Badge não encontrado ou informações não correspondem",
            418: "Erro interno da aplicação"
        }
    )
    @api.expect(validate_badge_model, validate=True)
    def get(self):
        """Endpoint para validar a autenticidade de um badge."""
        data = request.json
        result = business.badge_valid(data)
        return jsonify(result)
    
api.add_resource(ValidateBadge, '/validate_badge')


# Modelo de dados para a documentação Swagger e validação
user_badges_model = api.model('UserBadgesRequest', {
    'user_id': fields.String(required=True, description='ID do usuário para o qual os badges serão buscados')
})

class GetUserBadges(Resource):
    @api.doc(
        description="Obter a lista de badges de um usuário específico via JSON.",
        responses={
            200: "Lista de badges retornada com sucesso",
            400: "Dados inválidos",
            404: "Usuário não encontrado",
            418: "Erro interno da aplicação"
        }
    )
    @api.expect(user_badges_model, validate=True)
    def get(self):
        """Endpoint para obter a lista de badges de um usuário específico."""
        data = request.json
        result = business.badge_list(data)
        return jsonify(result)

api.add_resource(GetUserBadges, '/get_user_badges')


# Modelo de dados para a documentação Swagger e validação
badge_holders_model = api.model('BadgeHoldersRequest', {
    'badge_name': fields.String(required=True, description='Nome do badge para buscar os detentores')
})

class GetBadgeHolders(Resource):
    @api.doc(
        description="Obter a lista de usuários que possuem um badge específico via JSON.",
        responses={
            200: "Lista de detentores do badge retornada com sucesso",
            400: "Dados inválidos",
            404: "Badge não encontrado",
            418: "Erro interno da aplicação"
        }
    )
    @api.expect(badge_holders_model, validate=True)
    def get(self):
        """Endpoint para obter a lista de usuários que possuem um badge específico."""
        data = request.json
        result = business.badge_holder(data)
        return jsonify(result)

api.add_resource(GetBadgeHolders, '/get_badge_holders')


# Modelo de dados para a documentação Swagger e validação
linkedin_post_model = api.model('LinkedInPostRequest', {
    'badge_guid': fields.String(required=True, description='GUID do badge para gerar a postagem')
})

class GetLinkedInPost(Resource):
    @api.doc(
        description="Gerar um texto sugerido para postagem no LinkedIn sobre um badge via JSON.",
        responses={
            200: "Postagem gerada com sucesso",
            400: "Dados inválidos",
            404: "Badge não encontrado",
            418: "Erro interno da aplicação"
        }
    )
    @api.expect(linkedin_post_model, validate=True)
    def get(self):
        """Endpoint para gerar um texto sugerido para postagem no LinkedIn sobre um badge."""
        data = request.json
        result = business.linkedin_post(data)
        return jsonify(result)

api.add_resource(GetLinkedInPost, '/get_linkedin_post')


