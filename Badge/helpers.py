import traceback
import io
import base64
import uuid
import hashlib
import piexif
import re
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
import qrcode
import requests
from . import azure
from . import logger, LogLevel
from pgpy import PGPKey, PGPMessage
from pilmoji import Pilmoji

# Configuração do cliente Azure
azure_client = azure.Azure()

def gera_guid_badge():
    return str(uuid.uuid4())

def format_pgp_key(raw_key, type):
    if type == "pub":
      header = "-----BEGIN PGP PUBLIC KEY BLOCK-----"
      footer = "-----END PGP PUBLIC KEY BLOCK-----"
    else:
       if type == "pvt":
          header = "-----BEGIN PGP PRIVATE KEY BLOCK-----"
          footer = "-----END PGP PRIVATE KEY BLOCK-----"

    key_body = raw_key.replace(header, "").replace(footer, "")

    # Divide a chave em linhas
    lines = key_body.strip().split(" ")

    # Reconstrói a chave, mantendo o cabeçalho, o rodapé e as quebras de linha do corpo
    formatted_key = header + "\r\n\r\n"
    for line in lines:  # Ignora o cabeçalho e o rodapé
        formatted_key += line.strip() + "\r\n"
    formatted_key += footer

    return formatted_key

def get_pgp_private_key():
    private_key_name = azure_client.get_app_config_setting('PGPPrivateKeyName')
    private_key = azure_client.get_key_vault_secret(private_key_name)
    return format_pgp_key(private_key, "pvt")

def get_pgp_public_key():
    public_key_name = azure_client.get_app_config_setting('PGPPublicKeyName') 
    public_key = azure_client.get_key_vault_secret(public_key_name)
    return format_pgp_key(public_key, "pub")

def sign_data(data):
    private_key_str = get_pgp_private_key()
    passphrase = azure_client.get_key_vault_secret("PGPPassphrase")

    # Carregar a chave privada
    privkey = PGPKey()
    privkey.parse(private_key_str)

    #privkey, _ = PGPKey.from_blob(private_key_str)

    # Se a chave estiver protegida e a passphrase fornecida, tentar desbloquear
    if privkey.is_protected and passphrase:
        with privkey.unlock(passphrase):
            if privkey.is_unlocked:
                signature = privkey.sign(data)
            else:
                raise ValueError("Falha ao desbloquear a chave privada. Verifique a passphrase.")
    else:
        # Assinar o hash
        signature = privkey.sign(data)

    return str(signature)

def decrypt_data(encrypted_data):
    private_key_str = get_pgp_private_key()
    passphrase = azure_client.get_key_vault_secret("PGPPassphrase")

    # Carregar a chave privada
    privkey = PGPKey()
    privkey.parse(private_key_str)

    # Se a chave estiver protegida e a passphrase fornecida, tentar desbloquear
    if privkey.is_protected and passphrase:
        with privkey.unlock(passphrase):
            if privkey.is_unlocked:
                decrypted_message = privkey.decrypt(encrypted_data)
            else:
                raise ValueError("Falha ao desbloquear a chave privada. Verifique a passphrase.")
    else:
        decrypted_message = privkey.decrypt(encrypted_data)

    # Verificar se a descriptografia foi bem-sucedida
    if not decrypted_message:
        raise ValueError("Falha na descriptografia da mensagem.")

    return str(decrypted_message.message)

def encrypt_data(data):
    logger.log(LogLevel.DEBUG, f"Mensagem: {data}")
    public_key_str = get_pgp_public_key()
    logger.log(LogLevel.DEBUG, f"PGP Public Key: {public_key_str}")

    # Carregar a chave pública
    pubkey, _ = PGPKey.from_blob(public_key_str)

    # Verificar se a chave carregada é uma chave pública
    if not pubkey.is_public:
        raise ValueError("A chave fornecida não é uma chave pública válida.")

    # Criar uma nova mensagem PGP a partir dos dados
    message = PGPMessage.new(data)

    # Criptografar a mensagem com a chave pública
    encrypted_phrase = pubkey.encrypt(message)
    logger.log(LogLevel.DEBUG, f"Mensagem criptografada: {encrypted_phrase}")

    return encrypted_phrase

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

