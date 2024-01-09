from flask import Flask, request, jsonify
from flask_restx import Resource, Api
from flask import Flask, request, jsonify
import pyodbc
import gnupg
from . import helpers

application = Flask(__name__)
api = Api(application, doc='/doc/')


@api.route("/hello")
class Hello(Resource):
    @api.doc(
        params={},
        responses={
            200: 'Success',
            400: 'Validation Error'
        }
    )
    def get(self):
        req_body = request.get_json()
        user = req_body.get('owner_name')
        return jsonify({"message": f"Hello Azure Function {user}"}) 

@api.route("/ping")
class Ping(Resource):
    def get(self):
        return jsonify({
            "message": "back"
        })

        
api.add_resource(Hello, "/hello")
api.add_resource(Ping, "/ping") 

@api.route('/emit_badge', methods=['POST'])
def emit_badge():
  data = request.json
  result = helpers.generate_badge(data)
  return jsonify(result)

@api.route('/get_badge_image', methods=['GET'])
def get_badge_image():
  req_body = request.json
  badge_guid = req_body.get('badge_guid')

  conn_str = helpers.get_app_config_setting('SqlConnectionString')
  with pyodbc.connect(conn_str) as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT BadgeBase64 FROM Badges WHERE GUID = ?", badge_guid)
    row = cursor.fetchone()

  if row:
    return jsonify({"badge_image": row[0]})
  else:
    return jsonify({"error": "Badge não encontrado"}), 404

@api.route('/validate_badge', methods=['GET'])
def validate_badge():
  req_body = request.json
  encrypted_data = req_body.get('data')
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

@api.route('/get_user_badges', methods=['GET'])
def get_user_badges():
  req_body = request.json
  user_id = req_body.get('user_id')

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

@api.route('/get_badge_holders', methods=['GET'])
def get_badge_holders():
  req_body = request.json
  badge_name = req_body.get('badge_name')

  conn_str =  helpers.get_app_config_setting('SqlConnectionString')
  with pyodbc.connect(conn_str) as conn:
    cursor = conn.cursor()
    cursor.execute("SELECT UserName FROM Badges WHERE BadgeName = ?", badge_name)
    badge_holders = cursor.fetchall()

  users = [user[0] for user in badge_holders]

  return jsonify(users)

@api.route('/get_linkedin_post', methods=['GET'])
def get_linkedin_post():
  req_body = request.json
  badge_guid = req_body.get('badge_guid')

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
