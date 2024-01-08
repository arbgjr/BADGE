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
import azure.functions as func
from flask import Flask, jsonify, request
from azure.identity import DefaultAzureCredential
from azure.appconfiguration import AzureAppConfigurationClient
from . import helpers

app = Flask(__name__)
gpg = gnupg.GPG()

# Configuração do cliente Azure App Configuration
credential = DefaultAzureCredential()
connection_string = os.environ["CUSTOMCONNSTR_AppConfigConnectionString"] 
if connection_string is None:
    raise ValueError("A variável de ambiente 'AppConfigConnectionString' não está definida.")
client = AzureAppConfigurationClient.from_connection_string(connection_string)

# Rotas Flask
@app.route('/emit_badge', methods=['POST'])
def emit_badge():
	data = request.json
	result = helpers.generate_badge(data)
	return jsonify(result)

@app.route('/get_badge_image', methods=['GET'])
def get_badge_image():
	badge_guid = request.args.get('badge_guid')

	conn_str = helpers.get_app_config_setting('SqlConnectionString')
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

	conn_str = helpers.get_app_config_setting('SqlConnectionString')
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

	conn_str =  helpers.get_app_config_setting('SqlConnectionString')
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

	conn_str =  helpers.get_app_config_setting('SqlConnectionString')
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
	logging.info('Processando Hello.')
	
	name = request.args.get('name')  # Para parâmetros na query string

	if not name:
		try:
			req_body = request.get_json()
		except ValueError:
			pass
		else:
			name = req_body.get('owner_name')  # Para parâmetros no corpo da requisição

	if name:
		return jsonify(message=f"Hello, {name}. This HTTP triggered function executed successfully.")
	else:
		return jsonify(message="This HTTP triggered function executed successfully. Pass a name in the query string or in the request body for a personalized response.")

@app.route('/test', methods=['GET'])
def test():
    logging.info('Processando Test.') 
    return 'Test route'

def main(req: func.HttpRequest) -> func.HttpResponse:
    # Log da solicitação recebida
    logging.info('Python HTTP trigger function processed a request.')

    # Você pode logar informações específicas da solicitação, como o método HTTP e a URL
    logging.info(f'Request method: {req.method}')
    logging.info(f'Request URL: {req.url}')

    # Continua com a execução normal da função
    try:
        response = func.WsgiMiddleware(app.wsgi_app).handle(req)
        logging.info('Flask app processed the request successfully. Response: {response}')
        return response
    except Exception as e:
        # Log de erros, se ocorrerem
        logging.error('Error occurred: ' + str(e))
        return func.HttpResponse(
            "An error occurred", status_code=500
        )
 
