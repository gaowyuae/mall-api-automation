import json
import logging
from datetime import UTC, datetime

_RESERVED = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
}


def _has_value(value):
    return value not in (None, "", "-")


class PlainFormatter(logging.Formatter):
    def __init__(self):
        super().__init__(datefmt="%Y-%m-%d %H:%M:%S")

    def format(self, record):
        record.message = record.getMessage()
        timestamp = (f"{self.formatTime(record, self.datefmt)}."
                     f"{int(record.msecs):03d}")
        parts = [
            timestamp,
            record.levelname,
            record.name,
        ]

        event = getattr(record, "event", "-")
        if _has_value(event):
            parts.append(f"event={event}")

        parts.append(f"trace={getattr(record, 'trace_id', '-')}")

        request_id = getattr(record, "request_id", "-")
        if _has_value(request_id):
            parts.append(f"req={request_id}")

        parts.append(f"case={getattr(record, 'case_id', '-')}")
        parts.append(record.message)

        http_method = getattr(record, "http_method", None)
        http_path = getattr(record, "http_path", None)

        if _has_value(http_method) and _has_value(http_path):
            parts.append(f"{http_method} {http_path}")
        elif _has_value(http_method):
            parts.append(str(http_method))
        elif _has_value(http_path):
            parts.append(str(http_path))

        status_code = getattr(record, "response_status_code", None)
        if status_code is not None:
            parts.append(f"status={status_code}")

        elapsed_ms = getattr(record, "elapsed_ms", None)
        if elapsed_ms is not None:
            parts.append(f"{elapsed_ms}ms")

        line = " | ".join(str(part) for part in parts)

        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
            line = f"{line}\n{record.exc_text}"

        if record.stack_info:
            line = f"{line}\n{self.formatStack(record.stack_info)}"

        return line


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "ts": datetime.fromtimestamp(
                record.created, tz=UTC
            ).isoformat(),  # 日志时间
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),  # record.msg + record.args
            "trace_id": getattr(record, "trace_id", "-"),
            "case_id": getattr(record, "case_id", "-"),
            "service": getattr(record, "service", "python-mall"),
            "env": getattr(record, "env", "local"),
            "module": record.module,
            "func": record.funcName,
            "line": record.lineno,
        }

        for k, v in record.__dict__.items():
            if k not in _RESERVED and k not in payload:
                payload[k] = v

        if record.exc_info:
            payload["exception"] = self.formatException(
                record.exc_info
            )

        return json.dumps(payload, ensure_ascii=False)
