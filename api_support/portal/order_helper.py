
from api_support.common.response_helper import ApiResponseHelper
from core.logkit import get_logger

support_logger = get_logger("api_support.portal.order")


class PortalOrderHelper:
    @staticmethod
    def get_confirm_data(response):
        """返回订单确认单 data"""
        data = ApiResponseHelper.get_data(response)
        return data if isinstance(data, dict) else None

    @classmethod
    def get_confirm_items(cls, response):
        """返回订单确认单中的购物车商品行"""
        data = cls.get_confirm_data(response)
        if data is None:
            return None

        items = data.get("cartPromotionItemList")
        if not isinstance(items, list):
            return None
        if not all(isinstance(item, dict) for item in items):
            return None
        return items

    @classmethod
    def get_confirm_calc_amount(cls, response):
        """返回订单确认单金额汇总"""
        data = cls.get_confirm_data(response)
        if data is None:
            return None

        calc_amount = data.get("calcAmount")
        return calc_amount if isinstance(calc_amount, dict) else None

    @classmethod
    def get_confirm_coupon_details(
        cls,
        response,
    ):
        """返回确认单中的用户优惠券明细"""
        data = cls.get_confirm_data(response)
        if data is None:
            return None

        details = data.get("couponHistoryDetailList")
        if not isinstance(details, list):
            return None
        if not all(isinstance(detail, dict) for detail in details):
            return None
        return details

    @classmethod
    def get_confirm_integration_setting(
        cls,
        response,
    ):
        """返回确认单中的积分抵扣规则"""
        data = cls.get_confirm_data(response)
        if data is None:
            return None

        setting = data.get("integrationConsumeSetting")
        return setting if isinstance(setting, dict) else None

    @classmethod
    def get_confirm_member_integration(cls, response):
        """返回确认单中的会员积分余额"""
        data = cls.get_confirm_data(response)
        return data.get("memberIntegration") if data is not None else None

    @staticmethod
    def get_order(response):
        """返回前台订单信息字典"""
        if not isinstance(response, dict):
            support_logger.warning(
                "前台订单响应类型不对，实际是 %s",
                type(response).__name__,
                extra={"event": "api_support.portal.order.invalid"},
            )
            return {}

        data = response.get("data") or {}
        if not isinstance(data, dict):
            support_logger.warning(
                "前台订单 data 不是字典，实际是 %s",
                type(data).__name__,
                extra={"event": "api_support.portal.order.data_invalid"},
            )
            return {}

        order = data.get("order")
        return order if isinstance(order, dict) else data

    @staticmethod
    def _get_field(response, field):
        order = PortalOrderHelper.get_order(response)
        value = order.get(field)
        if value is None:
            support_logger.warning(
                "前台订单响应缺少字段 %s，现有字段: %s",
                field,
                list(order),
                extra={"event": "api_support.portal.order.field_missing"},
            )
        return value

    @staticmethod
    def get_order_id(response):
        """返回订单 ID"""
        return PortalOrderHelper._get_field(response, "id")

    @staticmethod
    def get_order_status(response):
        """返回订单状态"""
        return PortalOrderHelper._get_field(response, "status")

    @staticmethod
    def get_pay_type(response):
        """返回订单支付方式"""
        return PortalOrderHelper._get_field(response, "payType")

    @staticmethod
    def get_payment_time(response):
        """返回订单支付时间"""
        return PortalOrderHelper._get_field(response, "paymentTime")

    @staticmethod
    def get_delivery_company(response):
        """返回订单物流公司"""
        return PortalOrderHelper._get_field(response, "deliveryCompany")

    @staticmethod
    def get_delivery_sn(response):
        """返回订单物流单号"""
        return PortalOrderHelper._get_field(response, "deliverySn")

    @staticmethod
    def get_delivery_time(response):
        """返回订单发货时间"""
        return PortalOrderHelper._get_field(response, "deliveryTime")

    @staticmethod
    def get_receive_time(response):
        """返回订单确认收货时间"""
        return PortalOrderHelper._get_field(response, "receiveTime")

    @staticmethod
    def get_order_items(response):
        """返回订单响应中的商品明细"""
        data = ApiResponseHelper.get_data(response)
        if not isinstance(data, dict):
            return None

        items = data.get("orderItemList")
        if not isinstance(items, list):
            return None
        if not all(isinstance(item, dict) for item in items):
            return None
        return items

    @staticmethod
    def get_pay_amount(response):
        """返回订单实付金额；没有时兼容读取订单总金额"""
        order = PortalOrderHelper.get_order(response)
        for field in ("payAmount", "totalAmount"):
            pay_amount = order.get(field)
            if pay_amount is not None:
                return pay_amount

        support_logger.warning(
            "前台订单响应缺少 payAmount 或 totalAmount，现有字段: %s",
            list(order),
            extra={"event": "api_support.portal.order.pay_amount_missing"},
        )
        return None

    @staticmethod
    def get_order_amounts(response):
        """返回订单金额及优惠券、积分字段"""
        order = PortalOrderHelper.get_order(response)
        fields = (
            "totalAmount",
            "payAmount",
            "freightAmount",
            "promotionAmount",
            "integrationAmount",
            "couponAmount",
            "discountAmount",
            "couponId",
            "useIntegration",
        )
        return {field: order.get(field) for field in fields}
