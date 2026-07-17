import pytest

from api_support.portal.cart_helper import PortalCartHelper
from core.load_yaml import load_yaml
from test_support.db_queries.cart_queries import CartQueries
from test_support.db_queries.catalog_queries import CatalogQueries
from verifications.portal.cart import (
    verify_cart_add_rejected,
    verify_cart_add_success,
    verify_cart_count_unchanged,
    verify_cart_price_consistency,
)
from verifications.portal.product import (
    verify_database_sku_stock,
    verify_product_detail_content,
    verify_product_detail_not_found,
    verify_product_detail_parameter_rejected,
    verify_sku_absent,
    verify_sku_list_contains,
    verify_sku_stock,
)

pytestmark = [
    pytest.mark.api,
    pytest.mark.portal,
    pytest.mark.story("Product Detail and SKU"),
]
PRODUCT_DETAIL_DATA = load_yaml("portal/product_detail_data.yaml")


class TestProductDetail:
    """前台商品详情与 SKU 接口测试用例"""

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_012 查询有效商品详情成功")
    def test_valid_product_detail_success(self, product_api):
        """TC_ECOM_012 验证有效商品详情主体字段完整"""
        case_data = PRODUCT_DETAIL_DATA["TC_ECOM_012"][0]
        response = product_api.search_product_detail(product_id=case_data["product_id"])
        verify_product_detail_content(
            response,
            expected_product_id=case_data["product_id"],
            expected_code=case_data["expected_business_code"],
            required_fields=case_data["required_product_fields"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_013 查询不存在商品详情失败")
    def test_nonexistent_product_detail_failed(self, product_api):
        """TC_ECOM_013 验证不存在的商品不会返回其他商品详情"""
        case_data = PRODUCT_DETAIL_DATA["TC_ECOM_013"][0]
        response = product_api.search_product_detail(product_id=case_data["product_id"])
        verify_product_detail_not_found(
            response,
            requested_product_id=case_data["product_id"],
            success_code=case_data["success_business_code"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_014 商品详情包含目标SKU")
    def test_product_detail_contains_target_sku(self, product_api):
        """TC_ECOM_014 验证商品详情 SKU 列表包含目标 SKU"""
        case_data = PRODUCT_DETAIL_DATA["TC_ECOM_014"][0]
        response = product_api.search_product_detail(product_id=case_data["product_id"])
        verify_sku_list_contains(
            response,
            expected_sku_id=case_data["expected_sku_id"],
            expected_code=case_data["expected_business_code"],
            required_fields=case_data["required_sku_fields"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_015 SKU价格与购物车价格一致")
    def test_sku_price_matches_cart_price(
        self,
        product_api,
        cart_api,
        test_conn,
    ):
        """TC_ECOM_015 验证详情、购物车接口和购物车表价格一致"""
        case_data = PRODUCT_DETAIL_DATA["TC_ECOM_015"][0]
        detail_response = product_api.search_product_detail(
            product_id=case_data["product_id"]
        )
        detail_sku = verify_sku_list_contains(
            detail_response,
            expected_sku_id=case_data["sku_id"],
            expected_code=case_data["expected_business_code"],
            required_fields=case_data["required_sku_fields"],
        )

        cart_helper = PortalCartHelper(cart_api, product_api)
        add_response = cart_helper.add_cart(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        verify_cart_add_success(
            add_response,
            expected_code=case_data["expected_business_code"],
        )

        cart_item = cart_helper.find_item(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
        )
        database_item = CartQueries(test_conn).get_latest_active_member_sku_item(
            member_username=case_data["member_username"],
            product_id=case_data["product_id"],
            sku_id=case_data["sku_id"],
        )
        verify_cart_price_consistency(
            detail_sku,
            cart_item,
            database_item,
            expected_product_id=case_data["product_id"],
            expected_sku_id=case_data["sku_id"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_016 零库存SKU不可加入购物车")
    def test_zero_stock_sku_add_cart_failed(
        self,
        product_api,
        cart_api,
        test_conn,
    ):
        """TC_ECOM_016 验证零库存 SKU 加入购物车失败且无数据新增"""
        case_data = PRODUCT_DETAIL_DATA["TC_ECOM_016"][0]
        catalog_queries = CatalogQueries(test_conn)
        sku_data = catalog_queries.get_on_sale_sku(
            product_id=case_data["product_id"],
            sku_id=case_data["sku_id"],
        )
        product_id, sku_id = verify_database_sku_stock(
            sku_data,
            expected_stock=case_data["required_stock"],
        )

        detail_response = product_api.search_product_detail(product_id=product_id)
        verify_sku_stock(
            detail_response,
            expected_sku_id=sku_id,
            expected_stock=case_data["required_stock"],
            expected_code=case_data["expected_business_code"],
        )

        cart_queries = CartQueries(test_conn)
        before_count = cart_queries.count_member_sku_items(
            member_username=case_data["member_username"],
            product_id=product_id,
            sku_id=sku_id,
        )
        add_response = PortalCartHelper(cart_api, product_api).add_cart(
            product_id=product_id,
            product_sku_id=sku_id,
            quantity=case_data["quantity"],
        )
        after_count = cart_queries.count_member_sku_items(
            member_username=case_data["member_username"],
            product_id=product_id,
            sku_id=sku_id,
        )
        verify_cart_add_rejected(
            add_response,
            success_code=case_data["expected_business_code"],
            expected_message_keywords=case_data["expected_message_keywords"],
        )
        verify_cart_count_unchanged(
            before_count=before_count,
            after_count=after_count,
            product_id=product_id,
            sku_id=sku_id,
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_017 不存在SKU加入购物车失败")
    def test_nonexistent_sku_add_cart_failed(
        self,
        product_api,
        cart_api,
        test_conn,
    ):
        """TC_ECOM_017 验证不存在的 SKU 加入购物车失败且无数据新增"""
        case_data = PRODUCT_DETAIL_DATA["TC_ECOM_017"][0]
        detail_response = product_api.search_product_detail(
            product_id=case_data["product_id"]
        )
        verify_sku_absent(
            detail_response,
            unexpected_sku_id=case_data["nonexistent_sku_id"],
            expected_code=case_data["expected_business_code"],
        )

        cart_queries = CartQueries(test_conn)
        before_count = cart_queries.count_member_sku_items(
            member_username=case_data["member_username"],
            product_id=case_data["product_id"],
            sku_id=case_data["nonexistent_sku_id"],
        )
        add_response = PortalCartHelper(cart_api, product_api).add_cart(
            product_id=case_data["product_id"],
            product_sku_id=case_data["nonexistent_sku_id"],
            quantity=case_data["quantity"],
        )
        after_count = cart_queries.count_member_sku_items(
            member_username=case_data["member_username"],
            product_id=case_data["product_id"],
            sku_id=case_data["nonexistent_sku_id"],
        )
        verify_cart_add_rejected(
            add_response,
            success_code=case_data["expected_business_code"],
            expected_message_keywords=case_data["expected_message_keywords"],
        )
        verify_cart_count_unchanged(
            before_count=before_count,
            after_count=after_count,
            product_id=case_data["product_id"],
            sku_id=case_data["nonexistent_sku_id"],
        )

    @pytest.mark.p1
    @pytest.mark.title("TC_ECOM_092 商品详情 productId 非数字时失败")
    def test_product_detail_non_numeric_id_failed(self, product_api, test_conn):
        """TC_ECOM_092 验证非数字商品 ID 被拒绝且目录数据无副作用"""
        case_data = PRODUCT_DETAIL_DATA["TC_ECOM_092"][0]
        catalog_queries = CatalogQueries(test_conn)
        before_catalog_state = catalog_queries.get_catalog_state()

        request_error = None
        response = None
        try:
            response = product_api.search_product_detail(
                product_id=case_data["product_id"],
            )
        except AssertionError as error:
            request_error = error
        after_catalog_state = catalog_queries.get_catalog_state()

        verify_product_detail_parameter_rejected(
            response,
            request_error,
            before_catalog_state,
            after_catalog_state,
            success_code=case_data["success_business_code"],
            expected_message_field=case_data["expected_message_field"],
        )
