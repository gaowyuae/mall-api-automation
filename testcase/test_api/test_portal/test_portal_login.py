import pytest

from api_support.common.login_helper import LoginResponseHelper
from apis.portal.cart_item_api import CartItemAPI
from apis.portal.member_api import MemberAPI
from apis.portal.order_api import OrderAPI
from core.load_yaml import load_yaml
from test_support.db_queries.order_queries import OrderQueries
from verifications.common.login import (
    verify_login_failure,
    verify_login_success,
)
from verifications.common.response import (
    verify_business_code,
    verify_business_failure,
    verify_data_not_empty,
    verify_login_not_authorized,
    verify_message_contains_any,
)
from verifications.portal.order import (
    verify_order_exists,
    verify_order_unchanged,
)

pytestmark = [
    pytest.mark.api,
    pytest.mark.portal,
    pytest.mark.story("Login"),
]

PORTAL_LOGIN_DATA = load_yaml("portal/login_data.yaml")


class TestPortalLogin:
    """前台登录接口测试用例"""

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_001 portal登录成功")
    @pytest.mark.smoke
    def test_portal_login_success(self, portal_login_api, portal_public_session):
        """TC_ECOM_001 验证前台用户正常登录后可访问会员信息"""
        case_data = PORTAL_LOGIN_DATA["TC_ECOM_001"][0]
        response = portal_login_api.login(
            username=case_data["username"],
            password=case_data["password"],
        )
        verify_login_success(
            response,
            expected_code=case_data["expected_business_code"],
            expected_token_head=case_data["expected_token_head"],
        )

        portal_public_session.headers["Authorization"] = (
            LoginResponseHelper.build_authorization(response)
        )
        member_response = MemberAPI(portal_public_session).member_info()
        verify_business_code(
            member_response,
            case_data["expected_business_code"],
        )
        verify_data_not_empty(member_response, "会员信息")

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_002 前台用户密码错误时登录失败")
    def test_wrong_password_login_failed(
        self,
        portal_login_api,
        portal_public_session,
    ):
        """TC_ECOM_002 验证密码错误时登录失败且购物车拒绝访问"""
        case_data = PORTAL_LOGIN_DATA["TC_ECOM_002"][0]
        response = portal_login_api.login(
            username=case_data["username"],
            password=case_data["password"],
        )
        verify_login_failure(response, case_data["success_business_code"])

        cart_response = CartItemAPI(portal_public_session).cart_list()
        verify_business_failure(
            cart_response,
            case_data["success_business_code"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_003 不存在的前台用户登录失败")
    def test_unknown_user_login_failed(
        self,
        portal_login_api,
        portal_public_session,
    ):
        """TC_ECOM_003 验证不存在的用户登录失败且会员接口拒绝访问"""
        case_data = PORTAL_LOGIN_DATA["TC_ECOM_003"][0]
        response = portal_login_api.login(
            username=case_data["username"],
            password=case_data["password"],
        )
        verify_login_failure(response, case_data["success_business_code"])

        member_response = MemberAPI(portal_public_session).member_info()
        verify_business_failure(
            member_response,
            case_data["success_business_code"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_004 伪造Token访问购物车失败")
    @pytest.mark.smoke
    def test_invalid_token_access_cart_failed(self, portal_public_session):
        """TC_ECOM_004 验证伪造 Token 无法访问购物车"""
        case_data = PORTAL_LOGIN_DATA["TC_ECOM_004"][0]
        portal_public_session.headers["Authorization"] = case_data["authorization"]

        response = CartItemAPI(portal_public_session).cart_list()
        verify_business_code(response, case_data["expected_business_code"])
        verify_login_not_authorized(response, "购物车列表")

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_005 后台Token不能确认前台订单收货")
    def test_admin_token_confirm_portal_order_failed(
        self,
        admin_authorization,
        portal_public_session,
        test_conn,
    ):
        """TC_ECOM_005 验证后台 Token 不能用于确认前台订单收货"""
        case_data = PORTAL_LOGIN_DATA["TC_ECOM_005"][0]
        order_queries = OrderQueries(test_conn)
        before_state = order_queries.get_latest_member_order_by_status(
            member_username=case_data["member_username"],
            status=case_data["pending_receive_status"],
        )
        order_id = verify_order_exists(
            before_state,
            case_data["pending_receive_status"],
        )

        portal_public_session.headers["Authorization"] = admin_authorization
        response = OrderAPI(portal_public_session).confirm_receive(order_id=order_id)
        verify_business_failure(response, case_data["success_business_code"])
        verify_message_contains_any(
            response,
            case_data["expected_message_keywords"],
        )

        after_state = order_queries.get_order_state(order_id)
        verify_order_unchanged(
            before_state,
            after_state,
            case_data["pending_receive_status"],
        )
