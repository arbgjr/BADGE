import logging
import os
from opencensus.ext.azure.log_exporter import AzureLogHandler
from enum import Enum
import inspect

class LogLevel(Enum):
    INFO = logging.INFO
    WARNING = logging.WARNING
    DEBUG = logging.INFO
    CRITICAL = logging.CRITICAL
    EXCEPTION = logging.ERROR
    FATAL = logging.FATAL
    TRACE = logging.DEBUG
    ERROR = logging.ERROR

class Logger:
    def __init__(self, logger_name, default_level=LogLevel.INFO):
        logging.log(logging.INFO,"Inicializando Logger")
        self.logger = logging.getLogger(logger_name)
        logging.log(logging.INFO,"Definindo nivel default")
        self.default_level = default_level
        logging.log(logging.INFO, "Handler = none")
        self.handler = None

        # Configure o logger apenas se houver uma chave de instrumentação do Application Insights
        logging.log(logging.INFO, "Configure o logger apenas se houver uma chave de instrumentação do Application Insights")
        appinsights_key = os.environ.get("APPINSIGHTS_INSTRUMENTATIONKEY")
        if appinsights_key:
            logging.log(logging.INFO, "Configure o logger com a chave de instrumentação do Application Insights")
            self._configure_logger(appinsights_key)

    def _configure_logger(self, appinsights_key):
        logging.log(logging.INFO, "Iniciando coniguração do logger...")
        logging.log(logging.INFO, "Definindo handler de flush.")
        self.handler = FlushAzureLogHandler(connection_string=f'InstrumentationKey={appinsights_key}')
        logging.log(logging.INFO, "addHandler(self.handler)")
        self.logger.addHandler(self.handler)

        # Adicionar um filtro personalizado ao logger
        logging.log(logging.INFO, "Adicionar um filtro personalizado ao logger")
        custom_filter = CustomLogFilter()
        logging.log(logging.INFO, "addFilter(custom_filter)")
        self.logger.addFilter(custom_filter)

    def log(self, caller_info, level, message):
        if not isinstance(level, LogLevel):
            logging.log(logging.INFO,  f"Nível de log inválido: {level}, configurado para INFO. {message}")
        else:
            formatted_message = f"{caller_info} - {message}"
            self.logger.log(level.value, formatted_message)
        self.flush_logs()

    def flush_logs(self):
        if self.handler:
            self.handler.flush()

    def _get_caller_info(self):
        frame = inspect.currentframe().f_back
        module_name = inspect.getmodule(frame).__name__
        class_name = frame.f_globals.get('__qualname__')
        function_name = frame.f_code.co_name
        return f"{module_name}.{class_name}.{function_name}"

class CustomLogFilter(logging.Filter):
    def filter_conditions(self):
        return [
            self.filter_keyvault_response,
            self.filter_keyvault_request,
            self.filter_appconfig_request,
            self.filter_appconfig_response
        ]

    @staticmethod
    def filter_keyvault_request(message):
        result = 'vault.azure.net' not in message
        print(f"filter_keyvault_request: {message} -> {result}")
        return result
    
    @staticmethod
    def filter_keyvault_response(message):
        # Filtrar mensagens de resposta do Key Vault
        if 'Response status: 200' in message and 'x-ms-keyvault-region' in message:
            return False
        return True

    @staticmethod
    def filter_appconfig_request(message):
        # Filtrar requisições para o Azure App Configuration
        return 'azappconfigengagement.azconfig.io' not in message

    @staticmethod
    def filter_appconfig_response(message):
        # Filtrar mensagens de resposta do Key Vault
        if 'Response status: 200' in message and 'application/vnd.microsoft.appconfig.kv+json' in message:
            return False
        return True

    def filter(self, record):
        message = record.getMessage()
        return all(condition(message) for condition in self.filter_conditions())

class FlushAzureLogHandler(AzureLogHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()
