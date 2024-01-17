import traceback
import azure.functions as func
from flask import jsonify
from .logger import LogLevel, Logger
import inspect
import logging

logging.log(logging.INFO,"[__init__.py] Iniciando")

# Crie uma instância do Logger com um nome específico
logger = Logger("AzFuncBadges", default_level=LogLevel.DEBUG)

from .app import application

def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    # Log da solicitação recebida
    frame = inspect.currentframe().f_back
    module_name = inspect.getmodule(frame).__name__
    class_name = frame.f_globals.get('__qualname__')
    function_name = frame.f_code.co_name
    caller_info = f"{module_name}.{class_name}.{function_name}"
    logger.log(caller_info, LogLevel.DEBUG, 'Python HTTP trigger function processed a request.')
    logger.log(caller_info, LogLevel.DEBUG, f'Request method: {req.method}')
    logger.log(caller_info, LogLevel.DEBUG, f'Request URL: {req.url}')

    try:
        # Executar aplicação Flask através do WsgiMiddleware
        logger.log(caller_info, LogLevel.DEBUG, f"[__init__.py] Executar aplicação Flask através do WsgiMiddleware") 
        response = func.WsgiMiddleware(application.wsgi_app).handle(req, context)
        logger.log(caller_info, LogLevel.DEBUG, 'Flask app processed the request successfully.')
        return response
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.log(caller_info, LogLevel.ERROR, f'Erro ao processar a solicitação: {str(e)}\nStack Trace:\n{stack_trace}"')
        return func.HttpResponse("Erro interno do servidor", status_code=500)

