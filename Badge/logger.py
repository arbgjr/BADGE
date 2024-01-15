import logging
import os
from opencensus.ext.azure.log_exporter import AzureLogHandler
from enum import Enum

class LogLevel(Enum):
    INFO = logging.INFO
    WARNING = logging.WARNING
    DEBUG = logging.DEBUG
    CRITICAL = logging.CRITICAL
    EXCEPTION = logging.ERROR
    FATAL = logging.FATAL
    TRACE = logging.DEBUG
    ERROR = logging.ERROR

class Logger:
    def __init__(self, logger_name, default_level=LogLevel.INFO):
        self.logger = logging.getLogger(logger_name)
        self.default_level = default_level

        # Configure o logger apenas se houver uma chave de instrumentação do Application Insights
        appinsights_key = os.environ.get("APPINSIGHTS_INSTRUMENTATIONKEY")
        if appinsights_key:
            self._configure_logger(appinsights_key)

    def _configure_logger(self, appinsights_key):
        handler = AzureLogHandler(connection_string=f'InstrumentationKey={appinsights_key}')
        self.logger.addHandler(handler)

        # Adicionar um filtro personalizado
        custom_filter = CustomLogFilter()
        self.logger.addFilter(custom_filter)

    def log(self, level, message):
        if not isinstance(level, LogLevel):
            self.logger.log(LogLevel.INFO.value, f"Nível de log inválido: {level}, configurado para INFO. {message}")
        else:
            self.logger.log(level.value, message)

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