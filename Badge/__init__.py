import traceback
import azure.functions as func
from .app import application
from .logger import Logger

# Crie uma instância do Logger com um nome específico
logger = Logger("AzFuncBadges")

def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    # Log da solicitação recebida
    logger.log('debug', 'Python HTTP trigger function processed a request.')
    logger.log('debug', f'Request method: {req.method}')
    logger.log('debug', f'Request URL: {req.url}')

    try:
        # Executar aplicação Flask através do WsgiMiddleware
        logger.log('debug', f"[_init_.py] Executar aplicação Flask através do WsgiMiddleware") 
        response = func.WsgiMiddleware(application.wsgi_app).handle(req, context)
        logger.log('debug', 'Flask app processed the request successfully.')
        return response
    except Exception as e:
        stack_trace = traceback.format_exc()
        logger.log('error', f'Erro ao processar a solicitação: {str(e)}')
        return func.HttpResponse("Erro interno do servidor", status_code=500)

