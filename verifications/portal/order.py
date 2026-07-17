from decimal import Decimal, InvalidOperation

from api_support.common.response_helper import ApiResponseHelper
from api_support.portal.cart_helper import PortalCartHelper
from api_support.portal.order_helper import PortalOrderHelper
from verifications.common.response import (
    verify_business_code,
    verify_business_failure,
    verify_message_contains_any,
)


def _decimal_amount(value, field_name):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise AssertionError(f"{field_name} 应为有效金额，实际为：{value}") from exc


def verify_order_confirmation_success(
    response,
    expected_code,
    required_fields,
    expected_item_count,
):
    """校验订单确认单成功响应的业务结构"""
    verify_business_code(response, expected_code)
    confirm_data = PortalOrderHelper.get_confirm_data(response)
    assert isinstance(confirm_data, dict), (
        f"订单确认单 data 应为字典，实际为：{confirm_data}"
    )

    missing_fields = [field for field in required_fields if field not in confirm_data]
    assert not missing_fields, (
        f"订单确认单缺少字段 {missing_fields}，实际字段为：{list(confirm_data)}"
    )

    items = PortalOrderHelper.get_confirm_items(response)
    assert isinstance(items, list) and items, (
        f"订单确认单商品列表不应为空，实际为：{items}"
    )
    assert len(items) == expected_item_count, (
        f"订单确认单商品行数应为 {expected_item_count}，实际为：{len(items)}"
    )

    addresses = confirm_data.get("memberReceiveAddressList")
    assert isinstance(addresses, list) and addresses, (
        f"订单确认单收货地址列表不应为空，实际为：{addresses}"
    )
    assert isinstance(confirm_data.get("couponHistoryDetailList"), list), (
        "订单确认单 couponHistoryDetailList 应为列表，"
        f"实际为：{confirm_data.get('couponHistoryDetailList')}"
    )
    assert confirm_data.get("memberIntegration") is not None, (
        "订单确认单应包含 memberIntegration"
    )
    assert isinstance(confirm_data.get("integrationConsumeSetting"), dict), (
        "订单确认单 integrationConsumeSetting 应为字典，"
        f"实际为：{confirm_data.get('integrationConsumeSetting')}"
    )
    assert isinstance(PortalOrderHelper.get_confirm_calc_amount(response), dict), (
        f"订单确认单 calcAmount 应为字典，实际为：{confirm_data.get('calcAmount')}"
    )
    return items


def verify_order_confirmation_amount(
    response,
    expected_total_amount=None,
    expected_unit_price=None,
    expected_quantity=None,
):
    """校验确认单商品行金额与汇总总金额一致"""
    items = PortalOrderHelper.get_confirm_items(response)
    assert isinstance(items, list) and items, (
        f"订单确认单商品列表不应为空，实际为：{items}"
    )

    calculated_total = sum(
        (
            _decimal_amount(item.get("price"), "确认单商品 price")
            * _decimal_amount(item.get("quantity"), "确认单商品 quantity")
            for item in items
        ),
        Decimal("0"),
    )
    calc_amount = PortalOrderHelper.get_confirm_calc_amount(response)
    assert isinstance(calc_amount, dict), (
        f"订单确认单 calcAmount 应为字典，实际为：{calc_amount}"
    )
    actual_total = _decimal_amount(
        calc_amount.get("totalAmount"),
        "订单确认单 calcAmount.totalAmount",
    )
    assert actual_total == calculated_total, (
        f"确认单 totalAmount 应等于商品单价乘数量之和 {calculated_total}，"
        f"实际为：{actual_total}"
    )

    if expected_total_amount is not None:
        expected_total = _decimal_amount(expected_total_amount, "预期商品总金额")
        assert actual_total == expected_total, (
            f"确认单 totalAmount 应为 {expected_total}，实际为：{actual_total}"
        )

    if expected_unit_price is not None or expected_quantity is not None:
        assert len(items) == 1, f"校验单行金额时商品行数应为 1，实际为：{len(items)}"
        item = items[0]
        if expected_unit_price is not None:
            actual_price = _decimal_amount(item.get("price"), "确认单商品 price")
            expected_price = _decimal_amount(expected_unit_price, "预期商品单价")
            assert actual_price == expected_price, (
                f"确认单商品单价应为 {expected_price}，实际为：{actual_price}"
            )
        if expected_quantity is not None:
            actual_quantity = item.get("quantity")
            assert actual_quantity == expected_quantity, (
                f"确认单商品数量应为 {expected_quantity}，实际为：{actual_quantity}"
            )

    return actual_total


