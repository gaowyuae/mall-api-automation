import pytest

from api_support.portal.cart_helper import PortalCartHelper
from apis.portal.cart_item_api import CartItemAPI
from core.load_yaml import load_yaml
from test_support.db_preconditions import restore_sku_stock_precondition
from test_support.db_queries import CartQueries
from verifications.common.response import verify_business_code
from verifications.portal.cart import (
    verify_cart_add_rejected,
    verify_cart_add_success,
    verify_cart_count_unchanged,
    verify_cart_database_consistency,
    verify_cart_database_merge_consistency,
    verify_cart_duplicate_add_merged,
    verify_cart_http_rejected,
    verify_cart_id_matches_item,
    verify_cart_item_absent,
    verify_cart_item_added,
    verify_cart_list_contains_item,
    verify_cart_list_empty,
    verify_cart_parameter_rejected,
)
from verifications.portal.product import verify_sku_stock

pytestmark = [
    pytest.mark.api,
    pytest.mark.portal,
    pytest.mark.story("Cart"),
]
ADD_CART_DATA = load_yaml("portal/add_cart_data.yaml")


class TestAddCart:
    """前台购物车接口测试用例"""

    @staticmethod
    def _add_invalid_quantity(cart_api, case_data):
        try:
            return cart_api.add_cart(
                product_id=case_data["product_id"],
                product_sku_id=case_data["sku_id"],
                quantity=case_data["quantity"],
            )
        except AssertionError as error:
            verify_cart_parameter_rejected(
                error,
                expected_field=case_data["expected_rejected_field"],
            )
            return None

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_018 可售 SKU 正常加入购物车成功")
    def test_add_cart_success(self, cart_api, product_api, test_conn):
        """TC_ECOM_018 验证可售 SKU 正常加入购物车成功"""
        case_data = ADD_CART_DATA["TC_ECOM_018"][0]
        cart_helper = PortalCartHelper(cart_api, product_api)
        clear_response = cart_api.clear_cart()
        verify_business_code(clear_response, case_data["expected_business_code"])

        cart_response = cart_api.add_cart(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        cart_item = cart_helper.find_item(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        database_item = CartQueries(test_conn).get_latest_active_member_sku_item(
            member_username=case_data["member_username"],
            product_id=case_data["product_id"],
            sku_id=case_data["sku_id"],
        )

        verify_cart_add_success(cart_response, case_data["expected_business_code"])
        verify_cart_item_added(
            cart_item=cart_item,
            expected_product_id=case_data["product_id"],
            expected_sku_id=case_data["sku_id"],
            expected_quantity=case_data["quantity"],
        )
        verify_cart_database_consistency(
            cart_item=cart_item,
            database_item=database_item,
            expected_product_id=case_data["product_id"],
            expected_sku_id=case_data["sku_id"],
            expected_quantity=case_data["quantity"],
            expected_delete_status=case_data["expected_delete_status"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_019 同一 SKU 重复加入购物车数量合并")
    def test_add_cart_duplicate_sku_merge_quantity(
        self, cart_api, product_api, test_conn
    ):
        """TC_ECOM_019 验证同一 SKU 重复加入后数量累加且无重复记录"""
        case_data = ADD_CART_DATA["TC_ECOM_019"][0]
        cart_helper = PortalCartHelper(cart_api, product_api)
        cart_queries = CartQueries(test_conn)
        clear_response = cart_api.clear_cart()
        verify_business_code(clear_response, case_data["expected_business_code"])

        for _ in range(case_data["repeat"]):
            cart_response = cart_api.add_cart(
                product_id=case_data["product_id"],
                product_sku_id=case_data["sku_id"],
                quantity=case_data["quantity"],
            )
            verify_cart_add_success(
                cart_response,
                case_data["expected_business_code"],
            )
        cart_items = cart_helper.find_items(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
        )
        database_item = cart_queries.get_latest_active_member_sku_item(
            member_username=case_data["member_username"],
            product_id=case_data["product_id"],
            sku_id=case_data["sku_id"],
        )
        database_record_count = cart_queries.count_active_member_sku_items(
            member_username=case_data["member_username"],
            product_id=case_data["product_id"],
            sku_id=case_data["sku_id"],
        )

        verify_cart_duplicate_add_merged(
            cart_items=cart_items,
            expected_product_id=case_data["product_id"],
            expected_sku_id=case_data["sku_id"],
            expected_quantity=case_data["expected_quantity"],
            expected_record_count=case_data["expected_cart_record_count"],
        )
        verify_cart_database_merge_consistency(
            cart_item=cart_items[0],
            database_item=database_item,
            database_record_count=database_record_count,
            expected_product_id=case_data["product_id"],
            expected_sku_id=case_data["sku_id"],
            expected_quantity=case_data["expected_quantity"],
            expected_delete_status=case_data["expected_delete_status"],
            expected_record_count=case_data["expected_cart_record_count"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_020 加入购物车数量为 0 时失败")
    def test_add_cart_zero_quantity_failed(self, cart_api, test_conn):
        """TC_ECOM_020 验证数量为 0 的购物车记录不会新增"""
        case_data = ADD_CART_DATA["TC_ECOM_020"][0]
        cart_queries = CartQueries(test_conn)
        clear_response = cart_api.clear_cart()
        verify_business_code(clear_response, case_data["success_business_code"])
        before_count = cart_queries.count_active_member_sku_items(
            member_username=case_data["member_username"],
            product_id=case_data["product_id"],
            sku_id=case_data["sku_id"],
        )

        response = self._add_invalid_quantity(cart_api, case_data)
        after_count = cart_queries.count_active_member_sku_items(
            member_username=case_data["member_username"],
            product_id=case_data["product_id"],
            sku_id=case_data["sku_id"],
        )
        list_response = cart_api.cart_list()

        if response is not None:
            verify_cart_add_rejected(
                response,
                success_code=case_data["success_business_code"],
            )
        verify_cart_count_unchanged(
            before_count,
            after_count,
            product_id=case_data["product_id"],
            sku_id=case_data["sku_id"],
        )
        verify_cart_item_absent(
            list_response,
            expected_code=case_data["success_business_code"],
            expected_product_id=case_data["product_id"],
            expected_sku_id=case_data["sku_id"],
            unexpected_quantity=case_data["quantity"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_021 加入购物车数量为负数时失败")
    def test_add_cart_negative_quantity_failed(self, cart_api, test_conn):
        """TC_ECOM_021 验证负数数量的购物车记录不会新增"""
        case_data = ADD_CART_DATA["TC_ECOM_021"][0]
        cart_queries = CartQueries(test_conn)
        clear_response = cart_api.clear_cart()
        verify_business_code(clear_response, case_data["success_business_code"])
        before_count = cart_queries.count_active_member_sku_items(
            member_username=case_data["member_username"],
            product_id=case_data["product_id"],
            sku_id=case_data["sku_id"],
        )

        response = self._add_invalid_quantity(cart_api, case_data)
        after_count = cart_queries.count_active_member_sku_items(
            member_username=case_data["member_username"],
            product_id=case_data["product_id"],
            sku_id=case_data["sku_id"],
        )
        list_response = cart_api.cart_list()

        if response is not None:
            verify_cart_add_rejected(
                response,
                success_code=case_data["success_business_code"],
            )
        verify_cart_count_unchanged(
            before_count,
            after_count,
            product_id=case_data["product_id"],
            sku_id=case_data["sku_id"],
        )
        verify_cart_item_absent(
            list_response,
            expected_code=case_data["success_business_code"],
            expected_product_id=case_data["product_id"],
            expected_sku_id=case_data["sku_id"],
            unexpected_quantity=case_data["quantity"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_022 加入购物车数量超大时失败")
    def test_add_cart_excessive_quantity_failed(self, cart_api, test_conn):
        """TC_ECOM_022 验证超大数量因库存规则被拒绝"""
        case_data = ADD_CART_DATA["TC_ECOM_022"][0]
        cart_queries = CartQueries(test_conn)
        clear_response = cart_api.clear_cart()
        verify_business_code(clear_response, case_data["success_business_code"])
        before_count = cart_queries.count_active_member_sku_items(
            member_username=case_data["member_username"],
            product_id=case_data["product_id"],
            sku_id=case_data["sku_id"],
        )

        response = cart_api.add_cart(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        after_count = cart_queries.count_active_member_sku_items(
            member_username=case_data["member_username"],
            product_id=case_data["product_id"],
            sku_id=case_data["sku_id"],
        )
        list_response = cart_api.cart_list()

        verify_cart_add_rejected(
            response,
            success_code=case_data["success_business_code"],
            expected_message_keywords=case_data["expected_message_keywords"],
        )
        verify_cart_count_unchanged(
            before_count,
            after_count,
            product_id=case_data["product_id"],
            sku_id=case_data["sku_id"],
        )
        verify_cart_item_absent(
            list_response,
            expected_code=case_data["success_business_code"],
            expected_product_id=case_data["product_id"],
            expected_sku_id=case_data["sku_id"],
            unexpected_quantity=case_data["quantity"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_023 加购数量超过 SKU 库存时失败")
    def test_add_cart_quantity_over_stock_failed(
        self,
        cart_api,
        product_api,
        test_conn,
    ):
        """TC_ECOM_023 验证加购数量超过 SKU 库存时不写入购物车"""
        case_data = ADD_CART_DATA["TC_ECOM_023"][0]
        restore_sku_stock_precondition(
            test_conn,
            case_id="TC_ECOM_023",
            sku_id=case_data["sku_id"],
            stock=case_data["expected_stock"],
        )
        cart_queries = CartQueries(test_conn)
        detail_response = product_api.search_product_detail(case_data["product_id"])
        verify_sku_stock(
            detail_response,
            expected_sku_id=case_data["sku_id"],
            expected_stock=case_data["expected_stock"],
            expected_code=case_data["success_business_code"],
        )
        clear_response = cart_api.clear_cart()
        verify_business_code(clear_response, case_data["success_business_code"])
        before_count = cart_queries.count_active_member_sku_items(
            member_username=case_data["member_username"],
            product_id=case_data["product_id"],
            sku_id=case_data["sku_id"],
        )

        response = cart_api.add_cart(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        after_count = cart_queries.count_active_member_sku_items(
            member_username=case_data["member_username"],
            product_id=case_data["product_id"],
            sku_id=case_data["sku_id"],
        )
        list_response = cart_api.cart_list()

        verify_cart_add_rejected(
            response,
            success_code=case_data["success_business_code"],
            expected_message_keywords=case_data["expected_message_keywords"],
        )
        verify_cart_count_unchanged(
            before_count,
            after_count,
            product_id=case_data["product_id"],
            sku_id=case_data["sku_id"],
        )
        verify_cart_item_absent(
            list_response,
            expected_code=case_data["success_business_code"],
            expected_product_id=case_data["product_id"],
            expected_sku_id=case_data["sku_id"],
            unexpected_quantity=case_data["quantity"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_024 未登录用户加入购物车失败")
    def test_unauthenticated_add_cart_failed(
        self,
        cart_api,
        portal_public_session,
        test_conn,
    ):
        """TC_ECOM_024 验证未登录请求被拒绝且购物车无新增记录"""
        case_data = ADD_CART_DATA["TC_ECOM_024"][0]
        public_cart_api = CartItemAPI(portal_public_session)
        cart_queries = CartQueries(test_conn)
        clear_response = cart_api.clear_cart()
        verify_business_code(clear_response, case_data["success_business_code"])
        before_count = cart_queries.count_active_member_sku_items(
            member_username=case_data["member_username"],
            product_id=case_data["product_id"],
            sku_id=case_data["sku_id"],
        )

        response = None
        try:
            response = public_cart_api.add_cart(
                product_id=case_data["product_id"],
                product_sku_id=case_data["sku_id"],
                quantity=case_data["quantity"],
            )
        except AssertionError as error:
            verify_cart_http_rejected(error, case_data["expected_http_status"])
        after_count = cart_queries.count_active_member_sku_items(
            member_username=case_data["member_username"],
            product_id=case_data["product_id"],
            sku_id=case_data["sku_id"],
        )
        list_response = cart_api.cart_list()

        if response is not None:
            verify_cart_add_rejected(
                response,
                success_code=case_data["success_business_code"],
                expected_message_keywords=case_data["expected_message_keywords"],
            )
        verify_cart_count_unchanged(
            before_count,
            after_count,
            product_id=case_data["product_id"],
            sku_id=case_data["sku_id"],
        )
        verify_cart_item_absent(
            list_response,
            expected_code=case_data["success_business_code"],
            expected_product_id=case_data["product_id"],
            expected_sku_id=case_data["sku_id"],
            unexpected_quantity=case_data["quantity"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_025 不存在商品加入购物车失败")
    def test_nonexistent_product_add_cart_failed(self, cart_api, test_conn):
        """TC_ECOM_025 验证不存在的 productId 不能加入购物车"""
        case_data = ADD_CART_DATA["TC_ECOM_025"][0]
        cart_queries = CartQueries(test_conn)
        clear_response = cart_api.clear_cart()
        verify_business_code(clear_response, case_data["success_business_code"])
        before_count = cart_queries.count_active_member_sku_items(
            member_username=case_data["member_username"],
            product_id=case_data["product_id"],
            sku_id=case_data["sku_id"],
        )

        response = cart_api.add_cart(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        after_count = cart_queries.count_active_member_sku_items(
            member_username=case_data["member_username"],
            product_id=case_data["product_id"],
            sku_id=case_data["sku_id"],
        )
        list_response = cart_api.cart_list()

        verify_cart_add_rejected(
            response,
            success_code=case_data["success_business_code"],
            expected_message_keywords=case_data["expected_message_keywords"],
        )
        verify_cart_count_unchanged(
            before_count,
            after_count,
            product_id=case_data["product_id"],
            sku_id=case_data["sku_id"],
        )
        verify_cart_item_absent(
            list_response,
            expected_code=case_data["success_business_code"],
            expected_product_id=case_data["product_id"],
            expected_sku_id=case_data["sku_id"],
            unexpected_quantity=case_data["quantity"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_026 商品和SKU不匹配时加购失败")
    def test_product_sku_mismatch_add_cart_failed(self, cart_api, test_conn):
        """TC_ECOM_026 验证 productId 与 productSkuId 不匹配时不写入购物车"""
        case_data = ADD_CART_DATA["TC_ECOM_026"][0]
        cart_queries = CartQueries(test_conn)
        clear_response = cart_api.clear_cart()
        verify_business_code(clear_response, case_data["success_business_code"])
        before_count = cart_queries.count_active_member_sku_items(
            member_username=case_data["member_username"],
            product_id=case_data["product_id"],
            sku_id=case_data["sku_id"],
        )

        response = cart_api.add_cart(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        after_count = cart_queries.count_active_member_sku_items(
            member_username=case_data["member_username"],
            product_id=case_data["product_id"],
            sku_id=case_data["sku_id"],
        )
        list_response = cart_api.cart_list()

        verify_cart_add_rejected(
            response,
            success_code=case_data["success_business_code"],
            expected_message_keywords=case_data["expected_message_keywords"],
        )
        verify_cart_count_unchanged(
            before_count,
            after_count,
            product_id=case_data["product_id"],
            sku_id=case_data["sku_id"],
        )
        verify_cart_item_absent(
            list_response,
            expected_code=case_data["success_business_code"],
            expected_product_id=case_data["product_id"],
            expected_sku_id=case_data["sku_id"],
            unexpected_quantity=case_data["quantity"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_027 购物车列表返回完整购物车项")
    def test_cart_list_returns_complete_item(self, cart_api, product_api):
        """TC_ECOM_027 验证列表返回 cartId、skuId、数量和价格"""
        case_data = ADD_CART_DATA["TC_ECOM_027"][0]
        cart_helper = PortalCartHelper(cart_api, product_api)
        clear_response = cart_api.clear_cart()
        verify_business_code(clear_response, case_data["expected_business_code"])

        cart_response = cart_helper.add_cart(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        list_response = cart_api.cart_list()

        verify_cart_add_success(cart_response, case_data["expected_business_code"])
        verify_cart_list_contains_item(
            list_response,
            expected_code=case_data["expected_business_code"],
            expected_product_id=case_data["product_id"],
            expected_sku_id=case_data["sku_id"],
            expected_quantity=case_data["quantity"],
            required_fields=case_data["required_cart_item_fields"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_028 清空购物车后列表为空")
    def test_cart_list_empty_after_clear(self, cart_api, product_api):
        """TC_ECOM_028 验证清空购物车后列表为空"""
        case_data = ADD_CART_DATA["TC_ECOM_028"][0]
        add_data = ADD_CART_DATA["TC_ECOM_018"][0]
        cart_helper = PortalCartHelper(cart_api, product_api)
        initial_clear_response = cart_api.clear_cart()
        verify_business_code(
            initial_clear_response,
            case_data["expected_business_code"],
        )
        add_response = cart_helper.add_cart(
            product_id=add_data["product_id"],
            product_sku_id=add_data["sku_id"],
            quantity=add_data["quantity"],
        )
        verify_cart_add_success(add_response, case_data["expected_business_code"])

        clear_response = cart_api.clear_cart()
        list_response = cart_api.cart_list()

        verify_business_code(clear_response, case_data["expected_business_code"])
        verify_cart_list_empty(
            list_response,
            expected_code=case_data["expected_business_code"],
            expected_item_count=case_data["expected_cart_item_count"],
        )

    @pytest.mark.p0
    @pytest.mark.title("TC_ECOM_029 按商品信息获取最新 cartId")
    def test_get_latest_cart_id_by_item(self, cart_api, product_api):
        """TC_ECOM_029 验证按商品、SKU 和数量定位最新 cartId"""
        case_data = ADD_CART_DATA["TC_ECOM_029"][0]
        cart_helper = PortalCartHelper(cart_api, product_api)
        clear_response = cart_api.clear_cart()
        verify_business_code(clear_response, case_data["expected_business_code"])
        add_response = cart_helper.add_cart(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        verify_cart_add_success(add_response, case_data["expected_business_code"])

        cart_id = cart_helper.find_id(
            product_id=case_data["product_id"],
            product_sku_id=case_data["sku_id"],
            quantity=case_data["quantity"],
        )
        list_response = cart_api.cart_list()
        cart_item = verify_cart_list_contains_item(
            list_response,
            expected_code=case_data["expected_business_code"],
            expected_product_id=case_data["product_id"],
            expected_sku_id=case_data["sku_id"],
            expected_quantity=case_data["quantity"],
            required_fields=case_data["required_cart_item_fields"],
        )

        verify_cart_id_matches_item(cart_id, cart_item)
