import logging
import os
from logging.handlers import RotatingFileHandler
import sys

def setup_logging(max_bytes = 10*1024*1024):
    """Creates a logging system"""

    log_folder = os.path.join(os.path.expanduser('~'), 'p4cman-logs')
    os.makedirs(log_folder, exist_ok=True)
    log_file_path = os.path.join(log_folder, 'p4cman.log')

    # logger
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    log_format = '%(asctime)s - %(levelname)-8s - %(name)s - %(funcName)s:%(lineno)d - %(message)s'
    formatter = logging.Formatter(log_format)

    file_handler = RotatingFileHandler(log_file_path, maxBytes=max_bytes, backupCount=5, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    def handle_exception(exc_type, exc_value, exc_traceback):

        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logger.critical("Unhandled exception caught: ", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception

    logger.info("Logging system initialized Log file at : %s", log_file_path)
