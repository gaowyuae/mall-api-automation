from config.settings.portal_path import PORTAL_SSO_API_PATHS
from core.http_client import BaseAPI


class PortalLoginAPI(BaseAPI):
    def login(self, username=None, password=None, enable=True):
        payload = {
            "password": password,
            "username": username,
        }

        self.validate_required(
            "portal_login",
            payload,
            ["password", "username"],
            enable,
        )

        response = self.post(
            PORTAL_SSO_API_PATHS["LOGIN"],
            params=payload,
        )

        self.assert_http_ok(response, "portal_login")
        return self.to_json(response)


def portal_login(session, username=None, password=None, enable=True):
    return PortalLoginAPI(session).login(
        username=username,
        password=password,
        enable=enable,
    )
