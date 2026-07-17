
from api_support.common.response_helper import ApiResponseHelper


class LoginResponseHelper:
    """提取登录响应中的认证信息"""

    @staticmethod
    def get_login_data(response):
        data = ApiResponseHelper.get_data(response)
        return data if isinstance(data, dict) else {}

    @classmethod
    def get_token(cls, response):
        return cls.get_login_data(response).get("token")

    @classmethod
    def get_token_head(cls, response):
        return cls.get_login_data(response).get("tokenHead")

    @classmethod
    def build_authorization(cls, response):
        token = cls.get_token(response)
        if not token:
            return None

        token_head = str(cls.get_token_head(response) or "Bearer").strip()
        return f"{token_head} {token}"
