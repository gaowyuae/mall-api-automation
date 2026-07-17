from apis.portal.member_receive_address_api import MemberReceiveAddressAPI


class PortalAddressHelper:
    """从当前会员的地址列表中查找收货地址"""

    def __init__(self, address_api):
        self.address_api = address_api

    @staticmethod
    def get_addresses(response):
        """从地址列表响应中读取收货地址"""
        if not isinstance(response, dict):
            return None

        addresses = response.get("data")
        if not isinstance(addresses, list):
            return None
        if not all(isinstance(address, dict) for address in addresses):
            return None
        return addresses

    @classmethod
    def find_address_in_response(
        cls,
        response,
        name=None,
        phone_number=None,
        detail_address=None,
        default_status=None,
        index=0,
    ):
        """从已返回的地址列表中查找匹配的收货地址"""
        addresses = cls.get_addresses(response)
        if addresses is None:
            return None

        matched_addresses = [
            address
            for address in addresses
            if (name is None or str(address.get("name")) == str(name))
            and (
                phone_number is None
                or str(address.get("phoneNumber")) == str(phone_number)
            )
            and (
                detail_address is None
                or str(address.get("detailAddress")) == str(detail_address)
            )
            and (
                default_status is None
                or str(address.get("defaultStatus")) == str(default_status)
            )
        ]
        try:
            return matched_addresses[index]
        except IndexError:
            return None

    @classmethod
    def find_default_address_in_response(
        cls,
        response,
        default_status=1,
    ):
        """从已返回的地址列表中查找默认收货地址"""
        return cls.find_address_in_response(
            response,
            default_status=default_status,
        )

    def find_id(
        self,
        name=None,
        phone_number=None,
        city=None,
        index=0,
    ):
        """按条件查找收货地址并返回地址 ID"""
        response = self.address_api.address_list()
        addresses = self.get_addresses(response)
        if addresses == []:
            raise ValueError("收货地址列表为空，无法获取 address_id")
        if addresses is None:
            raise ValueError("收货地址列表响应结构错误")

        address = self.find_address_in_response(
            response,
            name=name,
            phone_number=phone_number,
            detail_address=city,
            index=index,
        )
        if address is None:
            raise ValueError("未找到匹配的收货地址")
        address_id = address.get("id")
        if address_id is None:
            raise ValueError("匹配到收货地址但 id 为空")
        return address_id


def find_address_id(
    session,
    name=None,
    phone_number=None,
    city=None,
    index=0,
):
    finder = PortalAddressHelper(MemberReceiveAddressAPI(session))
    return finder.find_id(
        name=name,
        phone_number=phone_number,
        city=city,
        index=index,
    )
