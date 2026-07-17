import pytest

from core.load_yaml import load_yaml
from test_support.db_queries.order_queries import OrderQueries
from verifications.admin.order import verify_admin_completed_order
from verifications.common.response import (
    verify_business_failure,
    verify_message_contains_any,
)
from verifications.portal.order import (
    verify_confirm_receive_rejected,
    verify_confirm_receive_success,
    verify_other_member_confirm_receive_rejected,
    verify_other_member_receive_candidate,
    verify_receive_candidate,
    verify_repeat_confirm_receive_idempotent,
)
from workflow.admin.order_workflow import AdminOrderWorkflow

pytestmark = [
    pytest.mark.api,
    pytest.mark.portal,
    pytest.mark.story("Order Receipt"),
]
ORDER_RECEIVE_DATA = load_yaml("portal/order_receive_data.yaml")


def _build_workflow(
    cart_api,
    product_api,
    address_api,
    order_api,
    admin_order_api,
):
    """构建确认收货场景复用的后台订单流程。"""
    return AdminOrderWorkflow(
        cart_api=cart_api,
        product_api=product_api,
        address_api=address_api,
        portal_order_api=order_api,
        admin_order_api=admin_order_api,
    )


class TestOrderReceive:
    """前台用户确认收货接口测试用例"""

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_078 待收货订单确认收货成功")
    def test_shipped_order_confirm_receive_success(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        admin_order_api,
        test_conn,
    ):
        """TC_ECOM_078 验证待收货订单确认后变为已完成并记录时间"""
        case_data = ORDER_RECEIVE_DATA["TC_ECOM_078"][0]
        workflow = _build_workflow(
            cart_api,
            product_api,
            address_api,
            order_api,
            admin_order_api,
        )
        order_queries = OrderQueries(test_conn)
        shipped_context = workflow.prepare_shipped_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
            pay_type=case_data["pay_type"],
            delivery_company=case_data["delivery_company"],
            delivery_sn=case_data["delivery_sn"],
        )
        before_database_order = order_queries.get_order_state(
            shipped_context["order_id"]
        )
        order_id = verify_receive_candidate(
            shipped_context["shipped_detail_response"],
            before_database_order,
            expected_code=case_data["expected_business_code"],
            expected_status=case_data["pending_receive_status"],
        )

        confirm_response = order_api.confirm_receive(order_id=order_id)
        detail_response = order_api.order_detail(order_id=order_id)
        after_database_order = order_queries.get_order_state(order_id)

        verify_confirm_receive_success(
            confirm_response,
            detail_response,
            before_database_order,
            after_database_order,
            expected_code=case_data["expected_business_code"],
            expected_order_id=order_id,
            expected_status=case_data["completed_order_status"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_079 已完成订单重复确认收货幂等或失败")
    def test_repeat_confirm_receive_is_idempotent(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        admin_order_api,
        test_conn,
    ):
        """TC_ECOM_079 验证重复确认收货不重复刷新完成状态和时间"""
        case_data = ORDER_RECEIVE_DATA["TC_ECOM_079"][0]
        workflow = _build_workflow(
            cart_api,
            product_api,
            address_api,
            order_api,
            admin_order_api,
        )
        order_queries = OrderQueries(test_conn)
        shipped_context = workflow.prepare_shipped_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
            pay_type=case_data["pay_type"],
            delivery_company=case_data["delivery_company"],
            delivery_sn=case_data["delivery_sn"],
        )
        shipped_database_order = order_queries.get_order_state(
            shipped_context["order_id"]
        )
        order_id = verify_receive_candidate(
            shipped_context["shipped_detail_response"],
            shipped_database_order,
            expected_code=case_data["expected_business_code"],
            expected_status=case_data["pending_receive_status"],
        )

        confirm_responses = []
        detail_responses = []
        database_states = []
        for _ in range(case_data["repeat"]):
            confirm_responses.append(order_api.confirm_receive(order_id=order_id))
            detail_responses.append(order_api.order_detail(order_id=order_id))
            database_states.append(order_queries.get_order_state(order_id))

        verify_repeat_confirm_receive_idempotent(
            confirm_responses[0],
            detail_responses[0],
            confirm_responses[1],
            detail_responses[1],
            database_states[0],
            database_states[1],
            success_code=case_data["expected_business_code"],
            expected_order_id=order_id,
            expected_status=case_data["completed_order_status"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_080 待发货订单不能确认收货")
    def test_paid_order_confirm_receive_failed(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        admin_order_api,
        test_conn,
    ):
        """TC_ECOM_080 验证未发货订单确认收货失败且状态保持待发货"""
        case_data = ORDER_RECEIVE_DATA["TC_ECOM_080"][0]
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
        order_id = verify_receive_candidate(
            paid_context["paid_detail_response"],
            before_database_order,
            expected_code=case_data["expected_business_code"],
            expected_status=case_data["pending_delivery_status"],
        )

        confirm_response = order_api.confirm_receive(order_id=order_id)
        detail_response = order_api.order_detail(order_id=order_id)
        after_database_order = order_queries.get_order_state(order_id)

        verify_confirm_receive_rejected(
            confirm_response,
            detail_response,
            before_database_order,
            after_database_order,
            success_code=case_data["expected_business_code"],
            detail_code=case_data["expected_business_code"],
            expected_order_id=order_id,
            expected_status=case_data["pending_delivery_status"],
            expected_message_keywords=case_data["expected_message_keywords"],
        )

    @pytest.mark.p1
    @pytest.mark.title("TC_ECOM_081 待支付订单不能确认收货")
    def test_pending_payment_order_confirm_receive_failed(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        admin_order_api,
        test_conn,
    ):
        """TC_ECOM_081 验证待支付订单确认收货失败且状态不变"""
        case_data = ORDER_RECEIVE_DATA["TC_ECOM_081"][0]
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
        order_id = verify_receive_candidate(
            pending_context["detail_response"],
            before_database_order,
            expected_code=case_data["expected_business_code"],
            expected_status=case_data["pending_order_status"],
        )

        try:
            confirm_response = order_api.confirm_receive(order_id=order_id)
            detail_response = order_api.order_detail(order_id=order_id)
            after_database_order = order_queries.get_order_state(order_id)

            verify_confirm_receive_rejected(
                confirm_response,
                detail_response,
                before_database_order,
                after_database_order,
                success_code=case_data["expected_business_code"],
                detail_code=case_data["expected_business_code"],
                expected_order_id=order_id,
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
    @pytest.mark.title("TC_ECOM_082 已取消订单不能确认收货")
    def test_canceled_order_confirm_receive_failed(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        admin_order_api,
        test_conn,
    ):
        """TC_ECOM_082 验证已取消订单确认收货失败且状态不变"""
        case_data = ORDER_RECEIVE_DATA["TC_ECOM_082"][0]
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
        workflow.portal_workflow.cancel_created_order(
            pending_context["generate_response"]
        )
        before_database_order = order_queries.get_order_state(
            pending_context["order_id"]
        )
        order_id = verify_receive_candidate(
            order_api.order_detail(order_id=pending_context["order_id"]),
            before_database_order,
            expected_code=case_data["expected_business_code"],
            expected_status=case_data["canceled_order_status"],
        )

        confirm_response = order_api.confirm_receive(order_id=order_id)
        detail_response = order_api.order_detail(order_id=order_id)
        after_database_order = order_queries.get_order_state(order_id)

        verify_confirm_receive_rejected(
            confirm_response,
            detail_response,
            before_database_order,
            after_database_order,
            success_code=case_data["expected_business_code"],
            detail_code=case_data["expected_business_code"],
            expected_order_id=order_id,
            expected_status=case_data["canceled_order_status"],
            expected_message_keywords=case_data["expected_message_keywords"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_083 用户不能确认其他会员订单")
    def test_other_member_order_confirm_receive_failed(
        self,
        order_api,
        test_conn,
    ):
        """TC_ECOM_083 验证当前用户不能确认其他会员待收货订单"""
        case_data = ORDER_RECEIVE_DATA["TC_ECOM_083"][0]
        order_queries = OrderQueries(test_conn)
        other_order = order_queries.get_latest_other_member_order_by_status(
            case_data["current_member_username"],
            case_data["other_member_order_status"],
        )
        order_id = verify_other_member_receive_candidate(
            other_order,
            current_member_username=case_data["current_member_username"],
            expected_status=case_data["other_member_order_status"],
        )
        before_database_order = order_queries.get_order_state(order_id)

        confirm_response = order_api.confirm_receive(order_id=order_id)
        detail_response = order_api.order_detail(order_id=order_id)
        after_database_order = order_queries.get_order_state(order_id)

        verify_other_member_confirm_receive_rejected(
            confirm_response,
            detail_response,
            before_database_order,
            after_database_order,
            success_code=case_data["success_business_code"],
            detail_code=case_data["detail_business_code"],
            expected_status=case_data["other_member_order_status"],
            expected_message_keywords=case_data["expected_message_keywords"],
        )

    @pytest.mark.p1
    @pytest.mark.title("TC_ECOM_084 确认收货缺少orderId失败")
    def test_confirm_receive_missing_order_id_failed(self, order_api):
        """TC_ECOM_084 验证缺少 orderId 时封装层拒绝请求"""
        case_data = ORDER_RECEIVE_DATA["TC_ECOM_084"][0]

        response = order_api.confirm_receive(
            order_id=case_data["order_id"],
            enable=False,
        )

        verify_business_failure(
            response,
            success_code=case_data["success_business_code"],
        )
        verify_message_contains_any(
            response,
            case_data["expected_message_keywords"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_085 确认收货后前后台和数据库状态一致")
    def test_confirm_receive_cross_system_consistency(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        admin_order_api,
        test_conn,
    ):
        """TC_ECOM_085 验证确认后前台、后台及数据库均显示已完成"""
        case_data = ORDER_RECEIVE_DATA["TC_ECOM_085"][0]
        workflow = _build_workflow(
            cart_api,
            product_api,
            address_api,
            order_api,
            admin_order_api,
        )
        order_queries = OrderQueries(test_conn)
        shipped_context = workflow.prepare_shipped_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
            pay_type=case_data["pay_type"],
            delivery_company=case_data["delivery_company"],
            delivery_sn=case_data["delivery_sn"],
        )
        before_database_order = order_queries.get_order_state(
            shipped_context["order_id"]
        )
        order_id = verify_receive_candidate(
            shipped_context["shipped_detail_response"],
            before_database_order,
            expected_code=case_data["expected_business_code"],
            expected_status=case_data["pending_receive_status"],
        )

        confirm_response = order_api.confirm_receive(order_id=order_id)
        portal_detail_response = order_api.order_detail(order_id=order_id)
        admin_detail_response = admin_order_api.order_detail(order_id=order_id)
        after_database_order = order_queries.get_order_state(order_id)

        verify_confirm_receive_success(
            confirm_response,
            portal_detail_response,
            before_database_order,
            after_database_order,
            expected_code=case_data["expected_business_code"],
            expected_order_id=order_id,
            expected_status=case_data["completed_order_status"],
        )
        verify_admin_completed_order(
            admin_detail_response,
            after_database_order,
            expected_code=case_data["expected_business_code"],
            expected_order_id=order_id,
            expected_status=case_data["completed_order_status"],
        )

    @pytest.mark.p1
    @pytest.mark.title("TC_ECOM_089 待收货订单确认后进入已完成")
    def test_shipped_to_completed_status_transition(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        admin_order_api,
        test_conn,
    ):
        """TC_ECOM_089 验证待收货订单确认后完成且重复确认幂等"""
        case_data = ORDER_RECEIVE_DATA["TC_ECOM_089"][0]
        workflow = _build_workflow(
            cart_api,
            product_api,
            address_api,
            order_api,
            admin_order_api,
        )
        order_queries = OrderQueries(test_conn)
        shipped_context = workflow.prepare_shipped_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
            pay_type=case_data["pay_type"],
            delivery_company=case_data["delivery_company"],
            delivery_sn=case_data["delivery_sn"],
        )
        shipped_database_order = order_queries.get_order_state(
            shipped_context["order_id"]
        )
        order_id = verify_receive_candidate(
            shipped_context["shipped_detail_response"],
            shipped_database_order,
            expected_code=case_data["expected_business_code"],
            expected_status=case_data["pending_receive_status"],
        )

        confirm_responses = []
        detail_responses = []
        database_states = []
        for _ in range(case_data["repeat"]):
            confirm_responses.append(order_api.confirm_receive(order_id=order_id))
            detail_responses.append(order_api.order_detail(order_id=order_id))
            database_states.append(order_queries.get_order_state(order_id))

        verify_repeat_confirm_receive_idempotent(
            confirm_responses[0],
            detail_responses[0],
            confirm_responses[1],
            detail_responses[1],
            database_states[0],
            database_states[1],
            success_code=case_data["expected_business_code"],
            expected_order_id=order_id,
            expected_status=case_data["completed_order_status"],
        )
