import logging
from logging.handlers import RotatingFileHandler
import pathlib

def configure_logging():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_path = pathlib.Path(__file__).resolve().parent.parent
    handler = RotatingFileHandler(root_path/"logs/tests.log", maxBytes=5*1024*1024, backupCount=3)
    formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s'
    )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

configure_logging()