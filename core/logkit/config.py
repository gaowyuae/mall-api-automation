import os
from pathlib import Path

from core.paths import project_root


def _is_true(value):
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _resolve_log_root():
    raw_log_dir = (os.getenv("LOG_DIR") or "logs").strip() or "logs"
    strict_root = _is_true(os.getenv("LOG_STRICT_ROOT", "0"))
    log_dir = Path(raw_log_dir)

    if log_dir.is_absolute():
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir

    try:
        root_dir = project_root()
    except FileNotFoundError:
        if strict_root:
            raise
        root_dir = Path.cwd()

    resolved = (root_dir / log_dir).resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def build_logging_dict(service="python-mall", env="local"):
    log_root = _resolve_log_root()

    current_env = (env or os.getenv("APP_ENV", "local")).strip().lower()
    forced_fmt = os.getenv("LOG_FORMAT", "").strip().lower()

    level = os.getenv("LOG_LEVEL", "INFO").upper()
    if forced_fmt in {"plain", "json"}:
        fmt = forced_fmt
    elif current_env in {"test", "ci", "prod", "production", "staging", "uat"}:
        fmt = "json"
    else:
        fmt = "plain"

    selected_type = "json" if fmt == "json" else "plain"
    log_dirs = {}

    for log_type in ("plain", "json"):
        log_type_dir = log_root / log_type
        app_dir = log_type_dir / "app"
        error_dir = log_type_dir / "error"
        http_dir = log_type_dir / "http"
        sql_dir = log_type_dir / "sql"
        app_dir.mkdir(parents=True, exist_ok=True)
        error_dir.mkdir(parents=True, exist_ok=True)
        http_dir.mkdir(parents=True, exist_ok=True)
        sql_dir.mkdir(parents=True, exist_ok=True)
        log_dirs[log_type] = {
            "app": app_dir,
            "error": error_dir,
            "http": http_dir,
            "sql": sql_dir,
        }

    selected_dirs = log_dirs[selected_type]
    app_log_dir = selected_dirs["app"]
    error_log_dir = selected_dirs["error"]
    http_log_dir = selected_dirs["http"]
    sql_log_dir = selected_dirs["sql"]

    backup_days = int(os.getenv("LOG_BACKUP_DAYS", "14"))

    formatter_name = "json" if fmt == "json" else "plain"

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "ctx": {
                "()": "core.logkit.filters.ContextFilter",
                "service": service,
                "env": current_env,
            },
            "redact": {
                "()": "core.logkit.filters.RedactionFilter",
                "sensitive_keys": os.getenv("LOG_SENSITIVE_KEYS", ""),
                "allow_keys": os.getenv("LOG_ALLOW_KEYS", ""),
            },
        },
        "formatters": {
            "plain": {"()": "core.logkit.formatters.PlainFormatter"},
            "json": {"()": "core.logkit.formatters.JsonFormatter"},
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": level,
                "formatter": formatter_name,
                "filters": ["ctx", "redact"],
            },
            "app_file": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "level": level,
                "filename": str(app_log_dir / "app.log"),
                "when": "midnight",
                "backupCount": backup_days,
                "encoding": "utf-8",
                "formatter": formatter_name,
                "filters": ["ctx", "redact"],
            },
            "error_file": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "level": "ERROR",
                "filename": str(error_log_dir / "error.log"),
                "when": "midnight",
                "backupCount": backup_days,
                "encoding": "utf-8",
                "formatter": formatter_name,
                "filters": ["ctx", "redact"],
            },
            "http_file": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "level": level,
                "filename": str(http_log_dir / "http.log"),
                "when": "midnight",
                "backupCount": backup_days,
                "encoding": "utf-8",
                "formatter": formatter_name,
                "filters": ["ctx", "redact"],
            },
            "sql_file": {
                "class": "logging.handlers.TimedRotatingFileHandler",
                "level": level,
                "filename": str(sql_log_dir / "sql.log"),
                "when": "midnight",
                "backupCount": backup_days,
                "encoding": "utf-8",
                "formatter": formatter_name,
                "filters": ["ctx", "redact"],
            },
        },
        "loggers": {
            "http": {
                "handlers": ["console", "http_file"],
                "level": level,
                "propagate": False,
            },
            "sql": {
                "handlers": ["console", "sql_file"],
                "level": level,
                "propagate": False,
            },
        },
        "root": {
            "handlers": ["console", "app_file", "error_file"],
            "level": level,
        },
    }
