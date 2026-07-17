import logging
import re

from core.logkit.context import get_context

MASK = "***"
DEFAULT_SENSITIVE_KEYS = {
    "password",
    "token",
    "authorization",
    "secret",
    "api_key",
    "access_token",
}
BEARER_RE = re.compile(r"(?i)\bbearer\s+[a-z0-9\-\._~\+\/]+=*")

LOG_RECORD_RESERVED_KEYS = {
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
    "funcname",
    "created",
    "msecs",
    "relativecreated",
    "thread",
    "threadname",
    "processname",
    "process",
    "message",
    "asctime",
}


def _parse_keys(value):
    """将输入值解析为标准化的键集合

    Args:
        value: 待解析的键值，支持 None、逗号分隔字符串、或列表/元组/集合类型

    Returns:
        set: 由去除空白并转为小写的非空键组成的集合；
             若输入为 None 或无法匹配任何类型，则返回空集合
    """
    if value is None:
        return set()

    # 将逗号分隔的字符串拆分并标准化为键集合
    if isinstance(value, str):
        return {item.strip().lower() for item in value.split(",") if item.strip()}

    # 将列表、元组或集合中的元素转为字符串并标准化为键集合
    if isinstance(value, list | tuple | set):
        return {str(item).strip().lower() for item in value if str(item).strip()}
    return set()


def _mask(obj, sensitive_keys, allow_keys):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            key = str(k).lower()
            if key in allow_keys:
                out[k] = v
            elif key in sensitive_keys:
                out[k] = MASK
            else:
                out[k] = _mask(v, sensitive_keys, allow_keys)
        return out

    if isinstance(obj, list):
        return [_mask(i, sensitive_keys, allow_keys) for i in obj]

    if isinstance(obj, tuple):
        return tuple(_mask(i, sensitive_keys, allow_keys) for i in obj)

    if isinstance(obj, str):
        return BEARER_RE.sub("Bearer ***", obj)

    return obj


class ContextFilter(logging.Filter):
    def __init__(self, service="python-mall", env="local"):
        super().__init__()
        self.service = service
        self.env = env

    def filter(self, record):
        ctx = get_context()
        record.trace_id = ctx["trace_id"]
        record.case_id = ctx["case_id"]
        if not hasattr(record, "request_id") or ctx["request_id"] != "-":
            record.request_id = ctx["request_id"]
        record.service = self.service
        record.env = self.env
        return True


class RedactionFilter(logging.Filter):
    def __init__(self, sensitive_keys="", allow_keys=""):
        super().__init__()
        # 获取配置的敏感字段
        configured_sensitive_keys = _parse_keys(sensitive_keys)
        self.sensitive_keys = (
            configured_sensitive_keys
            if configured_sensitive_keys
            else set(DEFAULT_SENSITIVE_KEYS)
        )
        self.allow_keys = _parse_keys(allow_keys)

    def filter(self, record):
        record.msg = _mask(record.msg, self.sensitive_keys, self.allow_keys)
        # 将args进行脱敏处理
        if isinstance(record.args, dict):
            record.args = _mask(
                record.args,
                self.sensitive_keys,
                self.allow_keys,
            )
        elif isinstance(record.args, tuple):
            record.args = tuple(
                _mask(i, self.sensitive_keys, self.allow_keys) for i in record.args
            )

        for key in list(record.__dict__.keys()):
            key_lower = key.lower()
            # 查看参数是否在允许的范围内
            if key_lower in self.allow_keys:
                continue
            # 查看参数是否在敏感的参数范围内
            if key_lower in self.sensitive_keys:
                setattr(record, key, MASK)  # 将record内的敏感字段替换成MASK
                continue
            #
            if key_lower not in LOG_RECORD_RESERVED_KEYS:
                value = getattr(record, key, None)  # 获取record的属性值
                setattr(
                    record,
                    key,
                    _mask(value, self.sensitive_keys, self.allow_keys),
                )  # 将不属于原本的logger内的属性值进行彻底脱敏处理

        return True
