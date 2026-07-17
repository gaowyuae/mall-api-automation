import pytest

from apis.admin.login_api import AdminLoginAPI
from apis.admin.order_api import AdminOrderAPI
from apis.portal.cart_item_api import CartItemAPI
from apis.portal.login_api import PortalLoginAPI
from apis.portal.member_api import MemberAPI
from apis.portal.member_coupon_api import MemberCouponAPI
from apis.portal.member_receive_address_api import MemberReceiveAddressAPI
from apis.portal.order_api import OrderAPI
from apis.portal.product_api import PortalProductAPI


@pytest.fixture
def portal_login_api(portal_public_session):
    return PortalLoginAPI(portal_public_session)


@pytest.fixture
def address_api(portal_session):
    return MemberReceiveAddressAPI(portal_session)


@pytest.fixture
def cart_api(portal_session):
    return CartItemAPI(portal_session)


@pytest.fixture
def coupon_api(portal_session):
    return MemberCouponAPI(portal_session)


@pytest.fixture
def member_api(portal_session):
    return MemberAPI(portal_session)


@pytest.fixture
def order_api(portal_session):
    return OrderAPI(portal_session)


@pytest.fixture
def product_api(portal_session):
    return PortalProductAPI(portal_session)


@pytest.fixture
def admin_login_api(admin_public_session):
    return AdminLoginAPI(admin_public_session)


@pytest.fixture
def admin_order_api(admin_session):
    return AdminOrderAPI(admin_session)
