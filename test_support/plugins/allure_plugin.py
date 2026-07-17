import time

import pytest

from test_support.reporting import (
    apply_allure_labels,
    attach_failure_logs,
    write_categories,
    write_environment,
    write_executor,
)


def pytest_runtest_setup(item):
    apply_allure_labels(item)


def pytest_sessionfinish(session, exitstatus):
    result_dir = getattr(session.config.option, "allure_report_dir", None)
    if result_dir:
        write_environment(result_dir)
        write_categories(result_dir)
        write_executor(result_dir)


def pytest_sessionstart(session):
    session.config._allure_log_started_at = time.time()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if not report.failed:
        return

    if report.when not in {"setup", "call", "teardown"}:
        return

    if getattr(item, "_allure_failure_logs_attached", False):
        return

    item._allure_failure_logs_attached = True

    attach_failure_logs(
        item.nodeid,
        started_at=getattr(item.config, "_allure_log_started_at", None),
    )
