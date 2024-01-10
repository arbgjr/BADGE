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
credential = DefaultAzureCredential()
connection_string = os.environ["CUSTOMCONNSTR_AppConfigConnectionString"] 
if connection_string is None:
    raise ValueError("A variável de ambiente 'AppConfigConnectionString' não está definida.")
client = AzureAppConfigurationClient.from_connection_string(connection_string)

# Funções auxiliares
def get_app_config_setting(key):
	return client.get_configuration_setting(key).value

def encrypt_data(data):
	gpg_key_id = get_app_config_setting('GpgKeyId')
	encrypted_data = gpg.encrypt(data, recipients=[gpg_key_id])
	return str(encrypted_data)

def load_image_from_base64(base64_img):
	img_data = base64.b64decode(base64_img)
	return Image.open(io.BytesIO(img_data))

def load_font(font_path, size):
	return ImageFont.truetype(font_path, size)

def generate_image_hash(image):
	img_hash = hashlib.sha256()
	img_hash.update(image.tobytes())
	return img_hash.hexdigest()

def insert_exif(image, exif_data):
	exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
	for key, value in exif_data.items():
		exif_dict[key] = value
	exif_bytes = piexif.dump(exif_dict)
	image.save("temp_img.jpg", "jpeg", exif=exif_bytes)
	return Image.open("temp_img.jpg")

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


