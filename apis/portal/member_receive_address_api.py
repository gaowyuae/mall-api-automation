from config.settings.portal_path import PORTAL_MEMBER_RECEIVE_ADDRESS_API_PATHS
from core.http_client import BaseAPI


class MemberReceiveAddressAPI(BaseAPI):
    def address_list(self):
        response = self.get(PORTAL_MEMBER_RECEIVE_ADDRESS_API_PATHS["ADDRESS_LIST"])
        self.assert_http_ok(response, "address_list")
        return self.to_json(response)


def address_list(session):
    return MemberReceiveAddressAPI(session).address_list()
