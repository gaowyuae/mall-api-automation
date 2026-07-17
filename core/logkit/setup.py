import logging
import logging.config
import os

from core.logkit.config import build_logging_dict

_INITIALIZED = False


def init_logging(force=False, service="python-mall"):
    global _INITIALIZED
    if _INITIALIZED and not force:
        return

    env = os.getenv("APP_ENV", "local")
    cfg = build_logging_dict(service=service, env=env)
    logging.config.dictConfig(cfg)
    _INITIALIZED = True


def get_logger(name=None):
    return logging.getLogger(name if name else "python-mall")