def verify_order_confirmation_rejected(
    response,
    success_code,
    expected_message_keywords,
):
    """校验订单确认单请求被业务层拒绝"""
    verify_business_failure(response, success_code)
    verify_message_contains_any(response, expected_message_keywords)


def verify_order_generation_rejected(
    response,
    success_code,
    expected_message_keywords,
):
    """校验正式订单生成请求被业务层拒绝"""
    verify_business_failure(response, success_code)
    verify_message_contains_any(response, expected_message_keywords)


def verify_order_confirmation_rejected_or_empty(
    response,
    success_code,
    expected_message_keywords,
):
    """校验无效购物车 ID 返回失败或明确的空商品确认单"""
    actual_code = ApiResponseHelper.get_code(response)
    assert actual_code is not None, f"订单确认单响应缺少业务 code：{response}"
    if actual_code == success_code:
        items = PortalOrderHelper.get_confirm_items(response)
        assert items == [], (
            f"无效购物车 ID 返回成功 code 时商品列表应为空，实际为：{items}"
        )
    verify_message_contains_any(response, expected_message_keywords)


def verify_required_parameter_error(error, expected_field):
    """校验 API 封装层报告必填参数缺失"""
    assert isinstance(error, AssertionError), (
        f"缺少 {expected_field} 时应触发 AssertionError，实际为：{type(error).__name__}"
    )
    assert expected_field in str(error), (
        f"参数错误应包含字段 {expected_field}，实际为：{error}"
    )


def verify_confirmation_preserves_cart(
    before_response,
    after_response,
    expected_item_count=None,
):
    """校验生成确认单前后购物车记录与数量保持不变"""
    before_items = PortalCartHelper.get_item_states(before_response)
    after_items = PortalCartHelper.get_item_states(after_response)
    assert before_items is not None, f"操作前购物车列表结构错误：{before_response}"
    assert after_items is not None, f"操作后购物车列表结构错误：{after_response}"
    if expected_item_count is not None:
        assert len(before_items) == expected_item_count, (
            f"操作前购物车商品行数应为 {expected_item_count}，"
            f"实际为：{len(before_items)}"
        )
    assert after_items == before_items, (
        f"生成确认单不应改变购物车，操作前={before_items}，操作后={after_items}"
    )


def verify_no_order_created(
    before_state,
    after_state,
    expected_status,
):
    """校验生成确认单前后没有新增指定状态的正式订单"""
    assert before_state is None or isinstance(before_state, dict), (
        f"操作前订单状态应为字典或 None，实际为：{before_state}"
    )
    assert after_state is None or isinstance(after_state, dict), (
        f"操作后订单状态应为字典或 None，实际为：{after_state}"
    )

    if before_state is not None:
        assert before_state.get("status") == expected_status, (
            f"操作前订单状态应为 {expected_status}，实际为：{before_state}"
        )
    if after_state is not None:
        assert after_state.get("status") == expected_status, (
            f"操作后订单状态应为 {expected_status}，实际为：{after_state}"
        )

    before_order_id = (before_state or {}).get("order_id")
    after_order_id = (after_state or {}).get("order_id")
    assert after_order_id == before_order_id, (
        f"生成确认单不应新增状态 {expected_status} 的订单，"
        f"操作前最新订单 ID={before_order_id}，操作后={after_order_id}"
    )


def verify_latest_order_unchanged(before_state, after_state):
    """校验失败操作没有新增任何状态的订单"""
    assert before_state is None or isinstance(before_state, dict), (
        f"操作前订单状态应为字典或 None，实际为：{before_state}"
    )
    assert after_state is None or isinstance(after_state, dict), (
        f"操作后订单状态应为字典或 None，实际为：{after_state}"
    )
    before_order_id = (before_state or {}).get("order_id")
    after_order_id = (after_state or {}).get("order_id")
    assert after_order_id == before_order_id, (
        f"失败操作不应新增订单，操作前最新订单 ID={before_order_id}，"
        f"操作后={after_order_id}"
    )


