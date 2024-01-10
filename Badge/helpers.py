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
from azure.functions import HttpRequest, HttpResponse as azfunc
from flask import Flask, jsonify, request
from azure.identity import DefaultAzureCredential
from azure.appconfiguration import AzureAppConfigurationClient

# Configuração do cliente Azure App Configuration
try:
    # Inicializar credenciais
    credential = DefaultAzureCredential()

    # Obter a string de conexão da variável de ambiente
    connection_string = os.getenv("CUSTOMCONNSTR_AppConfigConnectionString")

    # Verificar se a string de conexão existe
    if not connection_string:
        raise ValueError("A variável de ambiente 'AppConfigConnectionString' não está definida.")

    # Criar cliente de configuração do Azure
    client = AzureAppConfigurationClient.from_connection_string(connection_string)

except ValueError as ve:
    logging.error(f"Erro de configuração: {str(ve)}")
    # Tratamento adicional para o erro ou encerrar o programa
    raise

except Exception as e:
    logging.error(f"Erro ao inicializar o cliente Azure App Configuration: {str(e)}")
    # Tratamento adicional para o erro ou encerrar o programa
    raise

# Funções auxiliares
def get_app_config_setting(key):
    try:
        # Verificar se a chave fornecida é válida
        if not key or not isinstance(key, str):
            logging.error("Chave de configuração inválida ou nula fornecida.")
            return None

        # Obter a configuração
        config_setting = client.get_configuration_setting(key)

        # Verificar se a configuração foi encontrada
        if not config_setting:
            logging.warning(f"Configuração para a chave '{key}' não encontrada.")
            return None

        return config_setting.value

    except Exception as e:
        logging.error(f"Erro ao obter a configuração para a chave '{key}': {str(e)}")
        return None

def encrypt_data(data):
    try:
        # Verificar se os dados de entrada são válidos
        if data is None:
            logging.error("Dados fornecidos para criptografia estão vazios ou nulos.")
            return None

        # Obter a ID da chave GPG da configuração
        gpg_key_id = get_app_config_setting('GpgKeyId')
        if not gpg_key_id:
            logging.error("ID da chave GPG não está configurada.")
            return None

        # Criar uma instância GPG
        gpg = gnupg.GPG()

        # Criptografar os dados
        encrypted_data = gpg.encrypt(data, recipients=[gpg_key_id])
        if not encrypted_data.ok:
            logging.error(f"Falha na criptografia: {encrypted_data.status}")
            return None

        return str(encrypted_data)

    except Exception as e:
        logging.error(f"Erro ao criptografar dados: {str(e)}")
        return None

def load_image_from_base64(base64_img):
    try:
        # Verificar se a entrada é uma string
        if not isinstance(base64_img, str):
            logging.error("Dados de entrada não são uma string base64 válida.")
            return None

        # Decodificar dados base64
        img_data = base64.b64decode(base64_img)

        # Carregar imagem a partir dos dados decodificados
        image = Image.open(io.BytesIO(img_data))
        return image

    except base64.binascii.Error:
        # Erro específico para problemas relacionados à decodificação base64
        logging.error("Erro na decodificação dos dados base64.")
    except IOError:
        # Erro específico para problemas relacionados à I/O ao abrir a imagem
        logging.error("Não foi possível abrir a imagem a partir dos dados base64.")
    except Exception as e:
        # Captura outros tipos de exceções
        logging.error(f"Erro ao carregar imagem de base64: {str(e)}")
    return None


def load_font(font_path, size):
    try:
        # Carregar a fonte
        font = ImageFont.truetype(font_path, size)
        return font
    except IOError:
        # Erro específico para problemas relacionados à I/O, como arquivo de fonte não encontrado
        logging.error(f"Não foi possível carregar a fonte: {font_path}")
    except Exception as e:
        # Captura outros tipos de exceções
        logging.error(f"Erro ao carregar a fonte ({font_path}): {str(e)}")
    return None

def generate_image_hash(image):
    try:
        # Validar os dados de entrada
        if not isinstance(image, Image.Image):
            logging.error("O objeto fornecido não é uma imagem válida.")
            return None

        # Geração do hash da imagem
        img_hash = hashlib.sha256()
        img_hash.update(image.tobytes())
        return img_hash.hexdigest()

    except Exception as e:
        logging.error(f"Erro ao gerar o hash da imagem: {str(e)}")
        return None

