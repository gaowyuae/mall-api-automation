from api_support.common.response_helper import ApiResponseHelper
from api_support.portal.product_helper import PortalProductHelper
from verifications.common.response import (
    verify_business_code,
    verify_business_failure,
    verify_response_dict,
)


def _extract_search_result(
    response,
    expected_code,
):
    """校验搜索成功并提取分页数据和商品列表"""
    verify_business_code(response, expected_code)
    search_data = PortalProductHelper.get_search_data(response)
    assert isinstance(search_data, dict), (
        f"商品搜索 data 应为字典，实际为：{search_data}"
    )
    products = PortalProductHelper.get_search_products(response)
    assert isinstance(products, list), (
        f"商品搜索 data.list 应为列表，实际为：{products}"
    )
    assert all(isinstance(product, dict) for product in products), (
        f"商品搜索列表项应为字典，实际为：{products}"
    )
    return search_data, products


def _verify_pagination(
    search_data,
    expected_page_num,
    expected_page_size,
):
    """校验商品搜索分页字段及页码参数"""
    for field in ("pageNum", "pageSize", "total", "totalPage"):
        assert field in search_data, f"商品搜索分页数据缺少 {field}：{search_data}"
    assert search_data["pageNum"] == expected_page_num, (
        f"pageNum 应为 {expected_page_num}，实际为：{search_data['pageNum']}"
    )
    assert search_data["pageSize"] == expected_page_size, (
        f"pageSize 应为 {expected_page_size}，实际为：{search_data['pageSize']}"
    )


def _extract_product_detail_data(
    response,
    expected_code,
):
    """校验商品详情响应并返回 data 字典"""
    verify_business_code(response, expected_code)
    detail_data = PortalProductHelper.get_detail_data(response)
    assert isinstance(detail_data, dict), (
        f"商品详情 data 应为字典，实际为：{detail_data}"
    )
    return detail_data


def _extract_product_detail(
    response,
    expected_code,
):
    """校验商品详情响应并返回商品数据"""
    _extract_product_detail_data(response, expected_code)
    product = PortalProductHelper.get_product(response)
    assert isinstance(product, dict), f"商品详情内容应为字典，实际为：{product}"
    return product


def _get_verified_sku(
    detail_data,
    expected_sku_id,
):
    """校验 SKU 列表结构并返回指定 SKU"""
    sku_list = detail_data.get("skuStockList")
    assert isinstance(sku_list, list), (
        f"商品详情 skuStockList 应为列表，实际为：{sku_list}"
    )
    assert all(isinstance(sku, dict) for sku in sku_list), (
        f"商品详情 skuStockList 存在非字典项：{sku_list}"
    )
    return PortalProductHelper.find_sku_in_list(sku_list, expected_sku_id)


def verify_keyword_search(
    response,
    keyword,
    expected_code,
    expected_page_num,
    expected_page_size,
    required_fields,
):
    """校验关键词搜索返回匹配且字段完整的商品"""
    search_data, products = _extract_search_result(response, expected_code)
    _verify_pagination(search_data, expected_page_num, expected_page_size)
    assert products, f"关键词“{keyword}”应至少返回一个上架商品"

    normalized_keyword = keyword.casefold()
    for product in products:
        missing_fields = [field for field in required_fields if field not in product]
        assert not missing_fields, f"商品搜索结果缺少字段 {missing_fields}：{product}"
        product_name = str(product.get("name") or "")
        assert normalized_keyword in product_name.casefold(), (
            f"商品名称应包含关键词“{keyword}”，实际为：{product_name}"
        )
    return products


def verify_search_contains_product(products, expected_product_id):
    """校验商品搜索结果包含后续业务流程使用的目标商品"""
    assert isinstance(products, list), f"商品搜索结果应为列表，实际为：{products}"
    product = next(
        (
            item
            for item in products
            if isinstance(item, dict)
            and str(item.get("id")) == str(expected_product_id)
        ),
        None,
    )
    assert product is not None, f"商品搜索结果中未找到目标商品 {expected_product_id}"
    return product


def verify_product_detail(
    response,
    expected_product_id,
    expected_code,
):
    """校验商品详情可正常查询且商品 ID 一致"""
    product = _extract_product_detail(response, expected_code)
    assert product.get("id") == expected_product_id, (
        f"商品详情 ID 应为 {expected_product_id}，实际为：{product.get('id')}"
    )


def verify_product_detail_content(
    response,
    expected_product_id,
    expected_code,
    required_fields,
):
    """校验有效商品详情的主体字段完整"""
    product = _extract_product_detail(response, expected_code)
    assert str(product.get("id")) == str(expected_product_id), (
        f"商品详情 ID 应为 {expected_product_id}，实际为：{product.get('id')}"
    )
    missing_fields = [field for field in required_fields if field not in product]
    assert not missing_fields, f"商品详情缺少字段 {missing_fields}：{product}"
    empty_fields = [
        field for field in required_fields if product.get(field) in (None, "")
    ]
    assert not empty_fields, f"商品详情字段不能为空 {empty_fields}：{product}"
    return product


