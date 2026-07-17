import pytest

from api_support.portal.cart_helper import PortalCartHelper
from core.load_yaml import load_yaml
from test_support.db_queries.coupon_queries import CouponQueries
from test_support.db_queries.order_queries import OrderQueries
from verifications.common.response import verify_business_code
from verifications.portal.cart import verify_cart_add_success
from verifications.portal.coupon import (
    verify_confirm_coupon_availability,
    verify_coupon_threshold_boundary,
    verify_owned_coupon_query_consistency,
)
from verifications.portal.order import (
    verify_confirmation_preserves_cart,
    verify_no_order_created,
    verify_order_confirmation_amount,
    verify_order_confirmation_rejected,
    verify_order_confirmation_rejected_or_empty,
    verify_order_confirmation_success,
    verify_required_parameter_error,
)
from workflow.portal.order_workflow import PortalOrderWorkflow

pytestmark = [
    pytest.mark.api,
    pytest.mark.portal,
    pytest.mark.story("Order Confirmation"),
]
ORDER_CONFIRM_DATA = load_yaml("portal/order_confirm_data.yaml")


def _build_workflow(cart_api, product_api, address_api, order_api):
    """构建订单确认单场景复用的前台订单流程。"""
    return PortalOrderWorkflow(
        cart_api=cart_api,
        product_api=product_api,
        address_api=address_api,
        order_api=order_api,
    )


def _resolve_member_coupon_history_id(coupon_queries, case_data):
    """根据用例中的优惠券引用找到当前会员优惠券历史 ID。"""
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


