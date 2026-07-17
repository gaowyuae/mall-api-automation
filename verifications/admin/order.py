from api_support.admin.order_helper import AdminOrderHelper
from api_support.common.response_helper import ApiResponseHelper
from api_support.portal.order_helper import PortalOrderHelper
from verifications.common.response import (
    verify_business_code,
    verify_business_failure,
    verify_message_contains_any,
)


def verify_delivery_candidate(
    database_order,
    expected_status,
):
    """校验数据库订单可作为待发货或状态异常场景的前置订单"""
    assert isinstance(database_order, dict), (
        f"未找到状态为 {expected_status} 的发货场景订单：{database_order}"
    )
    order_id = database_order.get("order_id")
    assert order_id is not None, f"发货场景订单缺少 order_id：{database_order}"
    assert database_order.get("status") == expected_status, (
        f"发货前订单状态应为 {expected_status}，实际为：{database_order}"
    )
    return order_id


def verify_delivery_required_parameter_error(
    error,
    expected_field,
):
    """校验后台发货封装报告必填参数缺失"""
    assert isinstance(error, AssertionError), (
        f"缺少 {expected_field} 时应触发 AssertionError，实际为：{type(error).__name__}"
    )
    assert expected_field in str(error), (
        f"发货参数错误应包含字段 {expected_field}，实际为：{error}"
    )


def verify_delivery_state_unchanged(
    before_database_order,
    after_database_order,
    expected_status,
):
    """校验发货失败后订单状态和物流字段均未改变"""
    assert isinstance(before_database_order, dict), (
        f"发货前数据库订单应为字典：{before_database_order}"
    )
    assert before_database_order == after_database_order, (
        "发货失败不应改变订单，"
        f"操作前={before_database_order}，操作后={after_database_order}"
    )
    assert before_database_order.get("status") == expected_status


def verify_delivery_success(
    delivery_response,
    admin_detail_response,
    portal_detail_response,
    database_order,
    *,
    expected_code,
    expected_order_id,
    expected_status,
    expected_delivery_company,
    expected_delivery_sn,
):
    """校验发货响应、前后台详情和数据库物流字段一致"""
    verify_business_code(delivery_response, expected_code)
    verify_business_code(admin_detail_response, expected_code)
    verify_business_code(portal_detail_response, expected_code)

    admin_state = AdminOrderHelper.get_delivery_state(admin_detail_response)
    assert admin_state["id"] == expected_order_id
    assert admin_state["status"] == expected_status, (
        f"后台订单状态应为 {expected_status}，实际为：{admin_state}"
    )
    assert admin_state["deliveryCompany"] == expected_delivery_company
    assert admin_state["deliverySn"] == expected_delivery_sn
    assert admin_state["deliveryTime"] is not None, (
        f"后台订单发货时间不应为空：{admin_state}"
    )

    assert PortalOrderHelper.get_order_id(portal_detail_response) == expected_order_id
    assert PortalOrderHelper.get_order_status(portal_detail_response) == expected_status
    assert (
        PortalOrderHelper.get_delivery_company(portal_detail_response)
        == expected_delivery_company
    )
    assert PortalOrderHelper.get_delivery_sn(portal_detail_response) == (
        expected_delivery_sn
    )
    assert PortalOrderHelper.get_delivery_time(portal_detail_response) is not None

    assert isinstance(database_order, dict), (
        f"数据库应存在已发货订单 {expected_order_id}：{database_order}"
    )
    assert database_order.get("order_id") == expected_order_id
    assert database_order.get("status") == expected_status
    assert database_order.get("delivery_company") == expected_delivery_company
    assert database_order.get("delivery_sn") == expected_delivery_sn
    assert database_order.get("delivery_time") is not None


def verify_delivery_rejected(
    delivery_response,
    admin_detail_response,
    before_database_order,
    after_database_order,
    *,
    success_code,
    detail_code,
    expected_status,
    expected_message_keywords,
):
    """校验非待发货订单被拒绝且订单物流状态保持不变"""
    verify_business_failure(delivery_response, success_code)
    verify_message_contains_any(delivery_response, expected_message_keywords)
    verify_business_code(admin_detail_response, detail_code)
    verify_delivery_state_unchanged(
        before_database_order,
        after_database_order,
        expected_status,
    )
    admin_state = AdminOrderHelper.get_delivery_state(admin_detail_response)
    assert admin_state["status"] == expected_status
    assert admin_state["deliveryCompany"] == before_database_order.get(
        "delivery_company"
    )
    assert admin_state["deliverySn"] == before_database_order.get("delivery_sn")
    assert admin_state["deliveryTime"] == before_database_order.get("delivery_time")


