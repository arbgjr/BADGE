import traceback
import pyodbc
import os
import re
import datetime

from .database import Database
from . import helpers
from . import azure
from . import logger, LogLevel


# Configuração do cliente Azure
azure_client = azure.Azure()

def get_configs():
    try:
        owner_name, issuer_name, area_name = "Armando Guimarães", "Sinqia", "Agility"
        badge_guid = helpers.gera_guid_badge()

        logger.log(LogLevel.DEBUG, f"[business] Endpoint para recuperar configurações.")
        data = {}
        data['Ambiente']['APPINSIGHTS_INSTRUMENTATIONKEY'] = os.environ["APPINSIGHTS_INSTRUMENTATIONKEY"]
        data['Ambiente']['AzFunctionName'] = os.getenv('WEBSITE_SITE_NAME')
        data['Ambiente']['AZURE_SUBSCRIPTION_ID'] = os.environ["AZURE_SUBSCRIPTION_ID"]
        conexao = os.getenv("CUSTOMCONNSTR_AppConfigConnectionString")
        conexao = re.sub(r"Id=[^;]+", "Id=***", conexao)
        conexao = re.sub(r"Secret=[^;]+", "Secret=***", conexao)
        data['Ambiente']['AppConfigConnectionString'] = conexao
        data['Ambiente']['RGAzFunction'] = azure_client.get_resource_group()
        data['Ambiente']['pyodbcDrivers'] = pyodbc.drivers()
        data['Ambiente']['IPAzFunction'] = azure_client.get_function_ip()
        
        data['AzAppConfig']['AzKVURI'] = azure_client.get_app_config_setting("AzKVURI")
        data['AzAppConfig']['BadgeVerificationUrl'] = azure_client.get_app_config_setting('BadgeVerificationUrl')
        data['AzAppConfig']['PGPPrivateKeyName'] = azure_client.get_app_config_setting('PGPPrivateKeyName')
        public_key_name = azure_client.get_app_config_setting('PGPPublicKeyName') 
        data['AzAppConfig']['PGPPublicKeyName'] = public_key_name
        data['AzAppConfig']['LinkedInPost'] = azure_client.get_app_config_setting('LinkedInPost')
        data['AzAppConfig']['header_info'] = azure_client.get_app_config_setting('BadgeHeaderInfo')
        data['AzAppConfig']['container_name'] = azure_client.get_app_config_setting('BadgeContainerName')
        data['AzAppConfig']['badge_db_schema_url'] = azure_client.get_app_config_setting('BadgeDBSchemaURL')

        data['AzKeyVault']['PGPPublicKey'] = azure_client.get_key_vault_secret(public_key_name)
        data['AzKeyVault']['Palavra'] = f'{badge_guid}|{owner_name}|{issuer_name}|{area_name}'
        PalavraCriptada = helpers.encrypt_data(data['Palavra'])
        data['AzKeyVault']['PalavraCriptada'] = str(PalavraCriptada)
        data['AzKeyVault']['PalavraDescriptada'] = helpers.decrypt_data(PalavraCriptada)
        
        conexao = azure_client.get_key_vault_secret('CosmosDBConnectionString')
        conexao = re.sub(r"User ID=[^;]+", "User ID=***", conexao)
        conexao = re.sub(r"Password=[^;]+", "Password=***", conexao)
        data['AzKeyVault']['CosmosDBConnectionString'] = conexao

        db = Database()
        badge_template_info  = db.get_badge_template(issuer_name, area_name)
        data['Database']['badge_template_info'] = badge_template_info

#        badge_template = azure_client.return_blob_as_image(blob_url)
#        data['badge_template'] = badge_template


        return data

    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.log(LogLevel.ERROR, f"Erro ao recuperar informações: {str(e)}\nStack Trace:\n{stack_trace}")
        return {"error": f"Erro interno no servidor: {str(e)}\nStack Trace:\n{stack_trace}"}, 418
        
