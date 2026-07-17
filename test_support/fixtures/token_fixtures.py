import pytest

from apis.admin.login_api import AdminLoginAPI
from config.settings.admin_path import ADMIN_BASE_URL, ADMIN_SSO_API_PATHS
from config.settings.portal_path import PORTAL_BASE_URL, PORTAL_SSO_API_PATHS
from config.settings.test_accounts import (
    ADMIN_TEST_PASSWORD,
    ADMIN_TEST_USERNAME,
    PORTAL_TEST_PASSWORD,
    PORTAL_TEST_USERNAME,
)
from core.http_client import req_post
from core.logkit import bind_context, get_context, get_logger, new_trace_id
from test_support.fixtures._session_helpers import (
    assert_success,
    build_session,
    extract_login_auth,
)

app_logger = get_logger("app")


def _login_auth(case_id, session, path, action, **kwargs):
    previous_context = get_context()
    bind_context(trace_id=new_trace_id(), case_id=case_id, request_id="-")
    try:
        response = req_post(session, path, **kwargs)
        return extract_login_auth(response, action)
    finally:
        bind_context(**previous_context)


def _logout_admin_auth(session):
    """后台认证模块清理 测试会话结束后登出"""
    previous_context = get_context()
    bind_context(
        trace_id=new_trace_id(),
        case_id="session::admin_auth_cleanup",
        request_id="-",
    )
    try:
        response = AdminLoginAPI(session).logout()
        assert_success(response)
        app_logger.info(
            "后台认证信息登出销毁成功",
            extra={
                "event": "logout.auth.success",
                "action": "admin_logout",
            },
        )
    finally:
        bind_context(**previous_context)


@pytest.fixture(scope="session")
def portal_auth():
    session = build_session(PORTAL_BASE_URL)
    try:
        token, authorization = _login_auth(
            "session::portal_auth",
            session,
            PORTAL_SSO_API_PATHS["LOGIN"],
            "portal_login",
            params={
                "password": PORTAL_TEST_PASSWORD,
                "username": PORTAL_TEST_USERNAME,
            },
        )
        yield {
            "token": token,
            "authorization": authorization,
        }
    finally:
        session.close()


@pytest.fixture(scope="session")
def admin_auth():
    """后台认证模块 Fixture 登录复用并在会话结束后登出"""
    session = build_session(ADMIN_BASE_URL)
    authorization = None
    try:
        token, authorization = _login_auth(
            "session::admin_auth",
            session,
            ADMIN_SSO_API_PATHS["LOGIN"],
            "admin_login",
            json_data={
                "password": ADMIN_TEST_PASSWORD,
                "username": ADMIN_TEST_USERNAME,
            },
        )
        yield {
            "token": token,
            "authorization": authorization,
        }
    finally:
        try:
            if authorization:
                session.headers["Authorization"] = authorization
                _logout_admin_auth(session)
        finally:
            session.headers.pop("Authorization", None)
            session.close()


@pytest.fixture(scope="session")
def portal_token(portal_auth):
    return portal_auth["token"]


@pytest.fixture(scope="session")
def portal_authorization(portal_auth):
    return portal_auth["authorization"]


@pytest.fixture(scope="session")
def admin_token(admin_auth):
    return admin_auth["token"]


@pytest.fixture(scope="session")
def admin_authorization(admin_auth):
    return admin_auth["authorization"]
