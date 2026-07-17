from config.settings.admin_path import ADMIN_SSO_API_PATHS
from core.http_client import BaseAPI


class AdminLoginAPI(BaseAPI):
    def login(self, password=None, username=None, enable=True):
        payload = {
            "password": password,
            "username": username,
        }

        self.validate_required(
            "admin_login",
            payload,
            ["password", "username"],
            enable,
        )

        response = self.post(
            ADMIN_SSO_API_PATHS["LOGIN"],
            json_data=payload,
        )

        self.assert_http_ok(response, "admin_login")
        return self.to_json(response)

    def logout(self, name=None):
        """后台登录模块接口 管理员登出"""
        payload = {
            "name": name,
        }

        response = self.post(
            ADMIN_SSO_API_PATHS["LOGOUT"],
            params={key: value for key, value in payload.items() if value is not None},
        )

        self.assert_http_ok(response, "admin_logout")
        return self.to_json(response)


def admin_login(session, password=None, username=None, enable=True):
    return AdminLoginAPI(session).login(
        password=password,
        username=username,
        enable=enable,
    )


def admin_logout(session, name=None):
    return AdminLoginAPI(session).logout(name=name)