def verify_order_exists(
    order_state,
    expected_status,
):
    """校验指定状态的订单存在并返回订单 ID"""
    assert isinstance(order_state, dict), (
        f"未找到状态为 {expected_status} 的前台订单，实际为：{order_state}"
    )
    order_id = order_state.get("order_id")
    assert order_id is not None, f"订单数据缺少 order_id：{order_state}"
    assert order_state.get("status") == expected_status, (
        f"订单状态应为 {expected_status}，实际为：{order_state.get('status')}"
    )
    return order_id


def verify_order_unchanged(
    before_state,
    after_state,
    expected_status,
):
    """校验失败操作前后的订单状态保持不变"""
    before_order_id = verify_order_exists(before_state, expected_status)
    after_order_id = verify_order_exists(after_state, expected_status)
    assert after_order_id == before_order_id, (
        f"操作前后订单 ID 应一致，操作前为 {before_order_id}，操作后为 {after_order_id}"
    )
    assert before_state.get("confirm_time") is None, (
        f"待收货订单操作前 confirm_time 应为空，实际为：{before_state}"
    )
    assert after_state.get("confirm_time") is None, (
        f"Token 混用失败后 confirm_time 应为空，实际为：{after_state}"
    )


def verify_order_creation_success(
    generate_response,
    detail_response,
    database_order,
    database_items,
    *,
    baseline_order_id,
    expected_code,
    expected_status,
    expected_pay_type,
    expected_product_id,
    expected_sku_id,
    expected_quantity,
):
    """校验订单创建响应、详情和数据库记录一致"""
    verify_business_code(generate_response, expected_code)
    verify_business_code(detail_response, expected_code)

    generated_order_id = PortalOrderHelper.get_order_id(generate_response)
    detail_order_id = PortalOrderHelper.get_order_id(detail_response)
    assert generated_order_id is not None, "生成订单响应应返回订单 ID"
    assert detail_order_id == generated_order_id, (
        f"订单详情 ID 应为 {generated_order_id}，实际为：{detail_order_id}"
    )
    if baseline_order_id is not None:
        assert generated_order_id > baseline_order_id, (
            f"新订单 ID 应大于基准订单 ID {baseline_order_id}，"
            f"实际为：{generated_order_id}"
        )

    detail_status = PortalOrderHelper.get_order_status(detail_response)
    assert detail_status == expected_status, (
        f"新订单状态应为 {expected_status}，实际为：{detail_status}"
    )
    assert PortalOrderHelper.get_pay_type(detail_response) == expected_pay_type, (
        f"新订单 payType 应为 {expected_pay_type}，"
        f"实际为：{PortalOrderHelper.get_pay_type(detail_response)}"
    )

    assert isinstance(database_order, dict), (
        f"数据库应存在订单 {generated_order_id}，实际为：{database_order}"
    )
    assert database_order.get("order_id") == generated_order_id
    assert database_order.get("status") == expected_status, (
        f"数据库订单状态应为 {expected_status}，实际为：{database_order}"
    )
    assert database_order.get("pay_type") == expected_pay_type, (
        f"数据库订单 pay_type 应为 {expected_pay_type}，实际为：{database_order}"
    )

    assert isinstance(database_items, list), (
        f"数据库订单明细应为列表，实际为：{database_items}"
    )
    assert len(database_items) == 1, (
        f"订单 {generated_order_id} 应新增 1 条商品明细，实际为：{len(database_items)}"
    )
    database_item = database_items[0]
    assert database_item.get("product_id") == expected_product_id, (
        f"订单明细 product_id 应为 {expected_product_id}，实际为：{database_item}"
    )
    assert database_item.get("product_sku_id") == expected_sku_id, (
        f"订单明细 SKU ID 应为 {expected_sku_id}，实际为：{database_item}"
    )
    assert database_item.get("product_quantity") == expected_quantity, (
        f"订单明细数量应为 {expected_quantity}，实际为：{database_item}"
    )

    detail_items = PortalOrderHelper.get_order_items(detail_response)
    assert isinstance(detail_items, list) and len(detail_items) == 1, (
        f"订单详情应返回 1 条商品明细，实际为：{detail_items}"
    )
    detail_item = detail_items[0]
    assert detail_item.get("productSkuId") == expected_sku_id, (
        f"订单详情 SKU ID 应为 {expected_sku_id}，实际为：{detail_item}"
    )
    assert detail_item.get("productQuantity") == expected_quantity, (
        f"订单详情商品数量应为 {expected_quantity}，实际为：{detail_item}"
    )
    return generated_order_id


