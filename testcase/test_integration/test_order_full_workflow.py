from uuid import uuid4

import pytest

from core.load_yaml import load_yaml
from test_support.db_queries.order_queries import OrderQueries
from verifications.admin.order import (
    verify_admin_completed_order,
    verify_delivery_candidate,
    verify_delivery_success,
)
from verifications.common.response import verify_business_code
from verifications.portal.address import verify_default_address
from verifications.portal.cart import (
    verify_cart_add_success,
    verify_cart_id_matches_item,
    verify_cart_list_contains_item,
)
from verifications.portal.order import (
    verify_confirm_receive_success,
    verify_order_confirmation_amount,
    verify_order_confirmation_success,
    verify_order_creation_success,
    verify_payment_success,
    verify_pending_payment_order,
    verify_receive_candidate,
)
from verifications.portal.product import (
    verify_keyword_search,
    verify_product_detail_content,
    verify_search_contains_product,
    verify_sku_list_contains,
)
from workflow.admin.order_workflow import AdminOrderWorkflow

pytestmark = [
    pytest.mark.api,
    pytest.mark.portal,
    pytest.mark.integration,
    pytest.mark.story("Order Full Workflow"),
]
ORDER_FULL_WORKFLOW_DATA = load_yaml("portal/order_full_workflow_data.yaml")


def _build_workflow(
    cart_api,
    product_api,
    address_api,
    order_api,
    admin_order_api,
):
    return AdminOrderWorkflow(
        cart_api=cart_api,
        product_api=product_api,
        address_api=address_api,
        portal_order_api=order_api,
        admin_order_api=admin_order_api,
    )


