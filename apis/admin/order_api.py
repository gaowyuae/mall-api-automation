from config.settings.admin_path import ADMIN_ORDER_API_PATHS
from core.http_client import BaseAPI


class AdminOrderAPI(BaseAPI):
    def order_list(
        self,
        create_time=None,
        order_sn=None,
        order_type=None,
        page_num=1,
        page_size=5,
        receiver_keyword=None,
        source_type=None,
        status=None,
        enable=True,
    ):
        payload = {
            "createTime": create_time,
            "orderSn": order_sn,
            "orderType": order_type,
            "pageNum": page_num,
            "pageSize": page_size,
            "receiverKeyword": receiver_keyword,
            "sourceType": source_type,
            "status": status,
        }

        self.validate_required(
            "admin_order_list",
            payload,
            ["pageNum", "pageSize"],
            enable,
        )

        response = self.get(
            ADMIN_ORDER_API_PATHS["ORDER_LIST"],
            params={key: value for key, value in payload.items() if value is not None},
        )

        self.assert_http_ok(response, "admin_order_list")
        return self.to_json(response)

    def order_detail(self, order_id=None, enable=True):
        payload = {
            "id": order_id,
        }

        self.validate_required(
            "admin_order_detail",
            payload,
            ["id"],
            enable,
        )

        response = self.get(ADMIN_ORDER_API_PATHS["ORDER_DETAIL"].format(id=order_id))

        self.assert_http_ok(response, "admin_order_detail")
        return self.to_json(response)

    def update_delivery(
        self,
        order_id=None,
        delivery_company=None,
        delivery_sn=None,
        enable=True,
    ):
        """按后台批量发货接口要求提交发货信息。"""
        payload = {
            "orderId": order_id,
            "deliveryCompany": delivery_company,
            "deliverySn": delivery_sn,
        }

        self.validate_required(
            "update_delivery",
            payload,
            ["orderId", "deliveryCompany", "deliverySn"],
            enable,
        )

        response = self.post(
            ADMIN_ORDER_API_PATHS["ORDER_UPDATE_DELIVERY"],
            json_data=[payload],
        )

        self.assert_http_ok(response, "update_delivery")
        return self.to_json(response)


def order_list(
    session,
    create_time=None,
    order_sn=None,
    order_type=None,
    page_num=1,
    page_size=5,
    receiver_keyword=None,
    source_type=None,
    status=None,
    enable=True,
):
    return AdminOrderAPI(session).order_list(
        create_time=create_time,
        order_sn=order_sn,
        order_type=order_type,
        page_num=page_num,
        page_size=page_size,
        receiver_keyword=receiver_keyword,
        source_type=source_type,
        status=status,
        enable=enable,
    )


def order_detail(session, order_id=None, enable=True):
    return AdminOrderAPI(session).order_detail(
        order_id=order_id,
        enable=enable,
    )


def update_delivery(
    session,
    order_id=None,
    delivery_company=None,
    delivery_sn=None,
    enable=True,
):
    return AdminOrderAPI(session).update_delivery(
        order_id=order_id,
        delivery_company=delivery_company,
        delivery_sn=delivery_sn,
        enable=enable,
    )
