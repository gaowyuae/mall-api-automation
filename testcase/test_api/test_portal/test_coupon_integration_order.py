import pytest

from core.load_yaml import load_yaml
from test_support.db_preconditions import (
    restore_coupon_history_precondition,
    restore_member_integration_precondition,
)
from test_support.db_queries.coupon_queries import CouponQueries
from test_support.db_queries.integration_queries import IntegrationQueries
from test_support.db_queries.order_queries import OrderQueries
from verifications.common.response import verify_business_code
from verifications.portal.cart import verify_cart_add_success
from verifications.portal.coupon import (
    verify_confirm_coupon_availability,
    verify_coupon_query_responses,
    verify_owned_coupon_query_consistency,
)
from verifications.portal.coupon_integration import (
    verify_coupon_integration_candidate,
    verify_coupon_integration_order,
)
from verifications.portal.integration import (
    verify_confirm_integration_rule,
    verify_member_integration,
)
from verifications.portal.order import verify_order_confirmation_amount
from workflow.portal.order_workflow import PortalOrderWorkflow

pytestmark = [
    pytest.mark.api,
    pytest.mark.portal,
    pytest.mark.story("Coupon and Integration"),
]
COUPON_INTEGRATION_DATA = load_yaml("portal/coupon_integration_order_data.yaml")


def _build_workflow(cart_api, product_api, address_api, order_api):
    return PortalOrderWorkflow(
        cart_api=cart_api,
        product_api=product_api,
        address_api=address_api,
        order_api=order_api,
    )


