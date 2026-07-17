import pytest

from core.logkit import bind_context, clear_context, init_logging, new_trace_id


def pytest_sessionstart(session):
    init_logging(service="python-mall-test")


@pytest.fixture(autouse=True)
def _bind_case_log_context(request):
    bind_context(trace_id=new_trace_id(), case_id=request.node.nodeid)
    yield
    clear_context()
