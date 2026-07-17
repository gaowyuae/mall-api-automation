from config.settings.portal_path import PORTAL_MEMBER_API_PATHS
from core.http_client import BaseAPI


class MemberAPI(BaseAPI):
    def member_info(self, name=None):
        response = self.get(
            PORTAL_MEMBER_API_PATHS["MEMBER_INFO"],
            params={"name": name},
        )
        self.assert_http_ok(response, "member_info")
        return self.to_json(response)


def member_info(session, name=None):
    return MemberAPI(session).member_info(name)
