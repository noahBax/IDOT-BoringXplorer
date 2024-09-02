import logging
import logging.config
import sys
from typing import Any
from configparser import ConfigParser

logger_num = ''

def setup(console_level=logging.INFO, log_prefix:Any='', do_paddle=False):

    global logger_num
    logger_num = log_prefix

    logger = logging.getLogger()

    if do_paddle:
        import PIL
        import paddleocr

    # Access log settings
    config = ConfigParser()
    config.read('config.ini')

    # Clear existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    # Catch all messages
    logger.setLevel(logging.DEBUG)

    # Create formatters and add them to handlers
    formatter = logging.Formatter(f'[%(levelname)s] %(funcName)s - %(message)s')

    # Create StreamHandler for console output
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(console_level)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    if config['BEHAVIOR']['WriteAllLogsToFiles'] == 'yes':
        # Create file handlers
        debug_handler = logging.FileHandler(f'logs/out_{log_prefix}.log', mode='w')
        info_handler = logging.FileHandler(f'logs/events_{log_prefix}.log', mode='w')
        error_handler = logging.FileHandler(f'logs/errors_{log_prefix}.log', mode='w')

        # Set levels for handlers
        debug_handler.setLevel(logging.DEBUG)
        info_handler.setLevel(logging.INFO)
        error_handler.setLevel(logging.ERROR)

        debug_handler.setFormatter(formatter)
        info_handler.setFormatter(formatter)
        error_handler.setFormatter(formatter)

        # Add handlers to the logger
        logger.addHandler(debug_handler)
        logger.addHandler(info_handler)
        logger.addHandler(error_handler)

    # Disable loggers for utility libraries
    logging.getLogger('PIL.Image').setLevel(logging.WARNING)
    logging.getLogger('ppocr').setLevel(logging.ERROR)