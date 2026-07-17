class AddressQueries:
    def __init__(self, db_conn):
        """初始化收货地址数据库查询"""
        self.db = db_conn

    def _refresh_snapshot(self):
        """结束只读事务并刷新快照"""
        self.db.rollback()

    def get_default_member_address(
        self,
        member_username,
        address_id,
        default_status=1,
    ):
        """按接口地址 ID 查询会员的默认收货地址"""
        self._refresh_snapshot()
        sql = """
            SELECT
                a.id AS address_id,
                a.member_id,
                a.default_status,
                a.phone_number,
                a.detail_address
            FROM ums_member_receive_address a
            INNER JOIN ums_member m ON m.id = a.member_id
            WHERE m.username = %s
              AND a.id = %s
              AND a.default_status = %s
            LIMIT 1
        """
        return self.db.fetchone(
            sql,
            (member_username, address_id, default_status),
        )

    def count_member_addresses(self, member_username):
        """统计会员的收货地址数量"""
        self._refresh_snapshot()
        sql = """
            SELECT COUNT(*) AS address_count
            FROM ums_member_receive_address a
            INNER JOIN ums_member m ON m.id = a.member_id
            WHERE m.username = %s
        """
        result = self.db.fetchone(sql, (member_username,))
        return int((result or {}).get("address_count") or 0)

    def get_address_owner(self, address_id):
        """查询收货地址归属会员"""
        self._refresh_snapshot()
        sql = """
            SELECT
                a.id AS address_id,
                a.member_id,
                m.username AS member_username,
                a.default_status,
                a.phone_number,
                a.detail_address
            FROM ums_member_receive_address a
            INNER JOIN ums_member m ON m.id = a.member_id
            WHERE a.id = %s
            LIMIT 1
        """
        return self.db.fetchone(sql, (address_id,))