def verify_duplicate_order_submission(
    first_response,
    first_detail_response,
    second_response,
    new_pending_orders,
    stock_after_first,
    stock_after_second,
    *,
    success_code,
    expected_status,
    maximum_valid_orders,
):
    """校验同一购物车重复提交不会产生第二笔有效订单或重复扣库存"""
    verify_business_code(first_response, success_code)
    verify_business_code(first_detail_response, success_code)
    first_order_id = PortalOrderHelper.get_order_id(first_response)
    assert first_order_id is not None, "首次提交应返回订单 ID"
    assert PortalOrderHelper.get_order_id(first_detail_response) == first_order_id
    assert PortalOrderHelper.get_order_status(first_detail_response) == expected_status

    second_code = ApiResponseHelper.get_code(second_response)
    assert second_code is not None, f"第二次提交响应缺少业务 code：{second_response}"
    if second_code == success_code:
        second_order_id = PortalOrderHelper.get_order_id(second_response)
        assert second_order_id == first_order_id, (
            f"幂等成功应返回首次订单 ID {first_order_id}，实际为：{second_order_id}"
        )
    else:
        second_message = ApiResponseHelper.get_message(second_response)
        assert second_message, f"第二次提交失败时应返回可解释消息：{second_response}"

    assert isinstance(new_pending_orders, list), (
        f"新增待支付订单查询结果应为列表，实际为：{new_pending_orders}"
    )
    assert len(new_pending_orders) <= maximum_valid_orders, (
        f"重复提交最多生成 {maximum_valid_orders} 笔待支付订单，"
        f"实际为：{new_pending_orders}"
    )
    assert [item.get("order_id") for item in new_pending_orders] == [first_order_id], (
        f"重复提交后的有效订单应只有 {first_order_id}，实际为：{new_pending_orders}"
    )
    assert stock_after_first == stock_after_second, (
        "第二次提交不应再次改变 SKU 库存，"
        f"首次提交后={stock_after_first}，再次提交后={stock_after_second}"
    )
    return first_order_id


def verify_pending_payment_order(
    detail_response,
    database_order,
    *,
    expected_code,
    expected_status,
):
    """校验支付前订单处于待支付状态且尚无支付时间"""
    verify_business_code(detail_response, expected_code)
    order_id = PortalOrderHelper.get_order_id(detail_response)
    assert order_id is not None, "待支付订单详情应包含订单 ID"
    assert PortalOrderHelper.get_order_status(detail_response) == expected_status, (
        f"支付前订单状态应为 {expected_status}，实际为："
        f"{PortalOrderHelper.get_order_status(detail_response)}"
    )
    assert PortalOrderHelper.get_payment_time(detail_response) is None, (
        f"支付前 paymentTime 应为空，实际为：{detail_response}"
    )
    assert isinstance(database_order, dict), (
        f"数据库应存在待支付订单 {order_id}，实际为：{database_order}"
    )
    assert database_order.get("status") == expected_status
    assert database_order.get("payment_time") is None, (
        f"支付前数据库 payment_time 应为空，实际为：{database_order}"
    )
    return order_id


def _verify_payment_related_state_unchanged(
    before_order,
    after_order,
    before_stock,
    after_stock,
):
    unchanged_fields = ("coupon_id", "use_integration", "integration_amount")
    for field in unchanged_fields:
        assert after_order.get(field) == before_order.get(field), (
            f"支付不应改变订单 {field}，支付前={before_order.get(field)}，"
            f"支付后={after_order.get(field)}"
        )
    assert after_stock == before_stock, (
        f"支付不应再次改变 SKU 库存，支付前={before_stock}，支付后={after_stock}"
    )


