from api_support.portal.product_helper import PortalProductHelper
from apis.portal.cart_item_api import CartItemAPI


class PortalCartHelper:
    """处理加入购物车及购物车项查找"""

    def __init__(self, cart_api, product_api=None):
        self.cart_api = cart_api
        self.product_api = product_api

    @staticmethod
    def get_items(response):

        if not isinstance(response, dict):
            return None

        cart_items = response.get("data")
        if not isinstance(cart_items, list):
            return None
        if not all(isinstance(item, dict) for item in cart_items):
            return None
        return cart_items

    @classmethod
    def get_item_states(cls, response):
        """整理用于比较确认单调用前后状态的购物车字段"""
        cart_items = cls.get_items(response)
        if cart_items is None:
            return None

        states = [
            {
                "id": item.get("id"),
                "productId": item.get("productId"),
                "productSkuId": item.get("productSkuId"),
                "quantity": item.get("quantity"),
                "price": item.get("price"),
            }
            for item in cart_items
        ]
        return sorted(states, key=lambda item: str(item.get("id")))

    def add_cart(
        self,
        product_id=None,
        product_sku_id=None,
        quantity=None,
        with_snapshot=True,
        enable=True,
    ):
        """整理商品快照后调用加入购物车接口"""
        product_snapshot = None
        if with_snapshot and product_id is not None and product_sku_id is not None:
            if self.product_api is None:
                raise ValueError("获取商品快照需要传入 product_api")
            product_snapshot = PortalProductHelper.get_product_snapshot(
                self.product_api,
                product_id,
                product_sku_id,
            )

        return self.cart_api.add_cart(
            product_id=product_id,
            product_sku_id=product_sku_id,
            quantity=quantity,
            product_snapshot=product_snapshot,
            enable=enable,
        )

    @staticmethod
    def _is_match(item, product_id, product_sku_id, quantity):
        """匹配相对应的商品ID SKU ID以及商品数量"""
        if product_id is not None and str(item.get("productId")) != str(product_id):
            return False
        if product_sku_id is not None and str(item.get("productSkuId")) != str(
            product_sku_id
        ):
            return False
        return quantity is None or str(item.get("quantity")) == str(quantity)

    @staticmethod
    def _cart_id_sort_key(item):
        cart_item_id = item.get("id")
        try:
            return (1, int(cart_item_id))
        except (TypeError, ValueError):
            return (0, str(cart_item_id))

    @classmethod
    def find_items_in_response(
        cls,
        response,
        product_id=None,
        product_sku_id=None,
        quantity=None,
    ):
        """从已返回的购物车列表中查找匹配的购物车项"""
        cart_items = cls.get_items(response) or []
        return [
            item
            for item in cart_items
            if cls._is_match(item, product_id, product_sku_id, quantity)
        ]

    @classmethod
    def find_latest_item_in_response(
        cls,
        response,
        product_id=None,
        product_sku_id=None,
        quantity=None,
    ):
        """从已返回的购物车列表中返回最新匹配记录"""
        matched_items = cls.find_items_in_response(
            response,
            product_id=product_id,
            product_sku_id=product_sku_id,
            quantity=quantity,
        )
        if not matched_items:
            return None
        return max(matched_items, key=cls._cart_id_sort_key)

    def find_item(
        self,
        product_id=None,
        product_sku_id=None,
        quantity=None,
    ):
        response = self.cart_api.cart_list()
        cart_item = self.find_latest_item_in_response(
            response,
            product_id=product_id,
            product_sku_id=product_sku_id,
            quantity=quantity,
        )

        if not cart_item:
            raise LookupError(
                f"未找到匹配购物车项：product_id={product_id}，"
                f"product_sku_id={product_sku_id}，quantity={quantity}"
            )

        return cart_item

    def find_items(
        self,
        product_id=None,
        product_sku_id=None,
    ):
        """从购物车列表中查找符合商品 ID 和 SKU ID 的购物车记录"""
        response = self.cart_api.cart_list()
        return self.find_items_in_response(
            response,
            product_id=product_id,
            product_sku_id=product_sku_id,
        )

    def find_id(
        self,
        product_id=None,
        product_sku_id=None,
        quantity=None,
    ):

        cart_item = self.find_item(
            product_id=product_id,
            product_sku_id=product_sku_id,
            quantity=quantity,
        )
        cart_id = cart_item.get("id")
        if cart_id is None:
            raise LookupError(f"匹配到购物车项但 id 为空：{cart_item}")
        return cart_id


def find_cart_id(
    session,
    product_id=None,
    product_sku_id=None,
    quantity=None,
):

    helper = PortalCartHelper(CartItemAPI(session))
    return helper.find_id(
        product_id=product_id,
        product_sku_id=product_sku_id,
        quantity=quantity,
    )
