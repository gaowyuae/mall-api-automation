from decimal import Decimal, InvalidOperation

from api_support.portal.cart_helper import PortalCartHelper
from verifications.common.response import (
    verify_business_code,
    verify_business_failure,
    verify_message_contains_any,
)


def _decimal_price(value, field_name):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise AssertionError(f"{field_name} 应为有效价格，实际为：{value}") from exc


def verify_cart_add_success(response, expected_code):
    verify_business_code(response, expected_code)


def verify_cart_add_rejected(
    response,
    success_code,
    expected_message_keywords=None,
):
    """校验加入购物车请求被业务层拒绝"""
    verify_business_failure(response, success_code)
    if expected_message_keywords:
        verify_message_contains_any(response, expected_message_keywords)


def verify_cart_parameter_rejected(
    error,
    expected_field,
):
    """校验封装层因购物车参数非法拒绝请求"""
    error_text = str(error)
    assert expected_field in error_text, (
        f"购物车参数校验应指出字段 {expected_field}，实际异常为：{error_text}"
    )


def verify_cart_http_rejected(
    error,
    expected_http_status,
):
    """校验接口在 HTTP 层拒绝购物车请求"""
    error_text = str(error)
    assert str(expected_http_status) in error_text, (
        f"购物车请求应返回 HTTP {expected_http_status}，实际异常为：{error_text}"
    )


def _extract_cart_items(response, expected_code):
    verify_business_code(response, expected_code)
    cart_items = PortalCartHelper.get_items(response)
    assert isinstance(cart_items, list), (
        f"购物车列表 data 应为列表，实际为：{cart_items}"
    )
    return cart_items


def verify_cart_list_empty(
    response,
    expected_code,
    expected_item_count=0,
):
    """校验购物车列表为空"""
    cart_items = _extract_cart_items(response, expected_code)
    assert len(cart_items) == expected_item_count, (
        f"购物车列表记录数应为 {expected_item_count}，实际为：{len(cart_items)}，"
        f"列表内容：{cart_items}"
    )


def verify_cart_item_absent(
    response,
    expected_code,
    expected_product_id,
    expected_sku_id,
    unexpected_quantity=None,
):
    """校验购物车列表中不存在指定商品、SKU 和数量的记录"""
    _extract_cart_items(response, expected_code)
    matched_items = PortalCartHelper.find_items_in_response(
        response,
        product_id=expected_product_id,
        product_sku_id=expected_sku_id,
        quantity=unexpected_quantity,
    )
    assert not matched_items, (
        f"购物车不应存在 product_id={expected_product_id}、sku_id={expected_sku_id}、"
        f"quantity={unexpected_quantity} 的记录，实际为：{matched_items}"
    )


def verify_cart_list_contains_item(
    response,
    expected_code,
    expected_product_id,
    expected_sku_id,
    expected_quantity,
    required_fields,
):
    """校验购物车列表包含目标 SKU 且字段完整"""
    _extract_cart_items(response, expected_code)
    cart_item = PortalCartHelper.find_latest_item_in_response(
        response,
        product_id=expected_product_id,
        product_sku_id=expected_sku_id,
        quantity=expected_quantity,
    )
    assert cart_item is not None, (
        f"购物车列表中未找到 product_id={expected_product_id}、"
        f"sku_id={expected_sku_id}、quantity={expected_quantity} 的记录"
    )

    missing_fields = [field for field in required_fields if field not in cart_item]
    assert not missing_fields, f"购物车项缺少字段 {missing_fields}：{cart_item}"

    empty_fields = [
        field for field in required_fields if cart_item.get(field) in (None, "")
    ]
    assert not empty_fields, f"购物车项字段不能为空 {empty_fields}：{cart_item}"

    verify_cart_item_added(
        cart_item=cart_item,
        expected_product_id=expected_product_id,
        expected_sku_id=expected_sku_id,
        expected_quantity=expected_quantity,
    )
    return cart_item


