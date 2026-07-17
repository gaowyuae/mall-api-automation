from core.logkit import get_logger

support_logger = get_logger("api_support.admin.order")


class AdminOrderHelper:
    @staticmethod
    def _get_data(response):
        if not isinstance(response, dict):
            support_logger.warning(
                "后台订单响应类型不对，实际是 %s",
                type(response).__name__,
                extra={"event": "api_support.admin.order.invalid"},
            )
            return {}

        data = response.get("data") or {}
        if isinstance(data, dict | list):
            return data

        support_logger.warning(
            "后台订单 data 类型不对，实际是 %s",
            type(data).__name__,
            extra={"event": "api_support.admin.order.data_invalid"},
        )
        return {}

    @staticmethod
    def get_order_list(response):
        """返回统一的后台订单列表和总数"""
        data = AdminOrderHelper._get_data(response)
        if isinstance(data, list):
            return {"orders": data, "total": len(data)}

        orders = next(
            (
                data[field]
                for field in ("list", "records", "content")
                if isinstance(data.get(field), list)
            ),
            [],
        )
        total = next(
            (
                data[field]
                for field in ("total", "totalElements", "totalCount")
                if data.get(field) is not None
            ),
            len(orders),
        )
        return {"orders": orders, "total": total}

    @staticmethod
    def get_order_detail(response):
        data = AdminOrderHelper._get_data(response)
        if not isinstance(data, dict):
            return {}

        for field in ("order", "orderDetail", "orderInfo"):
            order_detail = data.get(field)
            if isinstance(order_detail, dict):
                return order_detail
        return data

    @classmethod
    def get_order_id(cls, response):
        return cls.get_order_detail(response).get("id")

    @classmethod
    def get_order_status(cls, response):
        return cls.get_order_detail(response).get("status")

    @classmethod
    def get_delivery_state(cls, response):
        detail = cls.get_order_detail(response)
        fields = (
            "id",
            "status",
            "deliveryCompany",
            "deliverySn",
            "deliveryTime",
            "receiveTime",
        )
        return {field: detail.get(field) for field in fields}
