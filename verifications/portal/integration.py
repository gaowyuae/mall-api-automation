from decimal import Decimal, InvalidOperation

from api_support.common.response_helper import ApiResponseHelper
from api_support.portal.member_helper import PortalMemberHelper
from api_support.portal.order_helper import PortalOrderHelper
from verifications.common.response import (
    verify_business_code,
    verify_business_failure,
    verify_message_contains_any,
)
from verifications.portal.order import verify_latest_order_unchanged


def _decimal(value, field_name):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise AssertionError(f"{field_name} 应为有效金额，实际为：{value}") from exc


def verify_member_integration(
    response,
    expected_code,
    expected_integration = None,
    minimum_integration = None,
):
    """校验会员积分接口并返回当前积分"""
    verify_business_code(response, expected_code)
    integration = PortalMemberHelper.get_integration(response)
    assert isinstance(integration, int), f"会员积分应为整数，实际为：{integration}"
    if expected_integration is not None:
        assert integration == expected_integration, (
            f"场景前置积分应为 {expected_integration}，实际为 {integration}；"
            "请检查积分测试数据准备"
        )
    if minimum_integration is not None:
        assert integration >= minimum_integration, (
            f"场景前置积分至少为 {minimum_integration}，实际为 {integration}；"
            "请检查积分测试数据准备"
        )
    return integration


def verify_confirm_integration_rule(
    confirm_response,
    expected_code,
    expected_member_integration,
    expected_deduction_per_amount,
):
    """校验确认单积分余额与抵扣比例规则"""
    verify_business_code(confirm_response, expected_code)
    actual_integration = PortalOrderHelper.get_confirm_member_integration(
        confirm_response
    )
    assert actual_integration == expected_member_integration, (
        f"确认单会员积分应为 {expected_member_integration}，"
        f"实际为：{actual_integration}"
    )
    setting = PortalOrderHelper.get_confirm_integration_setting(confirm_response)
    assert isinstance(setting, dict), f"确认单积分规则应为字典，实际为：{setting}"
    assert setting.get("deductionPerAmount") == expected_deduction_per_amount, (
        f"每 1 元抵扣积分应为 {expected_deduction_per_amount}，"
        f"实际为：{setting.get('deductionPerAmount')}"
    )
    return setting


def verify_integration_balance_change(
    before_response,
    after_response,
    expected_use_integration,
):
    """校验下单前后会员积分按使用值扣减"""
    before = PortalMemberHelper.get_integration(before_response)
    after = PortalMemberHelper.get_integration(after_response)
    assert isinstance(before, int) and isinstance(after, int), (
        f"会员积分应为整数，操作前={before}，操作后={after}"
    )
    assert after == before - expected_use_integration, (
        f"使用 {expected_use_integration} 积分后余额应为 "
        f"{before - expected_use_integration}，实际为：{after}"
    )


def verify_integration_order(
    generate_response,
    detail_response,
    database_order,
    expected_code,
    expected_use_integration,
    expected_integration_amount,
    expected_total_amount,
):
    """校验积分订单接口详情和数据库金额一致"""
    verify_business_code(generate_response, expected_code)
    verify_business_code(detail_response, expected_code)
    generated_order = PortalOrderHelper.get_order(generate_response)
    detail_order = PortalOrderHelper.get_order(detail_response)
    order_id = generated_order.get("id")
    assert order_id is not None, f"创建订单响应缺少订单 ID：{generated_order}"
    assert detail_order.get("id") == order_id, (
        f"订单详情 ID 应为 {order_id}，实际为：{detail_order.get('id')}"
    )

    amounts = PortalOrderHelper.get_order_amounts(detail_response)
    actual_amount = _decimal(amounts["integrationAmount"] or 0, "订单积分抵扣金额")
    expected_amount = _decimal(expected_integration_amount, "预期积分抵扣金额")
    assert actual_amount == expected_amount, (
        f"积分抵扣金额应为 {expected_amount}，实际为：{actual_amount}"
    )
    actual_use = amounts["useIntegration"] or 0
    assert actual_use == expected_use_integration, (
        f"订单 useIntegration 应为 {expected_use_integration}，实际为：{actual_use}"
    )
    total_amount = _decimal(amounts["totalAmount"], "订单商品总金额")
    expected_total = _decimal(expected_total_amount, "预期商品总金额")
    assert total_amount == expected_total, (
        f"订单商品总金额应为 {expected_total}，实际为：{total_amount}"
    )
    freight = _decimal(amounts["freightAmount"] or 0, "订单运费")
    promotion = _decimal(amounts["promotionAmount"] or 0, "订单促销金额")
    coupon = _decimal(amounts["couponAmount"] or 0, "订单优惠券金额")
    discount = _decimal(amounts["discountAmount"] or 0, "订单管理员优惠金额")
    expected_pay = total_amount + freight - promotion - coupon
    expected_pay -= actual_amount + discount
    pay_amount = _decimal(amounts["payAmount"], "订单应付金额")
    assert pay_amount == expected_pay, (
        f"订单应付金额应为 {expected_pay}，实际为：{pay_amount}"
    )
    assert pay_amount >= 0, f"订单应付金额不能为负数，实际为：{pay_amount}"

    assert isinstance(database_order, dict), f"数据库未找到订单 {order_id}"
    assert database_order.get("order_id") == order_id, (
        f"数据库订单 ID 应为 {order_id}，实际为：{database_order}"
    )
    assert (database_order.get("use_integration") or 0) == expected_use_integration
    assert (
        _decimal(
            database_order.get("integration_amount") or 0,
            "数据库积分抵扣金额",
        )
        == expected_amount
    )
    assert _decimal(database_order.get("pay_amount"), "数据库应付金额") == (pay_amount)
    return order_id


