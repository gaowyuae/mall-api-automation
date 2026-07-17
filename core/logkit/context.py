import uuid
from contextvars import ContextVar

_TRACE_ID = ContextVar("trace_id", default="-")
_CASE_ID = ContextVar("case_id", default="-")
_REQUEST_ID = ContextVar("request_id", default="-")


def new_trace_id():
    return uuid.uuid4().hex[:16]


def new_request_id():
    return uuid.uuid4().hex[:8]


def bind_context(trace_id=None, case_id=None, request_id=None):
    if trace_id is not None:
        _TRACE_ID.set(trace_id)
    if case_id is not None:
        _CASE_ID.set(case_id)
    if request_id is not None:
        _REQUEST_ID.set(request_id)


def clear_context():
    _TRACE_ID.set("-")
    _CASE_ID.set("-")
    _REQUEST_ID.set("-")


def get_context():
    return {
        "trace_id": _TRACE_ID.get(),
        "case_id": _CASE_ID.get(),
        "request_id": _REQUEST_ID.get(),
    }
