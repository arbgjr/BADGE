import traceback
import pyodbc
import os
import re

from .database import Database
from . import helpers
from . import azure
from . import logger

# Configuração do cliente Azure
azure_client = azure.Azure()
        
def get_configs():
    try:
        logger.log(logger.LogLevel.DEBUG, f"[business] Endpoint para recuperar configurações.")
        data = {}
        data['APPINSIGHTS_INSTRUMENTATIONKEY'] = os.environ["APPINSIGHTS_INSTRUMENTATIONKEY"]
        data['AzKVURI'] = azure_client.get_app_config_setting("AzKVURI")
        data['BadgeTemplateBase64'] = azure_client.get_app_config_setting('BadgeTemplateBase64')
        data['BadgeVerificationUrl'] = azure_client.get_app_config_setting('BadgeVerificationUrl')
        data['PGPPrivateKeyName'] = azure_client.get_app_config_setting('PGPPrivateKeyName')
        public_key_name = azure_client.get_app_config_setting('PGPPublicKeyName') 
        data['PGPPublicKeyName'] = public_key_name
        data['LinkedInPost'] = azure_client.get_app_config_setting('LinkedInPost')
        conexao = azure_client.get_key_vault_secret('SqlConnectionString')
        conexao = re.sub(r"User ID=[^;]+", "User ID=***", conexao)
        conexao = re.sub(r"Password=[^;]+", "Password=***", conexao)
        data['SqlConnectionString'] = conexao
        conexao = os.getenv("CUSTOMCONNSTR_AppConfigConnectionString")
        conexao = re.sub(r"Id=[^;]+", "Id=***", conexao)
        conexao = re.sub(r"Secret=[^;]+", "Secret=***", conexao)
        data['AppConfigConnectionString'] = conexao
        data['PGPPublicKey'] = azure_client.get_key_vault_secret(public_key_name)
        data['pyodbcDrivers'] = pyodbc.drivers()

        return data

    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.log(logger.LogLevel.ERROR, f"Erro ao recuperar informações: {str(e)}\nStack Trace:\n{stack_trace}")
        return {"error": "Erro interno no servidor"}, 500
    
        
