from api_support.portal.address_helper import PortalAddressHelper
from api_support.portal.cart_helper import PortalCartHelper
from api_support.portal.order_helper import PortalOrderHelper
from api_support.portal.product_helper import PortalProductHelper


class PortalOrderWorkflow:
    """编排订单优惠券和积分场景共用的下单流程"""

    def __init__(
        self,
        cart_api,
        product_api,
        address_api,
        order_api,
    ):
        self.cart_api = cart_api
        self.product_api = product_api
        self.address_api = address_api
        self.order_api = order_api
        self.cart_helper = PortalCartHelper(cart_api, product_api)
        self.address_helper = PortalAddressHelper(address_api)

    def prepare_order(
        self,
        product_id,
        product_sku_id,
        quantity,
        cart_price=None,
    ):
        """清理并准备购物车、地址及订单确认单上下文"""
        clear_response = self.cart_api.clear_cart()
        product_snapshot = PortalProductHelper.get_product_snapshot(
            self.product_api,
            product_id,
            product_sku_id,
        )
        if cart_price is not None:
            product_snapshot["price"] = cart_price

        add_response = self.cart_api.add_cart(
            product_id=product_id,
            product_sku_id=product_sku_id,
            quantity=quantity,
            product_snapshot=product_snapshot,
        )
        cart_id = self.cart_helper.find_id(
            product_id=product_id,
            product_sku_id=product_sku_id,
            quantity=quantity,
        )
        address_id = self.address_helper.find_id()
        confirm_response = self.order_api.generate_confirm(cart_id=cart_id)
        return {
            "clear_response": clear_response,
            "add_response": add_response,
            "cart_id": cart_id,
            "address_id": address_id,
            "confirm_response": confirm_response,
        }

    def generate_order(
        self,
        order_context,
        pay_type=1,
        coupon_id=None,
        use_integration=0,
    ):
        """根据已准备的上下文生成订单并读取订单详情"""
        generate_response = self.order_api.generate_order(
            cart_id=order_context["cart_id"],
            pay_type=pay_type,
            member_receive_address_id=order_context["address_id"],
            coupon_id=coupon_id,
            use_integration=use_integration,
        )
        order_id = PortalOrderHelper.get_order_id(generate_response)
        detail_response = None
        if order_id is not None:
            detail_response = self.order_api.order_detail(order_id=order_id)

        return {
            **order_context,
            "generate_response": generate_response,
            "order_id": order_id,
            "detail_response": detail_response,
        }

    def cancel_created_order(self, generate_response):
        """取消已创建订单，失败响应或无订单 ID 时不执行"""
        order_id = PortalOrderHelper.get_order_id(generate_response)
        if order_id is None:
            return None
        return self.order_api.cancel_order(order_id=order_id)

    def attempt_payment(self, order_id, pay_type):
        """查询订单、发起一次支付成功通知并再次读取订单"""
        before_detail_response = self.order_api.order_detail(order_id=order_id)
        pay_response = self.order_api.pay_success(
            order_id=order_id,
            paytype=pay_type,
        )
        after_detail_response = self.order_api.order_detail(order_id=order_id)
        return {
            "order_id": order_id,
            "before_detail_response": before_detail_response,
            "pay_response": pay_response,
            "after_detail_response": after_detail_response,
        }
