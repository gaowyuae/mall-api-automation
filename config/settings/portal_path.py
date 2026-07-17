import os

PORTAL_BASE_URL = os.getenv("PORTAL_BASE_URL", "http://localhost:8085/")

PORTAL_SSO_API_PATHS = {
    "LOGIN": "sso/login",
}

PORTAL_CART_ITEM_API_PATHS = {
    "CART_ADD": "cart/add",
    "CART_LIST": "cart/list",
    "CART_CLEAR": "cart/clear",
}

PORTAL_ORDER_API_PATHS = {
    "ORDER_CONFIRM": "order/generateConfirmOrder",
    "ORDER_GENERATE": "order/generateOrder",
    "ORDER_DETAIL": "order/detail/{orderId}",
    "ORDER_CANCEL": "order/cancelUserOrder",
    "ORDER_PAY_SUCCESS": "order/paySuccess",
    "ORDER_CONFIRM_RECEIVE": "order/confirmReceiveOrder",
}

PORTAL_MEMBER_API_PATHS = {
    "MEMBER_INFO": "sso/info",
}

PORTAL_MEMBER_COUPON_API_PATHS = {
    "COUPON_ADD": "member/coupon/add/{couponId}",
    "COUPON_LIST": "member/coupon/list",
    "COUPON_LIST_CART": "member/coupon/list/cart/{type}",
    "COUPON_LIST_BY_PRODUCT": "member/coupon/listByProduct/{productId}",
    "COUPON_LIST_HISTORY": "member/coupon/listHistory",
}

PORTAL_MEMBER_RECEIVE_ADDRESS_API_PATHS = {
    "ADDRESS_LIST": "member/address/list",
}

PORTAL_PRODUCT_API_PATHS = {
    "PRODUCT_DETAIL": "product/detail/{id}",
    "PRODUCT_SEARCH": "product/search",
}

PORTAL_ENDPOINT_GROUPS = {
    "SSO": PORTAL_SSO_API_PATHS,
    "CART_ITEM": PORTAL_CART_ITEM_API_PATHS,
    "ORDER": PORTAL_ORDER_API_PATHS,
    "MEMBER": PORTAL_MEMBER_API_PATHS,
    "MEMBER_COUPON": PORTAL_MEMBER_COUPON_API_PATHS,
    "MEMBER_RECEIVE_ADDRESS": PORTAL_MEMBER_RECEIVE_ADDRESS_API_PATHS,
    "PRODUCT": PORTAL_PRODUCT_API_PATHS,
}