class TestOrderConfirm:
    """前台订单确认单接口测试用例"""

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_033 单个购物车项生成订单确认单成功")
    def test_single_cart_item_order_confirmation_success(
        self,
        cart_api,
        product_api,
        order_api,
        test_conn,
    ):
        """TC_ECOM_033 验证单个购物车项可成功生成完整确认单"""
        case_data = ORDER_CONFIRM_DATA["TC_ECOM_033"][0]
        cart_helper = PortalCartHelper(cart_api, product_api)
        verify_business_code(
            cart_api.clear_cart(),
            case_data["expected_business_code"],
        )
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

        order_queries = OrderQueries(test_conn)
        before_cart = cart_api.cart_list()
        before_order = order_queries.get_latest_member_order_by_status(
            case_data["member_username"],
            case_data["pending_order_status"],
        )
        response = order_api.generate_confirm(cart_id=cart_id)
        after_cart = cart_api.cart_list()
        after_order = order_queries.get_latest_member_order_by_status(
            case_data["member_username"],
            case_data["pending_order_status"],
        )

        verify_order_confirmation_success(
            response,
            expected_code=case_data["expected_business_code"],
            required_fields=case_data["required_confirm_fields"],
            expected_item_count=case_data["expected_item_count"],
        )
        verify_confirmation_preserves_cart(
            before_cart,
            after_cart,
            expected_item_count=case_data["expected_item_count"],
        )
        verify_no_order_created(
            before_order,
            after_order,
            expected_status=case_data["pending_order_status"],
        )

    @pytest.mark.p1
    @pytest.mark.title("TC_ECOM_039 订单确认单展示满足条件的优惠券")
    def test_order_confirmation_lists_available_coupon(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        coupon_api,
        test_conn,
    ):
        """TC_ECOM_039 验证满足门槛的用户优惠券出现在确认单中"""
        case_data = ORDER_CONFIRM_DATA["TC_ECOM_039"][0]
        order_queries = OrderQueries(test_conn)
        coupon_queries = CouponQueries(test_conn)
        coupon_history_id = _resolve_member_coupon_history_id(
            coupon_queries,
            case_data,
        )
        before_order = order_queries.get_latest_member_order_by_status(
            case_data["member_username"],
            case_data.get("pending_order_status", 0),
        )

        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        context = workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
            cart_price=case_data["cart_price"],
        )
        coupon_response = coupon_api.member_coupon_list(
            use_status=case_data["expected_initial_use_status"],
        )
        history_response = coupon_api.member_coupon_history_list(
            use_status=case_data["expected_initial_use_status"],
        )
        after_order = order_queries.get_latest_member_order_by_status(
            case_data["member_username"],
            case_data.get("pending_order_status", 0),
        )

        verify_business_code(
            context["clear_response"], case_data["expected_business_code"]
        )
        verify_cart_add_success(
            context["add_response"], case_data["expected_business_code"]
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
            expected_code=case_data["expected_business_code"],
        )
        verify_no_order_created(
            before_order,
            after_order,
            expected_status=case_data.get("pending_order_status", 0),
        )

    @pytest.mark.p1
    @pytest.mark.title("TC_ECOM_040 订单金额低于门槛时优惠券不可用")
    def test_order_confirmation_hides_coupon_below_threshold(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        coupon_api,
        test_conn,
    ):
        """TC_ECOM_040 验证确认单金额低于门槛 0.01 时不展示优惠券"""
        case_data = ORDER_CONFIRM_DATA["TC_ECOM_040"][0]
        order_queries = OrderQueries(test_conn)
        coupon_queries = CouponQueries(test_conn)
        coupon_history_id = _resolve_member_coupon_history_id(
            coupon_queries,
            case_data,
        )
        before_order = order_queries.get_latest_member_order_by_status(
            case_data["member_username"],
            case_data.get("pending_order_status", 0),
        )

        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        context = workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
            cart_price=case_data["cart_price"],
        )
        coupon_response = coupon_api.member_coupon_list(
            use_status=case_data["expected_initial_use_status"],
        )
        history_response = coupon_api.member_coupon_history_list(
            use_status=case_data["expected_initial_use_status"],
        )
        after_order = order_queries.get_latest_member_order_by_status(
            case_data["member_username"],
            case_data.get("pending_order_status", 0),
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
        verify_no_order_created(
            before_order,
            after_order,
            expected_status=case_data.get("pending_order_status", 0),
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_034 多个购物车项生成确认单金额正确")
    def test_multiple_cart_items_order_confirmation_amount_correct(
        self,
        cart_api,
        product_api,
        order_api,
        test_conn,
    ):
        """TC_ECOM_034 验证多个购物车项的确认单行数和总金额正确"""
        case_data = ORDER_CONFIRM_DATA["TC_ECOM_034"][0]
        cart_helper = PortalCartHelper(cart_api, product_api)
        verify_business_code(
            cart_api.clear_cart(),
            case_data["expected_business_code"],
        )
        cart_ids = []
        for item in case_data["items"]:
            add_response = cart_helper.add_cart(
                product_id=item["product_id"],
                product_sku_id=item["sku_id"],
                quantity=item["quantity"],
            )
            verify_cart_add_success(
                add_response,
                case_data["expected_business_code"],
            )
            cart_ids.append(
                cart_helper.find_id(
                    product_id=item["product_id"],
                    product_sku_id=item["sku_id"],
                    quantity=item["quantity"],
                )
            )

        order_queries = OrderQueries(test_conn)
        before_cart = cart_api.cart_list()
        before_order = order_queries.get_latest_member_order_by_status(
            case_data["member_username"],
            case_data["pending_order_status"],
        )
        response = order_api.generate_confirm(cart_id=cart_ids)
        after_cart = cart_api.cart_list()
        after_order = order_queries.get_latest_member_order_by_status(
            case_data["member_username"],
            case_data["pending_order_status"],
        )

        verify_order_confirmation_success(
            response,
            expected_code=case_data["expected_business_code"],
            required_fields=case_data["required_confirm_fields"],
            expected_item_count=case_data["expected_item_count"],
        )
        verify_order_confirmation_amount(response)
        verify_confirmation_preserves_cart(
            before_cart,
            after_cart,
            expected_item_count=case_data["expected_item_count"],
        )
        verify_no_order_created(
            before_order,
            after_order,
            expected_status=case_data["pending_order_status"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_035 生成确认单缺少cartIds时失败")
    def test_order_confirmation_missing_cart_ids_failed(
        self,
        cart_api,
        order_api,
        test_conn,
    ):
        """TC_ECOM_035 验证缺少 cartIds 时封装层拒绝请求且无副作用"""
        case_data = ORDER_CONFIRM_DATA["TC_ECOM_035"][0]
        order_queries = OrderQueries(test_conn)
        before_cart = cart_api.cart_list()
        before_order = order_queries.get_latest_member_order_by_status(
            case_data["member_username"],
            case_data["pending_order_status"],
        )

        with pytest.raises(AssertionError) as exc_info:
            order_api.generate_confirm(cart_id=case_data["cart_ids"])

        after_cart = cart_api.cart_list()
        after_order = order_queries.get_latest_member_order_by_status(
            case_data["member_username"],
            case_data["pending_order_status"],
        )
        verify_required_parameter_error(
            exc_info.value,
            expected_field=case_data["expected_required_field"],
        )
        verify_confirmation_preserves_cart(before_cart, after_cart)
        verify_no_order_created(
            before_order,
            after_order,
            expected_status=case_data["pending_order_status"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_036 使用不存在cartId生成确认单失败")
    def test_order_confirmation_nonexistent_cart_id_failed(
        self,
        cart_api,
        order_api,
        test_conn,
    ):
        """TC_ECOM_036 验证不存在的 cartId 不会生成有效确认单"""
        case_data = ORDER_CONFIRM_DATA["TC_ECOM_036"][0]
        order_queries = OrderQueries(test_conn)
        before_cart = cart_api.cart_list()
        before_order = order_queries.get_latest_member_order_by_status(
            case_data["member_username"],
            case_data["pending_order_status"],
        )
        response = order_api.generate_confirm(cart_id=case_data["cart_ids"])
        after_cart = cart_api.cart_list()
        after_order = order_queries.get_latest_member_order_by_status(
            case_data["member_username"],
            case_data["pending_order_status"],
        )

        verify_order_confirmation_rejected_or_empty(
            response,
            success_code=case_data["success_business_code"],
            expected_message_keywords=case_data["expected_message_keywords"],
        )
        verify_confirmation_preserves_cart(before_cart, after_cart)
        verify_no_order_created(
            before_order,
            after_order,
            expected_status=case_data["pending_order_status"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_037 购物车为空时生成确认单失败")
    def test_order_confirmation_empty_cart_failed(
        self,
        cart_api,
        order_api,
        test_conn,
    ):
        """TC_ECOM_037 验证空购物车数组被拒绝且不产生订单"""
        case_data = ORDER_CONFIRM_DATA["TC_ECOM_037"][0]
        verify_business_code(
            cart_api.clear_cart(),
            case_data["expected_business_code"],
        )
        order_queries = OrderQueries(test_conn)
        before_cart = cart_api.cart_list()
        before_order = order_queries.get_latest_member_order_by_status(
            case_data["member_username"],
            case_data["pending_order_status"],
        )
        response = order_api.generate_confirm(
            cart_id=case_data["cart_ids"],
            enable=case_data["required_validation_enabled"],
        )
        after_cart = cart_api.cart_list()
        after_order = order_queries.get_latest_member_order_by_status(
            case_data["member_username"],
            case_data["pending_order_status"],
        )

        verify_order_confirmation_rejected(
            response,
            success_code=case_data["expected_business_code"],
            expected_message_keywords=case_data["expected_message_keywords"],
        )
        verify_confirmation_preserves_cart(
            before_cart,
            after_cart,
            expected_item_count=case_data["expected_cart_item_count"],
        )
        verify_no_order_created(
            before_order,
            after_order,
            expected_status=case_data["pending_order_status"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_038 确认单商品金额计算正确")
    def test_order_confirmation_item_amount_correct(
        self,
        cart_api,
        product_api,
        order_api,
        test_conn,
    ):
        """TC_ECOM_038 验证确认单单价乘数量等于商品总金额"""
        case_data = ORDER_CONFIRM_DATA["TC_ECOM_038"][0]
        cart_helper = PortalCartHelper(cart_api, product_api)
        verify_business_code(
            cart_api.clear_cart(),
            case_data["expected_business_code"],
        )
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

        order_queries = OrderQueries(test_conn)
        before_cart = cart_api.cart_list()
        before_order = order_queries.get_latest_member_order_by_status(
            case_data["member_username"],
            case_data["pending_order_status"],
        )
        response = order_api.generate_confirm(cart_id=cart_id)
        after_cart = cart_api.cart_list()
        after_order = order_queries.get_latest_member_order_by_status(
            case_data["member_username"],
            case_data["pending_order_status"],
        )

        verify_order_confirmation_success(
            response,
            expected_code=case_data["expected_business_code"],
            required_fields=case_data["required_confirm_fields"],
            expected_item_count=case_data["expected_item_count"],
        )
        verify_order_confirmation_amount(
            response,
            expected_total_amount=case_data["expected_total_amount"],
            expected_unit_price=case_data["expected_unit_price"],
            expected_quantity=case_data["quantity"],
        )
        verify_confirmation_preserves_cart(
            before_cart,
            after_cart,
            expected_item_count=case_data["expected_item_count"],
        )
        verify_no_order_created(
            before_order,
            after_order,
            expected_status=case_data["pending_order_status"],
        )
