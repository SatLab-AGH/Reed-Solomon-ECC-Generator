# src/my_package/logging_config.py
import logging.config
import os
from pathlib import Path

proj_path = Path(__file__).resolve().parent.parent.parent.resolve()

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "detailed",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "default",
            "filename": "unspecified.log",
            "maxBytes": 10485760,  # 10 MB
            "backupCount": 3,
        },
    },
    "root": {
        "level": "WARNING",
        "handlers": ["console", "file"],
    },
    "loggers": {
        "src": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
            "propagate": False,  # Avoid double logging
        },
        "tests": {
            "level": "DEBUG",
            "handlers": ["console"],
            "propagate": False,
        },
    },
}


def setup_logging(rel_log_path: Path | str = "unspecified.log"):
    """Call this once at program start."""
    log_path = proj_path / Path("build/logs/") / Path(rel_log_path)
    os.makedirs(log_path.parent, exist_ok=True)
    LOGGING_CONFIG["handlers"]["file"]["filename"] = log_path
    logging.config.dictConfig(LOGGING_CONFIG)
