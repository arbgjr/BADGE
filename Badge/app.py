from flask import Flask, jsonify, request 
from flask_restx import Resource, Api, fields, reqparse, Namespace
import traceback
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
    logging.log(logging.ERROR, f"response: {response}")
    return response

# Ativar a propagação de exceções para garantir que os erros sejam tratados de maneira adequada
application.config['PROPAGATE_EXCEPTIONS'] = True

# doc='/doc/' habilita a documentação Swagger em /doc/
api = Api(application, doc='/doc/')

# Criação de um namespace
ns = api.namespace('badges', description='Operações relacionadas a Badges')

from . import business

hello_model = api.model('Hello', {
    'owner_name': fields.String(required=True, description='Nome do proprietário da requisição')
})
@ns.route("/hello")
class Hello(Resource):
    @ns.doc(
        responses={
            200: 'Success',
            400: 'Validation Error'
        }
    )
    @ns.expect(hello_model)
    def get(self):
        """Endpoint para dizer olá."""
        args = request.args
        user = args['owner_name']
        return jsonify({"message": f"Hello Azure Function {user}"})


@ns.route("/version")
class Version(Resource):
    @ns.doc(
        description="Retorna versão da API.",
        responses={
            200: 'Success',
            500: 'Internal Error'
        }
    )
    def get(self):
        logging.log(logging.INFO, f"[app] Endpoint para retornar a versão do badge.")
        version = business.get_api_version()
        return jsonify({"version": version})

      
@ns.route('/ping')
class Ping(Resource):
    @ns.doc(
        description="Verifica se a API está ativa e respondendo.",
        responses={
            200: "API ativa",
            418: "Erro interno da aplicação"
        }
    )
    def get(self):
        """Endpoint para verificar a saúde da API."""
        return jsonify({"message": "API ativa"}), 200

      
@ns.route('/configs')
class Configs(Resource):
    @ns.doc(
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

# TODO: #74 Payload compactado


badge_model = ns.model('BadgeData', {
    'owner_name': fields.String(required=True, description='Nome do proprietário do badge'),
    'issuer_name': fields.String(required=True, description='Nome do emissor do badge')
})

@ns.route('/emit_badge')
class EmitBadge(Resource):
    @ns.doc(
        description="Emitir um novo badge.",
        responses={
            200: "Badge emitido com sucesso",
            400: "Erro de validação",
            418: "Erro interno da aplicação"
        }
    )
    @ns.expect(badge_model, validate=True)
    def post(self):
        """Endpoint para emitir um novo badge."""
        logging.log(logging.INFO, f"[app] Endpoint para emitir um novo badge.")
        data = request.json
        result = business.generate_badge(data)
        return jsonify(result)

      
badge_image_model = ns.model('BadgeImageRequest', {
    'badge_guid': fields.String(required=True, description='GUID do badge a ser buscado')
})

@ns.route('/get_badge_image')
class GetBadgeImage(Resource):
    @ns.doc(
        description="Obter a imagem de um badge específico via JSON.",
        responses={
            200: "Badge encontrado",
            400: "Dados inválidos",
            404: "Badge não encontrado",
            418: "Erro interno da aplicação"
        }
    )
    @ns.expect(badge_image_model, validate=True)
    def get(self):
        """Endpoint para obter a imagem de um badge específico."""
        data = request.json
        result = business.badge_image(data)
        return jsonify(result)

      
validate_badge_model = ns.model('ValidateBadgeRequest', {
    'data': fields.String(required=True, description='Dados criptografados do badge')
})

@ns.route('/validate_badge')
class ValidateBadge(Resource):
    @ns.doc(
        description="Validar a autenticidade de um badge.",
        responses={
            200: "Badge válido",
            400: "Falha na descriptografia ou dados inválidos",
            404: "Badge não encontrado ou informações não correspondem",
            418: "Erro interno da aplicação"
        }
    )
    @ns.expect(validate_badge_model, validate=True)
    def get(self):
        """Endpoint para validar a autenticidade de um badge."""
        logging.log(logging.INFO, f"Endpoint para validar a autenticidade de um badge: {request.json}")
        data = request.json
        result = business.badge_valid(data)
        return jsonify(result)

      
user_badges_model = ns.model('UserBadgesRequest', {
    'user_id': fields.String(required=True, description='ID do usuário para o qual os badges serão buscados')
})

@ns.route('/get_user_badges')
class GetUserBadges(Resource):
    @ns.doc(
        description="Obter a lista de badges de um usuário específico via JSON.",
        responses={
            200: "Lista de badges retornada com sucesso",
            400: "Dados inválidos",
            404: "Usuário não encontrado",
            418: "Erro interno da aplicação"
        }
    )
    @ns.expect(user_badges_model, validate=True)
    def get(self):
        """Endpoint para obter a lista de badges de um usuário específico."""
        data = request.json
        result = business.badge_list(data)
        return jsonify(result)

      
badge_holders_model = ns.model('BadgeHoldersRequest', {
    'badge_name': fields.String(required=True, description='Nome do badge para buscar os detentores')
})

@ns.route('/get_badge_holders')
class GetBadgeHolders(Resource):
    @ns.doc(
        description="Obter a lista de usuários que possuem um badge específico via JSON.",
        responses={
            200: "Lista de detentores do badge retornada com sucesso",
            400: "Dados inválidos",
            404: "Badge não encontrado",
            418: "Erro interno da aplicação"
        }
    )
    @ns.expect(badge_holders_model, validate=True)
    def get(self):
        """Endpoint para obter a lista de usuários que possuem um badge específico."""
        data = request.json
        result = business.badge_holder(data)
        return jsonify(result)

      
linkedin_post_model = ns.model('LinkedInPostRequest', {
    'badge_guid': fields.String(required=True, description='GUID do badge para gerar a postagem')
})

@ns.route('/get_linkedin_post')
class GetLinkedInPost(Resource):
    @ns.doc(
        description="Gerar um texto sugerido para postagem no LinkedIn sobre um badge via JSON.",
        responses={
            200: "Postagem gerada com sucesso",
            400: "Dados inválidos",
            404: "Badge não encontrado",
            418: "Erro interno da aplicação"
        }
    )
    @ns.expect(linkedin_post_model, validate=True)
    def get(self):
        """Endpoint para gerar um texto sugerido para postagem no LinkedIn sobre um badge."""
        data = request.json
        result = business.linkedin_post(data)
        return jsonify(result)