def verify_payment_success(
    pay_response,
    detail_response,
    before_database_order,
    after_database_order,
    before_stock,
    after_stock,
    *,
    expected_code,
    expected_order_id,
    expected_status,
    expected_pay_type,
):
    """校验支付成功后的订单、金额及关联状态"""
    verify_business_code(pay_response, expected_code)
    verify_business_code(detail_response, expected_code)
    assert isinstance(before_database_order, dict)
    assert isinstance(after_database_order, dict)

    detail_order_id = PortalOrderHelper.get_order_id(detail_response)
    detail_status = PortalOrderHelper.get_order_status(detail_response)
    detail_pay_type = PortalOrderHelper.get_pay_type(detail_response)
    detail_payment_time = PortalOrderHelper.get_payment_time(detail_response)
    detail_pay_amount = _decimal_amount(
        PortalOrderHelper.get_pay_amount(detail_response),
        "支付后订单详情 payAmount",
    )
    assert detail_order_id == expected_order_id
    assert detail_status == expected_status, (
        f"支付后订单状态应为 {expected_status}，实际为：{detail_status}"
    )
    assert detail_pay_type == expected_pay_type, (
        f"支付后 payType 应为 {expected_pay_type}，实际为：{detail_pay_type}"
    )
    assert detail_payment_time is not None, "支付成功后 paymentTime 不应为空"

    assert after_database_order.get("order_id") == expected_order_id
    assert after_database_order.get("status") == expected_status
    assert after_database_order.get("pay_type") == expected_pay_type
    assert after_database_order.get("payment_time") is not None, (
        f"支付成功后数据库 payment_time 不应为空：{after_database_order}"
    )
    database_pay_amount = _decimal_amount(
        after_database_order.get("pay_amount"),
        "支付后数据库 pay_amount",
    )
    assert database_pay_amount == detail_pay_amount, (
        f"支付后接口金额应与数据库一致，接口={detail_pay_amount}，"
        f"数据库={database_pay_amount}"
    )
    _verify_payment_related_state_unchanged(
        before_database_order,
        after_database_order,
        before_stock,
        after_stock,
    )


def verify_repeat_payment_idempotent(
    first_pay_response,
    first_detail_response,
    second_pay_response,
    second_detail_response,
    first_database_order,
    second_database_order,
    first_stock,
    second_stock,
    *,
    success_code,
    expected_order_id,
    expected_status,
):
    """校验重复支付不会产生第二次订单状态或关联数据变更"""
    verify_business_code(first_pay_response, success_code)
    verify_business_code(first_detail_response, success_code)
    verify_business_code(second_detail_response, success_code)
    second_code = ApiResponseHelper.get_code(second_pay_response)
    assert second_code is not None, (
        f"第二次支付响应缺少业务 code：{second_pay_response}"
    )
    if second_code != success_code:
        assert ApiResponseHelper.get_message(second_pay_response), (
            f"第二次支付失败时应返回可解释消息：{second_pay_response}"
        )

    assert isinstance(first_database_order, dict)
    assert isinstance(second_database_order, dict)
    assert first_database_order == second_database_order, (
        "重复支付不应再次修改订单支付状态，"
        f"首次支付后={first_database_order}，再次支付后={second_database_order}"
    )
    assert first_database_order.get("status") == expected_status
    assert first_database_order.get("payment_time") is not None
    assert first_stock == second_stock, (
        f"重复支付不应改变 SKU 库存，首次支付后={first_stock}，"
        f"再次支付后={second_stock}"
    )

    first_detail_id = PortalOrderHelper.get_order_id(first_detail_response)
    second_detail_id = PortalOrderHelper.get_order_id(second_detail_response)
    assert first_detail_id == second_detail_id == expected_order_id
    assert PortalOrderHelper.get_order_status(first_detail_response) == expected_status
    assert PortalOrderHelper.get_order_status(second_detail_response) == expected_status
    assert PortalOrderHelper.get_payment_time(first_detail_response) == (
        PortalOrderHelper.get_payment_time(second_detail_response)
    ), "重复支付不应刷新 paymentTime"
    first_amount = _decimal_amount(
        PortalOrderHelper.get_pay_amount(first_detail_response),
        "首次支付后 payAmount",
    )
    second_amount = _decimal_amount(
        PortalOrderHelper.get_pay_amount(second_detail_response),
        "重复支付后 payAmount",
    )
    assert first_amount == second_amount, (
        f"重复支付前后金额应一致，首次={first_amount}，再次={second_amount}"
    )


def verify_nonexistent_order_payment_rejected(
    before_detail_response,
    pay_response,
    after_detail_response,
    before_database_order,
    after_database_order,
    *,
    detail_code,
    success_code,
    expected_message_keywords,
):
    """校验不存在订单不能被支付且不会创建订单记录"""
    verify_business_code(before_detail_response, detail_code)
    verify_business_code(after_detail_response, detail_code)
    assert PortalOrderHelper.get_order_id(before_detail_response) is None
    assert PortalOrderHelper.get_order_id(after_detail_response) is None
    assert PortalOrderHelper.get_order_items(before_detail_response) == []
    assert PortalOrderHelper.get_order_items(after_detail_response) == []
    verify_business_failure(pay_response, success_code)
    verify_message_contains_any(pay_response, expected_message_keywords)
    assert before_database_order is None, (
        f"支付前不存在订单的数据库记录应为空：{before_database_order}"
    )
    assert after_database_order is None, (
        f"支付后不应创建不存在订单的记录：{after_database_order}"
    )


