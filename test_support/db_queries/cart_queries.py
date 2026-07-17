class CartQueries:
    """封装购物车数据一致性场景所需的只读查询"""

    def __init__(self, db_conn):
        """初始化购物车数据库查询"""
        self.db = db_conn

    def _refresh_snapshot(self):
        """结束上一次只读事务，确保读取到接口提交后的最新数据"""
        self.db.rollback()

    def count_member_sku_items(
        self,
        member_username,
        product_id,
        sku_id,
    ):
        """统计会员指定商品 SKU 的全部购物车记录"""
        self._refresh_snapshot()
        sql = """
            SELECT COUNT(*) AS item_count
            FROM oms_cart_item c
            INNER JOIN ums_member m ON m.id = c.member_id
            WHERE m.username = %s
              AND c.product_id = %s
              AND c.product_sku_id = %s
        """
        result = self.db.fetchone(sql, (member_username, product_id, sku_id))
        return int((result or {}).get("item_count") or 0)

    def get_latest_active_member_sku_item(
        self,
        member_username,
        product_id,
        sku_id,
    ):
        """查询会员指定商品 SKU 最新的有效购物车记录"""
        self._refresh_snapshot()
        sql = """
            SELECT
                c.id,
                c.product_id,
                c.product_sku_id,
                c.member_id,
                c.quantity,
                c.price,
                c.delete_status
            FROM oms_cart_item c
            INNER JOIN ums_member m ON m.id = c.member_id
            WHERE m.username = %s
              AND c.product_id = %s
              AND c.product_sku_id = %s
              AND c.delete_status = 0
            ORDER BY c.id DESC
            LIMIT 1
        """
        return self.db.fetchone(sql, (member_username, product_id, sku_id))

    def count_active_member_sku_items(
        self,
        member_username,
        product_id,
        sku_id,
    ):
        """统计会员指定商品 SKU 的有效购物车记录"""
        self._refresh_snapshot()
        sql = """
            SELECT COUNT(*) AS item_count
            FROM oms_cart_item c
            INNER JOIN ums_member m ON m.id = c.member_id
            WHERE m.username = %s
              AND c.product_id = %s
              AND c.product_sku_id = %s
              AND c.delete_status = 0
        """
        result = self.db.fetchone(sql, (member_username, product_id, sku_id))
        return int((result or {}).get("item_count") or 0)

    def get_cart_item(self, cart_id):
        """按购物车 ID 查询购物车记录状态"""
        self._refresh_snapshot()
        sql = """
            SELECT
                c.id,
                c.product_id,
                c.product_sku_id,
                c.member_id,
                c.quantity,
                c.price,
                c.delete_status
            FROM oms_cart_item c
            WHERE c.id = %s
            LIMIT 1
        """
        return self.db.fetchone(sql, (cart_id,))
