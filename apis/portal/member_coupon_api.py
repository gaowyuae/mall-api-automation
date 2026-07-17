from config.settings.portal_path import PORTAL_MEMBER_COUPON_API_PATHS
from core.http_client import BaseAPI


class MemberCouponAPI(BaseAPI):
    def add_coupon(self, coupon_id=None, enable=True):
        payload = {"couponId": coupon_id}

        self.validate_required(
            "add_coupon",
            payload,
            ["couponId"],
            enable,
        )

        response = self.post(
            PORTAL_MEMBER_COUPON_API_PATHS["COUPON_ADD"].format(couponId=coupon_id),
        )

        self.assert_http_ok(response, "add_coupon")
        return self.to_json(response)

    def member_coupon_list(self, use_status=None):
        params = {"useStatus": use_status}

        response = self.get(
            PORTAL_MEMBER_COUPON_API_PATHS["COUPON_LIST"],
            params=params,
        )

        self.assert_http_ok(response, "list_coupon")
        return self.to_json(response)

    def member_coupon_history_list(self, use_status=None):
        params = {"useStatus": use_status}

        response = self.get(
            PORTAL_MEMBER_COUPON_API_PATHS["COUPON_LIST_HISTORY"],
            params=params,
        )

        self.assert_http_ok(response, "list_coupon_history")
        return self.to_json(response)

    def cart_coupon_list(self, coupon_type=None, enable=True):
        payload = {"type": coupon_type}

        self.validate_required(
            "list_cart_coupon",
            payload,
            ["type"],
            enable,
        )

        response = self.get(
            PORTAL_MEMBER_COUPON_API_PATHS["COUPON_LIST_CART"].format(type=coupon_type),
        )

        self.assert_http_ok(response, "list_cart_coupon")
        return self.to_json(response)

    def coupon_list_by_product(self, product_id=None, enable=True):
        payload = {"productId": product_id}

        self.validate_required(
            "list_coupon_by_product",
            payload,
            ["productId"],
            enable,
        )

        response = self.get(
            PORTAL_MEMBER_COUPON_API_PATHS["COUPON_LIST_BY_PRODUCT"].format(
                productId=product_id
            ),
        )

        self.assert_http_ok(response, "list_coupon_by_product")
        return self.to_json(response)


def add_coupon(session, coupon_id=None, enable=True):
    return MemberCouponAPI(session).add_coupon(coupon_id, enable)


def member_coupon_list(session, use_status=None):
    return MemberCouponAPI(session).member_coupon_list(use_status)


def member_coupon_history_list(session, use_status=None):
    return MemberCouponAPI(session).member_coupon_history_list(use_status)


def cart_coupon_list(session, coupon_type=None, enable=True):
    return MemberCouponAPI(session).cart_coupon_list(coupon_type, enable)


def coupon_list_by_product(session, product_id=None, enable=True):
    return MemberCouponAPI(session).coupon_list_by_product(product_id, enable)
