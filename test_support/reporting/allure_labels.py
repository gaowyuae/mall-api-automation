import os

import allure

EPIC = "Python Mall 自动化测试"

FEATURE_BY_MARKER = {
    "portal": "Portal",
    "admin": "Admin",
    "integration": "Integration",
    "db": "Database",
}

SEVERITY_BY_MARKER = {
    "p0": allure.severity_level.BLOCKER,
    "p1": allure.severity_level.CRITICAL,
    "p2": allure.severity_level.NORMAL,
    "p3": allure.severity_level.MINOR,
}

TAG_MARKERS = ("api", "smoke")
DEFAULT_OWNER = os.getenv("ALLURE_OWNER", "gaojun")


def _has_marker(item, marker_name):
    return item.get_closest_marker(marker_name) is not None


def _marker_text(item, marker_name):
    marker = item.get_closest_marker(marker_name)
    if marker is None:
        return None

    value = marker.args[0] if marker.args else marker.kwargs.get("name")
    if value is None:
        return None

    value = str(value).strip()
    return value or None


def _case_param(item, *names):
    callspec = getattr(item, "callspec", None)
    if callspec is None:
        return None

    for name in names:
        value = callspec.params.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()

    return None


def _apply_title(item):
    case_id = _case_param(item, "case_id")
    case_title = _case_param(item, "case_title", "title")
    marker_title = _marker_text(item, "title")

    if case_id and case_title:
        allure.dynamic.title(f"{case_id} {case_title}")
    elif case_id:
        allure.dynamic.title(case_id)
    elif case_title:
        allure.dynamic.title(case_title)
    elif marker_title:
        allure.dynamic.title(marker_title)


def apply_allure_labels(item):
    allure.dynamic.epic(EPIC)
    _apply_title(item)

    feature_marker = next(
        (
            marker_name
            for marker_name in FEATURE_BY_MARKER
            if _has_marker(item, marker_name)
        ),
        None,
    )

    if feature_marker:
        allure.dynamic.feature(FEATURE_BY_MARKER[feature_marker])

    story = _marker_text(item, "story")
    if story:
        allure.dynamic.story(story)

    for marker_name, severity in SEVERITY_BY_MARKER.items():
        if _has_marker(item, marker_name):
            allure.dynamic.severity(severity)
            break

    allure.dynamic.label("owner", DEFAULT_OWNER)

    for marker_name in TAG_MARKERS:
        if _has_marker(item, marker_name):
            allure.dynamic.tag(marker_name)