def verify_canceled_order_payment_ignored(
    pay_response,
    before_detail_response,
    after_detail_response,
    before_database_order,
    after_database_order,
    before_stock,
    after_stock,
    *,
    detail_code,
    success_code,
    expected_order_id,
    expected_status,
):
    """校验已取消订单的支付请求被拒绝或不改变订单状态"""
    verify_business_code(before_detail_response, detail_code)
    verify_business_code(after_detail_response, detail_code)
    pay_code = ApiResponseHelper.get_code(pay_response)
    assert pay_code is not None, f"支付响应缺少业务 code：{pay_response}"
    if pay_code != success_code:
        assert ApiResponseHelper.get_message(pay_response), (
            f"已取消订单支付失败时应返回可解释消息：{pay_response}"
        )

    assert PortalOrderHelper.get_order_id(before_detail_response) == expected_order_id
    assert PortalOrderHelper.get_order_id(after_detail_response) == expected_order_id
    assert PortalOrderHelper.get_order_status(before_detail_response) == expected_status
    assert PortalOrderHelper.get_order_status(after_detail_response) == expected_status
    assert PortalOrderHelper.get_payment_time(before_detail_response) is None
    assert PortalOrderHelper.get_payment_time(after_detail_response) is None
    assert before_database_order == after_database_order, (
        "已取消订单支付后数据库状态不应改变，"
        f"支付前={before_database_order}，支付后={after_database_order}"
    )
    assert isinstance(after_database_order, dict)
    assert after_database_order.get("status") == expected_status
    assert after_database_order.get("payment_time") is None
    assert before_stock == after_stock, (
        f"已取消订单支付不应改变 SKU 库存，支付前={before_stock}，支付后={after_stock}"
    )


def verify_receive_candidate(
    detail_response,
    database_order,
    *,
    expected_code,
    expected_status,
):
    """校验确认收货场景的前台详情和数据库前置状态"""
    verify_business_code(detail_response, expected_code)
    order_id = PortalOrderHelper.get_order_id(detail_response)
    assert order_id is not None, "确认收货场景订单详情应包含订单 ID"
    assert PortalOrderHelper.get_order_status(detail_response) == expected_status, (
        f"确认收货前订单状态应为 {expected_status}，实际为："
        f"{PortalOrderHelper.get_order_status(detail_response)}"
    )
    assert isinstance(database_order, dict), (
        f"数据库应存在确认收货场景订单 {order_id}：{database_order}"
    )
    assert database_order.get("status") == expected_status
    return order_id


def verify_confirm_receive_success(
    confirm_response,
    detail_response,
    before_database_order,
    after_database_order,
    *,
    expected_code,
    expected_order_id,
    expected_status,
):
    """校验确认收货成功后接口详情与数据库状态一致"""
    verify_business_code(confirm_response, expected_code)
    verify_business_code(detail_response, expected_code)
    assert isinstance(before_database_order, dict)
    assert isinstance(after_database_order, dict)
    assert before_database_order.get("receive_time") is None, (
        f"确认收货前 receive_time 应为空：{before_database_order}"
    )

    assert PortalOrderHelper.get_order_id(detail_response) == expected_order_id
    assert PortalOrderHelper.get_order_status(detail_response) == expected_status
    assert PortalOrderHelper.get_receive_time(detail_response) is not None, (
        f"确认收货后前台详情 receiveTime 不应为空：{detail_response}"
    )
    assert after_database_order.get("order_id") == expected_order_id
    assert after_database_order.get("status") == expected_status
    assert after_database_order.get("receive_time") is not None, (
        f"确认收货后数据库 receive_time 不应为空：{after_database_order}"
    )
    assert after_database_order.get("confirm_time") is not None


