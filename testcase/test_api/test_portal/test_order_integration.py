import pytest

from core.load_yaml import load_yaml
from test_support.db_preconditions import restore_member_integration_precondition
from test_support.db_queries.integration_queries import IntegrationQueries
from test_support.db_queries.order_queries import OrderQueries
from verifications.common.response import verify_business_code
from verifications.portal.cart import verify_cart_add_success
from verifications.portal.integration import (
    verify_confirm_integration_rule,
    verify_excessive_integration_handling,
    verify_integration_balance_change,
    verify_integration_history_change,
    verify_integration_order,
    verify_member_integration,
)
from verifications.portal.order import verify_order_confirmation_amount
from workflow.portal.order_workflow import PortalOrderWorkflow

pytestmark = [
    pytest.mark.api,
    pytest.mark.portal,
    pytest.mark.story("Integration Points"),
]
INTEGRATION_ORDER_DATA = load_yaml("portal/integration_order_data.yaml")


def _build_workflow(cart_api, product_api, address_api, order_api):
    return PortalOrderWorkflow(
        cart_api=cart_api,
        product_api=product_api,
        address_api=address_api,
        order_api=order_api,
    )


class TestOrderIntegration:
    """前台订单积分抵扣接口测试用例"""

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_047 useIntegration=0时不抵扣积分")
    def test_order_without_integration_discount(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        member_api,
        test_conn,
    ):
        """TC_ECOM_047 验证不使用积分时余额和订单金额不被抵扣"""
        case_data = INTEGRATION_ORDER_DATA["TC_ECOM_047"][0]
        order_queries = OrderQueries(test_conn)
        integration_queries = IntegrationQueries(test_conn)
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
        verify_order_confirmation_amount(
            context["confirm_response"],
            expected_total_amount=case_data["expected_order_amount"],
        )
        member_before = member_api.member_info()
        member_integration = verify_member_integration(
            member_before,
            expected_code=case_data["expected_business_code"],
        )
        verify_confirm_integration_rule(
            context["confirm_response"],
            expected_code=case_data["expected_business_code"],
            expected_member_integration=member_integration,
            expected_deduction_per_amount=case_data["deduction_per_amount"],
        )
        history_before = integration_queries.get_member_history_state(
            case_data["member_username"],
        )

        order_context = None
        try:
            order_context = workflow.generate_order(
                context,
                pay_type=case_data["pay_type"],
                use_integration=case_data["use_integration"],
            )
            member_after = member_api.member_info()
            database_order = order_queries.get_order_benefit_state(
                order_context["order_id"],
            )
            history_after = integration_queries.get_member_history_state(
                case_data["member_username"],
            )

            verify_integration_order(
                order_context["generate_response"],
                order_context["detail_response"],
                database_order=database_order,
                expected_code=case_data["expected_business_code"],
                expected_use_integration=case_data["use_integration"],
                expected_integration_amount=(case_data["expected_integration_amount"]),
                expected_total_amount=case_data["expected_order_amount"],
            )
            verify_integration_balance_change(
                member_before,
                member_after,
                expected_use_integration=case_data["use_integration"],
            )
            verify_integration_history_change(
                history_before,
                history_after,
                expected_increment=case_data["expected_history_increment"],
            )
        finally:
            if order_context is not None:
                workflow.cancel_created_order(order_context["generate_response"])

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_048 使用部分积分抵扣成功")
    def test_partial_integration_discount_success(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        member_api,
        test_conn,
    ):
        """TC_ECOM_048 验证使用部分积分后余额、流水和订单金额一致"""
        case_data = INTEGRATION_ORDER_DATA["TC_ECOM_048"][0]
        restore_member_integration_precondition(
            test_conn,
            case_id="TC_ECOM_048",
            member_username=case_data["member_username"],
            integration=case_data["expected_member_integration"],
        )
        order_queries = OrderQueries(test_conn)
        integration_queries = IntegrationQueries(test_conn)
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        context = workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        verify_order_confirmation_amount(
            context["confirm_response"],
            expected_total_amount=case_data["expected_order_amount"],
        )
        member_before = member_api.member_info()
        member_integration = verify_member_integration(
            member_before,
            expected_code=case_data["expected_business_code"],
            expected_integration=case_data["expected_member_integration"],
        )
        verify_confirm_integration_rule(
            context["confirm_response"],
            expected_code=case_data["expected_business_code"],
            expected_member_integration=member_integration,
            expected_deduction_per_amount=case_data["deduction_per_amount"],
        )
        history_before = integration_queries.get_member_history_state(
            case_data["member_username"],
        )

        order_context = None
        try:
            order_context = workflow.generate_order(
                context,
                pay_type=case_data["pay_type"],
                use_integration=case_data["use_integration"],
            )
            member_after = member_api.member_info()
            database_order = order_queries.get_order_benefit_state(
                order_context["order_id"],
            )
            history_after = integration_queries.get_member_history_state(
                case_data["member_username"],
            )

            verify_integration_order(
                order_context["generate_response"],
                order_context["detail_response"],
                database_order=database_order,
                expected_code=case_data["expected_business_code"],
                expected_use_integration=case_data["use_integration"],
                expected_integration_amount=(case_data["expected_integration_amount"]),
                expected_total_amount=case_data["expected_order_amount"],
            )
            verify_integration_balance_change(
                member_before,
                member_after,
                expected_use_integration=case_data["use_integration"],
            )
            verify_integration_history_change(
                history_before,
                history_after,
                expected_increment=case_data["expected_history_increment"],
                expected_change_count=(case_data["expected_history_change_count"]),
            )
        finally:
            if order_context is not None:
                workflow.cancel_created_order(order_context["generate_response"])

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_049 使用积分大于余额时下单失败")
    def test_integration_greater_than_balance_rejected(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        member_api,
        test_conn,
    ):
        """TC_ECOM_049 验证积分不足时不能超扣或创建订单"""
        case_data = INTEGRATION_ORDER_DATA["TC_ECOM_049"][0]
        restore_member_integration_precondition(
            test_conn,
            case_id="TC_ECOM_049",
            member_username=case_data["member_username"],
            integration=case_data["expected_member_integration"],
        )
        order_queries = OrderQueries(test_conn)
        integration_queries = IntegrationQueries(test_conn)
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        context = workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        member_before = member_api.member_info()
        member_integration = verify_member_integration(
            member_before,
            expected_code=case_data["expected_business_code"],
            expected_integration=case_data["expected_member_integration"],
        )
        verify_confirm_integration_rule(
            context["confirm_response"],
            expected_code=case_data["expected_business_code"],
            expected_member_integration=member_integration,
            expected_deduction_per_amount=case_data["deduction_per_amount"],
        )
        before_order = order_queries.get_latest_member_order(
            case_data["member_username"]
        )
        history_before = integration_queries.get_member_history_state(
            case_data["member_username"],
        )

        order_context = None
        try:
            order_context = workflow.generate_order(
                context,
                pay_type=case_data["pay_type"],
                use_integration=case_data["use_integration"],
            )
            member_after = member_api.member_info()
            after_order = order_queries.get_latest_member_order(
                case_data["member_username"]
            )
            database_order = order_queries.get_order_benefit_state(
                order_context["order_id"],
            )
            history_after = integration_queries.get_member_history_state(
                case_data["member_username"],
            )

            verify_excessive_integration_handling(
                order_context["generate_response"],
                order_context["detail_response"],
                before_member_response=member_before,
                after_member_response=member_after,
                before_order=before_order,
                after_order=after_order,
                database_order=database_order,
                before_history=history_before,
                after_history=history_after,
                requested_integration=case_data["use_integration"],
                success_code=case_data["success_business_code"],
                expected_message_keywords=case_data["expected_message_keywords"],
            )
        finally:
            if order_context is not None:
                workflow.cancel_created_order(order_context["generate_response"])

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_050 积分抵扣超过订单金额时应付不为负")
    def test_integration_discount_cannot_make_pay_amount_negative(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        member_api,
        test_conn,
    ):
        """TC_ECOM_050 验证超额积分抵扣被拒绝且不会产生负金额订单"""
        case_data = INTEGRATION_ORDER_DATA["TC_ECOM_050"][0]
        order_queries = OrderQueries(test_conn)
        integration_queries = IntegrationQueries(test_conn)
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        context = workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
            cart_price=case_data["cart_price"],
        )
        verify_order_confirmation_amount(
            context["confirm_response"],
            expected_total_amount=case_data["expected_order_amount"],
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
        before_order = order_queries.get_latest_member_order(
            case_data["member_username"]
        )
        history_before = integration_queries.get_member_history_state(
            case_data["member_username"],
        )

        order_context = None
        try:
            order_context = workflow.generate_order(
                context,
                pay_type=case_data["pay_type"],
                use_integration=case_data["use_integration"],
            )
            member_after = member_api.member_info()
            after_order = order_queries.get_latest_member_order(
                case_data["member_username"]
            )
            database_order = order_queries.get_order_benefit_state(
                order_context["order_id"],
            )
            history_after = integration_queries.get_member_history_state(
                case_data["member_username"],
            )

            verify_excessive_integration_handling(
                order_context["generate_response"],
                order_context["detail_response"],
                before_member_response=member_before,
                after_member_response=member_after,
                before_order=before_order,
                after_order=after_order,
                database_order=database_order,
                before_history=history_before,
                after_history=history_after,
                requested_integration=case_data["use_integration"],
                success_code=case_data["success_business_code"],
                expected_message_keywords=case_data["expected_message_keywords"],
            )
        finally:
            if order_context is not None:
                workflow.cancel_created_order(order_context["generate_response"])

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_051 积分抵扣比例计算正确")
    def test_integration_deduction_ratio_calculated_correctly(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        member_api,
        test_conn,
    ):
        """TC_ECOM_051 验证300积分按100积分抵1元计算为3元"""
        case_data = INTEGRATION_ORDER_DATA["TC_ECOM_051"][0]
        order_queries = OrderQueries(test_conn)
        integration_queries = IntegrationQueries(test_conn)
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        context = workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        verify_order_confirmation_amount(
            context["confirm_response"],
            expected_total_amount=case_data["expected_order_amount"],
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
        history_before = integration_queries.get_member_history_state(
            case_data["member_username"],
        )

        order_context = None
        try:
            order_context = workflow.generate_order(
                context,
                pay_type=case_data["pay_type"],
                use_integration=case_data["use_integration"],
            )
            member_after = member_api.member_info()
            database_order = order_queries.get_order_benefit_state(
                order_context["order_id"],
            )
            history_after = integration_queries.get_member_history_state(
                case_data["member_username"],
            )

            verify_integration_order(
                order_context["generate_response"],
                order_context["detail_response"],
                database_order=database_order,
                expected_code=case_data["expected_business_code"],
                expected_use_integration=case_data["use_integration"],
                expected_integration_amount=(case_data["expected_integration_amount"]),
                expected_total_amount=case_data["expected_order_amount"],
            )
            verify_integration_balance_change(
                member_before,
                member_after,
                expected_use_integration=case_data["use_integration"],
            )
            verify_integration_history_change(
                history_before,
                history_after,
                expected_increment=case_data["expected_history_increment"],
                expected_change_count=(case_data["expected_history_change_count"]),
            )
        finally:
            if order_context is not None:
                workflow.cancel_created_order(order_context["generate_response"])
