import logging
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.trace import config_integration
import os
import io
import base64
import uuid
import hashlib
import pyodbc
from datetime import datetime, timedelta
import piexif
import re
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import qrcode
import gnupg
from azure.functions import HttpRequest, HttpResponse as azfunc
from flask import Flask, jsonify, request
from azure.identity import DefaultAzureCredential
from azure.appconfiguration import AzureAppConfigurationClient
import requests
import tempfile
from azure.keyvault.secrets import SecretClient

# Configurar o log
config_integration.trace_integrations(['logging'])
logger = logging.getLogger(__name__)
APPINSIGHTS_INSTRUMENTATIONKEY = os.environ["APPINSIGHTS_INSTRUMENTATIONKEY"]
handler = AzureLogHandler(connection_string=f'InstrumentationKey={APPINSIGHTS_INSTRUMENTATIONKEY}')
logger.addHandler(handler)

# Configuração do cliente Azure App Configuration
try:
    # Inicializar credenciais
    logger.info(f"[helpers] Inicializar credenciais.")
    credential = DefaultAzureCredential() 

    # Obter a string de conexão da variável de ambiente
    logger.info(f"[helpers] Obter a string de conexão da variável de ambiente.")
    connection_string = os.getenv("CUSTOMCONNSTR_AppConfigConnectionString")

    # Verificar se a string de conexão existe
    logger.info(f"[helpers] Obter a string de conexão da variável de ambiente") 
    if not connection_string:
        raise ValueError("A variável de ambiente 'AppConfigConnectionString' não está definida.")

    # Criar cliente de configuração do Azure
    logger.info(f"[helpers] Criar cliente de configuração do Azure") 
    client = AzureAppConfigurationClient.from_connection_string(connection_string)
    
except Exception as e:
    logger.error(f"Erro ao inicializar o cliente Azure App Configuration: {str(e)}")
    # Tratamento adicional para o erro ou encerrar o programa
    raise 

except ValueError as ve:
    logger.error(f"Erro de configuração: {str(ve)}")
    # Tratamento adicional para o erro ou encerrar o programa
    raise

def get_app_config_setting(key):
    try:
        # Verificar se a chave fornecida é válida
        logger.info(f"Verificar se a '{key}' fornecida é válida.")
        if not key or not isinstance(key, str):
            logger.error("Chave de configuração inválida ou nula fornecida.")
            return None

        # Obter a configuração
        logger.info(f"Obter a configuração '{key}'.")
        config_setting = client.get_configuration_setting(key)

        # Verificar se a configuração foi encontrada
        if not config_setting:
            logger.warning(f"Configuração para a chave '{key}' não encontrada.")
            return None

        logger.info(f"Valor obtido da configuração '{key}' é '{config_setting.value}'.")
        
        return config_setting.value

    except Exception as e:
        logger.error(f"Erro ao obter a configuração para a chave '{key}': {str(e)}")
        return None 
        
try:
    logger.info(f"Obter a configuração 'AzKVURI'.")
    key_vault_url = get_app_config_setting("AzKVURI")
    logger.info(f"key_vault_url: '{key_vault_url}'")

    logger.info(f"[helpers] Criar cliente do Azure KeyVaut") 
    secret_client = SecretClient(vault_url=key_vault_url, credential=credential)

except ValueError as ve:
    logger.error(f"Erro de configuração: {str(ve)}")
    # Tratamento adicional para o erro ou encerrar o programa
    raise

# Funções auxiliares

def get_key_vault_secret(secret_name):
    try:
        # Verificar se o nome do segredo fornecido é válido
        logger.info(f"Verificar se o '{secret_name}' fornecido é válido.")
        if not secret_name or not isinstance(secret_name, str):
            logger.error("Nome do segredo inválido ou nulo fornecido.")
            return None

        # Obter o segredo do Azure Key Vault
        logger.info(f"Obter o segredo '{secret_name}' do Azure Key Vault.")
        secret = secret_client.get_secret(secret_name)

        # Verificar se o segredo foi encontrado
        if not secret:
            logger.warning(f"Segredo '{secret_name}' não encontrado no Azure Key Vault.")
            return None

        logger.info(f"Valor obtido para o segredo '{secret_name}' é '{secret.value}'.")
        return secret.value

    except Exception as e:
        logger.error(f"Erro ao obter o segredo '{secret_name}' do Azure Key Vault: {str(e)}")
        return None
        
