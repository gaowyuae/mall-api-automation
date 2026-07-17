import os

REQUEST_TIMEOUT = (
    float(os.getenv("REQUEST_CONNECT_TIMEOUT", "5")),
    float(os.getenv("REQUEST_READ_TIMEOUT", "15")),
)

ORDER_PAY_TYPES = {
    "ALIPAY": 1,
}
