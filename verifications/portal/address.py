from api_support.portal.address_helper import PortalAddressHelper
from verifications.common.response import verify_business_code


def _extract_addresses(response, expected_code):
    verify_business_code(response, expected_code)
    addresses = PortalAddressHelper.get_addresses(response)
    assert isinstance(addresses, list), f"收货地址 data 应为列表，实际为：{addresses}"
    return addresses


def verify_default_address(
    response,
    expected_code,
    expected_default_status,
    required_fields,
):
    """校验地址列表返回字段完整的默认收货地址"""
    _extract_addresses(response, expected_code)
    address = PortalAddressHelper.find_default_address_in_response(
        response,
        default_status=expected_default_status,
    )
    assert address is not None, (
        f"地址列表中未找到 defaultStatus={expected_default_status} 的默认地址"
    )

    missing_fields = [field for field in required_fields if field not in address]
    assert not missing_fields, f"默认地址缺少字段 {missing_fields}：{address}"
    empty_fields = [
        field for field in required_fields if address.get(field) in (None, "")
    ]
    assert not empty_fields, f"默认地址字段不能为空 {empty_fields}：{address}"
    return address


def verify_address_list_empty(
    response,
    expected_code,
    expected_count=0,
):
    """校验当前会员的收货地址列表为空"""
    addresses = _extract_addresses(response, expected_code)
    assert len(addresses) == expected_count, (
        f"收货地址数量应为 {expected_count}，实际为：{len(addresses)}，"
        f"地址列表：{addresses}"
    )


def verify_database_address_count(
    actual_count,
    expected_count,
    member_username,
):
    """校验数据库中的会员收货地址数量"""
    assert actual_count == expected_count, (
        f"会员 {member_username} 的数据库地址数量应为 {expected_count}，"
        f"实际为：{actual_count}"
    )


def verify_default_address_database_consistency(
    address,
    database_address,
    expected_default_status,
):
    """校验接口默认地址与数据库默认地址一致"""
    assert isinstance(database_address, dict), "数据库中未找到当前会员的默认地址"
    assert str(address.get("id")) == str(database_address.get("address_id")), (
        f"默认地址 ID 不一致，接口为 {address.get('id')}，"
        f"数据库为 {database_address.get('address_id')}"
    )
    assert str(address.get("defaultStatus")) == str(expected_default_status), (
        f"接口默认状态应为 {expected_default_status}，"
        f"实际为：{address.get('defaultStatus')}"
    )
    assert str(database_address.get("default_status")) == str(
        expected_default_status
    ), (
        f"数据库默认状态应为 {expected_default_status}，"
        f"实际为：{database_address.get('default_status')}"
    )
    assert str(address.get("phoneNumber")) == str(
        database_address.get("phone_number")
    ), "接口手机号与数据库默认地址手机号不一致"
    assert str(address.get("detailAddress")) == str(
        database_address.get("detail_address")
    ), "接口详细地址与数据库默认地址不一致"


def verify_foreign_address(
    database_address,
    *,
    current_member_username,
    address_id,
):
    """校验目标地址属于其他会员"""
    assert isinstance(database_address, dict), (
        f"数据库未找到收货地址 {address_id}，请检查地址测试数据"
    )
    assert str(database_address.get("address_id")) == str(address_id), (
        f"数据库地址 ID 应为 {address_id}，实际为：{database_address}"
    )
    owner_username = database_address.get("member_username")
    assert owner_username != current_member_username, (
        f"地址 {address_id} 应属于其他会员，实际属于：{owner_username}"
    )
    return address_id


def verify_address_not_in_member_list(
    response,
    *,
    foreign_address_id,
    expected_code,
):
    """校验其他会员地址不出现在当前会员地址列表"""
    addresses = _extract_addresses(response, expected_code)
    matched_addresses = [
        address
        for address in addresses
        if str(address.get("id")) == str(foreign_address_id)
    ]
    assert not matched_addresses, (
        f"当前会员地址列表不应包含其他会员地址 {foreign_address_id}，"
        f"实际匹配：{matched_addresses}"
    )
