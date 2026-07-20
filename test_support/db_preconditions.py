import os
import socket


def _assert_found(row, case_id, subject):
    """确认前置 SQL 命中了目标数据。"""
    assert row is not None, f"{case_id} 前置数据不存在：{subject}"


def _redis_payload(parts):
    """构造最小 Redis RESP 命令。"""
    payload = f"*{len(parts)}\r\n"
    for part in parts:
        text = str(part)
        payload += f"${len(text.encode())}\r\n{text}\r\n"
    return payload.encode()


def _redis_del(key):
    """删除单个 Redis key，Redis 不可用时保持数据库前置逻辑可运行。"""
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    timeout = float(os.getenv("REDIS_TIMEOUT", "2"))

    try:
        with socket.create_connection((host, port), timeout=timeout) as redis_conn:
            redis_conn.sendall(_redis_payload(("DEL", key)))
            redis_conn.recv(1024)
    except OSError:
        return


def _clear_member_cache(member_username):
    """清理当前会员缓存，避免接口继续读取旧积分。"""
    prefix = os.getenv("REDIS_MEMBER_CACHE_PREFIX", "mall:ums:member:")
    _redis_del(f"{prefix}{member_username}")


def restore_sku_stock_precondition(
    test_conn,
    *,
    case_id,
    sku_id,
    stock,
    lock_stock=0,
):
    """恢复 TC_ECOM_023 的 SKU 库存前置。"""
    test_conn.execute(
        """
        UPDATE pms_sku_stock
        SET stock = %s, lock_stock = %s
        WHERE id = %s
        """,
        (stock, lock_stock, sku_id),
    )
    test_conn.commit()

    row = test_conn.fetchone(
        """
        SELECT id, stock, lock_stock
        FROM pms_sku_stock
        WHERE id = %s
        LIMIT 1
        """,
        (sku_id,),
    )
    _assert_found(row, case_id, f"sku_id={sku_id}")
    assert row["stock"] == stock, f"{case_id} SKU {sku_id} 库存恢复失败：{row}"
    assert row["lock_stock"] == lock_stock, (
        f"{case_id} SKU {sku_id} 锁定库存恢复失败：{row}"
    )


def restore_member_integration_precondition(
    test_conn,
    *,
    case_id,
    member_username,
    integration,
):
    """恢复 TC_ECOM_048/049/052/053 的会员积分前置。"""
    test_conn.execute(
        """
        UPDATE ums_member
        SET integration = %s
        WHERE username = %s
        """,
        (integration, member_username),
    )
    test_conn.commit()

    row = test_conn.fetchone(
        """
        SELECT username, integration
        FROM ums_member
        WHERE username = %s
        LIMIT 1
        """,
        (member_username,),
    )
    _assert_found(row, case_id, f"member_username={member_username}")
    assert row["integration"] == integration, (
        f"{case_id} 会员 {member_username} 积分恢复失败：{row}"
    )
    _clear_member_cache(member_username)


def restore_coupon_history_precondition(
    test_conn,
    *,
    case_id,
    member_username,
    coupon_history_reference,
):
    """恢复 TC_ECOM_052/053 的优惠券历史前置。"""
    test_conn.execute(
        """
        UPDATE sms_coupon_history h
        INNER JOIN ums_member m ON m.id = h.member_id
        SET h.use_status = 0,
            h.use_time = NULL,
            h.order_id = NULL
        WHERE m.username = %s
          AND h.coupon_code = %s
        """,
        (member_username, coupon_history_reference),
    )
    test_conn.commit()

    row = test_conn.fetchone(
        """
        SELECT h.coupon_code, h.use_status, h.use_time, h.order_id
        FROM sms_coupon_history h
        INNER JOIN ums_member m ON m.id = h.member_id
        WHERE m.username = %s
          AND h.coupon_code = %s
        LIMIT 1
        """,
        (member_username, coupon_history_reference),
    )
    _assert_found(row, case_id, f"coupon_code={coupon_history_reference}")
    assert row["use_status"] == 0, f"{case_id} 优惠券状态恢复失败：{row}"
    assert row["use_time"] is None, f"{case_id} 优惠券使用时间恢复失败：{row}"
    assert row["order_id"] is None, f"{case_id} 优惠券订单绑定恢复失败：{row}"
