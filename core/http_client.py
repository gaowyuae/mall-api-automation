import json
import time
from urllib.parse import urljoin, urlsplit

import allure

from config.settings.runtime import REQUEST_TIMEOUT
from core.logkit import get_context, get_logger, new_request_id
from test_support.reporting import (
    attach_context,
    attach_http_request,
    attach_http_response,
)

http_logger = get_logger("http")


def build_url(session, path):

    if not path:
        raise ValueError("request的API路径不能为空")
    # 判断接口地址（路径）是否为绝对路径
    if path.startswith(("http://", "https://")):
        return path
    base_url = getattr(session, "base_url", None)

    if not base_url:
        raise ValueError(
            "base_url为空，session内未有base_url，请检查fixture的helpers内部文件",
        )
    return urljoin(base_url.rstrip("/") + "/", path.lstrip("/"))


def _log_path(url):
    return urlsplit(url).path or "/"


# 发送请求,发送超时5秒，响应15秒
def send_request(session, method, path, *, params=None, json_data=None,
        data=None):
    request_id = new_request_id()
    method = str(method).upper()
    timeout = getattr(session, "timeout", REQUEST_TIMEOUT)
    url = build_url(session, path)
    http_path = _log_path(url)
    start = time.perf_counter()

    http_logger.info(
        "HTTP 请求开始发起",
        extra={
            "event": "http.request.start",
            "request_id": request_id,
            "http_method": method,
            "http_url": url,
            "http_path": http_path,
            "request_timeout": timeout,
            "request_params": params,
            "request_json": json_data,
            "request_data": data,
        },
    )

    try:
        with allure.step(f"HTTP {method} {http_path} 请求"):
            attach_context(
                {
                    **get_context(),
                    "request_id": request_id,
                    "http_method": method,
                    "http_path": http_path,
                },
            )

            attach_http_request(
                method=method,
                url=url,
                params=params,
                json_data=json_data,
                data=data,
                timeout=timeout,
            )

            response = session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                data=data,
                timeout=timeout,
            )


    except Exception:
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
        with allure.step(f"HTTP {method} {http_path} 失败"):
            attach_context(
                {
                    **get_context(),
                    "request_id": request_id,
                    "method": method,
                    "http_path": http_path,
                    "elapsed_ms": elapsed_ms,
                    "error": "http request 错误",
                },
            )

        http_logger.exception(
            "http请求异常",
            extra={
                "event": "http.request.error",
                "request_id": request_id,
                "http_method": method,
                "http_url": url,
                "http_path": http_path,
                "elapsed_ms": elapsed_ms,
            },
        )
        raise

    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    http_logger.info(
        "HTTP 请求结束",
        extra={
            "event": "http.request.end",
            "request_id": request_id,
            "http_method": method,
            "http_url": url,
            "http_path": http_path,
            "response_status_code": response.status_code,
            "elapsed_ms": elapsed_ms,
            "response_content_length": len(response.content),
        },
    )

    with allure.step(f"HTTP {method} {http_path} 响应"):
        attach_http_response(response, elapsed_ms)

    return response


def req_get(session, path, params=None):
    return send_request(session, "GET", path, params=params)


def req_post(session, path, json_data=None, params=None, data=None):
    return send_request(
        session, "POST", path, json_data=json_data, params=params, data=data,
    )


def response_json(response):
    try:
        return response.json()
    except json.JSONDecodeError as e:
        raise AssertionError(
            f"接口响应数据不是json:{response.text[:200]}"
        ) from e


class BaseAPI:
    def __init__(self, session):
        self.session = session

    def get(self, path, params=None):
        return req_get(self.session, path, params=params)

    def post(self, path, json_data=None, params=None, data=None):
        return req_post(
            self.session, path, json_data=json_data, params=params, data=data,
        )

    @staticmethod
    def to_json(response):
        return response_json(response)

    @staticmethod
    def assert_http_ok(response, action):
        assert response.status_code == 200, (
            f"{action}http响应失败，成功状态码200，实际{response.status_code},"
            f"{response.text}"
        )

    @staticmethod
    def _is_empty(value):

        if value is None:
            return True

        if isinstance(value, bool):
            return value is False

        if isinstance(value, str):
            return value.strip() == ""

        if isinstance(value, list | dict | tuple | set):
            return len(value) == 0

        if isinstance(value, int | float):
            return False  # 0/0.0 有效
        return False

    @classmethod
    def validate_required(cls, action, payload, candidate_fields, enable=True):
        """
        方法1：全部必填
        enable=True 才校验，enable=False 直接跳过
        """
        if not enable:
            return

        payload = payload or {}
        miss_required = [
            field for field in candidate_fields if
            cls._is_empty(payload.get(field))
        ]

        if miss_required:
            raise AssertionError(f"{action} 缺少必要字段: {miss_required}")

    @classmethod
    def validate_any_required(cls, action, payload, candidate_fields,
            enable=True):
        """
        方法2：至少一个必填（如 keyword / productCategoryId 二选一）
        enable=True 才校验，enable=False 直接跳过
        """
        if not enable:
            return

        payload = payload or {}
        has_any = any(
            not cls._is_empty(payload.get(field)) for field in
            candidate_fields
        )

        if not has_any:
            raise AssertionError(
                f"{action} 字段至少填写一个: {list(candidate_fields)}",
            )
