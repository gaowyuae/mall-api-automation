from decimal import Decimal, InvalidOperation

from api_support.portal.coupon_helper import PortalCouponHelper
from api_support.portal.order_helper import PortalOrderHelper
from verifications.common.response import verify_business_code


def _decimal(value, field_name):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise AssertionError(f"{field_name} 应为有效金额，实际为：{value}") from exc


def _verify_coupon_list(response, expected_code, list_name):
    verify_business_code(response, expected_code)
    coupons = PortalCouponHelper.get_coupon_list(response)
    assert isinstance(coupons, list), f"{list_name} data 应为列表，实际为：{coupons}"
    return coupons


def verify_coupon_query_responses(
    coupon_response,
    history_response,
    product_response,
    expected_code,
):
    """校验优惠券列表、历史及商品维度查询均成功且结构正确"""
    _verify_coupon_list(coupon_response, expected_code, "用户优惠券列表")
    _verify_coupon_list(history_response, expected_code, "用户优惠券历史")
    _verify_coupon_list(product_response, expected_code, "商品可领优惠券列表")


def verify_owned_coupon_query_consistency(
    coupon_response,
    history_response,
    coupon_history_id,
    expected_use_status,
):
    """校验当前用户的优惠券定义和领取历史状态一致"""
    history = PortalCouponHelper.find_coupon_history(
        history_response,
        coupon_history_id,
    )
    assert isinstance(history, dict), (
        f"当前用户未找到优惠券历史 ID={coupon_history_id}，请检查场景数据准备"
    )
    assert history.get("useStatus") == expected_use_status, (
        f"优惠券历史 {coupon_history_id} useStatus 应为 {expected_use_status}，"
        f"实际为：{history.get('useStatus')}"
    )

    coupon_id = history.get("couponId")
    coupon = PortalCouponHelper.find_coupon(coupon_response, coupon_id)
    assert isinstance(coupon, dict), (
        f"优惠券列表未找到历史 {coupon_history_id} 对应的 couponId={coupon_id}"
    )
    return history, coupon


def verify_coupon_not_owned(history_response, coupon_history_id):
    """校验当前用户的优惠券历史中不存在目标领取记录"""
    history = PortalCouponHelper.find_coupon_history(
        history_response,
        coupon_history_id,
    )
    assert history is None, (
        f"非本人优惠券历史 {coupon_history_id} 不应出现在当前用户列表：{history}"
    )


def verify_foreign_coupon_history(
    database_history,
    current_member_username,
    coupon_history_reference,
):
    """校验数据库引用对应其他用户的优惠券并返回数值历史 ID"""
    assert isinstance(database_history, dict), (
        f"数据库未找到非本人优惠券引用 {coupon_history_reference}，"
        "请检查优惠券场景数据准备"
    )
    owner_username = database_history.get("member_username")
    assert owner_username != current_member_username, (
        f"优惠券引用 {coupon_history_reference} 应属于其他用户，"
        f"实际属于：{owner_username}"
    )
    coupon_history_id = database_history.get("id")
    assert isinstance(coupon_history_id, int), (
        f"非本人优惠券历史 ID 应为整数，实际为：{coupon_history_id}"
    )
    return coupon_history_id


def verify_confirm_coupon_availability(
    confirm_response,
    coupon_history_id,
    expected_available,
    expected_code,
):
    """校验指定用户优惠券是否出现在订单确认单可用列表"""
    verify_business_code(confirm_response, expected_code)
    confirm_data = PortalOrderHelper.get_confirm_data(confirm_response)
    assert isinstance(confirm_data, dict), (
        f"订单确认单 data 应为字典，实际为：{confirm_data}"
    )
    details = PortalOrderHelper.get_confirm_coupon_details(confirm_response)
    assert isinstance(details, list), f"订单确认单优惠券明细应为列表，实际为：{details}"
    detail = PortalCouponHelper.find_confirm_coupon_detail(
        confirm_data,
        coupon_history_id,
    )
    if expected_available:
        assert isinstance(detail, dict), (
            f"优惠券历史 {coupon_history_id} 应在确认单中可用，实际列表为：{details}"
        )
    else:
        assert detail is None, (
            f"优惠券历史 {coupon_history_id} 不应在确认单中可用：{detail}"
        )
    return detail


def verify_coupon_threshold_boundary(
    coupon,
    expected_threshold,
    actual_order_amount,
):
    """校验优惠券门槛与订单金额正好相差 0.01"""
    actual_threshold = _decimal(coupon.get("minPoint"), "优惠券使用门槛")
    threshold = _decimal(expected_threshold, "预期优惠券使用门槛")
    order_amount = _decimal(actual_order_amount, "订单商品金额")
    assert actual_threshold == threshold, (
        f"优惠券使用门槛应为 {threshold}，实际为：{actual_threshold}"
    )
    assert threshold - order_amount == Decimal("0.01"), (
        f"订单金额应比优惠券门槛少 0.01，门槛={threshold}，订单金额={order_amount}"
    )


