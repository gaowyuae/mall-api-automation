import logging
import time
from contextlib import contextmanager

from core.logkit import get_logger

sql_logger = get_logger("sql")
mysql_logger = logging.getLogger("pymysql")


class Database:
    def __init__(self, **db_mysql):
        try:
            import pymysql
            from dbutils.pooled_db import PooledDB
        except ModuleNotFoundError as e:
            raise RuntimeError(
                f"缺少依赖包:{e}, 请使用pip install -r requirements.txt安装"
            ) from e

        db_mysql["cursorclass"] = pymysql.cursors.DictCursor
        self.pool = PooledDB(
            creator=pymysql,
            mincached=2,  # 最小化连接数
            maxconnections=10,
            blocking=True,  # 控制连接数
            **db_mysql,
        )

        sql_logger.info(
            "数据库连接池初始化完成",
            extra={
                "host": db_mysql.get("host"),
                "port": db_mysql.get("port"),
                "database": db_mysql.get("database"),
            },
        )

    @contextmanager
    def connection(self):
        conn = self.pool.connection()
        sql_logger.debug("数据库连接已打开")

        try:
            yield conn
        except Exception:
            raise
        finally:
            conn.rollback()
            conn.close()
            sql_logger.debug("数据库连接已关闭")

    def close(self):
        self.pool.close()
        sql_logger.info("数据库连接池已关闭")


class DBConnection:
    def __init__(self, raw_conn):
        self.db_conn = raw_conn

    def commit(self):
        self.db_conn.commit()
        sql_logger.debug("数据库事务成功（）提交")

    def rollback(self):
        self.db_conn.rollback()
        sql_logger.debug("数据库回滚")

    @contextmanager
    def cursor(self):
        with self.db_conn.cursor() as cur:
            yield cur

    def execute(self, sql, param=None):
        start = time.perf_counter()

        with self.cursor() as cur:
            cur.execute(sql, param or ())
            rowcount = cur.rowcount  # 受影响的行数

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        sql_logger.info(
            "sql_execute",
            extra={
                "sql": sql,
                "params": repr(param),
                "rowcount": rowcount,
                "elapsed_ms": elapsed_ms,
            },
        )

        return rowcount

    # 捕获第一条信息
    def fetchone(self, sql, param=None):
        start = time.perf_counter()

        with self.cursor() as cur:
            cur.execute(sql, param or ())
            result = cur.fetchone()  # 获取查询到的第一条数据

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        sql_logger.info(
            "sql_fetchone",
            extra={
                "sql": sql,
                "params": repr(param),
                "hit": result is not None,
                "elapsed_ms": elapsed_ms,
            },
        )

        return result

    # 捕获全部信息
    def fetchall(self, sql, param=None):
        start = time.perf_counter()

        with self.cursor() as cur:
            cur.execute(sql, param or ())
            result = cur.fetchall()  # 获取所有可查询到的数据

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        sql_logger.info(
            "sql_fetchall",
            extra={
                "sql": sql,
                "params": repr(param),
                "rows": len(result),
                "elapsed_ms": elapsed_ms,
            },
        )

        return result
