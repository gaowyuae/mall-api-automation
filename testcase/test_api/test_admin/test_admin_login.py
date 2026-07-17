import pytest

from core.load_yaml import load_yaml
from verifications.common.login import verify_login_success

ADMIN_LOGIN_DATA = load_yaml("admin/login_data.yaml")

pytestmark = [
    pytest.mark.api,
    pytest.mark.admin,
    pytest.mark.story("Login"),
]


class TestAdminLogin:
    """后台登录接口测试用例"""

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_006 后台商家登录成功")
    def test_admin_login_success(self, admin_login_api):
        """TC_ECOM_006 验证后台商家使用正确账号密码登录成功"""
        case_data = ADMIN_LOGIN_DATA["TC_ECOM_006"][0]
        response = admin_login_api.login(
            password=case_data["password"],
            username=case_data["username"],
        )
        verify_login_success(
            response,
            expected_code=case_data["expected_business_code"],
            expected_token_head=case_data["expected_token_head"],
        )