def generate_badge(data):
    try:
        # Validação e análise dos dados recebidos
        logger.log(LogLevel.DEBUG, f"[business] Endpoint para emitir um novo badge.")
        if 'owner_name' not in data or 'issuer_name' not in data or 'area_name' not in data:
            logger.log(LogLevel.ERROR, "Dados de entrada faltando: 'owner_name' ou 'issuer_name' ou 'area_name'")
            return {"error": "Falha ao gerar badge."}, 400

        owner_name = data['owner_name']
        issuer_name = data['issuer_name']
        area_name = data['area_name']

        logger.log(LogLevel.DEBUG, f"Gerando badge para {owner_name} emitido por {issuer_name}")

        logger.log(LogLevel.DEBUG, f"[business] Carregar URL de verificação do Badge.")
        base_url = azure_client.get_app_config_setting('BadgeVerificationUrl')
        logger.log(LogLevel.DEBUG, f"[business] URL de verificação do Badge: {base_url}.")
        if not base_url:
            logger.log(LogLevel.ERROR, "Falha ao carregar a URL de verificação do badge.")
            return {"error": "Falha ao gerar badge.1"}, 418
        
        if not helpers.validar_url_https(base_url):
            logger.log(LogLevel.ERROR, "URL de verificação do badge inválida.")
            return {"error": "Falha ao gerar badge.2"}, 418
 
        logger.log(LogLevel.DEBUG, f"[business] Gerando GUID do Badge.")
        badge_guid = helpers.gera_guid_badge() 
        
        logger.log(LogLevel.DEBUG, f"[business] Gerando dados de verificação do Badge: {badge_guid}.")
        concatenated_data = f"{badge_guid}|{owner_name}|{issuer_name}|{area_name}"
        encrypted_data = str(helpers.encrypt_data(concatenated_data))

        db = Database()

        # Carregar template de imagem
        badge_template_info  = db.get_badge_template(issuer_name, area_name)
        if not badge_template_info:
            logger.log(LogLevel.ERROR, "Template de badge não encontrado.")
            return {"error": "Falha ao gerar badge.3"}, 418

        blob_url = badge_template_info.get('BlobUrl')

        logger.log(LogLevel.DEBUG, f"[business] Carregar template de imagem.")
        badge_template = azure_client.return_blob_as_image(blob_url)
        if not badge_template:
            logger.log(LogLevel.ERROR, "Falha ao carregar template de badge.")
            return {"error": "Falha ao gerar badge.4"}, 418

        logger.log(LogLevel.DEBUG, f"[business] Convertendo para JPG com fundo branco.")
        badge_template = helpers.convert_image_to_jpg(badge_template)

        logger.log(LogLevel.DEBUG, f"[business] Recuperado informações de header do Badge.")
        header_info = azure_client.get_app_config_setting('BadgeHeaderInfo')
        owner_namer_position = tuple(header_info[0].get("position"))
        owner_name_font_url = header_info[0].get("font")
        owner_name_font_size = tuple(header_info[0].get("size"))
        owner_name_color = tuple(header_info[0].get("color"))

        issuer_name_position = tuple(header_info[1].get("position"))
        issuer_name_font_url = header_info[1].get("font")
        issuer_name_font_size = tuple(header_info[1].get("size"))
        issuer_name_color = tuple(header_info[1].get("color"))

        area_font_url = badge_template_info["AreaDetails"]["FontPath"]
        area_font_size = tuple(badge_template_info["AreaDetails"]["Size"])
        area_position = tuple(badge_template_info["AreaDetails"]["Position"])
        area_color = tuple(badge_template_info["AreaDetails"]["Color"])  # Converter a lista em uma tupla

        icon = badge_template_info["ContentDetails"]["Content"]
        icon_font_url = badge_template_info["ContentDetails"]["FontPath"]
        icon_size = tuple(badge_template_info["ContentDetails"]["Size"])
        icon_position = tuple(badge_template_info["ContentDetails"]["Position"])
        icon_color = tuple(badge_template_info["ContentDetails"]["Color"])  # Converter a lista em uma tupla

        logger.log(LogLevel.DEBUG, f"[business] Gerando dados a serem escritos no Badge.")
        text_data_json = [
            {"content": f"Detentor: {owner_name}", "position": owner_namer_position, "font": owner_name_font_url, "size": owner_name_font_size, "color": owner_name_color},
            {"content": f"Emissor: {issuer_name}", "position": issuer_name_position, "font": issuer_name_font_url, "size": issuer_name_font_size, "color": issuer_name_color},
            {"content": area_name, "position": area_position, "font": area_font_url, "size": area_font_size, "color": area_color},
            {"content": icon, "position": icon_position, "font": icon_font_url, "size": icon_size, "color": icon_color}
        ]

        logger.log(LogLevel.DEBUG, f"[business] Adicionando texto ao Badge.")
        badge_template = helpers.add_text_to_badge(badge_template, text_data_json)
        if badge_template is None:
            logger.log(LogLevel.ERROR, "Falha ao editar badge. ")
            return {"error": "Falha ao gerar badge.5"}, 418 

        logger.log(LogLevel.DEBUG, f"[business] Gerando QRCode do Badge.")
        qr_code_img = helpers.create_qr_code(badge_guid, base_url, box_size=10, border=4)
        if qr_code_img is None:
            logger.log(LogLevel.ERROR, "Falha ao gerar QR Code. ")
            return {"error": "Falha ao gerar badge.6"}, 418 

        logger.log(LogLevel.DEBUG, f"[business] Inserindo QRCode no Badge.")
        badge_template = helpers.colar_qr_code(badge_template, qr_code_img)
        if badge_template is None:
            logger.log(LogLevel.ERROR, "Falha ao inserir QRCode.")
            return {"error": "Falha ao gerar badge.7"}, 418 

        logger.log(LogLevel.DEBUG, "[business] Inserindo dados EXIF no Badge.")
        result = helpers.process_badge_image(badge_template, issuer_name)
        if result is not None:
            badge_hash, badge_base64, signed_hash, badge_template = result
        else:
            logger.log(LogLevel.ERROR, "Falha ao editar EXIF do badge.")
            return {"error": "Falha ao gerar badge.8"}, 418

        logger.log(LogLevel.DEBUG, f"[business] Upload do Badge para o Azure")
        container_name = azure_client.get_app_config_setting('BadgeContainerName')
        if not container_name:
            logger.log(LogLevel.ERROR, "Falha ao obter nome do container do Azure.")
            return {"error": "Falha ao gerar badge.9"}, 418
        
        blob_name = f"{badge_guid}.jpg"
        success = azure_client.upload_blob(container_name, blob_name, badge_template)
        if not success:
            logger.log(LogLevel.ERROR, "Falha ao enviar o badge para storage.")
            return {"error": "Falha ao gerar badge.10"}, 418

        logger.log(LogLevel.DEBUG, f"[business] Gerando URL do Badge.")
        badge_url = azure_client.generate_sas_url(container_name, blob_name)
        if not badge_url:
            logger.log(LogLevel.ERROR, "Falha ao gerar URL do badge.")
            return {"error": "Falha ao gerar badge.11"}, 418

        logger.log(LogLevel.DEBUG, f"[business] Gerando JSON do Badge.")
        badge_json = {}
        badge_json["badgeId"] = badge_guid
        badge_json["name"] = "Champion da Engenharia"
        badge_json["description"] = "Concedido por ser referência na sua área."
        badge_json["issuer"]["name"] = issuer_name
        badge_json["issuer"]["contactInfo"]["email"] = ""
        badge_json["issuer"]["contactInfo"]["phone"] = ""
        badge_json["holder"]["name"] = owner_name
        badge_json["holder"]["email"] = ""
        badge_json["category"]["mainCategory"] = "Engenharia"
        badge_json["category"]["subCategory"] = area_name
        badge_json["generatedBadge"]["badgeImageUrl"] = badge_url
        badge_json["generatedBadge"]["metadata"]["issuedDate"] = datetime.datetime.now()
        badge_json["generatedBadge"]["metadata"]["expiryDate"] = ""
        badge_json["generatedBadge"]["metadata"]["additionalInfo"] = ""
        badge_json["verificationLink"] = ""

        badge_db_schema_url  = azure_client.get_app_config_setting('BadgeDBSchemaURL')
        badge_db_schema  = azure_client.return_blob_as_text(badge_db_schema_url)
        badge_data = helpers.insert_data_into_json_schema(badge_db_schema, badge_json)


        logger.log(LogLevel.DEBUG, f"[business] Gravando Badge no banco.")
        success = db.insert_badge(badge_guid, badge_data)
        if not success:
            logger.log(LogLevel.ERROR, "Falha ao inserir o badge no banco de dados.")
            return {"error": "Falha ao gerar badge.12"}, 418

        return {"guid": badge_guid, "hash": badge_hash}

    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.log(LogLevel.ERROR, f"Erro ao gerar badge: {str(e)}\nStack Trace:\n{stack_trace}")
        return {"error": f"Erro interno no servidor: {str(e)}\nStack Trace:\n{stack_trace}"}, 500

