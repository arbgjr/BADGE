import traceback
import azure.functions as func
from flask import jsonify
from .logger import LogLevel, Logger

# Crie uma instância do Logger com um nome específico
logger = Logger("AzFuncBadges", default_level=LogLevel.DEBUG)

from .app import application

def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    # Log da solicitação recebida
    logger.log(LogLevel.DEBUG, 'Python HTTP trigger function processed a request.')
    logger.log(LogLevel.DEBUG, f'Request method: {req.method}')
    logger.log(LogLevel.DEBUG, f'Request URL: {req.url}')

    try:
        # Executar aplicação Flask através do WsgiMiddleware
        logger.log(LogLevel.DEBUG, f"[__init__.py] Executar aplicação Flask através do WsgiMiddleware") 
        response = func.WsgiMiddleware(application.wsgi_app).handle(req, context)
        logger.log(LogLevel.DEBUG, 'Flask app processed the request successfully.')
        return response
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.log(LogLevel.ERROR, f'Erro ao processar a solicitação: {str(e)}\nStack Trace:\n{stack_trace}"')
        return func.HttpResponse("Erro interno do servidor", status_code=500)

