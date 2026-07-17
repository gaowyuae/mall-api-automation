import pytest

from api_support.common.login_helper import LoginResponseHelper
from api_support.portal.address_helper import PortalAddressHelper
from api_support.portal.cart_helper import PortalCartHelper
from api_support.portal.order_helper import PortalOrderHelper
from apis.portal.cart_item_api import CartItemAPI
from apis.portal.login_api import PortalLoginAPI
from apis.portal.member_receive_address_api import MemberReceiveAddressAPI
from apis.portal.order_api import OrderAPI
from apis.portal.product_api import PortalProductAPI
from core.load_yaml import load_yaml
from test_support.db_queries.address_queries import AddressQueries
from test_support.db_queries.create_no_address_member import CreateNoAddressMember
from test_support.db_queries.order_queries import OrderQueries
from verifications.common.login import verify_login_success
from verifications.portal.address import (
    verify_address_list_empty,
    verify_address_not_in_member_list,
    verify_database_address_count,
    verify_default_address,
    verify_default_address_database_consistency,
    verify_foreign_address,
)
from verifications.portal.cart import verify_cart_add_success
from verifications.portal.order import (
    verify_no_order_created,
    verify_order_generation_rejected,
)

pytestmark = [
    pytest.mark.api,
    pytest.mark.portal,
    pytest.mark.story("Receive Address"),
]
RECEIVE_ADDRESS_DATA = load_yaml("portal/receive_address_data.yaml")


