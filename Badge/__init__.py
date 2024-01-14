import logging
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.trace import config_integration
import os
import azure.functions as func
from .app import application

# Configurar o log
config_integration.trace_integrations(['logging'])
logger = logging.getLogger(__name__)
APPINSIGHTS_INSTRUMENTATIONKEY = os.environ["APPINSIGHTS_INSTRUMENTATIONKEY"]
handler = AzureLogHandler(connection_string=f'InstrumentationKey={APPINSIGHTS_INSTRUMENTATIONKEY}')
logger.addHandler(handler)

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