def verify_repeat_confirm_receive_idempotent(
    first_response,
    first_detail_response,
    second_response,
    second_detail_response,
    first_database_order,
    second_database_order,
    *,
    success_code,
    expected_order_id,
    expected_status,
):
    """校验重复确认收货不重复刷新完成状态及收货时间"""
    verify_business_code(first_response, success_code)
    verify_business_code(first_detail_response, success_code)
    verify_business_code(second_detail_response, success_code)
    second_code = ApiResponseHelper.get_code(second_response)
    assert second_code is not None, f"第二次确认收货响应缺少 code：{second_response}"
    if second_code != success_code:
        assert ApiResponseHelper.get_message(second_response), (
            f"重复确认失败时应返回可解释消息：{second_response}"
        )

    assert isinstance(first_database_order, dict)
    assert first_database_order == second_database_order, (
        "重复确认收货不应再次修改订单，"
        f"首次确认后={first_database_order}，再次确认后={second_database_order}"
    )
    assert first_database_order.get("status") == expected_status
    assert first_database_order.get("receive_time") is not None

    assert PortalOrderHelper.get_order_id(first_detail_response) == expected_order_id
    assert PortalOrderHelper.get_order_id(second_detail_response) == expected_order_id
    assert PortalOrderHelper.get_order_status(first_detail_response) == expected_status
    assert PortalOrderHelper.get_order_status(second_detail_response) == expected_status
    assert PortalOrderHelper.get_receive_time(first_detail_response) == (
        PortalOrderHelper.get_receive_time(second_detail_response)
    ), "重复确认收货不应刷新 receiveTime"


def verify_confirm_receive_rejected(
    confirm_response,
    detail_response,
    before_database_order,
    after_database_order,
    *,
    success_code,
    detail_code,
    expected_order_id,
    expected_status,
    expected_message_keywords,
):
    """校验不允许确认收货的订单被拒绝且状态保持不变"""
    verify_business_failure(confirm_response, success_code)
    verify_message_contains_any(confirm_response, expected_message_keywords)
    verify_business_code(detail_response, detail_code)
    assert before_database_order == after_database_order, (
        "确认收货失败不应修改订单，"
        f"操作前={before_database_order}，操作后={after_database_order}"
    )
    assert isinstance(after_database_order, dict)
    assert after_database_order.get("order_id") == expected_order_id
    assert after_database_order.get("status") == expected_status
    assert after_database_order.get("receive_time") is None
    assert PortalOrderHelper.get_order_id(detail_response) == expected_order_id
    assert PortalOrderHelper.get_order_status(detail_response) == expected_status
    assert PortalOrderHelper.get_receive_time(detail_response) is None


def verify_other_member_confirm_receive_rejected(
    confirm_response,
    detail_response,
    before_database_order,
    after_database_order,
    *,
    success_code,
    detail_code,
    expected_status,
    expected_message_keywords,
):
    """校验当前用户不能确认其他会员订单且数据库状态不变"""
    verify_business_failure(confirm_response, success_code)
    verify_message_contains_any(confirm_response, expected_message_keywords)
    verify_business_code(detail_response, detail_code)
    assert PortalOrderHelper.get_order_id(detail_response) is None, (
        f"当前用户不应读取其他会员订单详情：{detail_response}"
    )
    assert isinstance(before_database_order, dict), (
        f"未找到其他会员待收货订单：{before_database_order}"
    )
    assert before_database_order == after_database_order, (
        "非本人确认收货不应修改订单，"
        f"操作前={before_database_order}，操作后={after_database_order}"
    )
    assert after_database_order.get("status") == expected_status


def verify_other_member_receive_candidate(
    database_order,
    *,
    current_member_username,
    expected_status,
):
    """校验非本人确认收货场景存在其他会员订单"""
    assert isinstance(database_order, dict), (
        f"未找到其他会员状态为 {expected_status} 的订单：{database_order}"
    )
    assert database_order.get("member_username") != current_member_username, (
        f"非本人场景订单不应属于 {current_member_username}：{database_order}"
    )
    assert database_order.get("status") == expected_status
    order_id = database_order.get("order_id")
    assert order_id is not None, f"其他会员订单缺少 order_id：{database_order}"
    return order_id