def verify_cart_id_matches_item(cart_id, cart_item):
    """校验封装方法返回的 cartId 与列表中的最新匹配项一致"""
    assert cart_id not in (None, ""), f"cartId 应非空，实际为：{cart_id}"
    assert str(cart_id) == str(cart_item.get("id")), (
        f"封装返回 cartId 应与 cart/list 最新匹配项一致，"
        f"封装返回：{cart_id}，列表返回：{cart_item.get('id')}"
    )


def verify_cart_count_unchanged(
    before_count,
    after_count,
    product_id,
    sku_id,
):
    """校验失败请求没有新增购物车记录"""
    assert after_count == before_count, (
        f"购物车记录数不应变化：product_id={product_id}，sku_id={sku_id}，"
        f"操作前={before_count}，操作后={after_count}"
    )


def verify_cart_price_consistency(
    detail_sku,
    cart_item,
    database_item,
    expected_product_id,
    expected_sku_id,
):
    """校验详情、购物车接口和数据库中的 SKU 价格一致"""
    assert isinstance(detail_sku, dict), f"商品详情 SKU 应为字典：{detail_sku}"
    assert isinstance(cart_item, dict), f"购物车接口数据应为字典：{cart_item}"
    assert isinstance(database_item, dict), (
        f"数据库中未找到有效购物车记录：product_id={expected_product_id}，"
        f"sku_id={expected_sku_id}"
    )

    assert str(cart_item.get("productId")) == str(expected_product_id), (
        f"购物车商品 ID 应为 {expected_product_id}，实际为："
        f"{cart_item.get('productId')}"
    )
    assert str(cart_item.get("productSkuId")) == str(expected_sku_id), (
        f"购物车 SKU ID 应为 {expected_sku_id}，实际为：{cart_item.get('productSkuId')}"
    )
    assert str(database_item.get("product_id")) == str(expected_product_id), (
        f"数据库购物车商品 ID 应为 {expected_product_id}：{database_item}"
    )
    assert str(database_item.get("product_sku_id")) == str(expected_sku_id), (
        f"数据库购物车 SKU ID 应为 {expected_sku_id}：{database_item}"
    )

    detail_price = _decimal_price(detail_sku.get("price"), "商品详情 SKU price")
    cart_price = _decimal_price(cart_item.get("price"), "购物车接口 price")
    database_price = _decimal_price(database_item.get("price"), "购物车表 price")

    assert cart_price == detail_price, (
        f"购物车接口价格应为 {detail_price}，实际为：{cart_price}"
    )
    assert database_price == detail_price, (
        f"购物车表价格应为 {detail_price}，实际为：{database_price}"
    )


def verify_cart_item_added(
    cart_item,
    expected_product_id,
    expected_sku_id,
    expected_quantity,
):
    """校验购物车列表中包含目标 SKU，且商品、SKU、数量、购物车 ID 正确"""

    assert cart_item.get("id"), f"购物车 cartId 应非空，实际为：{cart_item.get('id')}"

    assert str(cart_item.get("productId")) == str(expected_product_id), (
        f"购物车商品 ID 应为 {expected_product_id}，"
        f"实际为：{cart_item.get('productId')}"
    )
    assert str(cart_item.get("productSkuId")) == str(expected_sku_id), (
        f"购物车 SKU ID 应为 {expected_sku_id}，实际为：{cart_item.get('productSkuId')}"
    )
    assert str(cart_item.get("quantity")) == str(expected_quantity), (
        f"购物车商品数量应为 {expected_quantity}，实际为：{cart_item.get('quantity')}"
    )


