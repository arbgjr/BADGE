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
            caller_info = self._get_caller_info()
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
    @staticmethod
    def filter_azappconfig(record):
        return 'azappconfigengagement.azconfig.io' not in record.getMessage()

    @staticmethod
    def filter_azkv(record):
        return 'azkv-engagement.vault.azure.net' not in record.getMessage()

    @staticmethod
    def filter_response(record):
        message = record.getMessage()
        return not ('Response status:' in message and 'x-ms-request-id' in message)

    def filter(self, record):
        filters = [CustomLogFilter.filter_azappconfig, CustomLogFilter.filter_azkv, CustomLogFilter.filter_response]
        return all(f(record) for f in filters)

class FlushAzureLogHandler(AzureLogHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()
