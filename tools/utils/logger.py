# logger.py
import os
import logging
from logging.handlers import RotatingFileHandler

# Create a logger instance
def create_logger():

    # Get the base directory file path
    base_dir = f'{os.path.dirname(os.path.abspath(__file__))}/../../'
    print(base_dir)

    # Create logger
    logger = logging.getLogger('SEA_logger')
    logger.setLevel(logging.DEBUG)  # Set the root logger level to DEBUG

    # Stream handler with DEBUG level
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_formatter = logging.Formatter("%(asctime)s [%(levelname)s]: %(message)s", datefmt="%d-%m-%Y %H:%M:%S")
    stream_handler.setFormatter(stream_formatter)

    # File handler with DEBUG level and rotating file configuration
    file_handler = RotatingFileHandler(base_dir + '/logs/SEA.log',
                                       maxBytes=500000,  # 500 MB
                                       backupCount=5)   # 5 files are on rotation
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter("'%(asctime)s - %(name)s - [%(levelname)s]: %(message)s'", datefmt="%d-%m-%Y %H:%M:%S")
    file_handler.setFormatter(file_formatter)

    # Add handlers to the logger
    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

    return logger


# Instantiate the logger
logger = create_logger()