def verify_cart_database_consistency(
    cart_item,
    database_item,
    expected_product_id,
    expected_sku_id,
    expected_quantity,
    expected_delete_status,
):
    """校验数据库中购物车记录和接口返回的购物车记录一致"""
    assert database_item, "数据库中未找到目标购物车记录"

    assert str(cart_item.get("id")) == str(database_item.get("id")), (
        f"数据库购物车 ID 应与接口 cartId 一致，接口为：{cart_item.get('id')}，"
        f"数据库为：{database_item.get('id')}"
    )
    assert str(database_item.get("product_id")) == str(expected_product_id), (
        f"数据库购物车商品 ID 应为 {expected_product_id}，"
        f"实际为：{database_item.get('product_id')}"
    )
    assert str(database_item.get("product_sku_id")) == str(expected_sku_id), (
        f"数据库购物车 SKU ID 应为 {expected_sku_id}，"
        f"实际为：{database_item.get('product_sku_id')}"
    )
    assert str(database_item.get("quantity")) == str(expected_quantity), (
        f"数据库购物车商品数量应为 {expected_quantity}，"
        f"实际为：{database_item.get('quantity')}"
    )
    assert str(database_item.get("delete_status")) == str(expected_delete_status), (
        f"数据库购物车商品删除状态应为 {expected_delete_status}，"
        f"实际为：{database_item.get('delete_status')}"
    )


def verify_cart_duplicate_add_merged(
    cart_items,
    expected_product_id,
    expected_sku_id,
    expected_quantity,
    expected_record_count,
):
    """校验同一 SKU 重复加购后购物车记录合并且数量正确"""
    assert len(cart_items) == expected_record_count, (
        f"购物车中同一 SKU 记录数量应为 {expected_record_count}，"
        f"实际为：{len(cart_items)}"
    )

    cart_item = cart_items[0]

    assert cart_item.get("id"), f"购物车 cartId 应非空，实际为：{cart_item.get('id')}"

    assert str(cart_item.get("productId")) == str(expected_product_id), (
        f"购物车商品 ID 应为 {expected_product_id}，"
        f"实际为：{cart_item.get('productId')}"
    )
    assert str(cart_item.get("productSkuId")) == str(expected_sku_id), (
        f"购物车 SKU ID 应为 {expected_sku_id}，实际为：{cart_item.get('productSkuId')}"
    )
    assert str(cart_item.get("quantity")) == str(expected_quantity), (
        f"重复加购后购物车商品数量应为 {expected_quantity}，"
        f"实际为：{cart_item.get('quantity')}"
    )


def verify_cart_database_merge_consistency(
    cart_item,
    database_item,
    database_record_count,
    expected_product_id,
    expected_sku_id,
    expected_quantity,
    expected_delete_status,
    expected_record_count,
):
    """校验重复加购后数据库购物车记录合并且数量正确"""
    assert database_item, "数据库中未找到目标购物车记录"

    assert database_record_count == expected_record_count, (
        f"数据库同一用户同一 SKU 有效记录数应为 {expected_record_count}，"
        f"实际为：{database_record_count}"
    )

    assert str(cart_item.get("id")) == str(database_item.get("id")), (
        f"数据库购物车 ID 应与接口 cartId 一致，接口为：{cart_item.get('id')}，"
        f"数据库为：{database_item.get('id')}"
    )
    assert str(database_item.get("product_id")) == str(expected_product_id), (
        f"数据库购物车商品 ID 应为 {expected_product_id}，"
        f"实际为：{database_item.get('product_id')}"
    )
    assert str(database_item.get("product_sku_id")) == str(expected_sku_id), (
        f"数据库购物车 SKU ID 应为 {expected_sku_id}，"
        f"实际为：{database_item.get('product_sku_id')}"
    )
    assert str(database_item.get("quantity")) == str(expected_quantity), (
        f"数据库购物车商品数量应为 {expected_quantity}，"
        f"实际为：{database_item.get('quantity')}"
    )
    assert str(database_item.get("delete_status")) == str(expected_delete_status), (
        f"数据库购物车删除状态应为 {expected_delete_status}，"
        f"实际为：{database_item.get('delete_status')}"
    )


def verify_cart_item_consumed(
    database_item,
    *,
    expected_delete_status,
):
    """校验购物车记录已被清理或下单消费"""
    assert isinstance(database_item, dict), (
        f"数据库中未找到购物车记录，实际为：{database_item}"
    )
    assert str(database_item.get("delete_status")) == str(expected_delete_status), (
        f"购物车记录 delete_status 应为 {expected_delete_status}，"
        f"实际为：{database_item}"
    )