def gera_guid_badge():
    return str(uuid.uuid4())

def get_pgp_private_key():
    private_key_name = get_app_config_setting('PGPPrivateKeyName')
    private_key = get_key_vault_secret(private_key_name)
    return private_key

def get_pgp_public_key():
    public_key_name = get_app_config_setting('PGPPublicKeyName') 
    public_key = get_key_vault_secret(public_key_name)
    return public_key

def decrypt_data(encrypted_data):
    gpg = gnupg.GPG()
    private_key = get_pgp_private_key()
    import_result = gpg.import_keys(private_key)
    
    if not import_result.count:
        raise ValueError("Falha ao importar a chave privada PGP")

    decrypted_data = gpg.decrypt(encrypted_data)
    return str(decrypted_data)

def encrypt_data(data):
    gpg = gnupg.GPG()
    public_key = get_pgp_public_key()
    import_result = gpg.import_keys(public_key)
    
    if not import_result.count:
        raise ValueError("Falha ao importar a chave pública PGP")

    encrypted_data = gpg.encrypt(data, import_result.fingerprints[0])
    if not encrypted_data.ok:
        raise ValueError(f"Falha na criptografia: {encrypted_data.status}")
    
    return str(encrypted_data)

def deprecated_encrypt_data(data):
    try:
        # Verificar se os dados de entrada são válidos
        if data is None:
            logger.error("Dados fornecidos para criptografia estão vazios ou nulos.")
            return None

        # Obter a ID da chave GPG da configuração
        gpg_key_id = get_key_vault_secret('GpgKeyId')
        if not gpg_key_id:
            logger.error("ID da chave GPG não está configurada.")
            return None

        # Criar uma instância GPG
        gpg = gnupg.GPG()

        # Criptografar os dados
        encrypted_data = gpg.encrypt(data, recipients=[gpg_key_id])
        if not encrypted_data.ok:
            logger.error(f"Falha na criptografia: {encrypted_data.status}")
            return None

        return str(encrypted_data)

    except Exception as e:
        logger.error(f"Erro ao criptografar dados: {str(e)}")
        return None

def deprecated_decrypt_data(encrypted_data):
    try:
        # Verificar se os dados criptografados são válidos
        if encrypted_data is None or encrypted_data == "":
            logger.error("Dados fornecidos para descriptografia estão vazios ou nulos.")
            return None

        # Criar uma instância GPG
        gpg = gnupg.GPG()

        # Descriptografar os dados
        decrypted_data = gpg.decrypt(encrypted_data)
        if not decrypted_data.ok:
            logger.error(f"Falha na descriptografia: {decrypted_data.status}")
            return None

        return str(decrypted_data)

    except Exception as e:
        logger.error(f"Erro ao descriptografar dados: {str(e)}")
        return None
        
def load_image_from_base64(base64_img):
    try:
        # Verificar se a entrada é uma string
        if not isinstance(base64_img, str):
            logger.error("Dados de entrada não são uma string base64 válida.")
            return None

        # Decodificar dados base64
        img_data = base64.b64decode(base64_img)

        # Carregar imagem a partir dos dados decodificados
        image = Image.open(io.BytesIO(img_data))
        return image

    except base64.binascii.Error:
        # Erro específico para problemas relacionados à decodificação base64
        logger.error("Erro na decodificação dos dados base64.")
    except IOError:
        # Erro específico para problemas relacionados à I/O ao abrir a imagem
        logger.error("Não foi possível abrir a imagem a partir dos dados base64.")
    except Exception as e:
        # Captura outros tipos de exceções
        logger.error(f"Erro ao carregar imagem de base64: {str(e)}")
    return None

def add_text_to_badge(badge_template, owner_name, issuer_name):
    try:
        draw = ImageDraw.Draw(badge_template)
        css_url = 'https://fonts.googleapis.com/css2?family=Rubik&display=swap'
        font_size = 15
        font = load_font_from_google_fonts(css_url, font_size)

        if font is None:
            logger.error("Falha ao carregar a fonte Rubik.")
            return None

        # Adicionar texto à imagem
        draw.text((10, 10), f"Owner: {owner_name}", font=font, fill=(0, 0, 0))
        draw.text((10, 30), f"Issuer: {issuer_name}", font=font, fill=(0, 0, 0))

        return badge_template

    except Exception as e:
        logger.error(f"Erro ao adicionar texto ao badge: {str(e)}")
        return None

