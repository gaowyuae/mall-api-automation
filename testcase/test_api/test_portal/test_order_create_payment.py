import pytest

from api_support.portal.order_helper import PortalOrderHelper
from core.load_yaml import load_yaml
from test_support.db_queries.cart_queries import CartQueries
from test_support.db_queries.order_queries import OrderQueries
from verifications.common.response import verify_business_code
from verifications.portal.cart import verify_cart_item_consumed
from verifications.portal.order import (
    verify_canceled_order_payment_ignored,
    verify_duplicate_order_submission,
    verify_invalid_payment_rejected,
    verify_latest_order_unchanged,
    verify_nonexistent_order_payment_rejected,
    verify_order_cancel_success,
    verify_order_creation_success,
    verify_order_generation_rejected,
    verify_order_numbers_unique,
    verify_order_status_transition,
    verify_payment_success,
    verify_pending_payment_order,
    verify_repeat_payment_idempotent,
    verify_required_parameter_error,
    verify_stock_changed_after_order_creation,
)
from workflow.portal.order_workflow import PortalOrderWorkflow

pytestmark = [
    pytest.mark.api,
    pytest.mark.portal,
    pytest.mark.story("Order Creation and Payment"),
]
ORDER_CREATE_PAYMENT_DATA = load_yaml("portal/order_create_payment_data.yaml")


def _build_workflow(cart_api, product_api, address_api, order_api):
    """构建下单和支付场景复用的前台订单流程。"""
    return PortalOrderWorkflow(
        cart_api=cart_api,
        product_api=product_api,
        address_api=address_api,
        order_api=order_api,
    )


