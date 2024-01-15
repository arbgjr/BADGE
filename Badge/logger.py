import logging
import os
from opencensus.ext.azure.log_exporter import AzureLogHandler

class Logger:
    def __init__(self, logger_name):
        self.logger = logging.getLogger(logger_name)

        # Configure o logger apenas se houver uma chave de instrumentação do Application Insights
        appinsights_key = os.environ.get("APPINSIGHTS_INSTRUMENTATIONKEY")
        if appinsights_key:
            self._configure_logger(appinsights_key)

    def _configure_logger(self, appinsights_key):
        handler = AzureLogHandler(connection_string=f'InstrumentationKey={appinsights_key}')
        self.logger.addHandler(handler)

        # Configurar o nível de log padrão (você pode ajustar conforme necessário)
        self.logger.setLevel(logging.INFO)

        # Adicionar um filtro personalizado
        custom_filter = CustomLogFilter()
        self.logger.addFilter(custom_filter)

    def log(self, level, message):
        # Método genérico para registrar logs com o nível especificado
        if level == 'info':
            self.logger.info(message)
        elif level == 'warning':
            self.logger.warning(message)
        elif level == 'debug':
            self.logger.debug(message)
        elif level == 'critical':
            self.logger.critical(message)
        elif level == 'exception':
            self.logger.exception(message)
        elif level == 'fatal':
            self.logger.fatal(message)
        elif level == 'trace':
            self.logger.trace(message)
        elif level == 'error':
            self.logger.error(message)
        else:
            # Nível de log inválido, você pode lidar com isso de acordo com suas necessidades
            raise ValueError(f"Nível de log inválido: {level}")

class CustomLogFilter(logging.Filter):
    def filter_conditions(self):
        return [self.filter_azappconfig, self.filter_response, self.filter_azkv]

    def filter_azappconfig(self, message):
        return 'azappconfigengagement.azconfig.io' not in message

    def filter_azkv(self, message):
        return 'azkv-engagement.vault.azure.net' not in message

    def filter_response(self, message):
        return not ('Response status:' in message and 'x-ms-request-id' in message)

    def filter(self, record):
        message = record.getMessage()
        return all(condition(message) for condition in self.filter_conditions())