def create_qr_code(data, base_url, box_size=10, border=5):
    if not data or not base_url:
        logger.error("Dados ou URL base não fornecidos para o QR Code.")
        return None

    try:
        # Criar a instância QR Code
        qr = qrcode.QRCode(version=1, box_size=box_size, border=border)

        # Adicionar dados ao QR Code
        qr.add_data(f"{base_url}?data={data}")
        qr.make(fit=True)

        # Gerar a imagem QR Code
        qr_code_img = qr.make_image(fill='black', back_color='white')
        return qr_code_img

    except Exception as e:
        logger.error(f"Erro ao criar QR Code: {str(e)}")
        return None

def process_badge_image(badge_template, issuer_name):
    
    try:
        # Adicionar dados EXIF à imagem
        exif_data = {"0th": {piexif.ImageIFD.Make: issuer_name.encode()}}
        badge_with_exif = insert_exif(badge_template, exif_data)

        # Salvar a imagem em um buffer de bytes
        badge_bytes_io = io.BytesIO()
        badge_with_exif.save(badge_bytes_io, format='JPEG')

        # Gerar hash da imagem e converter para base64
        badge_hash = generate_image_hash(badge_with_exif)
        badge_base64 = base64.b64encode(badge_bytes_io.getvalue()).decode('utf-8')

        # Assinar o hash
        gpg = gnupg.GPG()
        signed_hash = gpg.sign(badge_hash)

        return badge_hash, badge_base64, signed_hash

    except Exception as e:
        logger.error(f"Erro ao processar a imagem do badge: {str(e)}")
        return None

def load_font_from_google_fonts(css_url, size):
    try:
        # Baixar o CSS da fonte
        response = requests.get(css_url)
        response.raise_for_status()

        # Extrair a URL da fonte do CSS
        font_url_match = re.search(r"url\((https://fonts.gstatic.com/[^)]+\.ttf)\)", response.text)
        if not font_url_match:
            raise Exception("URL da fonte não encontrada no CSS")

        font_url = font_url_match.group(1)

        # Baixar o arquivo da fonte
        font_response = requests.get(font_url)
        font_response.raise_for_status()

        # Carregar a fonte
        font = ImageFont.truetype(BytesIO(font_response.content), size)
        return font
    except requests.RequestException as e:
        print(f"Erro ao baixar a fonte: {e}")
    except Exception as e:
        print(f"Erro ao carregar a fonte: {e}")
    return None

def load_font(font_path, size):
    try:
        # Carregar a fonte
        font = ImageFont.truetype(font_path, size)
        return font
    except IOError:
        # Erro específico para problemas relacionados à I/O, como arquivo de fonte não encontrado
        logger.error(f"Não foi possível carregar a fonte: {font_path}")
    except Exception as e:
        # Captura outros tipos de exceções
        logger.error(f"Erro ao carregar a fonte ({font_path}): {str(e)}")
    return None

def generate_image_hash(image):
    try:
        # Validar os dados de entrada
        if not isinstance(image, Image.Image):
            logger.error("O objeto fornecido não é uma imagem válida.")
            return None

        # Geração do hash da imagem
        img_hash = hashlib.sha256()
        img_hash.update(image.tobytes())
        return img_hash.hexdigest()

    except Exception as e:
        logger.error(f"Erro ao gerar o hash da imagem: {str(e)}")
        return None

def insert_exif(image, exif_data):
    try:
        # Validar os dados de entrada
        if not isinstance(image, Image.Image):
            logger.error("O objeto fornecido não é uma imagem válida.")
            return None

        if not isinstance(exif_data, dict):
            logger.error("Os dados EXIF fornecidos não estão no formato de dicionário.")
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
        logger.error(f"Erro ao inserir dados EXIF na imagem: {str(e)}")
        return None

    finally:
        # Limpar a imagem temporária, se existir
        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)

