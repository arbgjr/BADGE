import logging

from .database import Database
from . import helpers

def generate_badge(data):
    try:
        # Validação e análise dos dados recebidos
        if 'owner_name' not in data or 'issuer_name' not in data:
            logging.error("Dados de entrada faltando: 'owner_name' ou 'issuer_name'")
            return {"error": "Dados de entrada inválidos"}, 400

        owner_name = data['owner_name']
        issuer_name = data['issuer_name']

        logging.info(f"Gerando badge para {owner_name} emitido por {issuer_name}")

        badge_template_base64 = helpers.get_app_config_setting('BadgeTemplateBase64')
        if not badge_template_base64:
            logging.error("Template de badge não encontrado.")
            return {"error": "Template de badge não encontrado"}, 500

        # Carregar template de imagem
        badge_template = helpers.load_image_from_base64(badge_template_base64)
        if not badge_template:
            logging.error("Falha ao carregar template de badge.")
            return {"error": "Falha ao carregar template de badge"}, 500

        base_url = helpers.get_app_config_setting('BadgeVerificationUrl')
        if not base_url:
            logging.error("Falha ao carregar a URL de verificação do badge.")
            return {"error": "Falha ao carregar url de verificação do badge"}, 500
 
        badge_guid = helpers.gera_guid_badge() 
        concatenated_data = f"{badge_guid}|{owner_name}|{issuer_name}"
        encrypted_data = helpers.encrypt_data(concatenated_data)

        badge_template = helpers.add_text_to_badge(badge_template, owner_name, issuer_name)
        if badge_template is None:
            logging.error("Falha ao editar badge. ")
            return {"error": "Falha ao editar badge."}, 500 

        qr_code_img = helpers.create_qr_code(encrypted_data, base_url, box_size=10, border=4)
        if qr_code_img is None:
            logging.error("Falha ao gerar QR Code. ")
            return {"error": "Falha ao editar badge."}, 500 

        badge_template.paste(qr_code_img, (10, 50))

        result = helpers.process_badge_image(badge_template, issuer_name)
        if result is not None:
            badge_hash, badge_base64, signed_hash = result
        else:
            logging.error("Falha ao editar exif do badge. ")
            return {"error": "Falha ao editar badge."}, 500 

        db = Database()
        success = db.insert_badge(badge_guid, badge_hash, badge_data, owner_name, issuer_name, signed_hash, badge_base64)
        if not success:
            current_app.logger.error("Falha ao inserir o badge no banco de dados.")
            return {"error": "Falha ao inserir o badge no banco de dados"}, 500

        return {"guid": badge_guid, "hash": badge_hash}

    except Exception as e:
        logging.error(f"Erro ao gerar badge: {str(e)}")
        return {"error": "Erro interno no servidor"}, 500

def badge_image(data):
    try:
        # Validação e análise dos dados recebidos
        if 'badge_guid' not in data:
            logging.error("Dados de entrada faltando: 'badge_guid'")
            return {"error": "Dados de entrada inválidos"}, 400

        badge_guid = data['badge_guid']
        
        logging.info(f"Recuoerando badge para {badge_guid} emitido por {issuer_name}")
        
        db = Database()
        row = db.get_badge_image(badge_guid)
        if row:
            return {"badge_image": row[0]}
        else:
            current_app.logger.error("Falha ao rechperar o badge no banco de dados.")
            return {"error": "Badge não encontrado"}, 404
    except Exception as e:
        logging.error(f"Erro ao recuoerar badge: {str(e)}")
        return {"error": "Erro interno no servidor"}, 500

