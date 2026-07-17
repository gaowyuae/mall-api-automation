import json

DEFAULT_SENSITIVE_KEYS = {
    "password",
    "token",
    "authorization",
    "secret",
    "api_key",
    "access_token",
}
MASK = "***"


def _mask_sensitive(values):
    """递归隐藏字典、列表、元组中的敏感信息"""
    if isinstance(values, dict):
        return {
            key: MASK
            if str(key).lower() in DEFAULT_SENSITIVE_KEYS
            else _mask_sensitive(value)
            for key, value in values.items()
        }

    if isinstance(values, list):
        return [_mask_sensitive(value) for value in values]

    if isinstance(values, tuple):
        return tuple(_mask_sensitive(value) for value in values)

    if isinstance(values, str) and values.lower().startswith("bearer "):
        return f"Bearer {MASK}"

    return values


def attach_json(name, data):
    import allure

    allure.attach(
        json.dumps(
            _mask_sensitive(data),
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        name=name,
        attachment_type=allure.attachment_type.JSON,
    )


def attach_http_request(
    method,
    url,
    params=None,
    json_data=None,
    data=None,
    timeout=None,
):
    attach_json(
        "request.json",
        {
            "method": method,
            "url": url,
            "params": params,
            "json": json_data,
            "data": data,
            "timeout": timeout,
        },
    )


def attach_http_response(response, elapsed_ms=None):
    try:
        body = response.json()
    except ValueError:
        body = response.text[:1000]

    attach_json(
        "response.json",
        {
            "status_code": response.status_code,
            "elapsed_ms": elapsed_ms,
            "body": body,
        },
    )


def attach_context(context):
    attach_json("context.json", context)