def convert_image_to_jpg(input_image):
    try:
        print("Verificando o formato da imagem")
        # Verifica o formato da imagem
        if input_image.format != "JPEG":
            logger.log(LogLevel.DEBUG, f"Convertendo {input_image.format} para JPG com fundo branco")
            width, height = input_image.size
            white_background_image = Image.new('RGB', (width, height), 'white')
            white_background_image.paste(input_image.convert('RGBA'), (0, 0), input_image.convert('RGBA'))

            # Salva a imagem em um buffer em memória no formato JPG
            buffer = io.BytesIO()
            white_background_image.save(buffer, 'JPEG')
            buffer.seek(0)

            logger.log(LogLevel.DEBUG, "Convertido para JPG com fundo branco")
            return Image.open(buffer)  # Retorna o objeto da imagem em memória
        else:
            # Se já for JPG, não precisa de conversão
            logger.log(LogLevel.ERROR, "A imagem já está em formato JPG")
            return input_image
    except Exception as e:
        logger.log(LogLevel.ERROR, f"Erro ao converter a imagem para JPG com fundo branco: {str(e)}")
        return None

def generate_image_with_emoji(emoji_string, font_data, font_size=70, background_color=(255, 255, 255), text_color=(0, 0, 0)):
    try:
        # Estimativa inicial do tamanho da imagem
        estimated_size = (font_size, font_size) 

        image = Image.new('RGB', estimated_size, background_color)
        font = ImageFont.truetype(font_data, font_size)

        with Pilmoji(image) as pilmoji:
            # Renderiza o emoji
            pilmoji.text((0, 0), emoji_string.strip(), text_color, font)

            # Encontrar a área ocupada pelo emoji
            bbox = image.getbbox()
            if bbox:
                # Cortar a imagem para o tamanho do conteúdo
                image = image.crop(bbox)

        return image  # Retorna a imagem cortada para o tamanho do emoji
    except Exception as e:
        logger.log(LogLevel.ERROR, f"Erro ao gerar imagem com emoji: {str(e)}")
        return None

def add_text_to_badge(badge_template, text_data_json):
    try:
        draw = ImageDraw.Draw(badge_template)

        for text_item in text_data_json:
            content = text_item.get("content", "")
            position = text_item.get("position", (0, 0))
            font_data = azure_client.return_blob_as_binary(text_item.get("font", ""))
            font_size = text_item.get("size", 20)
            color = tuple(text_item.get("color", (0, 0, 0)))

            if any(ord(char) > 256 for char in content):  # Tratar como emoji
                emoji_image = generate_image_with_emoji(content, font_data, font_size)
                if position[0] == "center":
                    image_width = badge_template.size[0]
                    x = (image_width - emoji_image.size[0]) / 2
                else:
                    x = position[0]
                y = position[1]

                if badge_template.mode != 'RGB':
                    badge_template = badge_template.convert('RGB')

                badge_template.paste(emoji_image, (int(x), int(y)))
                
            else:  # Tratar como texto normal
                try:
                    font = ImageFont.truetype(font_data, font_size)
                    text_bbox = draw.textbbox((0, 0), content, font=font)
                    text_width = text_bbox[2] - text_bbox[0]
                    if position[0] == "center":
                        image_width = badge_template.size[0]
                        x = (image_width - text_width) / 2
                    else:
                        x = position[0]
                    y = position[1]
                    draw.text((x, y), content, font=font, fill=color)
                except IOError:
                    logger.log(LogLevel.ERROR, f"Fonte não encontrada. Usando fonte padrão.")
                    font = ImageFont.load_default()

        return badge_template

    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.log(LogLevel.ERROR, f"Erro ao adicionar texto ao badge: {str(e)}\nStack Trace:\n{stack_trace}")
        return None

def create_qr_code(data, base_url, box_size=3, border=1):
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
        badge_with_exif = insert_exif(badge_template, issuer_name)

        # Verificar se a imagem foi retornada corretamente
        if badge_with_exif is None:
            logger.log(LogLevel.ERROR, "Falha ao inserir dados EXIF na imagem.")
            return None, None, None

        # Salvar a imagem em um buffer de bytes
        badge_bytes_io = io.BytesIO()
        badge_with_exif.save(badge_bytes_io, format='PNG')

        # Gerar hash da imagem e converter para base64
        badge_hash = generate_image_hash(badge_with_exif)
        badge_base64 = base64.b64encode(badge_bytes_io.getvalue()).decode('utf-8')

        signed_hash = sign_data(badge_hash)

        return badge_hash, badge_base64, signed_hash, badge_with_exif

    except Exception as e:
        logger.log(LogLevel.ERROR, f"Erro ao processar a imagem do badge: {e}")
        return None, None, None

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
        logger.log(LogLevel.ERROR, f"Erro ao baixar a fonte: {e}\nStack Trace:\n{stack_trace}")
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.log(LogLevel.ERROR, f"Erro ao carregar a fonte: {e}\nStack Trace:\n{stack_trace}")
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

