import pytest

from core.load_yaml import load_yaml
from test_support.db_queries.coupon_queries import CouponQueries
from test_support.db_queries.order_queries import OrderQueries
from verifications.common.response import (
    verify_business_code,
)
from verifications.portal.cart import verify_cart_add_success
from verifications.portal.coupon import (
    verify_confirm_coupon_availability,
    verify_coupon_history_unchanged,
    verify_coupon_not_owned,
    verify_coupon_order_discount,
    verify_coupon_query_responses,
    verify_coupon_threshold_boundary,
    verify_coupon_threshold_satisfied,
    verify_foreign_coupon_history,
    verify_owned_coupon_query_consistency,
)
from verifications.portal.order import (
    verify_latest_order_unchanged,
    verify_order_confirmation_amount,
    verify_order_generation_rejected,
)
from workflow.portal.order_workflow import PortalOrderWorkflow

pytestmark = [
    pytest.mark.api,
    pytest.mark.portal,
    pytest.mark.story("Coupon"),
]
COUPON_ORDER_DATA = load_yaml("portal/coupon_order_data.yaml")


def _build_workflow(cart_api, product_api, address_api, order_api):
    """构建优惠券订单场景复用的前台订单流程。"""
    return PortalOrderWorkflow(
        cart_api=cart_api,
        product_api=product_api,
        address_api=address_api,
        order_api=order_api,
    )


def _resolve_member_coupon_history_id(coupon_queries, case_data):
    """根据用例引用定位当前会员优惠券历史 ID。"""
    coupon_history = coupon_queries.get_member_coupon_history_by_reference(
        member_username=case_data["member_username"],
        coupon_history_reference=case_data["coupon_history_reference"],
    )
    assert isinstance(coupon_history, dict), (
        f"未找到会员 {case_data['member_username']} 的优惠券引用 "
        f"{case_data['coupon_history_reference']}，请检查优惠券测试数据"
    )
    coupon_history_id = coupon_history.get("id")
    assert isinstance(coupon_history_id, int), (
        f"优惠券引用 {case_data['coupon_history_reference']} 对应的历史 ID "
        f"应为整数，实际为：{coupon_history_id}"
    )
    return coupon_history_id