def generate_badge(data):
    try:
        # Validação e análise dos dados recebidos
        logger.log(logger.LogLevel.DEBUG, f"[business] Endpoint para emitir um novo badge.")
        if 'owner_name' not in data or 'issuer_name' not in data:
            logger.log(logger.LogLevel.ERROR, "Dados de entrada faltando: 'owner_name' ou 'issuer_name'")
            return {"error": "Dados de entrada inválidos"}, 400

        owner_name = data['owner_name']
        issuer_name = data['issuer_name']

        logger.log(logger.LogLevel.DEBUG, f"Gerando badge para {owner_name} emitido por {issuer_name}")

        db = Database()

        # Carregar template de imagem
        logger.log(logger.LogLevel.DEBUG, f"[business] Recuperando template do Badge em base64.")
        template_id = int(azure_client.get_app_config_setting('BadgeTemplateBase64'))
        logger.log(logger.LogLevel.DEBUG, f"[business] Template do Badge em base64: {template_id}.")
        if not template_id:
            logger.log(logger.LogLevel.ERROR, "Falha ao carregar id do template do badge.")
            return {"error": "Falha ao carregar id do template do badge"}, 500
        
        badge_template_base64  = db.get_badge_template(template_id)
        logger.log(logger.LogLevel.DEBUG, f"[business] Template do Badge em base64: {badge_template_base64}.")  
        if not badge_template_base64:
            logger.log(logger.LogLevel.ERROR, "Template de badge não encontrado.")
            return {"error": "Template de badge não encontrado"}, 500

        logger.log(logger.LogLevel.DEBUG, f"[business] Carregar template de imagem.")
        badge_template = helpers.load_image_from_base64(badge_template_base64)
        logger.log(logger.LogLevel.DEBUG, f"[business] Template do Badge: {badge_template}.")
        if not badge_template:
            logger.log(logger.LogLevel.ERROR, "Falha ao carregar template de badge.")
            return {"error": "Falha ao carregar template de badge"}, 500

        logger.log(logger.LogLevel.DEBUG, f"[business] Carregar URL de verificação do Badge.")
        base_url = azure_client.get_app_config_setting('BadgeVerificationUrl')
        logger.log(logger.LogLevel.DEBUG, f"[business] URL de verificação do Badge: {base_url}.")
        if not base_url:
            logger.log(logger.LogLevel.ERROR, "Falha ao carregar a URL de verificação do badge.")
            return {"error": "Falha ao carregar url de verificação do badge"}, 500
        
        if not helpers.validar_url_https(base_url):
            logger.log(logger.LogLevel.ERROR, "URL de verificação do badge inválida.")
            return {"error": "URL de verificação do badge inválida."}, 500
 
        logger.log(logger.LogLevel.DEBUG, f"[business] Gerando GUID do Badge.")
        badge_guid = helpers.gera_guid_badge() 
        logger.log(logger.LogLevel.DEBUG, f"[business] Gerando dados de verificação do Badge: {badge_guid}.")
        concatenated_data = f"{badge_guid}|{owner_name}|{issuer_name}"
        encrypted_data = helpers.encrypt_data(concatenated_data)

        logger.log(logger.LogLevel.DEBUG, f"[business] Adicionando texto ao Badge.")
        badge_template = helpers.add_text_to_badge(badge_template, owner_name, issuer_name)
        if badge_template is None:
            logger.log(logger.LogLevel.ERROR, "Falha ao editar badge. ")
            return {"error": "Falha ao editar badge."}, 500 

        logger.log(logger.LogLevel.DEBUG, f"[business] Gerando QRCode do Badge.")
        qr_code_img = helpers.create_qr_code(encrypted_data, base_url, box_size=10, border=4)
        if qr_code_img is None:
            logger.log(logger.LogLevel.ERROR, "Falha ao gerar QR Code. ")
            return {"error": "Falha ao editar badge."}, 500 

        logger.log(logger.LogLevel.DEBUG, f"[business] Inerindo Qrcode no Badge.")
        badge_template.paste(qr_code_img, (10, 50))

        logger.log(logger.LogLevel.DEBUG, f"[business] Inserindo dados EXIF do Badge.")
        result = helpers.process_badge_image(badge_template, issuer_name)
        if result is not None:
            badge_hash, badge_base64, signed_hash = result
        else:
            logger.log(logger.LogLevel.ERROR, "Falha ao editar exif do badge. ")
            return {"error": "Falha ao editar badge."}, 500 

        logger.log(logger.LogLevel.DEBUG, f"[business] Gerando Badge no banco.")
        success = db.insert_badge(badge_guid, badge_hash, owner_name, issuer_name, signed_hash, badge_base64)
        if not success:
            logger.log(logger.LogLevel.ERROR, "Falha ao inserir o badge no banco de dados.")
            return {"error": "Falha ao inserir o badge no banco de dados"}, 500

        return {"guid": badge_guid, "hash": badge_hash}

    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.log(logger.LogLevel.ERROR, f"Erro ao gerar badge: {str(e)}\nStack Trace:\n{stack_trace}")
        return {"error": "Erro interno no servidor"}, 500

def badge_image(data):
    try:
        # Validação e análise dos dados recebidos
        if 'badge_guid' not in data:
            logger.log(logger.LogLevel.ERROR, "Dados de entrada faltando: 'badge_guid'")
            return {"error": "Dados de entrada inválidos"}, 400

        badge_guid = data['badge_guid']
        
        logger.log(logger.LogLevel.DEBUG, f"Recuperando badge para {badge_guid}.")
        
        db = Database()
        row = db.get_badge_image(badge_guid)
        if row:
            return {"badge_image": row[0]}
        else:
            logger.log(logger.LogLevel.ERROR, "Falha ao rechperar o badge no banco de dados.")
            return {"error": "Badge não encontrado"}, 404
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.log(logger.LogLevel.ERROR, f"Erro ao recuoerar badge: {str(e)}\nStack Trace:\n{stack_trace}")
        return {"error": "Erro interno no servidor"}, 500

def badge_valid(data):
    try:
        # Validação e análise dos dados recebidos
        if 'data' not in data:
            logger.log(logger.LogLevel.ERROR, "Dados de entrada faltando: 'data'")
            return {"error": "Dados de entrada inválidos"}, 400

        encrypted_data = data['data']
                
        logger.log(logger.LogLevel.DEBUG, "Analisando dados enviados.")

        if not encrypted_data:
            logger.log(logger.LogLevel.ERROR, "Dados criptogtafados não informados.")
            return {"error": "Dados criptografados são obrigatórios"}, 400
            
        logger.log(logger.LogLevel.DEBUG, f"Descriptografando dados enviados: {encrypted_data}")

        decrypted_data = helpers.decrypt_data(encrypted_data)
        if not decrypted_data:
            logger.log(logger.LogLevel.ERROR, "Não foi possível descriptograr dados informados.")
            return {"error": "Falha na descriptografia"}, 400 

        logger.log(logger.LogLevel.DEBUG, f"Decodificando dados enviados: {encrypted_data}")

        try:
            badge_guid, owner_name, issuer_name = decrypted_data.data.split("|")
            logger.log(logger.LogLevel.DEBUG, f"Validando badge {badge_guid} emitido por {issuer_name}")

        except ValueError:
            stack_trace = traceback.format_exc()
            logger.log(logger.LogLevel.ERROR, "Não foi possível decodificar dados informados.")
            return {"error": "Dados decodificados inválidos"}, 400
        
        db = Database()
        badge = db.validate_badge(badge_guid, owner_name, issuer_name)
        if badge:
            return {"valid": True, "badge_info": badge}
        else:
            return {"valid": False, "error": "Badge não encontrado ou informações não correspondem"}, 404
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.log(logger.LogLevel.ERROR, f"Erro ao validar badge: {str(e)}\nStack Trace:\n{stack_trace}")
        return {"error": "Erro interno no servidor"}, 500
     