class TestOrderCreation:
    """前台创建订单接口测试用例"""

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_054 使用有效购物车和默认地址创建订单成功")
    def test_create_pending_order_success(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        test_conn,
    ):
        """TC_ECOM_054 验证有效购物车可创建待支付订单及商品明细"""
        case_data = ORDER_CREATE_PAYMENT_DATA["TC_ECOM_054"][0]
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        order_queries = OrderQueries(test_conn)
        context = workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        baseline_order = order_queries.get_latest_member_order(
            case_data["member_username"]
        )

        order_context = None
        try:
            order_context = workflow.generate_order(
                context,
                pay_type=case_data["pay_type"],
            )
            database_order = order_queries.get_order_state(order_context["order_id"])
            database_items = order_queries.get_order_items(order_context["order_id"])

            verify_order_creation_success(
                order_context["generate_response"],
                order_context["detail_response"],
                database_order,
                database_items,
                baseline_order_id=(baseline_order or {}).get("order_id"),
                expected_code=case_data["expected_business_code"],
                expected_status=case_data["pending_order_status"],
                expected_pay_type=case_data["pay_type"],
                expected_product_id=case_data["product_id"],
                expected_sku_id=case_data["sku_id"],
                expected_quantity=case_data["quantity"],
            )
        finally:
            if order_context is not None:
                workflow.cancel_created_order(order_context["generate_response"])

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_055 同一购物车重复提交不生成重复订单")
    def test_duplicate_order_submission_is_idempotent(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        test_conn,
    ):
        """TC_ECOM_055 验证同一 cartIds 连续提交不会重复下单或扣库存"""
        case_data = ORDER_CREATE_PAYMENT_DATA["TC_ECOM_055"][0]
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        order_queries = OrderQueries(test_conn)
        context = workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        baseline_order = order_queries.get_latest_member_order(
            case_data["member_username"]
        )
        baseline_order_id = (baseline_order or {}).get("order_id") or 0

        first_response = None
        try:
            first_response = order_api.generate_order(
                cart_id=context["cart_id"],
                pay_type=case_data["pay_type"],
                member_receive_address_id=context["address_id"],
            )
            first_order_id = PortalOrderHelper.get_order_id(first_response)
            first_detail_response = (
                order_api.order_detail(order_id=first_order_id)
                if first_order_id is not None
                else None
            )
            stock_after_first = order_queries.get_sku_stock_state(case_data["sku_id"])
            second_response = order_api.generate_order(
                cart_id=context["cart_id"],
                pay_type=case_data["pay_type"],
                member_receive_address_id=context["address_id"],
            )
            stock_after_second = order_queries.get_sku_stock_state(case_data["sku_id"])
            new_pending_orders = order_queries.get_member_orders_after(
                case_data["member_username"],
                baseline_order_id,
                case_data["pending_order_status"],
            )

            verify_duplicate_order_submission(
                first_response,
                first_detail_response,
                second_response,
                new_pending_orders,
                stock_after_first,
                stock_after_second,
                success_code=case_data["expected_business_code"],
                expected_status=case_data["pending_order_status"],
                maximum_valid_orders=case_data["maximum_valid_orders"],
            )
        finally:
            if first_response is not None:
                workflow.cancel_created_order(first_response)

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_056 创建订单缺少cartIds失败")
    def test_create_order_missing_cart_ids_failed(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        test_conn,
    ):
        """TC_ECOM_056 验证缺少 cartIds 时封装校验失败且订单不新增"""
        case_data = ORDER_CREATE_PAYMENT_DATA["TC_ECOM_056"][0]
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        order_queries = OrderQueries(test_conn)
        context = workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        before_order = order_queries.get_latest_member_order(
            case_data["member_username"]
        )

        try:
            response = order_api.generate_order(
                cart_id=case_data["cart_ids"],
                pay_type=case_data["pay_type"],
                member_receive_address_id=context["address_id"],
                enable=False,
            )
            after_order = order_queries.get_latest_member_order(
                case_data["member_username"]
            )

            verify_order_generation_rejected(
                response,
                success_code=case_data["success_business_code"],
                expected_message_keywords=case_data["expected_message_keywords"],
            )
            verify_latest_order_unchanged(before_order, after_order)
        finally:
            cart_api.clear_cart()

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_057 创建订单缺少payType失败")
    def test_create_order_missing_pay_type_failed(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        test_conn,
    ):
        """TC_ECOM_057 验证缺少 payType 时封装校验失败且订单不新增"""
        case_data = ORDER_CREATE_PAYMENT_DATA["TC_ECOM_057"][0]
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        order_queries = OrderQueries(test_conn)
        context = workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        before_order = order_queries.get_latest_member_order(
            case_data["member_username"]
        )

        try:
            with pytest.raises(AssertionError) as exc_info:
                order_api.generate_order(
                    cart_id=context["cart_id"],
                    pay_type=case_data["pay_type"],
                    member_receive_address_id=context["address_id"],
                )
            after_order = order_queries.get_latest_member_order(
                case_data["member_username"]
            )

            verify_required_parameter_error(
                exc_info.value,
                expected_field=case_data["expected_required_field"],
            )
            verify_latest_order_unchanged(before_order, after_order)
        finally:
            cart_api.clear_cart()

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_058 创建订单缺少收货地址失败")
    def test_create_order_missing_address_failed(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        test_conn,
    ):
        """TC_ECOM_058 验证缺少收货地址时封装校验失败且订单不新增"""
        case_data = ORDER_CREATE_PAYMENT_DATA["TC_ECOM_058"][0]
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        order_queries = OrderQueries(test_conn)
        context = workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        before_order = order_queries.get_latest_member_order(
            case_data["member_username"]
        )

        try:
            with pytest.raises(AssertionError) as exc_info:
                order_api.generate_order(
                    cart_id=context["cart_id"],
                    pay_type=case_data["pay_type"],
                    member_receive_address_id=(case_data["member_receive_address_id"]),
                )
            after_order = order_queries.get_latest_member_order(
                case_data["member_username"]
            )

            verify_required_parameter_error(
                exc_info.value,
                expected_field=case_data["expected_required_field"],
            )
            verify_latest_order_unchanged(before_order, after_order)
        finally:
            cart_api.clear_cart()

    @pytest.mark.p1
    @pytest.mark.title("TC_ECOM_059 已清空的旧cartId不能创建订单")
    def test_cleared_cart_id_create_order_failed(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        test_conn,
    ):
        """TC_ECOM_059 验证旧 cartId 被消费后不可再用于创建订单"""
        case_data = ORDER_CREATE_PAYMENT_DATA["TC_ECOM_059"][0]
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        order_queries = OrderQueries(test_conn)
        cart_queries = CartQueries(test_conn)
        context = workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        before_order = order_queries.get_latest_member_order(
            case_data["member_username"]
        )
        verify_business_code(cart_api.clear_cart(), case_data["expected_business_code"])
        database_cart = cart_queries.get_cart_item(context["cart_id"])

        response = None
        try:
            response = order_api.generate_order(
                cart_id=context["cart_id"],
                pay_type=case_data["pay_type"],
                member_receive_address_id=context["address_id"],
            )
            after_order = order_queries.get_latest_member_order(
                case_data["member_username"]
            )

            verify_cart_item_consumed(
                database_cart,
                expected_delete_status=case_data["expected_cart_delete_status"],
            )
            verify_order_generation_rejected(
                response,
                success_code=case_data["success_business_code"],
                expected_message_keywords=case_data["expected_message_keywords"],
            )
            verify_latest_order_unchanged(before_order, after_order)
        finally:
            if response is not None:
                workflow.cancel_created_order(response)

    @pytest.mark.p1
    @pytest.mark.title("TC_ECOM_060 创建订单后锁定或扣减库存")
    def test_create_order_updates_sku_stock_state(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        test_conn,
    ):
        """TC_ECOM_060 验证创建订单后 SKU 库存状态按数量变化"""
        case_data = ORDER_CREATE_PAYMENT_DATA["TC_ECOM_060"][0]
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        order_queries = OrderQueries(test_conn)
        context = workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        baseline_order = order_queries.get_latest_member_order(
            case_data["member_username"]
        )
        before_stock = order_queries.get_sku_stock_state(case_data["sku_id"])

        order_context = None
        try:
            order_context = workflow.generate_order(
                context,
                pay_type=case_data["pay_type"],
            )
            database_order = order_queries.get_order_state(order_context["order_id"])
            database_items = order_queries.get_order_items(order_context["order_id"])
            after_stock = order_queries.get_sku_stock_state(case_data["sku_id"])

            verify_order_creation_success(
                order_context["generate_response"],
                order_context["detail_response"],
                database_order,
                database_items,
                baseline_order_id=(baseline_order or {}).get("order_id"),
                expected_code=case_data["expected_business_code"],
                expected_status=case_data["pending_order_status"],
                expected_pay_type=case_data["pay_type"],
                expected_product_id=case_data["product_id"],
                expected_sku_id=case_data["sku_id"],
                expected_quantity=case_data["quantity"],
            )
            verify_stock_changed_after_order_creation(
                before_stock,
                after_stock,
                expected_quantity=case_data["quantity"],
            )
        finally:
            if order_context is not None:
                workflow.cancel_created_order(order_context["generate_response"])

    @pytest.mark.p1
    @pytest.mark.title("TC_ECOM_061 连续创建订单号唯一")
    def test_created_order_numbers_are_unique(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        test_conn,
    ):
        """TC_ECOM_061 验证连续创建的订单 ID 和订单号不重复"""
        case_data = ORDER_CREATE_PAYMENT_DATA["TC_ECOM_061"][0]
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        order_queries = OrderQueries(test_conn)
        created_contexts = []
        order_states = []
        baseline_order = order_queries.get_latest_member_order(
            case_data["member_username"]
        )
        previous_order_id = (baseline_order or {}).get("order_id")

        try:
            for _ in range(case_data["order_count"]):
                context = workflow.prepare_order(
                    product_id=case_data["product_id"],
                    product_sku_id=case_data["sku_id"],
                    quantity=case_data["quantity"],
                )
                order_context = workflow.generate_order(
                    context,
                    pay_type=case_data["pay_type"],
                )
                created_contexts.append(order_context)
                database_order = order_queries.get_order_state(
                    order_context["order_id"]
                )
                database_items = order_queries.get_order_items(
                    order_context["order_id"]
                )
                verify_order_creation_success(
                    order_context["generate_response"],
                    order_context["detail_response"],
                    database_order,
                    database_items,
                    baseline_order_id=previous_order_id,
                    expected_code=case_data["expected_business_code"],
                    expected_status=case_data["pending_order_status"],
                    expected_pay_type=case_data["pay_type"],
                    expected_product_id=case_data["product_id"],
                    expected_sku_id=case_data["sku_id"],
                    expected_quantity=case_data["quantity"],
                )
                previous_order_id = order_context["order_id"]
                order_states.append(database_order)

            verify_order_numbers_unique(order_states)
        finally:
            for order_context in created_contexts:
                workflow.cancel_created_order(order_context["generate_response"])

    @pytest.mark.p1
    @pytest.mark.title("TC_ECOM_062 已下单cartId不能重复创建订单")
    def test_ordered_cart_id_cannot_create_order_again(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        test_conn,
    ):
        """TC_ECOM_062 验证已下单的购物车记录不可再次创建新订单"""
        case_data = ORDER_CREATE_PAYMENT_DATA["TC_ECOM_062"][0]
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        order_queries = OrderQueries(test_conn)
        cart_queries = CartQueries(test_conn)
        context = workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        baseline_order = order_queries.get_latest_member_order(
            case_data["member_username"]
        )
        baseline_order_id = (baseline_order or {}).get("order_id") or 0
        first_response = None

        try:
            first_response = order_api.generate_order(
                cart_id=context["cart_id"],
                pay_type=case_data["pay_type"],
                member_receive_address_id=context["address_id"],
            )
            first_order_id = PortalOrderHelper.get_order_id(first_response)
            first_detail_response = order_api.order_detail(order_id=first_order_id)
            cart_after_first = cart_queries.get_cart_item(context["cart_id"])
            stock_after_first = order_queries.get_sku_stock_state(case_data["sku_id"])
            second_response = order_api.generate_order(
                cart_id=context["cart_id"],
                pay_type=case_data["pay_type"],
                member_receive_address_id=context["address_id"],
            )
            stock_after_second = order_queries.get_sku_stock_state(case_data["sku_id"])
            new_pending_orders = order_queries.get_member_orders_after(
                case_data["member_username"],
                baseline_order_id,
                case_data["pending_order_status"],
            )

            verify_cart_item_consumed(
                cart_after_first,
                expected_delete_status=case_data["expected_cart_delete_status"],
            )
            verify_duplicate_order_submission(
                first_response,
                first_detail_response,
                second_response,
                new_pending_orders,
                stock_after_first,
                stock_after_second,
                success_code=case_data["expected_business_code"],
                expected_status=case_data["pending_order_status"],
                maximum_valid_orders=case_data["maximum_valid_orders"],
            )
        finally:
            if first_response is not None:
                workflow.cancel_created_order(first_response)

    @pytest.mark.p1
    @pytest.mark.title("TC_ECOM_063 使用不存在优惠券创建订单失败")
    def test_create_order_with_invalid_coupon_failed(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        test_conn,
    ):
        """TC_ECOM_063 验证不存在优惠券不会创建订单"""
        case_data = ORDER_CREATE_PAYMENT_DATA["TC_ECOM_063"][0]
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        order_queries = OrderQueries(test_conn)
        context = workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        before_order = order_queries.get_latest_member_order(
            case_data["member_username"]
        )

        response = None
        try:
            response = order_api.generate_order(
                cart_id=context["cart_id"],
                pay_type=case_data["pay_type"],
                member_receive_address_id=context["address_id"],
                coupon_id=case_data["coupon_id"],
                use_integration=case_data["use_integration"],
            )
            after_order = order_queries.get_latest_member_order(
                case_data["member_username"]
            )

            verify_order_generation_rejected(
                response,
                success_code=case_data["success_business_code"],
                expected_message_keywords=case_data["expected_message_keywords"],
            )
            verify_latest_order_unchanged(before_order, after_order)
        finally:
            if response is not None:
                workflow.cancel_created_order(response)

    @pytest.mark.p1
    @pytest.mark.title("TC_ECOM_064 使用负数积分创建订单失败")
    def test_create_order_with_negative_integration_failed(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        test_conn,
    ):
        """TC_ECOM_064 验证负数积分不会创建订单"""
        case_data = ORDER_CREATE_PAYMENT_DATA["TC_ECOM_064"][0]
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        order_queries = OrderQueries(test_conn)
        context = workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        before_order = order_queries.get_latest_member_order(
            case_data["member_username"]
        )

        response = None
        try:
            response = order_api.generate_order(
                cart_id=context["cart_id"],
                pay_type=case_data["pay_type"],
                member_receive_address_id=context["address_id"],
                use_integration=case_data["use_integration"],
            )
            after_order = order_queries.get_latest_member_order(
                case_data["member_username"]
            )

            verify_order_generation_rejected(
                response,
                success_code=case_data["success_business_code"],
                expected_message_keywords=case_data["expected_message_keywords"],
            )
            verify_latest_order_unchanged(before_order, after_order)
        finally:
            if response is not None:
                workflow.cancel_created_order(response)


