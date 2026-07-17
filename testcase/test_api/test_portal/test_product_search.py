import pytest

from core.load_yaml import load_yaml
from test_support.db_queries.catalog_queries import CatalogQueries
from verifications.portal.product import (
    verify_brand_search,
    verify_category_search,
    verify_empty_search_result,
    verify_keyword_search,
    verify_off_sale_product_hidden,
    verify_product_detail,
    verify_product_publish_status,
    verify_safe_search_response,
    verify_search_parameter_rejected,
)

pytestmark = [
    pytest.mark.api,
    pytest.mark.portal,
    pytest.mark.story("Product Search"),
]
PRODUCT_SEARCH_DATA = load_yaml("portal/product_search_data.yaml")


class TestProductSearch:
    """前台商品搜索接口测试用例"""

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_093 商品关键词搜索成功")
    def test_keyword_search_success(self, product_api):
        """TC_ECOM_093 验证关键词搜索返回匹配且字段完整的商品"""
        case_data = PRODUCT_SEARCH_DATA["TC_ECOM_093"][0]
        response = product_api.product_search(
            keyword=case_data["keyword"],
            page_num=case_data["page_num"],
            page_size=case_data["page_size"],
            sort=case_data["sort"],
        )
        products = verify_keyword_search(
            response,
            keyword=case_data["keyword"],
            expected_code=case_data["expected_business_code"],
            expected_page_num=case_data["page_num"],
            expected_page_size=case_data["page_size"],
            required_fields=case_data["required_product_fields"],
        )

        product_id = products[0]["id"]
        detail_response = product_api.search_product_detail(product_id=product_id)
        verify_product_detail(
            detail_response,
            expected_product_id=product_id,
            expected_code=case_data["expected_business_code"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_007 无结果关键词搜索返回空列表")
    def test_no_result_keyword_search(self, product_api):
        """TC_ECOM_007 验证不存在的关键词返回空列表"""
        case_data = PRODUCT_SEARCH_DATA["TC_ECOM_007"][0]
        response = product_api.product_search(
            keyword=case_data["keyword"],
            page_num=case_data["page_num"],
            page_size=case_data["page_size"],
            sort=case_data["sort"],
        )
        verify_empty_search_result(
            response,
            expected_code=case_data["expected_business_code"],
        )

    @pytest.mark.p1
    @pytest.mark.title("TC_ECOM_008 按商品分类搜索成功")
    def test_category_search_success(self, product_api):
        """TC_ECOM_008 验证按商品分类搜索返回对应分类商品"""
        case_data = PRODUCT_SEARCH_DATA["TC_ECOM_008"][0]
        response = product_api.product_search(
            product_category_id=case_data["product_category_id"],
            page_num=case_data["page_num"],
            page_size=case_data["page_size"],
            sort=case_data["sort"],
        )
        verify_category_search(
            response,
            allowed_category_ids=case_data["allowed_category_ids"],
            expected_code=case_data["expected_business_code"],
            expected_page_num=case_data["page_num"],
            expected_page_size=case_data["page_size"],
        )

    @pytest.mark.p1
    @pytest.mark.title("TC_ECOM_009 按商品品牌搜索成功")
    def test_brand_search_success(self, product_api):
        """TC_ECOM_009 验证按商品品牌搜索返回对应品牌商品"""
        case_data = PRODUCT_SEARCH_DATA["TC_ECOM_009"][0]
        response = product_api.product_search(
            brand_id=case_data["brand_id"],
            page_num=case_data["page_num"],
            page_size=case_data["page_size"],
            sort=case_data["sort"],
        )
        verify_brand_search(
            response,
            expected_brand_id=case_data["brand_id"],
            expected_code=case_data["expected_business_code"],
            expected_page_num=case_data["page_num"],
            expected_page_size=case_data["page_size"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_010 下架商品不出现在前台搜索结果")
    def test_off_sale_product_hidden(self, product_api):
        """TC_ECOM_010 验证下架商品不在前台搜索结果中"""
        case_data = PRODUCT_SEARCH_DATA["TC_ECOM_010"][0]
        response = product_api.product_search(
            keyword=case_data["keyword"],
            page_num=case_data["page_num"],
            page_size=case_data["page_size"],
            sort=case_data["sort"],
        )
        products = verify_off_sale_product_hidden(
            response,
            excluded_product_ref=case_data["excluded_product_ref"],
            excluded_product_name=case_data["excluded_product_name"],
            expected_code=case_data["expected_business_code"],
        )

        for product in products:
            detail_response = product_api.search_product_detail(
                product_id=product["id"]
            )
            verify_product_publish_status(
                detail_response,
                expected_product_id=product["id"],
                expected_publish_status=case_data["expected_publish_status"],
                expected_code=case_data["expected_business_code"],
            )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_011 特殊字符关键词搜索接口不报错")
    def test_special_character_search_safe(self, product_api):
        """TC_ECOM_011 验证特殊字符搜索安全返回且不暴露 SQL 异常"""
        case_data = PRODUCT_SEARCH_DATA["TC_ECOM_011"][0]
        response = product_api.product_search(
            keyword=case_data["keyword"],
            page_num=case_data["page_num"],
            page_size=case_data["page_size"],
            sort=case_data["sort"],
        )
        verify_safe_search_response(
            response,
            forbidden_keywords=case_data["forbidden_response_keywords"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_090 商品搜索pageNum类型错误时明确失败")
    def test_product_search_page_num_type_error_rejected(
        self,
        product_api,
        test_conn,
    ):
        """TC_ECOM_090 验证 pageNum 类型错误被拒绝且目录数据不变"""
        case_data = PRODUCT_SEARCH_DATA["TC_ECOM_090"][0]
        catalog_queries = CatalogQueries(test_conn)
        before_catalog_state = catalog_queries.get_catalog_state()

        response = None
        request_error = None
        try:
            response = product_api.product_search(
                keyword=case_data["keyword"],
                page_num=case_data["page_num"],
                page_size=case_data["page_size"],
                sort=case_data["sort"],
            )
        except AssertionError as exc:
            request_error = exc
        after_catalog_state = catalog_queries.get_catalog_state()

        verify_search_parameter_rejected(
            response,
            request_error,
            before_catalog_state,
            after_catalog_state,
            success_code=case_data["success_business_code"],
            expected_message_field=case_data["expected_message_field"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_091 商品搜索pageSize为0时明确失败")
    def test_product_search_zero_page_size_rejected(
        self,
        product_api,
        test_conn,
    ):
        """TC_ECOM_091 验证 pageSize 为0被拒绝且目录数据不变"""
        case_data = PRODUCT_SEARCH_DATA["TC_ECOM_091"][0]
        catalog_queries = CatalogQueries(test_conn)
        before_catalog_state = catalog_queries.get_catalog_state()

        response = None
        request_error = None
        try:
            response = product_api.product_search(
                keyword=case_data["keyword"],
                page_num=case_data["page_num"],
                page_size=case_data["page_size"],
                sort=case_data["sort"],
            )
        except AssertionError as exc:
            request_error = exc
        after_catalog_state = catalog_queries.get_catalog_state()

        verify_search_parameter_rejected(
            response,
            request_error,
            before_catalog_state,
            after_catalog_state,
            success_code=case_data["success_business_code"],
            expected_message_field=case_data["expected_message_field"],
        )
