import os

ADMIN_BASE_URL = os.getenv("ADMIN_BASE_URL", "http://localhost:8080/")

ADMIN_SSO_API_PATHS = {
    "LOGIN": "admin/login",
    "LOGOUT": "admin/logout",
}

ADMIN_ORDER_API_PATHS = {
    "ORDER_LIST": "order/list",
    "ORDER_DETAIL": "order/{id}",
    "ORDER_UPDATE_DELIVERY": "order/update/delivery",
}

ADMIN_ENDPOINT_GROUPS = {
    "SSO": ADMIN_SSO_API_PATHS,
    "ORDER": ADMIN_ORDER_API_PATHS,
}