def badge_list(data):
    try:
        
        # Validação e análise dos dados recebidos
        if 'user_id' not in data:
            logger.log(logger.LogLevel.ERROR, "Dados de entrada faltando: 'user_id'")
            return {"error": "Dados de entrada inválidos"}, 400

        user_id = data['user_id']

        db = Database()
        badges = db.get_user_badges(user_id)

        if not badges:
            return {"error": "Nenhum badge encontrado para o usuário"}, 404

        base_url = azure_client.get_app_config_setting('BadgeVerificationUrl')
        if not base_url:
            logger.log(logger.LogLevel.ERROR, "Falha ao carregar a URL de verificação do badge.")
            return {"error": "Falha ao carregar url de verificação do badge"}, 500

        badge_list = []
        for badge in badges:
            badge_guid = badge[0]
            badge_name = badge[1]
            validation_url = f"{base_url}/validate?badge_guid={badge_guid}"
            badge_list.append({"name": badge_name, "validation_url": validation_url})

        return badge_list

    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.log(logger.LogLevel.ERROR, f"Erro ao listar badges: {str(e)}\nStack Trace:\n{stack_trace}")
        return {"error": "Erro interno no servidor"}, 500

def badge_holder(data):
    try:
      
        # Validação e análise dos dados recebidos
        if 'badge_name' not in data:
            logger.log(logger.LogLevel.ERROR, "Dados de entrada faltando: 'badge_name'")
            return {"error": "Dados de entrada inválidos"}, 400

        badge_name = data['badge_name']

        db = Database()
        badge_holders = db.get_badge_holders(badge_name)

        if not badge_holders:
            return {"error": "Nenhum detentor de badge encontrado para este nome de badge"}, 404

        users = [user[0] for user in badge_holders]
        return users

    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.log(logger.LogLevel.ERROR, f"Erro ao recuperar detentores do badge: {str(e)}\nStack Trace:\n{stack_trace}")
        return {"error": "Erro interno no servidor"}, 500

def linkedin_post(data):
    try:
      
        # Validação e análise dos dados recebidos
        if 'badge_guid' not in data:
            logger.log(logger.LogLevel.ERROR, "Dados de entrada faltando: 'badge_guid'")
            return {"error": "Dados de entrada inválidos"}, 400

        badge_guid = data['badge_guid']

        db = Database()
        badge_info = db.get_badge_info_for_post(badge_guid)

        if not badge_info:
            return {"error": "Badge não encontrado"}, 404

        badge_name, additional_info = badge_info

        base_url = azure_client.get_app_config_setting('BadgeVerificationUrl')
        if not base_url:
            logger.log(logger.LogLevel.ERROR, "Falha ao carregar a URL de verificação do badge.")
            return {"error": "Falha ao carregar url de verificação do badge"}, 500

        # URL de validação do badge
        validation_url = f"{base_url}/validate?badge_guid={badge_guid}"
        
        # Texto sugerido para postagem
        post_text = azure_client.get_app_config_setting('LinkedInPost')
        if not post_text:
          post_text = (
            f"Estou muito feliz em compartilhar que acabei de conquistar um novo badge: {badge_name}! "
            f"Esta conquista representa {additional_info}. "
            f"Você pode verificar a autenticidade do meu badge aqui: {validation_url} "
            "#Conquista #Badge #DesenvolvimentoProfissional"
          )
        
        return {"linkedin_post": post_text}
        
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.log(logger.LogLevel.ERROR, f"Erro ao recuperar a mensagem do post do LinkedIn: {str(e)}\nStack Trace:\n{stack_trace}")
        return {"error": "Erro interno no servidor"}, 500
        
        
