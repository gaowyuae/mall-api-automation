from config.settings.portal_path import PORTAL_CART_ITEM_API_PATHS
from core.http_client import BaseAPI


class CartItemAPI(BaseAPI):
    def add_cart(
        self,
        product_id=None,
        product_sku_id=None,
        quantity=None,
        product_snapshot=None,
        enable=True,
    ):
        """调用加入购物车接口"""
        payload = {
            "productId": product_id,
            "productSkuId": product_sku_id,
            "quantity": quantity,
        }

        self.validate_required(
            "add_cart",
            payload,
            ["productId", "productSkuId", "quantity"],
            enable,
        )

        if product_snapshot:
            payload.update(product_snapshot)

        response = self.post(PORTAL_CART_ITEM_API_PATHS["CART_ADD"], json_data=payload)
        self.assert_http_ok(response, "add_cart")

        return self.to_json(response)

    def cart_list(self):
        """获取当前用户购物车列表"""
        response = self.get(PORTAL_CART_ITEM_API_PATHS["CART_LIST"])
        self.assert_http_ok(response, "list_cart")
        return self.to_json(response)

    def clear_cart(self):
        """清空当前用户购物车"""
        response = self.post(PORTAL_CART_ITEM_API_PATHS["CART_CLEAR"])
        self.assert_http_ok(response, "clear_cart")
        return self.to_json(response)


def add_cart(
    session,
    product_id=None,
    product_sku_id=None,
    quantity=None,
    enable=True,
    product_snapshot=None,
):
    return CartItemAPI(session).add_cart(
        product_id=product_id,
        product_sku_id=product_sku_id,
        quantity=quantity,
        enable=enable,
        product_snapshot=product_snapshot,
    )


def cart_list(session):
    return CartItemAPI(session).cart_list()


def clear_cart(session):
    return CartItemAPI(session).clear_cart()
