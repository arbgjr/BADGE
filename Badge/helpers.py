import traceback
import os
import io
import base64
import uuid
import hashlib
import piexif
import re
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import qrcode
import gnupg
import requests
from . import azure
from . import logger, LogLevel

# Configuração do cliente Azure
azure_client = azure.Azure()
        
def gera_guid_badge():
    return str(uuid.uuid4())

def get_pgp_private_key():
    private_key_name = azure_client.get_app_config_setting('PGPPrivateKeyName')
    private_key = azure_client.get_key_vault_secret(private_key_name)
    return private_key

def get_pgp_public_key():
    public_key_name = azure_client.get_app_config_setting('PGPPublicKeyName') 
    public_key = azure_client.get_key_vault_secret(public_key_name)
    return public_key

def decrypt_data(encrypted_data):
    gpg = gnupg.GPG()
    private_key = get_pgp_private_key()
    import_result = gpg.import_keys(private_key)
    
    if not import_result.counts['imported'] and not import_result.fingerprints:
        raise ValueError("Falha ao importar a chave privada PGP")

    decrypted_data = gpg.decrypt(encrypted_data)
    if not decrypted_data.ok:
        raise ValueError(f"Falha na descriptografia: {decrypted_data.status}")

    return str(decrypted_data)

def encrypt_data(data):
    gpg = gnupg.GPG()
    public_key = get_pgp_public_key()
    logger.log(LogLevel.DEBUG, f"Public Key: {public_key}")

    # Importar a chave pública PGP
    logger.log(LogLevel.DEBUG, f"Importando a chave pública PGP:")
    import_result = gpg.import_keys(public_key)

    # Verifique se a importação foi bem-sucedida
    if not import_result.counts['imported'] and not import_result.fingerprints:
        # Imprimir informações detalhadas do resultado da importação
        logger.log(LogLevel.DEBUG, f"Detalhes da Importação:")
        logger.log(LogLevel.DEBUG, f"Contagem de importados: {import_result.counts['imported']}")
        logger.log(LogLevel.DEBUG, f"Contagem de não alterados: {import_result.counts['unchanged']}")
        logger.log(LogLevel.DEBUG, f"Resultados da importação: {import_result.results}")
        logger.log(LogLevel.DEBUG, f"Stderr: {import_result.stderr}")
        raise ValueError("Falha ao importar a chave pública PGP")

    encrypted_data = gpg.encrypt(data, import_result.fingerprints[0])
    if not encrypted_data.ok:
        raise ValueError(f"Falha na criptografia: {encrypted_data.status}")
    
    return str(encrypted_data)
        
def load_image_from_base64(base64_img):
    try:
        # Verificar se a entrada é uma string
        if not isinstance(base64_img, str):
            logger.log(LogLevel.ERROR, "Dados de entrada não são uma string base64 válida.")
            return None

        # Decodificar dados base64
        img_data = base64.b64decode(base64_img)

        # Carregar imagem a partir dos dados decodificados
        image = Image.open(io.BytesIO(img_data))
        return image

    except base64.binascii.Error:
        # Erro específico para problemas relacionados à decodificação base64
        logger.log(LogLevel.ERROR, "Erro na decodificação dos dados base64.")
    except IOError:
        # Erro específico para problemas relacionados à I/O ao abrir a imagem
        logger.log(LogLevel.ERROR, "Não foi possível abrir a imagem a partir dos dados base64.")
    except Exception as e:
        stack_trace = traceback.format_exc()
        # Captura outros tipos de exceções
        logger.log(LogLevel.ERROR, f"Erro ao carregar imagem de base64: {str(e)}\nStack Trace:\n{stack_trace}")
    return None

def add_text_to_badge(badge_template, owner_name, issuer_name):
    try:
        draw = ImageDraw.Draw(badge_template)
        css_url = 'https://fonts.googleapis.com/css2?family=Rubik&display=swap'
        font_size = 15
        font = load_font_from_google_fonts(css_url, font_size)

        if font is None:
            logger.log(LogLevel.ERROR, "Falha ao carregar a fonte Rubik.")
            return None

        # Adicionar texto à imagem
        draw.text((10, 10), f"Owner: {owner_name}", font=font, fill=(0, 0, 0))
        draw.text((10, 30), f"Issuer: {issuer_name}", font=font, fill=(0, 0, 0))

        return badge_template

    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.log(LogLevel.ERROR, f"Erro ao adicionar texto ao badge: {str(e)}\nStack Trace:\n{stack_trace}")
        return None

def create_qr_code(data, base_url, box_size=10, border=5):
    if not data or not base_url:
        logger.log(LogLevel.ERROR, "Dados ou URL base não fornecidos para o QR Code.")
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
        stack_trace = traceback.format_exc()
        logger.log(LogLevel.ERROR, f"Erro ao criar QR Code: {str(e)}\nStack Trace:\n{stack_trace}")
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
        stack_trace = traceback.format_exc()
        logger.log(LogLevel.ERROR, f"Erro ao processar a imagem do badge: {str(e)}\nStack Trace:\n{stack_trace}")
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
        stack_trace = traceback.format_exc()
        print(f"Erro ao baixar a fonte: {e}\nStack Trace:\n{stack_trace}")
    except Exception as e:
        stack_trace = traceback.format_exc()
        print(f"Erro ao carregar a fonte: {e}\nStack Trace:\n{stack_trace}")
    return None

def load_font(font_path, size):
    try:
        # Carregar a fonte
        font = ImageFont.truetype(font_path, size)
        return font
    except IOError:
        stack_trace = traceback.format_exc()
        # Erro específico para problemas relacionados à I/O, como arquivo de fonte não encontrado
        logger.log(LogLevel.ERROR, f"Não foi possível carregar a fonte: {font_path}\nStack Trace:\n{stack_trace}")
    except Exception as e:
        stack_trace = traceback.format_exc()
        # Captura outros tipos de exceções
        logger.log(LogLevel.ERROR, f"Erro ao carregar a fonte ({font_path}): {str(e)}\nStack Trace:\n{stack_trace}")
    return None

def generate_image_hash(image):
    try:
        # Validar os dados de entrada
        if not isinstance(image, Image.Image):
            logger.log(LogLevel.ERROR, "O objeto fornecido não é uma imagem válida.")
            return None

        # Geração do hash da imagem usando SHA-3
        img_hash = hashlib.sha3_256()
        img_hash.update(image.tobytes())
        return img_hash.hexdigest()

    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.log(LogLevel.ERROR, f"Erro ao gerar o hash da imagem: {str(e)}\nStack Trace:\n{stack_trace}")
        return None

def insert_exif(image, exif_data):
    try:
        # Validar os dados de entrada
        if not isinstance(image, Image.Image):
            logger.log(LogLevel.ERROR, "O objeto fornecido não é uma imagem válida.")
            return None

        if not isinstance(exif_data, dict):
            logger.log(LogLevel.ERROR, "Os dados EXIF fornecidos não estão no formato de dicionário.")
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
        stack_trace = traceback.format_exc()
        logger.log(LogLevel.ERROR, f"Erro ao inserir dados EXIF na imagem: {str(e)}\nStack Trace:\n{stack_trace}")
        return None

    finally:
        # Limpar a imagem temporária, se existir
        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)

def validar_url_https(url):
    pattern = r'^https:\/\/[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(\/[^\s]*)?$'
    return re.match(pattern, url) is not None