def verify_coupon_threshold_satisfied(
    coupon,
    expected_threshold,
    actual_order_amount,
):
    """校验订单金额已达到优惠券使用门槛"""
    actual_threshold = _decimal(coupon.get("minPoint"), "优惠券使用门槛")
    threshold = _decimal(expected_threshold, "预期优惠券使用门槛")
    order_amount = _decimal(actual_order_amount, "订单商品金额")
    assert actual_threshold == threshold, (
        f"优惠券使用门槛应为 {threshold}，实际为：{actual_threshold}"
    )
    assert order_amount >= threshold, (
        f"订单金额应达到优惠券门槛，门槛={threshold}，订单金额={order_amount}"
    )


def verify_coupon_order_discount(
    generate_response,
    detail_response,
    confirm_coupon_detail,
    database_order,
    database_coupon_history,
    expected_code,
    expected_used_status,
    expected_total_amount,
):
    """校验优惠券订单接口、数据库金额及使用状态一致"""
    verify_business_code(generate_response, expected_code)
    verify_business_code(detail_response, expected_code)
    generated_order = PortalOrderHelper.get_order(generate_response)
    detail_order = PortalOrderHelper.get_order(detail_response)
    order_id = generated_order.get("id")
    assert order_id is not None, f"创建订单响应缺少订单 ID：{generated_order}"
    assert detail_order.get("id") == order_id, (
        f"订单详情 ID 应为 {order_id}，实际为：{detail_order.get('id')}"
    )

    coupon = PortalCouponHelper.get_detail_coupon(confirm_coupon_detail)
    assert isinstance(coupon, dict), (
        f"确认单优惠券明细缺少 coupon：{confirm_coupon_detail}"
    )
    expected_coupon_id = coupon.get("id")
    expected_coupon_amount = _decimal(coupon.get("amount"), "确认单优惠券金额")
    assert expected_coupon_amount > 0, (
        f"确认单优惠券抵扣金额应大于 0，实际为：{expected_coupon_amount}"
    )

    amounts = PortalOrderHelper.get_order_amounts(detail_response)
    actual_coupon_amount = _decimal(amounts["couponAmount"], "订单优惠券金额")
    assert actual_coupon_amount == expected_coupon_amount, (
        f"订单优惠券金额应为 {expected_coupon_amount}，实际为：{actual_coupon_amount}"
    )
    assert str(amounts["couponId"]) == str(expected_coupon_id), (
        f"订单 couponId 应为 {expected_coupon_id}，实际为：{amounts['couponId']}"
    )

    total = _decimal(amounts["totalAmount"], "订单商品总金额")
    expected_total = _decimal(expected_total_amount, "预期商品总金额")
    assert total == expected_total, (
        f"订单商品总金额应为 {expected_total}，实际为：{total}"
    )
    freight = _decimal(amounts["freightAmount"] or 0, "订单运费")
    promotion = _decimal(amounts["promotionAmount"] or 0, "订单促销金额")
    integration = _decimal(amounts["integrationAmount"] or 0, "订单积分金额")
    discount = _decimal(amounts["discountAmount"] or 0, "订单管理员优惠金额")
    expected_pay = total + freight - promotion - actual_coupon_amount
    expected_pay -= integration + discount
    actual_pay = _decimal(amounts["payAmount"], "订单应付金额")
    assert actual_pay == expected_pay, (
        f"订单应付金额应为 {expected_pay}，实际为：{actual_pay}"
    )

    assert isinstance(database_order, dict), f"数据库未找到订单 {order_id}"
    assert database_order.get("order_id") == order_id, (
        f"数据库订单 ID 应为 {order_id}，实际为：{database_order}"
    )
    assert str(database_order.get("coupon_id")) == str(expected_coupon_id), (
        f"数据库 coupon_id 应为 {expected_coupon_id}，实际为：{database_order}"
    )
    assert _decimal(database_order.get("coupon_amount"), "数据库优惠券金额") == (
        actual_coupon_amount
    )
    assert _decimal(database_order.get("pay_amount"), "数据库应付金额") == actual_pay

    assert isinstance(database_coupon_history, dict), "数据库未找到已使用的优惠券历史"
    assert database_coupon_history.get("use_status") == expected_used_status, (
        f"优惠券历史 use_status 应为 {expected_used_status}，"
        f"实际为：{database_coupon_history}"
    )
    assert database_coupon_history.get("order_id") == order_id, (
        f"优惠券历史 order_id 应为 {order_id}，实际为："
        f"{database_coupon_history.get('order_id')}"
    )
    return order_id


def verify_coupon_history_unchanged(
    before_state,
    after_state,
    coupon_history_id,
):
    """校验失败下单没有改变优惠券历史状态"""
    assert after_state == before_state, (
        f"优惠券历史 {coupon_history_id} 在下单失败后不应改变，"
        f"操作前={before_state}，操作后={after_state}"
    )