def verify_product_detail_not_found(
    response,
    requested_product_id,
    success_code,
):
    """校验不存在的商品未返回任何有效商品详情"""
    response_data = verify_response_dict(response)
    actual_code = response_data.get("code")
    assert actual_code is not None, f"商品详情响应缺少业务 code：{response_data}"

    detail_data = ApiResponseHelper.get_data(response_data)
    product = PortalProductHelper.get_product(response_data)
    if isinstance(product, dict) and product:
        actual_product_id = product.get("id")
        raise AssertionError(
            f"不存在的商品 {requested_product_id} 不应返回有效商品，"
            f"实际返回商品 ID：{actual_product_id}"
        )

    empty_detail = detail_data in (None, {}, []) or (
        isinstance(detail_data, dict) and detail_data.get("product") in (None, {}, [])
    )
    assert actual_code != success_code or empty_detail, (
        f"不存在的商品应返回失败 code 或空 data，实际为：{response_data}"
    )


def verify_sku_list_contains(
    response,
    expected_sku_id,
    expected_code,
    required_fields,
):
    """校验商品详情 SKU 列表包含目标 SKU 且字段完整"""
    detail_data = _extract_product_detail_data(response, expected_code)
    sku = _get_verified_sku(detail_data, expected_sku_id)
    assert sku is not None, f"skuStockList 中未找到 SKU {expected_sku_id}"

    missing_fields = [field for field in required_fields if field not in sku]
    assert not missing_fields, f"SKU {expected_sku_id} 缺少字段 {missing_fields}：{sku}"
    empty_fields = [field for field in required_fields if sku.get(field) in (None, "")]
    assert not empty_fields, f"SKU {expected_sku_id} 字段不能为空 {empty_fields}：{sku}"
    return sku


def verify_sku_absent(
    response,
    unexpected_sku_id,
    expected_code,
):
    """校验商品详情中不存在指定 SKU"""
    detail_data = _extract_product_detail_data(response, expected_code)
    sku = _get_verified_sku(detail_data, unexpected_sku_id)
    assert sku is None, f"商品详情中不应存在 SKU {unexpected_sku_id}：{sku}"


def verify_sku_stock(
    response,
    expected_sku_id,
    expected_stock,
    expected_code,
):
    """校验商品详情中目标 SKU 的库存"""
    detail_data = _extract_product_detail_data(response, expected_code)
    sku = _get_verified_sku(detail_data, expected_sku_id)
    assert sku is not None, f"商品详情中未找到 SKU {expected_sku_id}"
    assert sku.get("stock") == expected_stock, (
        f"SKU {expected_sku_id} 库存应为 {expected_stock}，实际为：{sku.get('stock')}"
    )
    return sku


def verify_database_sku_stock(
    sku_data,
    expected_stock,
):
    """校验数据库中存在指定库存的有效上架商品 SKU"""
    assert isinstance(sku_data, dict), (
        f"数据库中未找到库存为 {expected_stock} 的有效上架商品 SKU"
    )
    assert sku_data.get("publish_status") == 1, f"商品应为上架状态：{sku_data}"
    assert sku_data.get("delete_status") == 0, f"商品应为未删除状态：{sku_data}"
    assert sku_data.get("stock") == expected_stock, (
        f"数据库 SKU 库存应为 {expected_stock}，实际为：{sku_data.get('stock')}"
    )

    product_id = sku_data.get("product_id")
    sku_id = sku_data.get("sku_id")
    assert product_id is not None and sku_id is not None, (
        f"数据库 SKU 数据缺少 product_id 或 sku_id：{sku_data}"
    )
    return product_id, sku_id


def verify_empty_search_result(response, expected_code):
    """校验无结果搜索的列表和总数都为空"""
    search_data, products = _extract_search_result(response, expected_code)
    total = search_data.get("total")
    assert products == [], f"无结果搜索应返回空列表，实际为：{products}"
    assert total == 0, f"无结果搜索 total 应为 0，实际为：{total}"


def verify_category_search(
    response,
    allowed_category_ids,
    expected_code,
    expected_page_num,
    expected_page_size,
):
    """校验分类搜索结果及分页信息"""
    search_data, products = _extract_search_result(response, expected_code)
    _verify_pagination(search_data, expected_page_num, expected_page_size)
    assert products, f"分类 {allowed_category_ids} 应至少返回一个上架商品"

    normalized_category_ids = {str(category_id) for category_id in allowed_category_ids}
    for product in products:
        actual_category_id = product.get("productCategoryId")
        assert str(actual_category_id) in normalized_category_ids, (
            f"商品分类应属于 {allowed_category_ids}，实际为：{actual_category_id}"
        )