def verify_stock_changed_after_order_creation(
    before_stock,
    after_stock,
    *,
    expected_quantity,
):
    """校验创建订单后 SKU 库存或锁定库存按数量变化"""
    assert isinstance(before_stock, dict), f"下单前 SKU 库存应存在：{before_stock}"
    assert isinstance(after_stock, dict), f"下单后 SKU 库存应存在：{after_stock}"
    stock_delta = int(before_stock.get("stock") or 0) - int(
        after_stock.get("stock") or 0
    )
    lock_delta = int(after_stock.get("lock_stock") or 0) - int(
        before_stock.get("lock_stock") or 0
    )
    assert stock_delta == expected_quantity or lock_delta == expected_quantity, (
        "创建订单后应扣减库存或增加锁定库存，"
        f"预期数量={expected_quantity}，下单前={before_stock}，下单后={after_stock}"
    )


def verify_order_numbers_unique(order_states):
    """校验连续创建的订单 ID 和订单号唯一"""
    assert isinstance(order_states, list) and len(order_states) >= 2, (
        f"订单唯一性校验至少需要 2 笔订单，实际为：{order_states}"
    )
    order_ids = [order.get("order_id") for order in order_states]
    assert len(order_ids) == len(set(order_ids)), f"订单 ID 应唯一，实际为：{order_ids}"
    order_sns = [order.get("order_sn") for order in order_states]
    assert all(order_sns), f"订单号不应为空，实际为：{order_states}"
    assert len(order_sns) == len(set(order_sns)), f"订单号应唯一，实际为：{order_sns}"


def verify_invalid_payment_rejected(
    pay_response,
    before_detail_response,
    after_detail_response,
    before_database_order,
    after_database_order,
    *,
    success_code,
    expected_order_id,
    expected_status,
    expected_message_keywords,
):
    """校验非法支付方式被拒绝且待支付订单不变"""
    verify_business_code(before_detail_response, success_code)
    verify_business_code(after_detail_response, success_code)
    verify_business_failure(pay_response, success_code)
    verify_message_contains_any(pay_response, expected_message_keywords)
    assert before_database_order == after_database_order, (
        "非法支付不应改变订单数据库状态，"
        f"支付前={before_database_order}，支付后={after_database_order}"
    )
    assert isinstance(after_database_order, dict)
    assert after_database_order.get("order_id") == expected_order_id
    assert after_database_order.get("status") == expected_status
    assert after_database_order.get("payment_time") is None
    assert PortalOrderHelper.get_order_id(after_detail_response) == expected_order_id
    assert PortalOrderHelper.get_order_status(after_detail_response) == expected_status
    assert PortalOrderHelper.get_payment_time(after_detail_response) is None


def verify_order_status_transition(
    detail_response,
    database_order,
    *,
    expected_code,
    expected_order_id,
    expected_status,
    required_time_field=None,
):
    """校验订单详情和数据库进入预期状态"""
    verify_business_code(detail_response, expected_code)
    assert PortalOrderHelper.get_order_id(detail_response) == expected_order_id
    assert PortalOrderHelper.get_order_status(detail_response) == expected_status
    assert isinstance(database_order, dict), (
        f"数据库应存在订单 {expected_order_id}，实际为：{database_order}"
    )
    assert database_order.get("order_id") == expected_order_id
    assert database_order.get("status") == expected_status

    if required_time_field is None:
        return

    api_time_getters = {
        "payment_time": PortalOrderHelper.get_payment_time,
        "delivery_time": PortalOrderHelper.get_delivery_time,
        "receive_time": PortalOrderHelper.get_receive_time,
    }
    assert database_order.get(required_time_field) is not None, (
        f"订单状态 {expected_status} 应写入 {required_time_field}：{database_order}"
    )
    api_time_getter = api_time_getters.get(required_time_field)
    if api_time_getter is not None:
        assert api_time_getter(detail_response) is not None, (
            f"订单详情应返回 {required_time_field} 对应时间：{detail_response}"
        )


def verify_order_cancel_success(
    cancel_response,
    detail_response,
    before_database_order,
    after_database_order,
    *,
    expected_code,
    expected_order_id,
    expected_status,
):
    """校验待支付订单取消后进入已取消状态"""
    verify_business_code(cancel_response, expected_code)
    verify_order_status_transition(
        detail_response,
        after_database_order,
        expected_code=expected_code,
        expected_order_id=expected_order_id,
        expected_status=expected_status,
    )
    assert isinstance(before_database_order, dict)
    assert before_database_order.get("order_id") == expected_order_id
    assert before_database_order.get("payment_time") is None, (
        f"取消前待支付订单 payment_time 应为空：{before_database_order}"
    )
    assert after_database_order.get("payment_time") is None, (
        f"取消后订单不应写入 payment_time：{after_database_order}"
    )