def insert_exif(image, issuer_name):
    try:
        # Validação dos dados de entrada
        if not isinstance(image, Image.Image):
            logger.log(LogLevel.ERROR, "O objeto fornecido não é uma imagem válida.")
            return None

        exif_data = {"0th": {piexif.ImageIFD.Make: issuer_name.encode()}}
        if not isinstance(exif_data, dict):
            logger.log(LogLevel.ERROR, "Os dados EXIF fornecidos não estão no formato de dicionário.")
            return None

        # Preparar os dados EXIF para inserção
        exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
        for key, value in exif_data.items():
            exif_dict[key] = value

        exif_bytes = piexif.dump(exif_dict)

        # Salvar a imagem em um buffer de memória com os dados EXIF
        img_byte_arr = io.BytesIO()
        if image.format == 'PNG':
            image.save(img_byte_arr, format='PNG')
        else:
            if image.mode == 'RGBA':
                image = image.convert('RGB')
            image.save(img_byte_arr, format='JPEG', exif=exif_bytes)

        img_byte_arr.seek(0)

        # Reabrir a imagem do buffer de memória
        return Image.open(img_byte_arr)

    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.log(LogLevel.ERROR, f"Erro ao inserir dados EXIF na imagem: {e}\nStack Trace:\n{stack_trace}")
        return None

def validar_url_https(url):
    pattern = r'^https:\/\/[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(\/[^\s]*)?$'
    return re.match(pattern, url) is not None

def colar_qr_code(badge_img, qr_code_img, espaco_extra=0):
    badge_width, badge_height = badge_img.size
    qr_width, qr_height = qr_code_img.size

    # Altura total da nova imagem (badge + espaço extra + altura do QR Code)
    nova_altura = badge_height + espaco_extra + qr_height

    # Criar uma nova imagem com a altura estendida e fundo branco (RGB)
    nova_imagem = Image.new('RGB', (badge_width, nova_altura), (255, 255, 255))

    # Colar o badge na parte superior da nova imagem
    # Se badge_img tiver canal alfa, converter para 'RGB'
    if badge_img.mode == 'RGBA':
        badge_img = badge_img.convert('RGB')
    nova_imagem.paste(badge_img, (0, 0))

    # Calcular posição horizontal do QR Code (centralizar)
    x_position = (badge_width - qr_width) // 2

    # Posição vertical do QR Code (abaixo do badge)
    y_position = badge_height + espaco_extra

    # Colar o QR Code na nova imagem
    # Se qr_code_img tiver canal alfa, converter para 'RGB'
    if qr_code_img.mode == 'RGBA':
        qr_code_img = qr_code_img.convert('RGB')
    nova_imagem.paste(qr_code_img, (x_position, y_position))

    return nova_imagem

def png_to_jpeg(png_image, background_color=(255, 255, 255)):
    try:
        # Verificar se o objeto é uma imagem
        if not isinstance(png_image, Image.Image):
            raise ValueError("O objeto fornecido não é uma imagem válida.")

        # Criar uma nova imagem com fundo na cor especificada, do mesmo tamanho da imagem PNG
        background = Image.new('RGB', png_image.size, background_color)

        # Colar a imagem PNG no fundo
        background.paste(png_image, (0, 0), png_image)

        # Retornar a imagem resultante como JPEG
        return background

    except Exception as e:
        logger.log(LogLevel.ERROR, f"Erro ao converter a imagem: {e}")
        return None

def insert_data_into_json_schema(json_schema, data):
    try:
        import jsonschema

        # Valide os dados em relação ao esquema para garantir que estejam em conformidade
        jsonschema.validate(instance=data, schema=json_schema)

        # Se a validação for bem-sucedida, os dados estão em conformidade com o esquema
        # Você pode simplesmente mesclar os dados no esquema original
        json_schema.update(data)

        return json_schema
    except jsonschema.ValidationError as ve:
        logger.log(LogLevel.ERROR, f"Erro de validação do esquema JSON: {ve}")
        return None
    except Exception as e:
        logger.log(LogLevel.ERROR, f"Erro ao inserir dados no esquema JSON: {str(e)}")
        return None
    