def verify_brand_search(
    response,
    expected_brand_id,
    expected_code,
    expected_page_num,
    expected_page_size,
):
    """校验品牌搜索结果及品牌名称"""
    search_data, products = _extract_search_result(response, expected_code)
    _verify_pagination(search_data, expected_page_num, expected_page_size)
    assert products, f"品牌 {expected_brand_id} 应至少返回一个上架商品"

    for product in products:
        actual_brand_id = product.get("brandId")
        assert str(actual_brand_id) == str(expected_brand_id), (
            f"商品品牌 ID 应为 {expected_brand_id}，实际为：{actual_brand_id}"
        )
        brand_name = product.get("brandName")
        assert brand_name and str(brand_name).strip(), (
            f"品牌搜索结果 brandName 不应为空：{product}"
        )


def verify_off_sale_product_hidden(
    response,
    excluded_product_ref,
    excluded_product_name,
    expected_code,
):
    """校验下架商品未出现在前台搜索结果中"""
    _, products = _extract_search_result(response, expected_code)
    normalized_ref = str(excluded_product_ref).casefold()
    normalized_name = excluded_product_name.casefold()

    exposed_products = []
    for product in products:
        references = (
            product.get("id"),
            product.get("productId"),
            product.get("productSn"),
        )
        reference_matched = normalized_ref in {
            str(reference).casefold()
            for reference in references
            if reference is not None
        }
        name_matched = normalized_name in str(product.get("name") or "").casefold()
        if reference_matched or name_matched:
            exposed_products.append(product)

    assert not exposed_products, (
        f"下架商品不应出现在前台搜索结果中，实际为：{exposed_products}"
    )
    return products


def verify_product_publish_status(
    response,
    expected_product_id,
    expected_publish_status,
    expected_code,
):
    """校验商品详情中的上架状态"""
    product = _extract_product_detail(response, expected_code)
    assert product.get("id") == expected_product_id, (
        f"商品详情 ID 应为 {expected_product_id}，实际为：{product.get('id')}"
    )
    assert product.get("publishStatus") == expected_publish_status, (
        f"商品 {expected_product_id} 的 publishStatus 应为 "
        f"{expected_publish_status}，实际为：{product.get('publishStatus')}"
    )


def verify_safe_search_response(
    response,
    forbidden_keywords,
):
    """校验特殊字符搜索响应完整且不暴露 SQL 异常"""
    response_data = verify_response_dict(response)
    for field in ("code", "message", "data"):
        assert field in response_data, f"特殊字符搜索响应缺少 {field}：{response_data}"

    search_data = PortalProductHelper.get_search_data(response_data)
    assert isinstance(search_data, dict), (
        f"特殊字符搜索 data 应为合法分页字典，实际为：{search_data}"
    )
    products = PortalProductHelper.get_search_products(response_data)
    assert isinstance(products, list), (
        f"特殊字符搜索 data.list 应为列表，实际为：{search_data}"
    )

    response_text = str(response_data).casefold()
    exposed_keywords = [
        keyword for keyword in forbidden_keywords if keyword.casefold() in response_text
    ]
    assert not exposed_keywords, (
        f"特殊字符搜索响应不应暴露 SQL 异常关键词：{exposed_keywords}"
    )


def verify_search_parameter_rejected(
    response,
    request_error,
    before_catalog_state,
    after_catalog_state,
    *,
    success_code,
    expected_message_field,
):
    """校验商品搜索参数异常被明确拒绝且目录数据没有副作用"""
    assert before_catalog_state == after_catalog_state, (
        "只读商品搜索不应改变商品或 SKU 数据，"
        f"搜索前={before_catalog_state}，搜索后={after_catalog_state}"
    )
    assert request_error is None, (
        "商品搜索参数错误应返回可解析的业务失败响应，"
        f"实际被 HTTP 校验拦截：{request_error}"
    )
    verify_business_failure(response, success_code)
    message = ApiResponseHelper.get_message(response)
    assert expected_message_field.casefold() in message.casefold(), (
        f"参数错误消息应定位字段 {expected_message_field}，实际为：{message}"
    )


def verify_product_detail_parameter_rejected(
    response,
    request_error,
    before_catalog_state,
    after_catalog_state,
    *,
    success_code,
    expected_message_field,
):
    """校验商品详情参数异常被拒绝且目录数据没有副作用"""
    assert before_catalog_state == after_catalog_state, (
        "只读商品详情不应改变商品或 SKU 数据，"
        f"查询前={before_catalog_state}，查询后={after_catalog_state}"
    )

    if request_error is not None:
        error_text = str(request_error)
        normalized_error = error_text.casefold()
        field = expected_message_field.casefold()
        assert field in normalized_error or "http响应失败" in normalized_error, (
            f"商品详情参数错误应定位字段 {expected_message_field} 或明确 HTTP 拒绝，"
            f"实际异常为：{request_error}"
        )
        return

    assert response is not None, "商品详情参数错误应返回业务失败响应或 HTTP 拦截异常"
    verify_business_failure(response, success_code)
    message = ApiResponseHelper.get_message(response)
    assert expected_message_field.casefold() in message.casefold(), (
        f"参数错误消息应定位字段 {expected_message_field}，实际为：{message}"
    )
