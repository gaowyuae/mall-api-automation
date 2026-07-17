from api_support.portal.order_helper import PortalOrderHelper
from workflow.portal.order_workflow import PortalOrderWorkflow


class AdminOrderWorkflow:
    """编排后台发货及前台收货场景所需的订单状态准备"""

    def __init__(
        self,
        cart_api,
        product_api,
        address_api,
        portal_order_api,
        admin_order_api,
    ):
        self.portal_order_api = portal_order_api
        self.admin_order_api = admin_order_api
        self.portal_workflow = PortalOrderWorkflow(
            cart_api=cart_api,
            product_api=product_api,
            address_api=address_api,
            order_api=portal_order_api,
        )

    def prepare_paid_order(
        self,
        product_id,
        product_sku_id,
        quantity,
        pay_type,
    ):
        """创建待支付订单并推进为待发货"""
        order_context = self.prepare_pending_order(
            product_id=product_id,
            product_sku_id=product_sku_id,
            quantity=quantity,
            pay_type=pay_type,
        )
        order_id = PortalOrderHelper.get_order_id(order_context["generate_response"])
        payment_context = self.portal_workflow.attempt_payment(
            order_id=order_id,
            pay_type=pay_type,
        )
        return {
            **order_context,
            "payment_context": payment_context,
            "paid_detail_response": payment_context["after_detail_response"],
        }

    def prepare_pending_order(
        self,
        product_id,
        product_sku_id,
        quantity,
        pay_type,
    ):
        """创建待支付订单供后台状态校验场景使用"""
        prepared_context = self.portal_workflow.prepare_order(
            product_id=product_id,
            product_sku_id=product_sku_id,
            quantity=quantity,
        )
        return self.portal_workflow.generate_order(
            prepared_context,
            pay_type=pay_type,
        )

    def attempt_delivery(
        self,
        order_id,
        delivery_company,
        delivery_sn,
    ):
        """查询后台订单、发货并读取前后台最新详情"""
        before_admin_detail = self.admin_order_api.order_detail(order_id=order_id)
        delivery_response = self.admin_order_api.update_delivery(
            order_id=order_id,
            delivery_company=delivery_company,
            delivery_sn=delivery_sn,
        )
        after_admin_detail = self.admin_order_api.order_detail(order_id=order_id)
        portal_detail = self.portal_order_api.order_detail(order_id=order_id)
        return {
            "order_id": order_id,
            "before_admin_detail": before_admin_detail,
            "delivery_response": delivery_response,
            "after_admin_detail": after_admin_detail,
            "portal_detail": portal_detail,
        }

    def prepare_shipped_order(
        self,
        product_id,
        product_sku_id,
        quantity,
        pay_type,
        delivery_company,
        delivery_sn,
    ):
        """创建、支付并发货，返回待收货订单上下文"""
        paid_context = self.prepare_paid_order(
            product_id=product_id,
            product_sku_id=product_sku_id,
            quantity=quantity,
            pay_type=pay_type,
        )
        delivery_context = self.attempt_delivery(
            order_id=paid_context["order_id"],
            delivery_company=delivery_company,
            delivery_sn=delivery_sn,
        )
        return {
            **paid_context,
            "delivery_context": delivery_context,
            "shipped_detail_response": delivery_context["portal_detail"],
        }
