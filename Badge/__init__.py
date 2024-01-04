import logging
from azure.functions import HttpRequest, HttpResponse
import azure.identity
import azure.appconfiguration
from azure.functions_wsgi import WsgiMiddleware
from flask import Flask, jsonify, request
from PIL import Image, ImageDraw, ImageFont
import qrcode
import uuid
import hashlib
import piexif
import gnupg
import pyodbc
from datetime import datetime, timedelta

app = Flask(__name__)
gpg = gnupg.GPG()

# Configurar o cliente Azure App Configuration
credential = azure.identity.DefaultAzureCredential()
client = azure.appconfiguration.AppConfigurationClient.from_connection_string(os.getenv("AppConfigConnectionString"), credential)

def get_app_config_setting(key):
    return client.get_configuration_setting(key).value

def encrypt_data(data, gpg):
    """ Função para criptografar dados usando PGP """
    encrypted_data = gpg.encrypt(data, recipients=[gpg_key_id])  # Substitua gpg_key_id pela ID da chave
    return str(encrypted_data)

def carregar_template():
    # Carrega a imagem base64 da variável de ambiente
    base64_img = os.environ['PNG_TEMPLATE_BASE64']
    img_data = base64.b64decode(base64_img)
    return Image.open(io.BytesIO(img_data))

def carregar_fonte():
    font_path = os.path.join(os.getcwd(), 'fonts', 'Rubik-Regular.ttf')
    return ImageFont.truetype(font_path, tamanho)

def gerar_hash_imagem(imagem):
    img_hash = hashlib.sha256()
    img_hash.update(imagem.tobytes())
    return img_hash.hexdigest()

def inserir_exif(imagem, dados_exif):
    exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}
    
    # Exemplo: Inserção de dados personalizados
    exif_dict["0th"][piexif.ImageIFD.Make] = dados_exif["nome"]
    exif_dict["0th"][piexif.ImageIFD.Model] = dados_exif["empresa"]
    exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = dados_exif["data_inicio"]
    
    exif_bytes = piexif.dump(exif_dict)
    imagem.save("temp_img.jpg", "jpeg", exif=exif_bytes)

    # Recarregar imagem com EXIF
    imagem_com_exif = Image.open("temp_img.jpg")
    return imagem_com_exif

@app.route('/generate_badge', methods=['POST'])
def generate_badge():
    data = request.json
    owner_name = data['owner_name']
    issuer_name = data['issuer_name']

    # Ler o template do badge em Base64
    badge_template_base64 = get_app_config_setting('BadgeTemplateBase64')
    badge_template = Image.open(io.BytesIO(base64.b64decode(badge_template_base64)))

    # Recuperar a URL base do App Configuration
    base_url = get_app_config_setting('BadgeVerificationUrl')

    # Gerar GUID
    badge_guid = str(uuid.uuid4())

    # Concatenar informações e criptografar
    concatenated_data = f"{badge_guid}|{owner_name}|{issuer_name}"
    encrypted_data = encrypt_data(concatenated_data, gpg)

    # Inserir texto e QR Code no badge
    draw = ImageDraw.Draw(badge_template)
    font = ImageFont.truetype("Arial.ttf", 15)
    draw.text((10, 10), f"Owner: {owner_name}", font=font, fill=(0, 0, 0))
    draw.text((10, 30), f"Issuer: {issuer_name}", font=font, fill=(0, 0, 0))

    # Gerar QR Code com a URL e dados criptografados
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f"{base_url}?data={encrypted_data}")
    qr.make(fit=True)
    qr_code_img = qr.make_image(fill='black', back_color='white')
    badge_template.paste(qr_code_img, (10, 50))

    # Inserir EXIF
    exif_data = {"0th": {piexif.ImageIFD.Make: issuer_name.encode()}}
    exif_bytes = piexif.dump(exif_data)
    badge_bytes_io = io.BytesIO()
    badge_template.save(badge_bytes_io, format='JPEG', exif=exif_bytes)

    # Gerar o Hash da Imagem
    badge_hash = hashlib.sha256(badge_bytes_io.getvalue()).hexdigest()

    # Converter a imagem para Base64
    badge_base64 = base64.b64encode(badge_bytes_io.getvalue()).decode('utf-8')

    # Assinar Hash
    signed_hash = gpg.sign(badge_hash)

    # Armazenar no Banco de Dados
    conn_str = get_app_config_setting('SqlConnectionString')
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO Badges (GUID, BadgeHash, BadgeData, CreationDate, ExpiryDate, OwnerName, IssuerName, PgpSignature, BadgeBase64) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                       badge_guid, badge_hash, badge_data, datetime.now(), datetime.now() + timedelta(days=365), owner_name, issuer_name, str(signed_hash), badge_base64)
        conn.commit()

    return jsonify({"guid": badge_guid, "hash": badge_hash})