class TestCouponIntegrationOrder:
    """前台优惠券与积分组合下单测试用例"""

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_052 先使用优惠券再使用积分金额正确")
    def test_coupon_then_integration_amount_correct(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        coupon_api,
        member_api,
        test_conn,
    ):
        """TC_ECOM_052 验证先券后积分的订单金额及关联数据一致"""
        case_data = COUPON_INTEGRATION_DATA["TC_ECOM_052"][0]
        restore_member_integration_precondition(
            test_conn,
            case_id="TC_ECOM_052",
            member_username=case_data["member_username"],
            integration=case_data["minimum_member_integration"],
        )
        restore_coupon_history_precondition(
            test_conn,
            case_id="TC_ECOM_052",
            member_username=case_data["member_username"],
            coupon_history_reference=case_data["coupon_history_reference"],
        )
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        order_queries = OrderQueries(test_conn)
        coupon_queries = CouponQueries(test_conn)
        integration_queries = IntegrationQueries(test_conn)
        coupon_candidate = (
            coupon_queries.get_available_member_coupon_history_by_reference(
                member_username=case_data["member_username"],
                coupon_history_reference=case_data["coupon_history_reference"],
                coupon_amount=case_data["coupon_amount"],
                minimum_amount=case_data["coupon_minimum_amount"],
                use_type=case_data["coupon_use_type"],
            )
        )
        coupon_history_id = verify_coupon_integration_candidate(
            coupon_candidate,
            member_username=case_data["member_username"],
            expected_coupon_amount=case_data["coupon_amount"],
            expected_minimum_amount=case_data["coupon_minimum_amount"],
            expected_use_type=case_data["coupon_use_type"],
            expected_use_status=case_data["expected_initial_use_status"],
        )
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
        verify_order_confirmation_amount(
            context["confirm_response"],
            expected_total_amount=case_data["expected_order_amount"],
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
        confirm_coupon_detail = verify_confirm_coupon_availability(
            context["confirm_response"],
            coupon_history_id=coupon_history_id,
            expected_available=case_data["available_in_confirm"],
            expected_code=case_data["expected_business_code"],
        )
        member_before = member_api.member_info()
        member_integration = verify_member_integration(
            member_before,
            expected_code=case_data["expected_business_code"],
            minimum_integration=case_data["minimum_member_integration"],
        )
        verify_confirm_integration_rule(
            context["confirm_response"],
            expected_code=case_data["expected_business_code"],
            expected_member_integration=member_integration,
            expected_deduction_per_amount=case_data["deduction_per_amount"],
        )
        integration_history_before = integration_queries.get_member_history_state(
            case_data["member_username"]
        )

        order_context = None
        try:
            order_context = workflow.generate_order(
                context,
                pay_type=case_data["pay_type"],
                coupon_id=coupon_history_id,
                use_integration=case_data["use_integration"],
            )
            member_after = member_api.member_info()
            used_coupon_response = coupon_api.member_coupon_list(
                use_status=case_data["expected_used_status"]
            )
            used_history_response = coupon_api.member_coupon_history_list(
                use_status=case_data["expected_used_status"]
            )
            database_order = order_queries.get_order_benefit_state(
                order_context["order_id"]
            )
            database_coupon_history = coupon_queries.get_coupon_history_state(
                coupon_history_id
            )
            integration_history_after = integration_queries.get_member_history_state(
                case_data["member_username"]
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
            verify_coupon_integration_order(
                order_context["generate_response"],
                order_context["detail_response"],
                member_before,
                member_after,
                integration_history_before,
                integration_history_after,
                confirm_coupon_detail=confirm_coupon_detail,
                database_order=database_order,
                database_coupon_history=database_coupon_history,
                expected_code=case_data["expected_business_code"],
                expected_used_status=case_data["expected_used_status"],
                expected_total_amount=case_data["expected_order_amount"],
                expected_coupon_amount=case_data["coupon_amount"],
                expected_use_integration=case_data["use_integration"],
                expected_integration_amount=(case_data["expected_integration_amount"]),
                expected_pay_amount=case_data["expected_pay_amount"],
                expected_history_increment=case_data["expected_history_increment"],
                expected_history_change_count=(
                    case_data["expected_history_change_count"]
                ),
            )
        finally:
            if order_context is not None:
                workflow.cancel_created_order(order_context["generate_response"])

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_053 优惠券和积分同时满足时创建订单成功")
    def test_coupon_and_integration_both_applied_successfully(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        coupon_api,
        member_api,
        test_conn,
    ):
        """TC_ECOM_053 验证优惠券和积分同时满足时均被使用"""
        case_data = COUPON_INTEGRATION_DATA["TC_ECOM_053"][0]
        restore_member_integration_precondition(
            test_conn,
            case_id="TC_ECOM_053",
            member_username=case_data["member_username"],
            integration=case_data["minimum_member_integration"],
        )
        restore_coupon_history_precondition(
            test_conn,
            case_id="TC_ECOM_053",
            member_username=case_data["member_username"],
            coupon_history_reference=case_data["coupon_history_reference"],
        )
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        order_queries = OrderQueries(test_conn)
        coupon_queries = CouponQueries(test_conn)
        integration_queries = IntegrationQueries(test_conn)
        coupon_candidate = (
            coupon_queries.get_available_member_coupon_history_by_reference(
                member_username=case_data["member_username"],
                coupon_history_reference=case_data["coupon_history_reference"],
                coupon_amount=case_data["coupon_amount"],
                minimum_amount=case_data["coupon_minimum_amount"],
                use_type=case_data["coupon_use_type"],
            )
        )
        coupon_history_id = verify_coupon_integration_candidate(
            coupon_candidate,
            member_username=case_data["member_username"],
            expected_coupon_amount=case_data["coupon_amount"],
            expected_minimum_amount=case_data["coupon_minimum_amount"],
            expected_use_type=case_data["coupon_use_type"],
            expected_use_status=case_data["expected_initial_use_status"],
        )
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
        verify_order_confirmation_amount(
            context["confirm_response"],
            expected_total_amount=case_data["expected_order_amount"],
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
        confirm_coupon_detail = verify_confirm_coupon_availability(
            context["confirm_response"],
            coupon_history_id=coupon_history_id,
            expected_available=case_data["available_in_confirm"],
            expected_code=case_data["expected_business_code"],
        )
        member_before = member_api.member_info()
        member_integration = verify_member_integration(
            member_before,
            expected_code=case_data["expected_business_code"],
            minimum_integration=case_data["minimum_member_integration"],
        )
        verify_confirm_integration_rule(
            context["confirm_response"],
            expected_code=case_data["expected_business_code"],
            expected_member_integration=member_integration,
            expected_deduction_per_amount=case_data["deduction_per_amount"],
        )
        integration_history_before = integration_queries.get_member_history_state(
            case_data["member_username"]
        )

        order_context = None
        try:
            order_context = workflow.generate_order(
                context,
                pay_type=case_data["pay_type"],
                coupon_id=coupon_history_id,
                use_integration=case_data["use_integration"],
            )
            member_after = member_api.member_info()
            used_coupon_response = coupon_api.member_coupon_list(
                use_status=case_data["expected_used_status"]
            )
            used_history_response = coupon_api.member_coupon_history_list(
                use_status=case_data["expected_used_status"]
            )
            database_order = order_queries.get_order_benefit_state(
                order_context["order_id"]
            )
            database_coupon_history = coupon_queries.get_coupon_history_state(
                coupon_history_id
            )
            integration_history_after = integration_queries.get_member_history_state(
                case_data["member_username"]
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
            verify_coupon_integration_order(
                order_context["generate_response"],
                order_context["detail_response"],
                member_before,
                member_after,
                integration_history_before,
                integration_history_after,
                confirm_coupon_detail=confirm_coupon_detail,
                database_order=database_order,
                database_coupon_history=database_coupon_history,
                expected_code=case_data["expected_business_code"],
                expected_used_status=case_data["expected_used_status"],
                expected_total_amount=case_data["expected_order_amount"],
                expected_coupon_amount=case_data["coupon_amount"],
                expected_use_integration=case_data["use_integration"],
                expected_integration_amount=(case_data["expected_integration_amount"]),
                expected_pay_amount=case_data["expected_pay_amount"],
                expected_history_increment=case_data["expected_history_increment"],
                expected_history_change_count=(
                    case_data["expected_history_change_count"]
                ),
            )
        finally:
            if order_context is not None:
                workflow.cancel_created_order(order_context["generate_response"])