class TestCouponOrder:
    """前台订单优惠券接口测试用例"""

    @pytest.mark.p1
    @pytest.mark.title("TC_ECOM_041 全场通用券对普通商品可用")
    def test_general_coupon_applied_to_regular_product(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        coupon_api,
        test_conn,
    ):
        """TC_ECOM_041 验证全场券在确认单可用且下单成功抵扣"""
        case_data = COUPON_ORDER_DATA["TC_ECOM_041"][0]
        order_queries = OrderQueries(test_conn)
        coupon_queries = CouponQueries(test_conn)
        coupon_history_id = _resolve_member_coupon_history_id(
            coupon_queries,
            case_data,
        )
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        context = workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        verify_business_code(
            context["clear_response"],
            case_data["expected_business_code"],
        )
        verify_cart_add_success(
            context["add_response"],
            case_data["expected_business_code"],
        )
        coupon_response = coupon_api.member_coupon_list(
            use_status=case_data["query_use_status"]
        )
        history_response = coupon_api.member_coupon_history_list(
            use_status=case_data["query_use_status"]
        )
        product_coupon_response = coupon_api.coupon_list_by_product(
            product_id=case_data["product_id"]
        )
        verify_coupon_query_responses(
            coupon_response,
            history_response,
            product_coupon_response,
            expected_code=case_data["expected_business_code"],
        )
        verify_owned_coupon_query_consistency(
            coupon_response,
            history_response,
            coupon_history_id=coupon_history_id,
            expected_use_status=case_data["expected_initial_use_status"],
        )
        verify_order_confirmation_amount(
            context["confirm_response"],
            expected_total_amount=case_data["expected_order_amount"],
        )
        confirm_coupon_detail = verify_confirm_coupon_availability(
            context["confirm_response"],
            coupon_history_id=coupon_history_id,
            expected_available=case_data["available_in_confirm"],
            expected_code=case_data["expected_business_code"],
        )

        order_context = None
        try:
            order_context = workflow.generate_order(
                context,
                pay_type=case_data["pay_type"],
                coupon_id=coupon_history_id,
                use_integration=case_data["use_integration"],
            )
            used_coupon_response = coupon_api.member_coupon_list(
                use_status=case_data["expected_used_status"]
            )
            used_history_response = coupon_api.member_coupon_history_list(
                use_status=case_data["expected_used_status"]
            )
            database_order = order_queries.get_order_benefit_state(
                order_context["order_id"],
            )
            database_history = coupon_queries.get_coupon_history_state(
                coupon_history_id,
            )

            verify_business_code(
                used_coupon_response,
                case_data["expected_business_code"],
            )
            verify_business_code(
                used_history_response,
                case_data["expected_business_code"],
            )
            verify_owned_coupon_query_consistency(
                used_coupon_response,
                used_history_response,
                coupon_history_id=coupon_history_id,
                expected_use_status=case_data["expected_used_status"],
            )
            verify_coupon_order_discount(
                order_context["generate_response"],
                order_context["detail_response"],
                confirm_coupon_detail=confirm_coupon_detail,
                database_order=database_order,
                database_coupon_history=database_history,
                expected_code=case_data["expected_business_code"],
                expected_used_status=case_data["expected_used_status"],
                expected_total_amount=case_data["expected_order_amount"],
            )
        finally:
            if order_context is not None:
                workflow.cancel_created_order(order_context["generate_response"])

    @pytest.mark.p1
    @pytest.mark.title("TC_ECOM_043 已使用优惠券不能重复使用")
    def test_used_coupon_cannot_be_reused(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        coupon_api,
        test_conn,
    ):
        """TC_ECOM_043 验证已使用优惠券下单失败且状态不变"""
        case_data = COUPON_ORDER_DATA["TC_ECOM_043"][0]
        order_queries = OrderQueries(test_conn)
        coupon_queries = CouponQueries(test_conn)
        coupon_history_id = _resolve_member_coupon_history_id(
            coupon_queries,
            case_data,
        )
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        context = workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        coupon_response = coupon_api.member_coupon_list(
            use_status=case_data["query_use_status"]
        )
        history_response = coupon_api.member_coupon_history_list(
            use_status=case_data["query_use_status"]
        )
        product_coupon_response = coupon_api.coupon_list_by_product(
            product_id=case_data["product_id"]
        )
        verify_coupon_query_responses(
            coupon_response,
            history_response,
            product_coupon_response,
            expected_code=case_data["success_business_code"],
        )
        verify_owned_coupon_query_consistency(
            coupon_response,
            history_response,
            coupon_history_id=coupon_history_id,
            expected_use_status=case_data["expected_initial_use_status"],
        )
        verify_confirm_coupon_availability(
            context["confirm_response"],
            coupon_history_id=coupon_history_id,
            expected_available=case_data["available_in_confirm"],
            expected_code=case_data["success_business_code"],
        )
        before_order = order_queries.get_latest_member_order(
            case_data["member_username"]
        )
        before_history = coupon_queries.get_coupon_history_state(
            coupon_history_id,
        )

        order_context = None
        try:
            order_context = workflow.generate_order(
                context,
                pay_type=case_data["pay_type"],
                coupon_id=coupon_history_id,
                use_integration=case_data["use_integration"],
            )
            after_order = order_queries.get_latest_member_order(
                case_data["member_username"]
            )
            after_history = coupon_queries.get_coupon_history_state(
                coupon_history_id,
            )

            verify_order_generation_rejected(
                order_context["generate_response"],
                success_code=case_data["success_business_code"],
                expected_message_keywords=case_data["expected_message_keywords"],
            )
            verify_latest_order_unchanged(before_order, after_order)
            verify_coupon_history_unchanged(
                before_history,
                after_history,
                coupon_history_id=coupon_history_id,
            )
        finally:
            if order_context is not None:
                workflow.cancel_created_order(order_context["generate_response"])

    @pytest.mark.p1
    @pytest.mark.title("TC_ECOM_042 过期优惠券不可用于创建订单")
    def test_expired_coupon_cannot_be_used_for_order(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        test_conn,
    ):
        """TC_ECOM_042 验证过期优惠券下单失败且历史状态不变"""
        case_data = COUPON_ORDER_DATA["TC_ECOM_042"][0]
        order_queries = OrderQueries(test_conn)
        coupon_queries = CouponQueries(test_conn)
        coupon_history_id = _resolve_member_coupon_history_id(
            coupon_queries,
            case_data,
        )
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        context = workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
            cart_price=case_data["cart_price"],
        )
        verify_confirm_coupon_availability(
            context["confirm_response"],
            coupon_history_id=coupon_history_id,
            expected_available=case_data["available_in_confirm"],
            expected_code=case_data["expected_business_code"],
        )
        before_order = order_queries.get_latest_member_order(
            case_data["member_username"]
        )
        before_history = coupon_queries.get_coupon_history_state(coupon_history_id)
        assert (
            before_history.get("use_status") == case_data["expected_initial_use_status"]
        ), (
            "过期券用例前置 use_status 应为 "
            f"{case_data['expected_initial_use_status']}，实际为：{before_history}"
        )

        order_context = None
        try:
            order_context = workflow.generate_order(
                context,
                pay_type=case_data["pay_type"],
                coupon_id=coupon_history_id,
                use_integration=case_data["use_integration"],
            )
            after_order = order_queries.get_latest_member_order(
                case_data["member_username"]
            )
            after_history = coupon_queries.get_coupon_history_state(
                coupon_history_id,
            )

            verify_order_generation_rejected(
                order_context["generate_response"],
                success_code=case_data["success_business_code"],
                expected_message_keywords=case_data["expected_message_keywords"],
            )
            verify_latest_order_unchanged(before_order, after_order)
            verify_coupon_history_unchanged(
                before_history,
                after_history,
                coupon_history_id=coupon_history_id,
            )
        finally:
            if order_context is not None:
                workflow.cancel_created_order(order_context["generate_response"])

    @pytest.mark.p1
    @pytest.mark.title("TC_ECOM_046 订单金额等于门槛时优惠券可用")
    def test_coupon_available_when_amount_equals_threshold(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        coupon_api,
        test_conn,
    ):
        """TC_ECOM_046 验证确认单金额等于优惠券门槛时可使用"""
        case_data = COUPON_ORDER_DATA["TC_ECOM_046"][0]
        coupon_queries = CouponQueries(test_conn)
        coupon_history_id = _resolve_member_coupon_history_id(
            coupon_queries,
            case_data,
        )
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        context = workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
            cart_price=case_data["cart_price"],
        )
        coupon_response = coupon_api.member_coupon_list(
            use_status=case_data["query_use_status"]
        )
        history_response = coupon_api.member_coupon_history_list(
            use_status=case_data["query_use_status"]
        )

        _, coupon = verify_owned_coupon_query_consistency(
            coupon_response,
            history_response,
            coupon_history_id=coupon_history_id,
            expected_use_status=case_data["expected_initial_use_status"],
        )
        verify_order_confirmation_amount(
            context["confirm_response"],
            expected_total_amount=case_data["expected_order_amount"],
        )
        verify_coupon_threshold_satisfied(
            coupon,
            expected_threshold=case_data["coupon_threshold"],
            actual_order_amount=case_data["expected_order_amount"],
        )
        verify_confirm_coupon_availability(
            context["confirm_response"],
            coupon_history_id=coupon_history_id,
            expected_available=case_data["available_in_confirm"],
            expected_code=case_data["expected_business_code"],
        )

    @pytest.mark.p1
    @pytest.mark.title("TC_ECOM_044 用户A使用用户B优惠券失败")
    def test_coupon_owned_by_another_member_rejected(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        coupon_api,
        test_conn,
    ):
        """TC_ECOM_044 验证非本人优惠券不可查询和用于创建订单"""
        case_data = COUPON_ORDER_DATA["TC_ECOM_044"][0]
        order_queries = OrderQueries(test_conn)
        coupon_queries = CouponQueries(test_conn)
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        context = workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        coupon_response = coupon_api.member_coupon_list()
        history_response = coupon_api.member_coupon_history_list()
        product_coupon_response = coupon_api.coupon_list_by_product(
            product_id=case_data["product_id"]
        )
        verify_coupon_query_responses(
            coupon_response,
            history_response,
            product_coupon_response,
            expected_code=case_data["expected_business_code"],
        )
        foreign_history = coupon_queries.get_coupon_history_by_reference(
            case_data["coupon_history_reference"],
        )
        coupon_history_id = verify_foreign_coupon_history(
            foreign_history,
            current_member_username=case_data["member_username"],
            coupon_history_reference=case_data["coupon_history_reference"],
        )
        verify_coupon_not_owned(
            history_response,
            coupon_history_id=coupon_history_id,
        )
        verify_confirm_coupon_availability(
            context["confirm_response"],
            coupon_history_id=coupon_history_id,
            expected_available=case_data["available_in_confirm"],
            expected_code=case_data["expected_business_code"],
        )
        before_order = order_queries.get_latest_member_order(
            case_data["member_username"]
        )
        before_history = coupon_queries.get_coupon_history_state(
            coupon_history_id,
        )

        order_context = None
        try:
            order_context = workflow.generate_order(
                context,
                pay_type=case_data["pay_type"],
                coupon_id=coupon_history_id,
                use_integration=case_data["use_integration"],
            )
            after_order = order_queries.get_latest_member_order(
                case_data["member_username"]
            )
            after_history = coupon_queries.get_coupon_history_state(
                coupon_history_id,
            )

            verify_order_generation_rejected(
                order_context["generate_response"],
                success_code=case_data["success_business_code"],
                expected_message_keywords=case_data["expected_message_keywords"],
            )
            verify_latest_order_unchanged(before_order, after_order)
            verify_coupon_history_unchanged(
                before_history,
                after_history,
                coupon_history_id=coupon_history_id,
            )
        finally:
            if order_context is not None:
                workflow.cancel_created_order(order_context["generate_response"])

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_045 满减门槛差0.01时不可用")
    def test_coupon_rejected_when_below_threshold_by_one_cent(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        coupon_api,
        test_conn,
    ):
        """TC_ECOM_045 验证商品金额比门槛少0.01时优惠券不可用"""
        case_data = COUPON_ORDER_DATA["TC_ECOM_045"][0]
        order_queries = OrderQueries(test_conn)
        coupon_queries = CouponQueries(test_conn)
        coupon_history_id = _resolve_member_coupon_history_id(
            coupon_queries,
            case_data,
        )
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        context = workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
            cart_price=case_data["cart_price"],
        )
        coupon_response = coupon_api.member_coupon_list(
            use_status=case_data["query_use_status"]
        )
        history_response = coupon_api.member_coupon_history_list(
            use_status=case_data["query_use_status"]
        )
        product_coupon_response = coupon_api.coupon_list_by_product(
            product_id=case_data["product_id"]
        )
        verify_coupon_query_responses(
            coupon_response,
            history_response,
            product_coupon_response,
            expected_code=case_data["expected_business_code"],
        )
        _, coupon = verify_owned_coupon_query_consistency(
            coupon_response,
            history_response,
            coupon_history_id=coupon_history_id,
            expected_use_status=case_data["expected_initial_use_status"],
        )
        verify_order_confirmation_amount(
            context["confirm_response"],
            expected_total_amount=case_data["expected_order_amount"],
        )
        verify_coupon_threshold_boundary(
            coupon,
            expected_threshold=case_data["coupon_threshold"],
            actual_order_amount=case_data["expected_order_amount"],
        )
        verify_confirm_coupon_availability(
            context["confirm_response"],
            coupon_history_id=coupon_history_id,
            expected_available=case_data["available_in_confirm"],
            expected_code=case_data["expected_business_code"],
        )
        before_order = order_queries.get_latest_member_order(
            case_data["member_username"]
        )
        before_history = coupon_queries.get_coupon_history_state(
            coupon_history_id,
        )

        order_context = None
        try:
            order_context = workflow.generate_order(
                context,
                pay_type=case_data["pay_type"],
                coupon_id=coupon_history_id,
                use_integration=case_data["use_integration"],
            )
            after_order = order_queries.get_latest_member_order(
                case_data["member_username"]
            )
            after_history = coupon_queries.get_coupon_history_state(
                coupon_history_id,
            )

            verify_order_generation_rejected(
                order_context["generate_response"],
                success_code=case_data["success_business_code"],
                expected_message_keywords=case_data["expected_message_keywords"],
            )
            verify_latest_order_unchanged(before_order, after_order)
            verify_coupon_history_unchanged(
                before_history,
                after_history,
                coupon_history_id=coupon_history_id,
            )
        finally:
            if order_context is not None:
                workflow.cancel_created_order(order_context["generate_response"])
