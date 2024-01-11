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
import requests
import logging
import tempfile


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

def decrypt_data(encrypted_data):
    try:
        # Verificar se os dados criptografados são válidos
        if encrypted_data is None or encrypted_data == "":
            logging.error("Dados fornecidos para descriptografia estão vazios ou nulos.")
            return None

        # Criar uma instância GPG
        gpg = gnupg.GPG()

        # Descriptografar os dados
        decrypted_data = gpg.decrypt(encrypted_data)
        if not decrypted_data.ok:
            logging.error(f"Falha na descriptografia: {decrypted_data.status}")
            return None

        return str(decrypted_data)

    except Exception as e:
        logging.error(f"Erro ao descriptografar dados: {str(e)}")
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




