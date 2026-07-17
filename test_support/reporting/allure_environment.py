import json
import os
import platform
from pathlib import Path

from config.settings.admin_path import ADMIN_BASE_URL
from config.settings.database import DB_CONFIG
from config.settings.portal_path import PORTAL_BASE_URL


def write_environment(result_dir):
    import pytest

    result_path = Path(result_dir)
    result_path.mkdir(parents=True, exist_ok=True)

    env_file = result_path / "environment.properties"

    values = {
        "APP_ENV": os.getenv("APP_ENV", "local"),
        "PORTAL_BASE_URL": PORTAL_BASE_URL,
        "ADMIN_BASE_URL": ADMIN_BASE_URL,
        "DB_HOST": DB_CONFIG["host"],
        "DB_DATABASE": DB_CONFIG["database"],
        "PYTHON_VERSION": platform.python_version(),
        "PYTEST_VERSION": pytest.__version__,
        "OS": platform.platform(),
    }

    env_file.write_text(
        "\n".join(f"{key}={value}" for key, value in values.items()),
        encoding="utf-8",
    )


def write_categories(result_dir):
    categories = [
        {
            "name": "接口断言失败",
            "matchedStatuses": ["failed"],
            "messageRegex": ".*业务断言失败.*|.*响应.*|.*code.*",
        },
        {
            "name": "环境或服务不可用",
            "matchedStatuses": ["broken"],
            "messageRegex": ".*ConnectionError.*|.*Timeout.*|.*Max retries "
            "exceeded.*",
        },
        {
            "name": "数据库问题",
            "matchedStatuses": ["broken", "failed"],
            "messageRegex": ".*pymysql.*|.*MySQL.*|.*DB.*|.*database.*",
        },
        {
            "name": "用例代码异常",
            "matchedStatuses": ["broken"],
            "messageRegex": ".*TypeError.*|.*AttributeError.*|.*KeyError.*",
        },
    ]

    Path(result_dir, "categories.json").write_text(
        json.dumps(categories, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_executor(result_dir):
    executor = {
        "name": "Local Pytest",
        "type": "pytest",
        "url": "",
        "buildName": os.getenv("BUILD_NAME", "local-run"),
        "buildUrl": os.getenv("BUILD_URL", ""),
        "reportName": "Python Mall 自动化测试报告",
    }

    Path(result_dir, "executor.json").write_text(
        json.dumps(executor, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
