import requests

from config.settings.runtime import REQUEST_TIMEOUT
from core.logkit import get_logger

app_logger = get_logger("app")


def assert_success(response, expect_code=200):
    assert isinstance(response, dict), f"响应非字典类型:{response}"
    code = response.get("code")
    assert code is not None, f"响应中缺少 code 字段: {response}"
    assert code == expect_code, (
        f"业务断言失败，预期code={expect_code}，实际code={code}: {response}"
    )


def build_session(base_url):
    session = requests.session()
    session.base_url = base_url
    session.timeout = REQUEST_TIMEOUT
    return session


def extract_login_auth(response, action):
    assert response.status_code == 200, (
        f"{action} 登录HTTP状态码应为200，实际为：{response.status_code}，"
        f"response={response.text[:300]}"
    )

    response_data = response.json()
    assert response_data.get("code") == 200, (
        f"{action} 登录业务code应为200，实际为：{response_data.get('code')}，"
        f"response={response_data}"
    )

    data = response_data.get("data") or {}
    assert isinstance(data, dict), (
        f"{action} 登录响应data应为dict，实际为：{type(data).__name__}"
    )

    token = data.get("token")
    assert token, f"{action} 登录响应缺少token，实际字段为：{list(data.keys())}"

    token_head = (data.get("tokenHead") or "Bearer").strip()
    authorization = f"{token_head} {token}"

    app_logger.info(
        "登录认证信息获取成功",
        extra={
            "event": "login.auth.success",
            "action": action,
            "token_head": token_head,
        },
    )

    return token, authorization
