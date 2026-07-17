import pytest

from config.settings.database import DB_CONFIG


@pytest.fixture(scope="session")
def db_pool():
    from core.conn_mysql import Database

    db = Database(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        database=DB_CONFIG["database"],
        charset=DB_CONFIG["charset"],
    )
    yield db
    db.close()


@pytest.fixture
def test_conn(db_pool):
    from core.conn_mysql import DBConnection

    with db_pool.connection() as conn:
        db_conn = DBConnection(conn)
        yield db_conn
