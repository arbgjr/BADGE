import logging
import os
from opencensus.ext.azure.log_exporter import AzureLogHandler
from enum import Enum
import inspect
from concurrent.futures import ThreadPoolExecutor
import sys
import threading
from datetime import datetime
import pytz


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
    def __init__(self, logger_name, default_level=logging.DEBUG):
        self.logger = logging.getLogger(logger_name)
        self.default_level = default_level
        self.handler = None

        # Executor assíncrono para operações de logging
        self.executor = ThreadPoolExecutor(max_workers=1)

        appinsights_key = os.environ.get("APPINSIGHTS_INSTRUMENTATIONKEY")
        if appinsights_key:
            self._configure_logger(appinsights_key)

    def _configure_logger(self, appinsights_key):
        self.handler = FlushAzureLogHandler(connection_string=f'InstrumentationKey={appinsights_key}')
        formatter = logging.Formatter(
            fmt='%(asctime)s [Thread %(thread)d] %(module)s.%(funcName)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S %Z'
        )
        self.handler.setFormatter(formatter)
        self.logger.addHandler(self.handler)

        # Adicionar um filtro personalizado ao logger
        custom_filter = CustomLogFilter()
        self.logger.addFilter(custom_filter)

    def log(self, level, message):
        caller_info = self._get_caller_info()
        # Utilize o executor para fazer o log de forma assíncrona
        self.executor.submit(self._log_message, caller_info, level, message)

    def _log_message(self, caller_info, level, message):
        if not isinstance(level, LogLevel):
            level = LogLevel.INFO
        
        # Obter o ID da thread atual
        thread_id = threading.get_ident()
        
        formatted_message = f"[Thread {thread_id}] {caller_info} - {message}"
        self.logger.log(level.value, formatted_message)

    def flush_logs(self):
        # Assíncrono: agende a operação de flush no executor
        self.executor.submit(self.handler.flush)

    def _get_caller_info(self):
        """
        Obtém informações sobre o chamador da função de log.
        Retorna o nome do módulo, da classe e da função.
        """
        frame = inspect.currentframe()

        # Sobe dois níveis na pilha de chamadas
        frame = frame.f_back.f_back 

        module_name = inspect.getmodule(frame).__name__
        class_name = frame.f_globals.get('__qualname__', '<no class>')
        function_name = frame.f_code.co_name

        return f"{module_name}.{class_name}.{function_name}"

    def add_file_handler(self, filename, level=None):
        """Adiciona um FileHandler ao logger."""
        file_handler = logging.FileHandler(filename)
        file_handler.setLevel(level if level is not None else self.default_level.value)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)

    def add_stream_handler(self, stream=sys.stdout, level=None):
        """Adiciona um StreamHandler ao logger."""
        stream_handler = logging.StreamHandler(stream)
        stream_handler.setLevel(level if level is not None else self.default_level.value)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        stream_handler.setFormatter(formatter)
        self.logger.addHandler(stream_handler)

    def add_custom_handler(self, handler):
        """Adiciona um handler customizado ao logger."""
        self.logger.addHandler(handler)

    def remove_all_handlers(self):
        """Remove todos os handlers do logger."""
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)

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
