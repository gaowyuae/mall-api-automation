import pytest

from apis.admin.order_api import AdminOrderAPI
from core.load_yaml import load_yaml
from test_support.db_queries.order_queries import OrderQueries
from verifications.common.response import (
    verify_business_failure,
    verify_message_contains_any,
)
from verifications.admin.order import (
    verify_delivery_candidate,
    verify_delivery_permission_rejected,
    verify_delivery_rejected,
    verify_delivery_state_unchanged,
    verify_delivery_success,
    verify_nonexistent_delivery_rejected,
    verify_repeat_delivery_stable,
)
from workflow.admin.order_workflow import AdminOrderWorkflow

pytestmark = [
    pytest.mark.api,
    pytest.mark.admin,
    pytest.mark.story("Order Delivery"),
]
ORDER_DELIVERY_DATA = load_yaml("admin/order_delivery_data.yaml")


def _build_workflow(
    cart_api,
    product_api,
    address_api,
    order_api,
    admin_order_api,
):
    """构建后台发货场景复用的订单流程。"""
    return AdminOrderWorkflow(
        cart_api=cart_api,
        product_api=product_api,
        address_api=address_api,
        portal_order_api=order_api,
        admin_order_api=admin_order_api,
    )


class TestOrderDelivery:
    """后台商家订单发货接口测试用例"""

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_070 待发货订单填写物流信息发货成功")
    def test_paid_order_delivery_success(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        admin_order_api,
        test_conn,
    ):
        """TC_ECOM_070 验证待发货订单成功进入待收货并保存物流信息"""
        case_data = ORDER_DELIVERY_DATA["TC_ECOM_070"][0]
        workflow = _build_workflow(
            cart_api,
            product_api,
            address_api,
            order_api,
            admin_order_api,
        )
        order_queries = OrderQueries(test_conn)
        paid_context = workflow.prepare_paid_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
            pay_type=case_data["pay_type"],
        )
        paid_database_order = order_queries.get_order_state(paid_context["order_id"])
        order_id = verify_delivery_candidate(
            paid_database_order,
            case_data["paid_order_status"],
        )

        delivery_context = workflow.attempt_delivery(
            order_id=order_id,
            delivery_company=case_data["delivery_company"],
            delivery_sn=case_data["delivery_sn"],
        )
        delivered_database_order = order_queries.get_order_state(order_id)

        verify_delivery_success(
            delivery_context["delivery_response"],
            delivery_context["after_admin_detail"],
            delivery_context["portal_detail"],
            delivered_database_order,
            expected_code=case_data["expected_business_code"],
            expected_order_id=order_id,
            expected_status=case_data["shipped_order_status"],
            expected_delivery_company=case_data["delivery_company"],
            expected_delivery_sn=case_data["delivery_sn"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_071 后台发货缺少orderId失败")
    def test_delivery_missing_order_id_failed(
        self,
        admin_order_api,
        test_conn,
    ):
        """TC_ECOM_071 验证缺少 orderId 时封装校验失败且订单不变"""
        case_data = ORDER_DELIVERY_DATA["TC_ECOM_071"][0]
        order_queries = OrderQueries(test_conn)
        candidate = order_queries.get_latest_member_order_by_status(
            case_data["member_username"],
            case_data["candidate_order_status"],
        )
        order_id = verify_delivery_candidate(
            candidate,
            case_data["candidate_order_status"],
        )
        before_database_order = order_queries.get_order_state(order_id)

        delivery_response = admin_order_api.update_delivery(
            order_id=case_data["order_id"],
            delivery_company=case_data["delivery_company"],
            delivery_sn=case_data["delivery_sn"],
            enable=False,
        )
        after_database_order = order_queries.get_order_state(order_id)

        verify_business_failure(
            delivery_response,
            success_code=case_data["success_business_code"],
        )
        verify_message_contains_any(
            delivery_response,
            case_data["expected_message_keywords"],
        )
        verify_delivery_state_unchanged(
            before_database_order,
            after_database_order,
            case_data["candidate_order_status"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_072 后台发货缺少物流公司失败")
    def test_delivery_missing_company_failed(
        self,
        admin_order_api,
        test_conn,
    ):
        """TC_ECOM_072 验证缺少物流公司时封装校验失败且订单不变"""
        case_data = ORDER_DELIVERY_DATA["TC_ECOM_072"][0]
        order_queries = OrderQueries(test_conn)
        candidate = order_queries.get_latest_member_order_by_status(
            case_data["member_username"],
            case_data["candidate_order_status"],
        )
        order_id = verify_delivery_candidate(
            candidate,
            case_data["candidate_order_status"],
        )
        before_database_order = order_queries.get_order_state(order_id)

        delivery_response = admin_order_api.update_delivery(
            order_id=order_id,
            delivery_company=case_data["delivery_company"],
            delivery_sn=case_data["delivery_sn"],
            enable=False,
        )
        after_database_order = order_queries.get_order_state(order_id)

        verify_business_failure(
            delivery_response,
            success_code=case_data["success_business_code"],
        )
        verify_message_contains_any(
            delivery_response,
            case_data["expected_message_keywords"],
        )
        verify_delivery_state_unchanged(
            before_database_order,
            after_database_order,
            case_data["candidate_order_status"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_073 后台发货缺少物流单号失败")
    def test_delivery_missing_tracking_number_failed(
        self,
        admin_order_api,
        test_conn,
    ):
        """TC_ECOM_073 验证缺少物流单号时封装校验失败且订单不变"""
        case_data = ORDER_DELIVERY_DATA["TC_ECOM_073"][0]
        order_queries = OrderQueries(test_conn)
        candidate = order_queries.get_latest_member_order_by_status(
            case_data["member_username"],
            case_data["candidate_order_status"],
        )
        order_id = verify_delivery_candidate(
            candidate,
            case_data["candidate_order_status"],
        )
        before_database_order = order_queries.get_order_state(order_id)

        delivery_response = admin_order_api.update_delivery(
            order_id=order_id,
            delivery_company=case_data["delivery_company"],
            delivery_sn=case_data["delivery_sn"],
            enable=False,
        )
        after_database_order = order_queries.get_order_state(order_id)

        verify_business_failure(
            delivery_response,
            success_code=case_data["success_business_code"],
        )
        verify_message_contains_any(
            delivery_response,
            case_data["expected_message_keywords"],
        )
        verify_delivery_state_unchanged(
            before_database_order,
            after_database_order,
            case_data["candidate_order_status"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_075 待支付订单不能发货")
    def test_pending_payment_order_delivery_failed(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        admin_order_api,
        test_conn,
    ):
        """TC_ECOM_075 验证待支付订单发货失败且状态和物流字段不变"""
        case_data = ORDER_DELIVERY_DATA["TC_ECOM_075"][0]
        workflow = _build_workflow(
            cart_api,
            product_api,
            address_api,
            order_api,
            admin_order_api,
        )
        order_queries = OrderQueries(test_conn)
        pending_context = workflow.prepare_pending_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
            pay_type=case_data["pay_type"],
        )
        before_database_order = order_queries.get_order_state(
            pending_context["order_id"]
        )
        order_id = verify_delivery_candidate(
            before_database_order,
            case_data["pending_order_status"],
        )

        try:
            delivery_response = admin_order_api.update_delivery(
                order_id=order_id,
                delivery_company=case_data["delivery_company"],
                delivery_sn=case_data["delivery_sn"],
            )
            admin_detail_response = admin_order_api.order_detail(order_id=order_id)
            after_database_order = order_queries.get_order_state(order_id)

            verify_delivery_rejected(
                delivery_response,
                admin_detail_response,
                before_database_order,
                after_database_order,
                success_code=case_data["expected_business_code"],
                detail_code=case_data["expected_business_code"],
                expected_status=case_data["pending_order_status"],
                expected_message_keywords=case_data["expected_message_keywords"],
            )
        finally:
            current_order = order_queries.get_order_state(order_id)
            if (current_order or {}).get("status") == case_data["pending_order_status"]:
                workflow.portal_workflow.cancel_created_order(
                    pending_context["generate_response"]
                )

    @pytest.mark.p1
    @pytest.mark.title("TC_ECOM_074 后台发货不存在订单失败")
    def test_nonexistent_order_delivery_failed(
        self,
        admin_order_api,
        test_conn,
    ):
        """TC_ECOM_074 验证不存在订单不能被后台发货"""
        case_data = ORDER_DELIVERY_DATA["TC_ECOM_074"][0]
        order_queries = OrderQueries(test_conn)
        before_database_order = order_queries.get_order_state(case_data["order_id"])

        delivery_response = admin_order_api.update_delivery(
            order_id=case_data["order_id"],
            delivery_company=case_data["delivery_company"],
            delivery_sn=case_data["delivery_sn"],
        )
        after_database_order = order_queries.get_order_state(case_data["order_id"])

        verify_nonexistent_delivery_rejected(
            delivery_response,
            before_database_order,
            after_database_order,
            success_code=case_data["success_business_code"],
            expected_message_keywords=case_data["expected_message_keywords"],
        )

    @pytest.mark.p1
    @pytest.mark.title("TC_ECOM_076 已发货订单重复发货失败或保持不变")
    def test_repeat_delivery_is_rejected_or_stable(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        admin_order_api,
        test_conn,
    ):
        """TC_ECOM_076 验证重复发货不会重复修改已发货订单"""
        case_data = ORDER_DELIVERY_DATA["TC_ECOM_076"][0]
        workflow = _build_workflow(
            cart_api,
            product_api,
            address_api,
            order_api,
            admin_order_api,
        )
        order_queries = OrderQueries(test_conn)
        paid_context = workflow.prepare_paid_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
            pay_type=case_data["pay_type"],
        )
        delivery_context = workflow.attempt_delivery(
            order_id=paid_context["order_id"],
            delivery_company=case_data["delivery_company"],
            delivery_sn=case_data["delivery_sn"],
        )
        first_database_order = order_queries.get_order_state(paid_context["order_id"])
        verify_delivery_success(
            delivery_context["delivery_response"],
            delivery_context["after_admin_detail"],
            delivery_context["portal_detail"],
            first_database_order,
            expected_code=case_data["expected_business_code"],
            expected_order_id=paid_context["order_id"],
            expected_status=case_data["shipped_order_status"],
            expected_delivery_company=case_data["delivery_company"],
            expected_delivery_sn=case_data["delivery_sn"],
        )

        repeat_response = admin_order_api.update_delivery(
            order_id=paid_context["order_id"],
            delivery_company=case_data["repeat_delivery_company"],
            delivery_sn=case_data["repeat_delivery_sn"],
        )
        repeat_admin_detail = admin_order_api.order_detail(
            order_id=paid_context["order_id"]
        )
        second_database_order = order_queries.get_order_state(paid_context["order_id"])

        verify_repeat_delivery_stable(
            first_database_order,
            repeat_response,
            repeat_admin_detail,
            second_database_order,
            success_code=case_data["expected_business_code"],
            expected_status=case_data["shipped_order_status"],
        )

    @pytest.mark.p1
    @pytest.mark.title("TC_ECOM_077 前台token不能调用后台发货")
    def test_portal_token_cannot_update_admin_delivery(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        admin_order_api,
        admin_public_session,
        portal_authorization,
        test_conn,
    ):
        """TC_ECOM_077 验证前台 token 调后台发货被拒绝且订单不变"""
        case_data = ORDER_DELIVERY_DATA["TC_ECOM_077"][0]
        workflow = _build_workflow(
            cart_api,
            product_api,
            address_api,
            order_api,
            admin_order_api,
        )
        order_queries = OrderQueries(test_conn)
        paid_context = workflow.prepare_paid_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
            pay_type=case_data["pay_type"],
        )
        before_database_order = order_queries.get_order_state(paid_context["order_id"])
        mixed_token_api = AdminOrderAPI(admin_public_session)
        original_authorization = admin_public_session.headers.get("Authorization")
        delivery_error = None
        delivery_response = None

        try:
            admin_public_session.headers["Authorization"] = portal_authorization
            try:
                delivery_response = mixed_token_api.update_delivery(
                    order_id=paid_context["order_id"],
                    delivery_company=case_data["delivery_company"],
                    delivery_sn=case_data["delivery_sn"],
                )
            except AssertionError as error:
                delivery_error = error
        finally:
            if original_authorization is None:
                admin_public_session.headers.pop("Authorization", None)
            else:
                admin_public_session.headers["Authorization"] = original_authorization

        after_database_order = order_queries.get_order_state(paid_context["order_id"])
        verify_delivery_permission_rejected(
            delivery_error,
            delivery_response,
            before_database_order,
            after_database_order,
            expected_http_status=case_data["expected_http_status"],
            success_code=case_data["success_business_code"],
            expected_status=case_data["paid_order_status"],
            expected_message_keywords=case_data["expected_message_keywords"],
        )

    @pytest.mark.p1
    @pytest.mark.title("TC_ECOM_088 待发货订单发货后进入待收货")
    def test_paid_to_shipped_status_transition(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        admin_order_api,
        test_conn,
    ):
        """TC_ECOM_088 验证后台发货后订单进入待收货状态"""
        case_data = ORDER_DELIVERY_DATA["TC_ECOM_088"][0]
        workflow = _build_workflow(
            cart_api,
            product_api,
            address_api,
            order_api,
            admin_order_api,
        )
        order_queries = OrderQueries(test_conn)
        paid_context = workflow.prepare_paid_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
            pay_type=case_data["pay_type"],
        )
        before_database_order = order_queries.get_order_state(paid_context["order_id"])
        order_id = verify_delivery_candidate(
            before_database_order,
            case_data["paid_order_status"],
        )

        delivery_context = workflow.attempt_delivery(
            order_id=order_id,
            delivery_company=case_data["delivery_company"],
            delivery_sn=case_data["delivery_sn"],
        )
        after_database_order = order_queries.get_order_state(order_id)

        verify_delivery_success(
            delivery_context["delivery_response"],
            delivery_context["after_admin_detail"],
            delivery_context["portal_detail"],
            after_database_order,
            expected_code=case_data["expected_business_code"],
            expected_order_id=order_id,
            expected_status=case_data["shipped_order_status"],
            expected_delivery_company=case_data["delivery_company"],
            expected_delivery_sn=case_data["delivery_sn"],
        )
