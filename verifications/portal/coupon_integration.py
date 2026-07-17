from decimal import Decimal, InvalidOperation

from api_support.portal.order_helper import PortalOrderHelper
from verifications.portal.coupon import verify_coupon_order_discount
from verifications.portal.integration import (
    verify_integration_balance_change,
    verify_integration_history_change,
    verify_integration_order,
)


def _decimal(value, field_name):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise AssertionError(f"{field_name} 应为有效金额，实际为：{value}") from exc


def verify_coupon_integration_candidate(
    database_history,
    *,
    member_username,
    expected_coupon_amount,
    expected_minimum_amount,
    expected_use_type,
    expected_use_status,
):
    """校验组合优惠场景存在当前会员可用的目标优惠券历史"""
    assert isinstance(database_history, dict), (
        "未找到当前有效的组合优惠券，请检查优惠券测试数据准备"
    )
    assert database_history.get("member_username") == member_username
    assert database_history.get("use_status") == expected_use_status
    assert database_history.get("use_time") is None
    assert database_history.get("order_id") is None
    assert _decimal(database_history.get("coupon_amount"), "优惠券金额") == (
        _decimal(expected_coupon_amount, "预期优惠券金额")
    )
    assert _decimal(database_history.get("min_point"), "优惠券使用门槛") == (
        _decimal(expected_minimum_amount, "预期优惠券使用门槛")
    )
    assert database_history.get("use_type") == expected_use_type
    history_id = database_history.get("id")
    assert isinstance(history_id, int), (
        f"组合优惠券历史 ID 应为整数，实际为：{history_id}"
    )
    return history_id


def verify_coupon_integration_order(
    generate_response,
    detail_response,
    before_member_response,
    after_member_response,
    before_integration_history,
    after_integration_history,
    *,
    confirm_coupon_detail,
    database_order,
    database_coupon_history,
    expected_code,
    expected_used_status,
    expected_total_amount,
    expected_coupon_amount,
    expected_use_integration,
    expected_integration_amount,
    expected_pay_amount,
    expected_history_increment,
    expected_history_change_count,
):
    """校验优惠券后使用积分的接口、余额、流水和数据库金额一致"""
    coupon_order_id = verify_coupon_order_discount(
        generate_response,
        detail_response,
        confirm_coupon_detail=confirm_coupon_detail,
        database_order=database_order,
        database_coupon_history=database_coupon_history,
        expected_code=expected_code,
        expected_used_status=expected_used_status,
        expected_total_amount=expected_total_amount,
    )
    integration_order_id = verify_integration_order(
        generate_response,
        detail_response,
        database_order=database_order,
        expected_code=expected_code,
        expected_use_integration=expected_use_integration,
        expected_integration_amount=expected_integration_amount,
        expected_total_amount=expected_total_amount,
    )
    assert coupon_order_id == integration_order_id, (
        f"优惠券与积分校验的订单 ID 应一致，优惠券={coupon_order_id}，"
        f"积分={integration_order_id}"
    )

    verify_integration_balance_change(
        before_member_response,
        after_member_response,
        expected_use_integration=expected_use_integration,
    )
    verify_integration_history_change(
        before_integration_history,
        after_integration_history,
        expected_increment=expected_history_increment,
        expected_change_count=expected_history_change_count,
    )

    amounts = PortalOrderHelper.get_order_amounts(detail_response)
    actual_coupon_amount = _decimal(
        amounts["couponAmount"] or 0,
        "组合优惠订单 couponAmount",
    )
    actual_integration_amount = _decimal(
        amounts["integrationAmount"] or 0,
        "组合优惠订单 integrationAmount",
    )
    actual_pay_amount = _decimal(
        amounts["payAmount"],
        "组合优惠订单 payAmount",
    )
    assert actual_coupon_amount == _decimal(
        expected_coupon_amount,
        "预期优惠券金额",
    )
    assert actual_integration_amount == _decimal(
        expected_integration_amount,
        "预期积分抵扣金额",
    )
    assert actual_pay_amount == _decimal(expected_pay_amount, "预期应付金额"), (
        f"先券后积分的应付金额应为 {expected_pay_amount}，实际为：{actual_pay_amount}"
    )
    return coupon_order_id
