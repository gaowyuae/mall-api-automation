from pathlib import Path

import allure

from core.paths import project_root

LOG_TARGETS = [
    ("plain-http-log-tail.txt", Path("logs/plain/http/http.log")),
    ("plain-error-log-tail.txt", Path("logs/plain/error/error.log")),
    ("json-http-log-tail.txt", Path("logs/json/http/http.log")),
    ("json-error-log-tail.txt", Path("logs/json/error/error.log")),
]


def _read_tail(path, nodeid, max_lines):
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    case_lines = [line for line in lines if nodeid in line]

    selected_lines = case_lines[-max_lines:] if case_lines else lines[
        -max_lines:]
    return "\n".join(selected_lines)


def attach_failure_logs(nodeid, *, max_lines=120, started_at=None):
    root = project_root()

    for name, relative_path in LOG_TARGETS:
        path = root / relative_path

        if not path.exists() or path.stat().st_size == 0:
            continue

        if started_at is not None and path.stat().st_mtime < started_at:
            continue

        content = _read_tail(path, nodeid=nodeid, max_lines=max_lines)
        if not content.strip():
            continue

        allure.attach(
            content,
            name=name,
            attachment_type=allure.attachment_type.TEXT,
        )