class TestOrderPayment:
    """前台订单支付接口测试用例"""

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_065 待支付订单支付成功后变为待发货")
    def test_pending_order_payment_success(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        test_conn,
    ):
        """TC_ECOM_065 验证支付成功后状态、金额和关联状态一致"""
        case_data = ORDER_CREATE_PAYMENT_DATA["TC_ECOM_065"][0]
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        order_queries = OrderQueries(test_conn)
        prepared_context = workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        order_context = workflow.generate_order(
            prepared_context,
            pay_type=case_data["pay_type"],
        )
        before_database_order = order_queries.get_order_state(order_context["order_id"])
        before_stock = order_queries.get_sku_stock_state(case_data["sku_id"])
        order_id = verify_pending_payment_order(
            order_context["detail_response"],
            before_database_order,
            expected_code=case_data["expected_business_code"],
            expected_status=case_data["pending_order_status"],
        )

        try:
            payment_context = workflow.attempt_payment(
                order_id=order_id,
                pay_type=case_data["pay_type"],
            )
            after_database_order = order_queries.get_order_state(order_id)
            after_stock = order_queries.get_sku_stock_state(case_data["sku_id"])

            verify_payment_success(
                payment_context["pay_response"],
                payment_context["after_detail_response"],
                before_database_order,
                after_database_order,
                before_stock,
                after_stock,
                expected_code=case_data["expected_business_code"],
                expected_order_id=order_id,
                expected_status=case_data["paid_order_status"],
                expected_pay_type=case_data["pay_type"],
            )
        finally:
            current_order = order_queries.get_order_state(order_id)
            if (current_order or {}).get("status") == case_data["pending_order_status"]:
                workflow.cancel_created_order(order_context["generate_response"])

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_066 同一订单重复支付不重复处理")
    def test_duplicate_payment_is_idempotent(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        test_conn,
    ):
        """TC_ECOM_066 验证同一订单重复支付不重复改变金额及关联状态"""
        case_data = ORDER_CREATE_PAYMENT_DATA["TC_ECOM_066"][0]
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        order_queries = OrderQueries(test_conn)
        prepared_context = workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        order_context = workflow.generate_order(
            prepared_context,
            pay_type=case_data["pay_type"],
        )
        pending_database_order = order_queries.get_order_state(
            order_context["order_id"]
        )
        order_id = verify_pending_payment_order(
            order_context["detail_response"],
            pending_database_order,
            expected_code=case_data["expected_business_code"],
            expected_status=case_data["pending_order_status"],
        )

        payment_attempts = []
        database_states = []
        stock_states = []
        try:
            for _ in range(case_data["repeat_pay"]):
                payment_attempts.append(
                    workflow.attempt_payment(
                        order_id=order_id,
                        pay_type=case_data["pay_type"],
                    )
                )
                database_states.append(order_queries.get_order_state(order_id))
                stock_states.append(
                    order_queries.get_sku_stock_state(case_data["sku_id"])
                )

            verify_repeat_payment_idempotent(
                payment_attempts[0]["pay_response"],
                payment_attempts[0]["after_detail_response"],
                payment_attempts[1]["pay_response"],
                payment_attempts[1]["after_detail_response"],
                database_states[0],
                database_states[1],
                stock_states[0],
                stock_states[1],
                success_code=case_data["expected_business_code"],
                expected_order_id=order_id,
                expected_status=case_data["paid_order_status"],
            )
        finally:
            current_order = order_queries.get_order_state(order_id)
            if (current_order or {}).get("status") == case_data["pending_order_status"]:
                workflow.cancel_created_order(order_context["generate_response"])

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_067 支付不存在订单号失败")
    def test_nonexistent_order_payment_failed(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        test_conn,
    ):
        """TC_ECOM_067 验证不存在订单支付失败且数据库不新增订单"""
        case_data = ORDER_CREATE_PAYMENT_DATA["TC_ECOM_067"][0]
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        order_queries = OrderQueries(test_conn)
        before_database_order = order_queries.get_order_state(case_data["order_id"])

        payment_context = workflow.attempt_payment(
            order_id=case_data["order_id"],
            pay_type=case_data["pay_type"],
        )
        after_database_order = order_queries.get_order_state(case_data["order_id"])

        verify_nonexistent_order_payment_rejected(
            payment_context["before_detail_response"],
            payment_context["pay_response"],
            payment_context["after_detail_response"],
            before_database_order,
            after_database_order,
            detail_code=case_data["detail_business_code"],
            success_code=case_data["success_business_code"],
            expected_message_keywords=case_data["expected_message_keywords"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_068 已取消订单不能支付成功")
    def test_canceled_order_payment_is_rejected_or_ignored(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        test_conn,
    ):
        """TC_ECOM_068 验证已取消订单支付不会恢复为待发货"""
        case_data = ORDER_CREATE_PAYMENT_DATA["TC_ECOM_068"][0]
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        order_queries = OrderQueries(test_conn)
        prepared_context = workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        order_context = workflow.generate_order(
            prepared_context,
            pay_type=case_data["pay_type"],
        )
        pending_database_order = order_queries.get_order_state(
            order_context["order_id"]
        )
        order_id = verify_pending_payment_order(
            order_context["detail_response"],
            pending_database_order,
            expected_code=case_data["expected_business_code"],
            expected_status=case_data["pending_order_status"],
        )
        cancel_response = workflow.cancel_created_order(
            order_context["generate_response"]
        )
        verify_business_code(cancel_response, case_data["expected_business_code"])
        canceled_detail_response = order_api.order_detail(order_id=order_id)
        before_database_order = order_queries.get_order_state(order_id)
        before_stock = order_queries.get_sku_stock_state(case_data["sku_id"])

        payment_context = workflow.attempt_payment(
            order_id=order_id,
            pay_type=case_data["pay_type"],
        )
        after_database_order = order_queries.get_order_state(order_id)
        after_stock = order_queries.get_sku_stock_state(case_data["sku_id"])

        verify_canceled_order_payment_ignored(
            payment_context["pay_response"],
            canceled_detail_response,
            payment_context["after_detail_response"],
            before_database_order,
            after_database_order,
            before_stock,
            after_stock,
            detail_code=case_data["expected_business_code"],
            success_code=case_data["expected_business_code"],
            expected_order_id=order_id,
            expected_status=case_data["canceled_order_status"],
        )

    @pytest.mark.p1
    @pytest.mark.title("TC_ECOM_069 非法payType支付失败")
    def test_invalid_pay_type_payment_failed(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        test_conn,
    ):
        """TC_ECOM_069 验证非法支付方式不会改变待支付订单"""
        case_data = ORDER_CREATE_PAYMENT_DATA["TC_ECOM_069"][0]
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        order_queries = OrderQueries(test_conn)
        prepared_context = workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        order_context = workflow.generate_order(
            prepared_context,
            pay_type=case_data["pay_type"],
        )
        before_database_order = order_queries.get_order_state(order_context["order_id"])
        order_id = verify_pending_payment_order(
            order_context["detail_response"],
            before_database_order,
            expected_code=case_data["success_business_code"],
            expected_status=case_data["pending_order_status"],
        )

        try:
            payment_context = workflow.attempt_payment(
                order_id=order_id,
                pay_type=case_data["invalid_pay_type"],
            )
            after_database_order = order_queries.get_order_state(order_id)

            verify_invalid_payment_rejected(
                payment_context["pay_response"],
                payment_context["before_detail_response"],
                payment_context["after_detail_response"],
                before_database_order,
                after_database_order,
                success_code=case_data["success_business_code"],
                expected_order_id=order_id,
                expected_status=case_data["pending_order_status"],
                expected_message_keywords=case_data["expected_message_keywords"],
            )
        finally:
            current_order = order_queries.get_order_state(order_id)
            if (current_order or {}).get("status") == case_data["pending_order_status"]:
                workflow.cancel_created_order(order_context["generate_response"])

    @pytest.mark.p1
    @pytest.mark.title("TC_ECOM_086 待支付订单支付后变为待发货")
    def test_pending_to_paid_status_transition(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        test_conn,
    ):
        """TC_ECOM_086 验证待支付订单支付成功后的状态流转"""
        case_data = ORDER_CREATE_PAYMENT_DATA["TC_ECOM_086"][0]
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        order_queries = OrderQueries(test_conn)
        prepared_context = workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        order_context = workflow.generate_order(
            prepared_context,
            pay_type=case_data["pay_type"],
        )
        before_database_order = order_queries.get_order_state(order_context["order_id"])
        order_id = verify_pending_payment_order(
            order_context["detail_response"],
            before_database_order,
            expected_code=case_data["expected_business_code"],
            expected_status=case_data["pending_order_status"],
        )

        try:
            payment_context = workflow.attempt_payment(
                order_id=order_id,
                pay_type=case_data["pay_type"],
            )
            after_database_order = order_queries.get_order_state(order_id)

            verify_business_code(
                payment_context["pay_response"],
                case_data["expected_business_code"],
            )
            verify_order_status_transition(
                payment_context["after_detail_response"],
                after_database_order,
                expected_code=case_data["expected_business_code"],
                expected_order_id=order_id,
                expected_status=case_data["paid_order_status"],
                required_time_field="payment_time",
            )
        finally:
            current_order = order_queries.get_order_state(order_id)
            if (current_order or {}).get("status") == case_data["pending_order_status"]:
                workflow.cancel_created_order(order_context["generate_response"])

    @pytest.mark.p1
    @pytest.mark.title("TC_ECOM_087 待支付订单取消后变为已取消")
    def test_pending_to_canceled_status_transition(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
        test_conn,
    ):
        """TC_ECOM_087 验证待支付订单取消后的状态流转"""
        case_data = ORDER_CREATE_PAYMENT_DATA["TC_ECOM_087"][0]
        workflow = _build_workflow(cart_api, product_api, address_api, order_api)
        order_queries = OrderQueries(test_conn)
        prepared_context = workflow.prepare_order(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        order_context = workflow.generate_order(
            prepared_context,
            pay_type=case_data["pay_type"],
        )
        before_database_order = order_queries.get_order_state(order_context["order_id"])
        order_id = verify_pending_payment_order(
            order_context["detail_response"],
            before_database_order,
            expected_code=case_data["expected_business_code"],
            expected_status=case_data["pending_order_status"],
        )

        cancel_response = workflow.cancel_created_order(
            order_context["generate_response"]
        )
        detail_response = order_api.order_detail(order_id=order_id)
        after_database_order = order_queries.get_order_state(order_id)

        verify_order_cancel_success(
            cancel_response,
            detail_response,
            before_database_order,
            after_database_order,
            expected_code=case_data["expected_business_code"],
            expected_order_id=order_id,
            expected_status=case_data["canceled_order_status"],
        )
