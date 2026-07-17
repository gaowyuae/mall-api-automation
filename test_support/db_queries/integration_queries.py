

class IntegrationQueries:
    """封装订单积分场景所需的只读查询"""

    def __init__(self, db_conn):
        self.db = db_conn

    def _refresh_snapshot(self):
        self.db.rollback()

    def get_member_history_state(
        self,
        member_username,
    ):
        """查询会员积分流水数量及最新一条流水"""
        self._refresh_snapshot()
        count_sql = """
            SELECT COUNT(*) AS history_count
            FROM ums_integration_change_history h
            INNER JOIN ums_member m ON m.id = h.member_id
            WHERE m.username = %s
        """
        latest_sql = """
            SELECT
                h.id AS history_id,
                h.change_count,
                h.change_type,
                h.source_type
            FROM ums_integration_change_history h
            INNER JOIN ums_member m ON m.id = h.member_id
            WHERE m.username = %s
            ORDER BY h.id DESC
            LIMIT 1
        """
        count_result = self.db.fetchone(count_sql, (member_username,))
        latest = self.db.fetchone(latest_sql, (member_username,))
        return {
            "history_count": (count_result or {}).get("history_count") or 0,
            **(latest or {}),
        }
