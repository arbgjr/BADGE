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
from azf_wsgi import AzureFunctionsWsgi 
from flask import Flask, jsonify, request
from azure.identity import DefaultAzureCredential
from azure.appconfiguration import AzureAppConfigurationClient
from . import helpers
from werkzeug.exceptions import HTTPException
import flask, werkzeug
from .app import application

app = Flask(__name__)
app.config['PROPAGATE_EXCEPTIONS'] = True

def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    # Log da solicitação recebida
    logging.info('Python HTTP trigger function processed a request.')

    logging.info('Flask version: %s' % flask.__version__) 
    logging.info('Werkzeug version: %s' % werkzeug.__version__) 

    # Você pode logar informações específicas da solicitação, como o método HTTP e a URL
    logging.info(f'Request method: {req.method}')
    logging.info(f'Request URL: {req.url}')

    # Continua com a execução normal da função
    try:
        response = func.WsgiMiddleware(application.wsgi_app).handle(req, context)
        logging.info(f'Flask app processed the request successfully. Response: {response}')
        return response
    except Exception as e:
        # Log de erros, se ocorrerem
        logging.error('Deu ruim: ' + str(e))
        return func.HttpResponse(
            "Deu ruim ", status_code=500
        )
 