class TestReceiveAddress:
    """前台会员收货地址接口测试用例"""

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_030 获取默认收货地址成功")
    def test_get_default_receive_address_success(self, address_api, test_conn):
        """TC_ECOM_030 验证返回当前会员字段完整的默认收货地址"""
        case_data = RECEIVE_ADDRESS_DATA["TC_ECOM_030"][0]
        address_queries = AddressQueries(test_conn)

        response = address_api.address_list()
        actual_default_address = PortalAddressHelper.find_default_address_in_response(
            response,
            default_status=case_data["default_status"],
        )
        database_address = address_queries.get_default_member_address(
            member_username=case_data["member_username"],
            address_id=(actual_default_address or {}).get("id"),
            default_status=case_data["default_status"],
        )

        address = verify_default_address(
            response,
            expected_code=case_data["expected_business_code"],
            expected_default_status=case_data["default_status"],
            required_fields=case_data["required_address_fields"],
        )
        verify_default_address_database_consistency(
            address,
            database_address,
            expected_default_status=case_data["default_status"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_031 无地址用户生成订单时被拦截")
    def test_generate_order_without_address_failed(
        self,
        portal_public_session,
        test_conn,
    ):
        """TC_ECOM_031 验证无地址用户不能生成有效订单"""
        case_data = RECEIVE_ADDRESS_DATA["TC_ECOM_031"][0]
        member_data = CreateNoAddressMember(test_conn)
        member_id = None
        cleanup_succeeded = False

        try:
            member_id = member_data.create_no_address_member(
                source_username=case_data["source_username"],
                target_username=case_data["username"],
            )
            login_response = PortalLoginAPI(portal_public_session).login(
                username=case_data["username"],
                password=case_data["password"],
            )
            verify_login_success(
                login_response,
                expected_code=case_data["expected_login_code"],
            )
            authorization = LoginResponseHelper.build_authorization(login_response)
            portal_public_session.headers["Authorization"] = authorization

            address_api = MemberReceiveAddressAPI(portal_public_session)
            cart_api = CartItemAPI(portal_public_session)
            product_api = PortalProductAPI(portal_public_session)
            order_api = OrderAPI(portal_public_session)
            cart_helper = PortalCartHelper(cart_api, product_api)
            address_queries = AddressQueries(test_conn)
            order_queries = OrderQueries(test_conn)

            address_response = address_api.address_list()
            database_address_count = address_queries.count_member_addresses(
                case_data["username"]
            )
            add_response = cart_helper.add_cart(
                product_id=case_data["product_id"],
                product_sku_id=case_data["sku_id"],
                quantity=case_data["quantity"],
            )
            verify_cart_add_success(
                add_response,
                case_data["expected_business_code"],
            )
            cart_id = cart_helper.find_id(
                product_id=case_data["product_id"],
                product_sku_id=case_data["sku_id"],
                quantity=case_data["quantity"],
            )
            before_order = order_queries.get_latest_member_order_by_status(
                case_data["username"],
                case_data["pending_order_status"],
            )

            response = order_api.generate_order(
                cart_id=cart_id,
                pay_type=case_data["pay_type"],
                member_receive_address_id=None,
                use_integration=case_data["use_integration"],
                enable=case_data["required_validation_enabled"],
            )
            after_order = order_queries.get_latest_member_order_by_status(
                case_data["username"],
                case_data["pending_order_status"],
            )

            verify_address_list_empty(
                address_response,
                expected_code=case_data["expected_business_code"],
                expected_count=case_data["expected_address_count"],
            )
            verify_database_address_count(
                database_address_count,
                expected_count=case_data["expected_address_count"],
                member_username=case_data["username"],
            )
            verify_order_generation_rejected(
                response,
                success_code=case_data["expected_business_code"],
                expected_message_keywords=case_data["expected_message_keywords"],
            )
            verify_no_order_created(
                before_order,
                after_order,
                expected_status=case_data["pending_order_status"],
            )
        finally:
            if member_id is not None:
                cleanup_succeeded = member_data.delete_no_address_member(
                    member_id=member_id,
                    target_username=case_data["username"],
                )

        if member_id is not None and not cleanup_succeeded:
            raise RuntimeError(
                "无地址测试会员存在地址、订单或清理异常，已保留现场："
                f"{case_data['username']}"
            )

    @pytest.mark.p1
    @pytest.mark.title("TC_ECOM_032 用户不能使用其他会员收货地址下单")
    def test_generate_order_with_foreign_address_failed(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        test_conn,
    ):
        """TC_ECOM_032 验证其他会员地址不出现在列表且不能用于下单"""
        case_data = RECEIVE_ADDRESS_DATA["TC_ECOM_032"][0]
        address_queries = AddressQueries(test_conn)
        order_queries = OrderQueries(test_conn)
        cart_helper = PortalCartHelper(cart_api, product_api)
        foreign_address = address_queries.get_address_owner(
            case_data["foreign_address_id"]
        )
        address_response = address_api.address_list()
        verify_foreign_address(
            foreign_address,
            current_member_username=case_data["current_member_username"],
            address_id=case_data["foreign_address_id"],
        )
        verify_address_not_in_member_list(
            address_response,
            foreign_address_id=case_data["foreign_address_id"],
            expected_code=case_data["expected_business_code"],
        )
        cart_api.clear_cart()
        add_response = cart_helper.add_cart(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        verify_cart_add_success(add_response, case_data["expected_business_code"])
        cart_id = cart_helper.find_id(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        before_order = order_queries.get_latest_member_order_by_status(
            case_data["current_member_username"],
            case_data["pending_order_status"],
        )

        response = None
        try:
            response = order_api.generate_order(
                cart_id=cart_id,
                pay_type=case_data["pay_type"],
                member_receive_address_id=case_data["foreign_address_id"],
                use_integration=case_data["use_integration"],
            )
            after_order = order_queries.get_latest_member_order_by_status(
                case_data["current_member_username"],
                case_data["pending_order_status"],
            )

            verify_order_generation_rejected(
                response,
                success_code=case_data["expected_business_code"],
                expected_message_keywords=case_data["expected_message_keywords"],
            )
            verify_no_order_created(
                before_order,
                after_order,
                expected_status=case_data["pending_order_status"],
            )
        finally:
            order_id = PortalOrderHelper.get_order_id(response)
            if order_id is not None:
                order_api.cancel_order(order_id=order_id)