def badge_image(data):
    try:
        # Validação e análise dos dados recebidos
        if 'badge_guid' not in data:
            logger.log(LogLevel.ERROR, "Dados de entrada faltando: 'badge_guid'")
            return {"error": "Dados de entrada inválidos"}, 400

        badge_guid = data['badge_guid']
        
        logger.log(LogLevel.DEBUG, f"Recuperando badge para {badge_guid}.")
        
        db = Database()
        row = db.get_badge_image(badge_guid)
        if row:
            return {"badge_image": row[0]}
        else:
            logger.log(LogLevel.ERROR, "Falha ao recuperar o badge no banco de dados.")
            return {"error": "Badge não encontrado"}, 404
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.log(LogLevel.ERROR, f"Erro ao recuperar badge: {str(e)}\nStack Trace:\n{stack_trace}")
        return {"error": "Erro interno no servidor"}, 418

def badge_valid(data):
    try:
        # Validação e análise dos dados recebidos
        if 'data' not in data:
            logger.log(LogLevel.ERROR, "Dados de entrada faltando: 'data'")
            return {"error": "Dados de entrada inválidos"}, 400

        encrypted_data = data['data']
                
        logger.log(LogLevel.DEBUG, "Analisando dados enviados.")

        if not encrypted_data:
            logger.log(LogLevel.ERROR, "Dados criptogtafados não informados.")
            return {"error": "Dados criptografados são obrigatórios"}, 400
            
        logger.log(LogLevel.DEBUG, f"Descriptografando dados enviados: {encrypted_data}")

        decrypted_data = helpers.decrypt_data(encrypted_data)
        if not decrypted_data:
            logger.log(LogLevel.ERROR, "Não foi possível descriptograr dados informados.")
            return {"error": "Falha na descriptografia"}, 400 

        logger.log(LogLevel.DEBUG, f"Decodificando dados enviados: {encrypted_data}")

        try:
            badge_guid, owner_name, issuer_name = decrypted_data.data.split("|")
            logger.log(LogLevel.DEBUG, f"Validando badge {badge_guid} emitido por {issuer_name}")

        except ValueError:
            stack_trace = traceback.format_exc()
            logger.log(LogLevel.ERROR, "Não foi possível decodificar dados informados.")
            return {"error": "Dados decodificados inválidos"}, 400
        
        db = Database()
        badge = db.validate_badge(badge_guid, owner_name, issuer_name)
        if badge:
            return {"valid": True, "badge_info": badge}
        else:
            return {"valid": False, "error": "Badge não encontrado ou informações não correspondem"}, 404
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.log(LogLevel.ERROR, f"Erro ao validar badge: {str(e)}\nStack Trace:\n{stack_trace}")
        return {"error": "Erro interno no servidor"}, 418
     
