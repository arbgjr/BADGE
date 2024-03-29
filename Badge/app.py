from flask import Flask, jsonify, request 
from flask_restx import Resource, Api, fields, reqparse, Namespace
import traceback
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Criação da aplicação Flask
application = Flask(__name__)

@application.errorhandler(Exception)
def handle_exception(e):
    # Mensagem de erro personalizada
    error_message = f"Erro inesperado: {type(e).__name__} - {str(e)}"
    
    # Registra a mensagem de erro e o stack trace completo da exceção
    logging.exception(error_message)
    
    # Retorna uma resposta JSON com a mensagem de erro e um código de status HTTP 500
    return jsonify({"error": "Erro interno no servidor", "message": error_message}), 500

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
        logging.info(f"[app] Endpoint para retornar a versão do badge.")
        version = business.get_api_version()
        return jsonify({"version": version})

@ns.route('/ping')
class Ping(Resource):
    def get(self):
        return {"message": "API ativa"}, 200
      
      
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
        logging.info(f"[app] Endpoint para emitir um novo badge.")
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
        try:
            if request.data:
                data = request.get_json(silent=True)
                result = business.badge_image(data)
                return jsonify(result)
            else:
                return jsonify({"error": "Nenhum dado enviado"}), 400
        except Exception as e:
            logging.exception("Erro ao processar a solicitação:")
            return jsonify({"error": "Erro interno no servidor"}), 500

      
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
        logging.info(f"Endpoint para validar a autenticidade de um badge: {request.json}")
        try:
            if request.data:
                data = request.get_json(silent=True)
                result = business.badge_valid(data)
                return jsonify(result)
            else:
                return jsonify({"error": "Nenhum dado enviado"}), 400
        except Exception as e:
            logging.exception("Erro ao processar a solicitação:")
            return jsonify({"error": "Erro interno no servidor"}), 500

      
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
        try:
            if request.data:
                data = request.get_json(silent=True)
                result = business.badge_list(data)
                return jsonify(result)
            else:
                return jsonify({"error": "Nenhum dado enviado"}), 400
        except Exception as e:
            logging.exception("Erro ao processar a solicitação:")
            return jsonify({"error": "Erro interno no servidor"}), 500

      
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
        try:
            if request.data:
                data = request.get_json(silent=True)
                result = business.badge_holder(data)
                return jsonify(result)
            else:
                return jsonify({"error": "Nenhum dado enviado"}), 400
        except Exception as e:
            logging.exception("Erro ao processar a solicitação:")
            return jsonify({"error": "Erro interno no servidor"}), 500

      
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
        try:
            if request.data:
                data = request.get_json(silent=True)
                result = business.linkedin_post(data)
                return jsonify(result)
            else:
                return jsonify({"error": "Nenhum dado enviado"}), 400
        except Exception as e:
            logging.exception("Erro ao processar a solicitação:")
            return jsonify({"error": "Erro interno no servidor"}), 500