class TestOrderFullWorkflow:
    """商城订单从商品搜索到确认收货的完整业务流程"""

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_UNMAPPED_203 商品购买完整业务流程成功")
    def test_product_purchase_full_workflow_success(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        admin_order_api,
        test_conn,
    ):
        """TC_ECOM_UNMAPPED_203 验证订单状态按0、1、2、3完整流转且数据一致"""
        case_data = ORDER_FULL_WORKFLOW_DATA["TC_ECOM_UNMAPPED_203"][0]
        workflow = _build_workflow(
            cart_api,
            product_api,
            address_api,
            order_api,
            admin_order_api,
        )
        order_queries = OrderQueries(test_conn)
        delivery_sn = f"{case_data['delivery_sn_prefix']}{uuid4().hex[:12].upper()}"

        search_response = product_api.product_search(
            keyword=case_data["keyword"],
            page_num=case_data["page_num"],
            page_size=case_data["page_size"],
            sort=case_data["sort"],
        )
        products = verify_keyword_search(
            search_response,
            keyword=case_data["keyword"],
            expected_code=case_data["expected_business_code"],
            expected_page_num=case_data["page_num"],
            expected_page_size=case_data["page_size"],
            required_fields=case_data["required_search_fields"],
        )
        verify_search_contains_product(products, case_data["product_id"])

        detail_response = product_api.search_product_detail(
            product_id=case_data["product_id"]
        )
        verify_product_detail_content(
            detail_response,
            expected_product_id=case_data["product_id"],
            expected_code=case_data["expected_business_code"],
            required_fields=case_data["required_product_fields"],
        )
        verify_sku_list_contains(
            detail_response,
            expected_sku_id=case_data["sku_id"],
            expected_code=case_data["expected_business_code"],
            required_fields=case_data["required_sku_fields"],
        )

        prepared_context = workflow.portal_workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        verify_business_code(
            prepared_context["clear_response"],
            case_data["expected_business_code"],
        )
        verify_cart_add_success(
            prepared_context["add_response"],
            case_data["expected_business_code"],
        )
        cart_response = cart_api.cart_list()
        cart_item = verify_cart_list_contains_item(
            cart_response,
            expected_code=case_data["expected_business_code"],
            expected_product_id=case_data["product_id"],
            expected_sku_id=case_data["sku_id"],
            expected_quantity=case_data["quantity"],
            required_fields=case_data["required_cart_item_fields"],
        )
        verify_cart_id_matches_item(prepared_context["cart_id"], cart_item)

        address_response = address_api.address_list()
        default_address = verify_default_address(
            address_response,
            expected_code=case_data["expected_business_code"],
            expected_default_status=case_data["default_address_status"],
            required_fields=case_data["required_address_fields"],
        )
        prepared_context["address_id"] = default_address["id"]
        verify_order_confirmation_success(
            prepared_context["confirm_response"],
            expected_code=case_data["expected_business_code"],
            required_fields=case_data["required_confirm_fields"],
            expected_item_count=case_data["expected_item_count"],
        )
        verify_order_confirmation_amount(prepared_context["confirm_response"])

        baseline_order = order_queries.get_latest_member_order(
            case_data["member_username"]
        )
        order_context = workflow.portal_workflow.generate_order(
            prepared_context,
            pay_type=case_data["pay_type"],
            coupon_id=case_data["coupon_id"],
            use_integration=case_data["use_integration"],
        )
        order_id = order_context["order_id"]
        pending_database_order = order_queries.get_order_state(order_id)
        database_items = order_queries.get_order_items(order_id)
        verify_order_creation_success(
            order_context["generate_response"],
            order_context["detail_response"],
            pending_database_order,
            database_items,
            baseline_order_id=(baseline_order or {}).get("order_id"),
            expected_code=case_data["expected_business_code"],
            expected_status=case_data["pending_order_status"],
            expected_pay_type=case_data["pay_type"],
            expected_product_id=case_data["product_id"],
            expected_sku_id=case_data["sku_id"],
            expected_quantity=case_data["quantity"],
        )
        verify_pending_payment_order(
            order_context["detail_response"],
            pending_database_order,
            expected_code=case_data["expected_business_code"],
            expected_status=case_data["pending_order_status"],
        )

        stock_before_payment = order_queries.get_sku_stock_state(case_data["sku_id"])
        payment_context = workflow.portal_workflow.attempt_payment(
            order_id=order_id,
            pay_type=case_data["pay_type"],
        )
        paid_database_order = order_queries.get_order_state(order_id)
        stock_after_payment = order_queries.get_sku_stock_state(case_data["sku_id"])
        verify_payment_success(
            payment_context["pay_response"],
            payment_context["after_detail_response"],
            pending_database_order,
            paid_database_order,
            stock_before_payment,
            stock_after_payment,
            expected_code=case_data["expected_business_code"],
            expected_order_id=order_id,
            expected_status=case_data["paid_order_status"],
            expected_pay_type=case_data["pay_type"],
        )

        verify_delivery_candidate(
            paid_database_order,
            case_data["paid_order_status"],
        )
        delivery_context = workflow.attempt_delivery(
            order_id=order_id,
            delivery_company=case_data["delivery_company"],
            delivery_sn=delivery_sn,
        )
        shipped_database_order = order_queries.get_order_state(order_id)
        verify_delivery_success(
            delivery_context["delivery_response"],
            delivery_context["after_admin_detail"],
            delivery_context["portal_detail"],
            shipped_database_order,
            expected_code=case_data["expected_business_code"],
            expected_order_id=order_id,
            expected_status=case_data["shipped_order_status"],
            expected_delivery_company=case_data["delivery_company"],
            expected_delivery_sn=delivery_sn,
        )

        verify_receive_candidate(
            delivery_context["portal_detail"],
            shipped_database_order,
            expected_code=case_data["expected_business_code"],
            expected_status=case_data["shipped_order_status"],
        )
        confirm_response = order_api.confirm_receive(order_id=order_id)
        portal_completed_detail = order_api.order_detail(order_id=order_id)
        admin_completed_detail = admin_order_api.order_detail(order_id=order_id)
        completed_database_order = order_queries.get_order_state(order_id)
        verify_confirm_receive_success(
            confirm_response,
            portal_completed_detail,
            shipped_database_order,
            completed_database_order,
            expected_code=case_data["expected_business_code"],
            expected_order_id=order_id,
            expected_status=case_data["completed_order_status"],
        )
        verify_admin_completed_order(
            admin_completed_detail,
            completed_database_order,
            expected_code=case_data["expected_business_code"],
            expected_order_id=order_id,
            expected_status=case_data["completed_order_status"],
        )