def gera_badge(nome, empresa, data_inicio, validade, matricula, categoria, emoji=None):
# Exemplo de uso
#guid, hash_imagem = gerar_badge("João Silva", "Empresa X", "01/01/2023", "31/12/2023", "123456", "Categoria Exemplo", "🏆")

    guid = str(uuid.uuid4())
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(f'https://championsbadgevalidator.com/verify/{guid}')
    qr.make(fit=True)
    img_qr = qr.make_image(fill='black', back_color='white')

    badge_template = Image.open("badge_template.png")
    draw = ImageDraw.Draw(badge_template)
    font = carregar_fonte()

    # Adicionar informações ao badge
    draw.text((10, 10), f"Nome: {nome}", (0, 0, 0), font=font)
    # Adicionar outras informações conforme necessário

    badge_template.paste(img_qr, (10, 150))

    # Inserir dados EXIF
    dados_exif = {
        "nome": nome,
        "empresa": empresa,
        "data_inicio": data_inicio
    }
    badge_com_exif = inserir_exif(badge_template, dados_exif)

    # Gerar o hash da imagem com EXIF
    imagem_hash = gerar_hash_imagem(badge_com_exif)

    badge_com_exif.save(f'badge_{guid}.png')

    return guid, imagem_hash

# Definição das rotas Flask
@app.route('/get_badge_image', methods=['GET'])
def get_badge_image():
    badge_guid = request.args.get('badge_guid')

    conn_str = get_app_config_setting('SqlConnectionString')
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT BadgeBase64 FROM Badges WHERE GUID = ?", badge_guid)
        row = cursor.fetchone()

    if row:
        return jsonify({"badge_image": row[0]})
    else:
        return jsonify({"error": "Badge não encontrado"}), 404

@app.route('/validate_badge', methods=['GET'])
def validate_badge():
    encrypted_data = request.args.get('data')
    decrypted_data = gpg.decrypt(encrypted_data)

    if not decrypted_data.ok:
        return jsonify({"error": "Falha na descriptografia"}), 400

    badge_guid, owner_name, issuer_name = decrypted_data.data.split("|")

    conn_str = get_app_config_setting('SqlConnectionString')
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Badges WHERE GUID = ? AND OwnerName = ? AND IssuerName = ?", badge_guid, owner_name, issuer_name)
        badge = cursor.fetchone()

    if badge:
        return jsonify({"valid": True, "badge_info": badge})
    else:
        return jsonify({"valid": False, "error": "Badge não encontrado ou informações não correspondem"}), 404

@app.route('/get_user_badges', methods=['GET'])
def get_user_badges():
    user_id = request.args.get('user_id')

    conn_str = get_app_config_setting('SqlConnectionString')
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT GUID, BadgeName FROM Badges WHERE UserID = ?", user_id)
        badges = cursor.fetchall()

    badge_list = []
    for badge in badges:
        badge_guid = badge[0]
        badge_name = badge[1]
        validation_url = "https://yourdomain.com/validate?badge_guid=" + badge_guid
        badge_list.append({"name": badge_name, "validation_url": validation_url})

    return jsonify(badge_list)

@app.route('/get_badge_holders', methods=['GET'])
def get_badge_holders():
    badge_name = request.args.get('badge_name')

    conn_str = get_app_config_setting('SqlConnectionString')
    with pyodbc.connect(conn_str) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT UserName FROM Badges WHERE BadgeName = ?", badge_name)
        badge_holders = cursor.fetchall()

    users = [user[0] for user in badge_holders]

    return jsonify(users)

@app.route('/get_linkedin_post', methods=['GET'])
def get_linkedin_post():
    badge_guid = request.args.get('badge_guid')

    # Recuperar informações adicionais do badge, se necessário
    # ...

    # URL de validação do badge
    validation_url = "https://yourdomain.com/validate?badge_guid=" + badge_guid

    # Texto sugerido para postagem
    post_text = (
        "Estou muito feliz em compartilhar que acabei de conquistar um novo badge: [Nome do Badge]! "
        "Esta conquista representa [breve descrição do que o badge representa]. "
        "Você pode verificar a autenticidade do meu badge aqui: " + validation_url + 
        " #Conquista #Badge #DesenvolvimentoProfissional"
    )

    return jsonify({"linkedin_post": post_text})

@app.route('/', methods=['GET', 'POST'])
def hello():
    logging.info('Python HTTP trigger function processed a request.')
    
    name = request.args.get('name')  # Para parâmetros na query string

    if not name:
        try:
            req_body = request.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')  # Para parâmetros no corpo da requisição

    if name:
        return jsonify(message=f"Hello, {name}. This HTTP triggered function executed successfully.")
    else:
        return jsonify(message="This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.")

def main(req: HttpRequest) -> HttpResponse:
    # Utiliza WsgiMiddleware para integrar o Flask com Azure Functions
    return WsgiMiddleware(app.wsgi_app).handle(req)
