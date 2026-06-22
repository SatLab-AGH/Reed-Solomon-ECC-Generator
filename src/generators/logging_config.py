# MIT License

# Copyright (c) 2026 Jan Rosa, Mateusz Maź, SatLab AGH

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

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


def _running_under_cocotb() -> bool:
    return "COCOTB_SIM" in os.environ


def setup_logging(rel_log_path: Path | str = "unspecified.log"):
    """Initialize logging safely for both normal runs and cocotb."""
    log_path = proj_path / "build/logs" / Path(rel_log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    LOGGING_CONFIG["handlers"]["file"]["filename"] = str(log_path)

    if _running_under_cocotb():
        # Configure only project loggers, leave cocotb root intact
        for name, cfg in LOGGING_CONFIG["loggers"].items():
            logger = logging.getLogger(name)
            logger.setLevel(cfg["level"])

            # remove existing handlers only from this logger
            logger.handlers.clear()

            for handler_name in cfg["handlers"]:
                handler_cfg = LOGGING_CONFIG["handlers"][handler_name]
                handler = logging.config._handlers.get(handler_name)

                if handler is None:
                    handler = logging.config.dictConfig(
                        {
                            "version": 1,
                            "handlers": {handler_name: handler_cfg},
                        }
                    )

                logger.addHandler(logging.getHandlerByName(handler_name))

            logger.propagate = cfg.get("propagate", True)

    else:
        # Normal execution
        logging.config.dictConfig(LOGGING_CONFIG)