def badge_list(data):
    try:
        
        # Validação e análise dos dados recebidos
        if 'user_id' not in data:
            logger.log(LogLevel.ERROR, "Dados de entrada faltando: 'user_id'")
            return {"error": "Dados de entrada inválidos"}, 400

        user_id = data['user_id']

        db = Database()
        badges = db.get_user_badges(user_id)

        if not badges:
            return {"error": "Nenhum badge encontrado para o usuário"}, 404

        base_url = azure_client.get_app_config_setting('BadgeVerificationUrl')
        if not base_url:
            logger.log(LogLevel.ERROR, "Falha ao carregar a URL de verificação do badge.")
            return {"error": "Falha ao carregar url de verificação do badge"}, 418

        badge_list = []
        for badge in badges:
            badge_guid = badge[0]
            badge_name = badge[1]
            validation_url = f"{base_url}/validate?badge_guid={badge_guid}"
            badge_list.append({"name": badge_name, "validation_url": validation_url})

        return badge_list

    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.log(LogLevel.ERROR, f"Erro ao listar badges: {str(e)}\nStack Trace:\n{stack_trace}")
        return {"error": "Erro interno no servidor"}, 418

def badge_holder(data):
    try:
      
        # Validação e análise dos dados recebidos
        if 'badge_name' not in data:
            logger.log(LogLevel.ERROR, "Dados de entrada faltando: 'badge_name'")
            return {"error": "Dados de entrada inválidos"}, 400

        badge_name = data['badge_name']

        db = Database()
        badge_holders = db.get_badge_holders(badge_name)

        if not badge_holders:
            return {"error": "Nenhum detentor de badge encontrado para este nome de badge"}, 404

        users = [user[0] for user in badge_holders]
        return users

    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.log(LogLevel.ERROR, f"Erro ao recuperar detentores do badge: {str(e)}\nStack Trace:\n{stack_trace}")
        return {"error": "Erro interno no servidor"}, 418

