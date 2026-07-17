from config.settings.portal_path import PORTAL_ORDER_API_PATHS
from core.http_client import BaseAPI


class OrderAPI(BaseAPI):
    @staticmethod
    def _transform_list(cart_id):
        if cart_id is None:
            return None
        if isinstance(cart_id, list):
            return cart_id
        return [cart_id]

    def generate_order(
        self,
        cart_id=None,
        pay_type=1,
        member_receive_address_id=None,
        coupon_id=None,
        use_integration=0,
        enable=True,
    ):
        cart_id = self._transform_list(cart_id)

        payload = {
            "cartIds": cart_id,
            "payType": pay_type,
            "memberReceiveAddressId": member_receive_address_id,
            "couponId": coupon_id,
            "useIntegration": use_integration,
        }

        self.validate_required(
            "generate_order",
            payload,
            [
                "cartIds",
                "payType",
                "memberReceiveAddressId",
            ],
            enable,
        )

        response = self.post(
            PORTAL_ORDER_API_PATHS["ORDER_GENERATE"],
            json_data={
                key: value for key, value in payload.items() if value is not None
            },
        )

        self.assert_http_ok(response, "generate_order")
        return self.to_json(response)

    def order_detail(self, order_id=None, enable=True):
        payload = {"orderId": order_id}

        self.validate_required("order_detail", payload, ["orderId"], enable)

        response = self.get(
            PORTAL_ORDER_API_PATHS["ORDER_DETAIL"].format(orderId=order_id)
        )

        self.assert_http_ok(response, "order_detail")
        return self.to_json(response)

    def generate_confirm(self, cart_id=None, enable=True):
        cart_id = self._transform_list(cart_id)

        payload = {"cartIds": cart_id}

        self.validate_required("generate_confirm", payload, ["cartIds"], enable)

        response = self.post(PORTAL_ORDER_API_PATHS["ORDER_CONFIRM"], json_data=cart_id)

        self.assert_http_ok(response, "generate_confirm")
        return self.to_json(response)

    def cancel_order(self, order_id=None, enable=True):
        payload = {"orderId": order_id}

        self.validate_required("cancel_order", payload, ["orderId"], enable)

        response = self.post(PORTAL_ORDER_API_PATHS["ORDER_CANCEL"], params=payload)

        self.assert_http_ok(response, "cancel_order")
        return self.to_json(response)

    def confirm_receive(self, order_id=None, enable=True):
        payload = {"orderId": order_id}

        self.validate_required("confirm_receive", payload, ["orderId"], enable)
        response = self.post(
            PORTAL_ORDER_API_PATHS["ORDER_CONFIRM_RECEIVE"], params=payload
        )

        self.assert_http_ok(response, "confirm_receive")
        return self.to_json(response)

    def pay_success(self, order_id=None, paytype=None, enable=True):
        payload = {"orderId": order_id, "payType": paytype}
        self.validate_required("pay_success", payload, ["orderId", "payType"], enable)

        response = self.post(
            PORTAL_ORDER_API_PATHS["ORDER_PAY_SUCCESS"], params=payload
        )

        self.assert_http_ok(response, "pay_success")
        return self.to_json(response)


def generate_order(
    session,
    cart_id=None,
    pay_type=1,
    member_receive_address_id=None,
    coupon_id=None,
    use_integration=0,
    enable=True,
):
    return OrderAPI(session).generate_order(
        cart_id,
        pay_type,
        member_receive_address_id,
        coupon_id,
        use_integration,
        enable,
    )


def generate_confirm(session, cart_id=None, enable=True):
    return OrderAPI(session).generate_confirm(cart_id, enable)


def order_detail(session, order_id=None, enable=True):
    return OrderAPI(session).order_detail(order_id, enable)


def cancel_order(session, order_id=None, enable=True):
    return OrderAPI(session).cancel_order(order_id, enable)


def confirm_receive(session, order_id=None, enable=True):
    return OrderAPI(session).confirm_receive(order_id, enable)


def pay_success(session, order_id=None, paytype=None, enable=True):
    return OrderAPI(session).pay_success(order_id, paytype, enable)