def verify_admin_completed_order(
    admin_detail_response,
    database_order,
    *,
    expected_code,
    expected_order_id,
    expected_status,
):
    """校验后台详情和数据库均显示订单已完成"""
    verify_business_code(admin_detail_response, expected_code)
    admin_state = AdminOrderHelper.get_delivery_state(admin_detail_response)
    assert admin_state["id"] == expected_order_id
    assert admin_state["status"] == expected_status
    assert admin_state["receiveTime"] is not None, (
        f"后台已完成订单 receiveTime 不应为空：{admin_state}"
    )
    assert isinstance(database_order, dict)
    assert database_order.get("order_id") == expected_order_id
    assert database_order.get("status") == expected_status
    assert database_order.get("receive_time") is not None


def verify_nonexistent_delivery_rejected(
    delivery_response,
    before_database_order,
    after_database_order,
    *,
    success_code,
    expected_message_keywords,
):
    """校验不存在订单不能被发货且数据库无记录新增"""
    assert before_database_order is None, (
        f"发货前不存在订单的数据库记录应为空：{before_database_order}"
    )
    assert after_database_order is None, (
        f"发货后不应创建不存在订单的记录：{after_database_order}"
    )
    verify_business_failure(delivery_response, success_code)
    verify_message_contains_any(delivery_response, expected_message_keywords)


def verify_repeat_delivery_stable(
    first_database_order,
    repeat_response,
    repeat_admin_detail,
    second_database_order,
    *,
    success_code,
    expected_status,
):
    """校验重复发货不会再次修改已发货订单"""
    assert isinstance(first_database_order, dict), (
        f"首次发货后的数据库订单应存在：{first_database_order}"
    )
    assert isinstance(second_database_order, dict), (
        f"重复发货后的数据库订单应存在：{second_database_order}"
    )
    repeat_code = ApiResponseHelper.get_code(repeat_response)
    assert repeat_code is not None, f"重复发货响应缺少业务 code：{repeat_response}"
    if repeat_code != success_code:
        assert ApiResponseHelper.get_message(repeat_response), (
            f"重复发货失败时应返回可解释消息：{repeat_response}"
        )

    assert first_database_order == second_database_order, (
        "重复发货不应修改订单状态或物流字段，"
        f"首次发货后={first_database_order}，重复发货后={second_database_order}"
    )
    assert second_database_order.get("status") == expected_status
    verify_business_code(repeat_admin_detail, success_code)
    admin_state = AdminOrderHelper.get_delivery_state(repeat_admin_detail)
    assert admin_state["status"] == expected_status
    assert admin_state["deliveryCompany"] == first_database_order.get(
        "delivery_company"
    )
    assert admin_state["deliverySn"] == first_database_order.get("delivery_sn")
    assert admin_state["deliveryTime"] == first_database_order.get("delivery_time")


def verify_delivery_permission_rejected(
    error,
    delivery_response,
    before_database_order,
    after_database_order,
    *,
    expected_http_status,
    success_code,
    expected_status,
    expected_message_keywords,
):
    """校验前台 token 调后台发货被拒绝且订单不变"""
    verify_delivery_state_unchanged(
        before_database_order,
        after_database_order,
        expected_status,
    )
    if error is not None:
        error_text = str(error)
        normalized_text = error_text.casefold()
        normalized_keywords = [
            str(keyword).casefold() for keyword in expected_message_keywords
        ]
        assert str(expected_http_status) in error_text or any(
            keyword in normalized_text for keyword in normalized_keywords
        ), f"权限错误应包含 HTTP {expected_http_status} 或权限关键词，实际为：{error}"
        return

    assert delivery_response is not None, "权限错误应返回业务失败响应或 HTTP 拦截异常"
    verify_business_failure(delivery_response, success_code)
    verify_message_contains_any(delivery_response, expected_message_keywords)
