import logging
import azure.functions as func
from .app import application

# Configurar o nível de log para INFO
logging.basicConfig(level=logging.INFO)

def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    # Log da solicitação recebida
    logging.info('Python HTTP trigger function processed a request.')
    logging.info(f'Request method: {req.method}')
    logging.info(f'Request URL: {req.url}')

    try:
        # Executar aplicação Flask através do WsgiMiddleware
        logging.info(f"[_init_.py] Executar aplicação Flask através do WsgiMiddleware") 
        response = func.WsgiMiddleware(application.wsgi_app).handle(req, context)
        logging.info('Flask app processed the request successfully.')
        return response
    except Exception as e:
        logging.error(f'Erro ao processar a solicitação: {str(e)}')
        return func.HttpResponse("Erro interno do servidor", status_code=500)

