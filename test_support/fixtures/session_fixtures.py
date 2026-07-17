import pytest

from config.settings.admin_path import ADMIN_BASE_URL
from config.settings.portal_path import PORTAL_BASE_URL
from test_support.fixtures._session_helpers import build_session


@pytest.fixture
def portal_public_session():
    session = build_session(PORTAL_BASE_URL)
    yield session
    session.close()


@pytest.fixture
def portal_session(portal_authorization):
    session = build_session(PORTAL_BASE_URL)
    session.headers["Authorization"] = portal_authorization
    yield session
    session.close()


@pytest.fixture
def admin_public_session():
    session = build_session(ADMIN_BASE_URL)
    yield session
    session.close()


@pytest.fixture
def admin_session(admin_authorization):
    session = build_session(ADMIN_BASE_URL)
    session.headers["Authorization"] = admin_authorization
    yield session
    session.close()