def badge_valid(data):
    try:
        # Validação e análise dos dados recebidos
        if 'data' not in data:
            logging.error("Dados de entrada faltando: 'data'")
            return {"error": "Dados de entrada inválidos"}, 400

        encrypted_data = data['data']
                
        logging.info("Analisando dados enviados.")

        if not encrypted_data:
            logging.error("Dados criptogtafados não informados.")
            return {"error": "Dados criptografados são obrigatórios"}, 400
            
        logging.info(f"Descriptografando dados enviados: {encrypted_data}")

        decrypted_data = helpers.decrypt_data(encrypted_data)
        if not decrypted_data:
            logging.error("Não foi possível descriptograr dados informados.")
            return {"error": "Falha na descriptografia"}, 400 

        logging.info(f"Decodificando dados enviados: {encrypted_data}")

        try:
            badge_guid, owner_name, issuer_name = decrypted_data.data.split("|")
            logging.info(f"Validando badge {badge_guid} emitido por {issuer_name}")

        except ValueError:
            logging.error("Não foi possível decodificar dados informados.")
            return {"error": "Dados decodificados inválidos"}, 400
        
        db = Database()
        badge = db.validate_badge(badge_guid, owner_name, issuer_name)
        if badge:
            return {"valid": True, "badge_info": badge}
        else:
            return {"valid": False, "error": "Badge não encontrado ou informações não correspondem"}, 404
    except Exception as e:
        logging.error(f"Erro ao validar badge: {str(e)}")
        return {"error": "Erro interno no servidor"}, 500
     
def badge_list(data):
    try:
        
        # Validação e análise dos dados recebidos
        if 'user_id' not in data:
            logging.error("Dados de entrada faltando: 'user_id'")
            return {"error": "Dados de entrada inválidos"}, 400

        user_id = data['user_id']

        db = Database()
        badges = db.get_user_badges(user_id)

        if not badges:
            return {"error": "Nenhum badge encontrado para o usuário"}, 404

        base_url = helpers.get_app_config_setting('BadgeVerificationUrl')
        if not base_url:
            logging.error("Falha ao carregar a URL de verificação do badge.")
            return {"error": "Falha ao carregar url de verificação do badge"}, 500

        badge_list = []
        for badge in badges:
            badge_guid = badge[0]
            badge_name = badge[1]
            validation_url = f"{base_url}/validate?badge_guid={badge_guid}"
            badge_list.append({"name": badge_name, "validation_url": validation_url})

        return badge_list

    except Exception as e:
        logging.error(f"Erro ao listar badges: {str(e)}")
        return {"error": "Erro interno no servidor"}, 500

def badge_holder(data):
    try:
      
        # Validação e análise dos dados recebidos
        if 'badge_name' not in data:
            logging.error("Dados de entrada faltando: 'badge_name'")
            return {"error": "Dados de entrada inválidos"}, 400

        badge_name = data['badge_name']

        db = Database()
        badge_holders = db.get_badge_holders(badge_name)

        if not badge_holders:
            return {"error": "Nenhum detentor de badge encontrado para este nome de badge"}, 404

        users = [user[0] for user in badge_holders]
        return users

    except Exception as e:
        logging.error(f"Erro ao recuperar detentores do badge: {str(e)}")
        return {"error": "Erro interno no servidor"}, 500

def linkedin_post(data):
    try:
      
        # Validação e análise dos dados recebidos
        if 'badge_guid' not in data:
            logging.error("Dados de entrada faltando: 'badge_guid'")
            return {"error": "Dados de entrada inválidos"}, 400

        badge_guid = data['badge_guid']

        db = Database()
        badge_info = db.get_badge_info_for_post(badge_guid)

        if not badge:
            return {"error": "Badge não encontrado"}, 404

        badge_name, additional_info = badge

        base_url = helpers.get_app_config_setting('BadgeVerificationUrl')
        if not base_url:
            logging.error("Falha ao carregar a URL de verificação do badge.")
            return {"error": "Falha ao carregar url de verificação do badge"}, 500

        # URL de validação do badge
        validation_url = f"{base_url}/validate?badge_guid={badge_guid}"
        
        # Texto sugerido para postagem
        post_text = helpers.get_app_config_setting('LinkedInPost')
        if not post_text:
          post_text = (
            f"Estou muito feliz em compartilhar que acabei de conquistar um novo badge: {badge_name}! "
            f"Esta conquista representa {additional_info}. "
            f"Você pode verificar a autenticidade do meu badge aqui: {validation_url} "
            "#Conquista #Badge #DesenvolvimentoProfissional"
          )
        
        return {"linkedin_post": post_text}
        
    except Exception as e:
        logging.error(f"Erro ao recuperar a mensagem do post do LinkedIn: {str(e)}")
        return {"error": "Erro interno no servidor"}, 500
        
        
