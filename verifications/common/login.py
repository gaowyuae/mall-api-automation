
from api_support.common.login_helper import LoginResponseHelper
from verifications.common.response import (
    verify_business_code,
    verify_business_failure,
)


def verify_login_success(
    response,
    expected_code = 200,
    expected_token_head = None,
):
    """校验登录成功响应及认证信息"""
    verify_business_code(response, expected_code)

    login_data = LoginResponseHelper.get_login_data(response)
    assert login_data, f"登录成功后 data 不应为空，实际为：{login_data}"

    token = LoginResponseHelper.get_token(response)
    assert token, f"登录成功后 token 不应为空，实际为：{login_data}"

    token_head = LoginResponseHelper.get_token_head(response)
    assert token_head and str(token_head).strip(), (
        f"登录成功后 tokenHead 不应为空，实际为：{login_data}"
    )
    if expected_token_head is not None:
        assert str(token_head).strip() == expected_token_head, (
            f"tokenHead 应为 {expected_token_head}，实际为：{token_head}"
        )
    return login_data


def verify_login_failure(response, success_code = 200):
    """校验登录失败且响应中不存在可用 token"""
    verify_business_failure(response, success_code)

    login_data = LoginResponseHelper.get_login_data(response)
    token = LoginResponseHelper.get_token(response)
    assert not token, f"登录失败时不应返回可用 token，实际为：{login_data}"