def insert_exif(image, exif_data):
    try:
        # Validar os dados de entrada
        if not isinstance(image, Image.Image):
            logging.error("O objeto fornecido não é uma imagem válida.")
            return None

        if not isinstance(exif_data, dict):
            logging.error("Os dados EXIF fornecidos não estão no formato de dicionário.")
            return None

        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
        for key, value in exif_data.items():
            exif_dict[key] = value

        exif_bytes = piexif.dump(exif_dict)

        # Salvar a imagem temporariamente com os dados EXIF
        temp_img_path = "temp_img.jpg"
        image.save(temp_img_path, "jpeg", exif=exif_bytes)

        # Reabrir e retornar a imagem
        return Image.open(temp_img_path)

    except Exception as e:
        logging.error(f"Erro ao inserir dados EXIF na imagem: {str(e)}")
        return None

    finally:
        # Limpar a imagem temporária, se existir
        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)

def generate_badge(data):
    try:
        # Validação e análise dos dados recebidos
        if 'owner_name' not in data or 'issuer_name' not in data:
            logging.error("Dados de entrada faltando: 'owner_name' ou 'issuer_name'")
            return {"error": "Dados de entrada inválidos"}, 400

        owner_name = data['owner_name']
        issuer_name = data['issuer_name']

        logging.info(f"Gerando badge para {owner_name} emitido por {issuer_name}")

        badge_template_base64 = get_app_config_setting('BadgeTemplateBase64')
        if not badge_template_base64:
            logging.error("Template de badge não encontrado.")
            return {"error": "Template de badge não encontrado"}, 500

        # Carregar template de imagem
        badge_template = load_image_from_base64(badge_template_base64)
        if not badge_template:
            logging.error("Falha ao carregar template de badge.")
            return {"error": "Falha ao carregar template de badge"}, 500

        base_url = get_app_config_setting('BadgeVerificationUrl')
        if not base_url:
            logging.error("Falha ao carregar a URL de verificação do badge.")
            return {"error": "Falha ao carregar url de verificação do badge"}, 500
 
        badge_guid = str(uuid.uuid4())
        concatenated_data = f"{badge_guid}|{owner_name}|{issuer_name}"
        encrypted_data = encrypt_data(concatenated_data)
        
        draw = ImageDraw.Draw(badge_template)
        font = load_font("Arial.ttf", 15)
        draw.text((10, 10), f"Owner: {owner_name}", font=font, fill=(0, 0, 0))
        draw.text((10, 30), f"Issuer: {issuer_name}", font=font, fill=(0, 0, 0))

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(f"{base_url}?data={encrypted_data}")
        qr.make(fit=True)
        qr_code_img = qr.make_image(fill='black', back_color='white')
        badge_template.paste(qr_code_img, (10, 50))

        exif_data = {"0th": {piexif.ImageIFD.Make: issuer_name.encode()}}
        badge_with_exif = insert_exif(badge_template, exif_data)
        badge_bytes_io = io.BytesIO()
        badge_with_exif.save(badge_bytes_io, format='JPEG')
        badge_hash = generate_image_hash(badge_with_exif)
        badge_base64 = base64.b64encode(badge_bytes_io.getvalue()).decode('utf-8')
        signed_hash = gpg.sign(badge_hash)

        conn_str = get_app_config_setting('SqlConnectionString')
        with pyodbc.connect(conn_str) as conn:
          cursor = conn.cursor()
          cursor.execute("INSERT INTO Badges (GUID, BadgeHash, BadgeData, CreationDate, ExpiryDate, OwnerName, IssuerName, PgpSignature, BadgeBase64) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
             badge_guid, badge_hash, badge_data, datetime.now(), datetime.now() + timedelta(days=365), owner_name, issuer_name, str(signed_hash), badge_base64)
       conn.commit() 

        return {"guid": badge_guid, "hash": badge_hash}

    except Exception as e:
        logging.error(f"Erro ao gerar badge: {str(e)}")
        return {"error": "Erro interno no servidor"}, 500

