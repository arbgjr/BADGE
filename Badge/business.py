import logging
import os
import io
import uuid
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import qrcode
import gnupg

from .database import Database
from . import helpers

# Configuração do cliente Azure App Configuration
try:
    # Inicialização do GnuPG para criptografia
    # Certifique-se de que o caminho para o diretório GPG está correto e acessível
    gpg_home = os.getenv('GPG_HOME', '/path/to/.gnupg')
    gpg = gnupg.GPG(gnupghome=gpg_home)

    # Verificar se o GnuPG está configurado corretamente
    if not gpg.list_keys():
        raise EnvironmentError("GPG não está configurado corretamente ou não tem chaves disponíveis.")

except ValueError as ve:
    logging.error(f"Erro de configuração: {str(ve)}")
    # Tratamento adicional para o erro ou encerrar o programa
    raise

except Exception as e:
    logging.error(f"Erro ao inicializar o cliente Azure App Configuration: {str(e)}")
    # Tratamento adicional para o erro ou encerrar o programa
    raise

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
 
        badge_guid = str(uuid.uuid4())
        concatenated_data = f"{badge_guid}|{owner_name}|{issuer_name}"
        encrypted_data = helpers.encrypt_data(concatenated_data)
        
        draw = ImageDraw.Draw(badge_template)
        css_url = 'https://fonts.googleapis.com/css2?family=Rubik&display=swap'
        font_size = 15
        font = helpers.load_font_from_google_fonts(css_url, font_size)
        if font is None:
            logging.error("Falha ao carregar a fonte Rubik.")
            return {"error": "Falha ao carregar a fonte Rubik."}, 500 

        draw.text((10, 10), f"Owner: {owner_name}", font=font, fill=(0, 0, 0))
        draw.text((10, 30), f"Issuer: {issuer_name}", font=font, fill=(0, 0, 0))

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(f"{base_url}?data={encrypted_data}")
        qr.make(fit=True)
        qr_code_img = qr.make_image(fill='black', back_color='white')
        badge_template.paste(qr_code_img, (10, 50))

        exif_data = {"0th": {piexif.ImageIFD.Make: issuer_name.encode()}}
        badge_with_exif = helpers.insert_exif(badge_template, exif_data)
        badge_bytes_io = io.BytesIO()
        badge_with_exif.save(badge_bytes_io, format='JPEG')
        badge_hash = helpers.generate_image_hash(badge_with_exif)
        badge_base64 = base64.b64encode(badge_bytes_io.getvalue()).decode('utf-8')
        signed_hash = gpg.sign(badge_hash)

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

        decrypted_data = gpg.decrypt(encrypted_data)
        if not decrypted_data.ok:
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
            return {"error": "Nenhum badge encontrado para o usuário"}), 404

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

def linkedin_post
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
        
        