def linkedin_post(data):
    try:
      
        # Validação e análise dos dados recebidos
        if 'badge_guid' not in data:
            logger.log(LogLevel.ERROR, "Dados de entrada faltando: 'badge_guid'")
            return {"error": "Dados de entrada inválidos"}, 400

        badge_guid = data['badge_guid']

        db = Database()
        badge_info = db.get_badge_info_for_post(badge_guid)

        if not badge_info:
            return {"error": "Badge não encontrado"}, 404

        badge_name, additional_info = badge_info

        base_url = azure_client.get_app_config_setting('BadgeVerificationUrl')
        if not base_url:
            logger.log(LogLevel.ERROR, "Falha ao carregar a URL de verificação do badge.")
            return {"error": "Falha ao carregar url de verificação do badge"}, 418

        # URL de validação do badge
        validation_url = f"{base_url}/validate?badge_guid={badge_guid}"
        
        # Texto sugerido para postagem
        post_text = azure_client.get_app_config_setting('LinkedInPost')
        if not post_text:
          post_text = (
            f"Estou muito feliz em compartilhar que acabei de conquistar um novo badge: {badge_name}! "
            f"Esta conquista representa {additional_info}. "
            f"Você pode verificar a autenticidade do meu badge aqui: {validation_url} "
            "#Conquista #Badge #DesenvolvimentoProfissional"
          )
        
        return {"linkedin_post": post_text}
        
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.log(LogLevel.ERROR, f"Erro ao recuperar a mensagem do post do LinkedIn: {str(e)}\nStack Trace:\n{stack_trace}")
        return {"error": "Erro interno no servidor"}, 418
        
        