def verify_integration_history_change(
    before_state,
    after_state,
    expected_increment,
    expected_change_count = None,
):
    """校验积分流水数量及最新变动值"""
    before_count = before_state.get("history_count") or 0
    after_count = after_state.get("history_count") or 0
    assert after_count - before_count == expected_increment, (
        f"积分流水应新增 {expected_increment} 条，操作前={before_count}，"
        f"操作后={after_count}"
    )
    if expected_change_count is not None:
        assert after_state.get("change_count") == expected_change_count, (
            f"最新积分流水 change_count 应为 {expected_change_count}，"
            f"实际为：{after_state.get('change_count')}"
        )


def verify_integration_unchanged(
    before_member_response,
    after_member_response,
    before_history,
    after_history,
):
    """校验失败下单没有扣减积分或新增积分流水"""
    before = PortalMemberHelper.get_integration(before_member_response)
    after = PortalMemberHelper.get_integration(after_member_response)
    assert after == before, (
        f"下单失败后积分余额不应改变，操作前={before}，操作后={after}"
    )
    assert after_history == before_history, (
        f"下单失败后积分流水不应改变，操作前={before_history}，操作后={after_history}"
    )


def verify_excessive_integration_handling(
    generate_response,
    detail_response,
    before_member_response,
    after_member_response,
    before_order,
    after_order,
    database_order,
    before_history,
    after_history,
    requested_integration,
    success_code,
    expected_message_keywords,
):
    """校验超量积分请求被拒绝或按规则安全截断"""
    actual_code = ApiResponseHelper.get_code(generate_response)
    assert actual_code is not None, f"创建订单响应缺少业务 code：{generate_response}"
    if actual_code != success_code:
        verify_business_failure(generate_response, success_code)
        verify_message_contains_any(generate_response, expected_message_keywords)
        verify_latest_order_unchanged(before_order, after_order)
        verify_integration_unchanged(
            before_member_response,
            after_member_response,
            before_history,
            after_history,
        )
        return

    verify_business_code(detail_response, success_code)
    order = PortalOrderHelper.get_order(detail_response)
    order_id = order.get("id")
    assert order_id is not None, f"截断积分后创建的订单缺少 ID：{order}"
    assert (after_order or {}).get("order_id") == order_id, (
        f"最新订单 ID 应为 {order_id}，实际为：{after_order}"
    )

    before_integration = PortalMemberHelper.get_integration(before_member_response)
    after_integration = PortalMemberHelper.get_integration(after_member_response)
    assert isinstance(before_integration, int), (
        f"下单前会员积分应为整数，实际为：{before_integration}"
    )
    used_integration = order.get("useIntegration") or 0
    assert 0 <= used_integration <= before_integration, (
        f"实际使用积分不能超过余额 {before_integration}，实际为：{used_integration}"
    )
    assert used_integration <= requested_integration, (
        f"实际使用积分不能超过请求值 {requested_integration}，实际为："
        f"{used_integration}"
    )
    assert after_integration == before_integration - used_integration, (
        f"截断后积分余额应为 {before_integration - used_integration}，"
        f"实际为：{after_integration}"
    )
    pay_amount = _decimal(order.get("payAmount"), "截断积分订单应付金额")
    assert pay_amount >= 0, f"截断积分后的应付金额不能为负数，实际为：{pay_amount}"

    assert isinstance(database_order, dict), f"数据库未找到订单 {order_id}"
    assert database_order.get("order_id") == order_id
    assert (database_order.get("use_integration") or 0) == used_integration
    expected_increment = 1 if used_integration else 0
    expected_change = -used_integration if used_integration else None
    verify_integration_history_change(
        before_history,
        after_history,
        expected_increment=expected_increment,
        expected_change_count=expected_change,
    )
