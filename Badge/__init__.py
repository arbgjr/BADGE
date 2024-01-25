import traceback
import azure.functions as func
from flask import jsonify

import logging

logging.log(logging.INFO,"[__init__.py] Iniciando")

from .app import application

def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    logging.log(logging.INFO, 'Python HTTP trigger function processed a request.')
    logging.log(logging.INFO, f'Request method: {req.method}')
    logging.log(logging.INFO, f'Request URL: {req.url}')

    try:
        # Executar aplicação Flask através do WsgiMiddleware
        logging.log(logging.INFO, f"[__init__.py] Executar aplicação Flask através do WsgiMiddleware") 
        response = func.WsgiMiddleware(application.wsgi_app).handle(req, context)
        logging.log(logging.INFO, 'Flask app processed the request successfully.')
        return response
    except Exception as e:
        stack_trace = traceback.format_exc()
        logging.log(logging.ERROR, f'Erro ao processar a solicitação: {str(e)}\nStack Trace:\n{stack_trace}"')
        return func.HttpResponse("Erro interno do servidor", status_code=500)

