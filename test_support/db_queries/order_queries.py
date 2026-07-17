class OrderQueries:
    """订单权限与状态场景使用的只读查询"""

    def __init__(self, db_conn):
        self.db = db_conn

    def _refresh_snapshot(self):
        self.db.rollback()

    def get_latest_member_order_by_status(
        self,
        member_username,
        status,
    ):
        self._refresh_snapshot()
        sql = """
            SELECT
                o.id AS order_id,
                o.status,
                o.receive_time AS confirm_time
            FROM oms_order o
            INNER JOIN ums_member m ON m.id = o.member_id
            WHERE m.username = %s
              AND o.status = %s
            ORDER BY o.id DESC
            LIMIT 1
        """
        return self.db.fetchone(sql, (member_username, status))

    def get_latest_member_order(
        self,
        member_username,
    ):
        """查询会员最新订单，不限制订单状态"""
        self._refresh_snapshot()
        sql = """
            SELECT
                o.id AS order_id,
                o.status
            FROM oms_order o
            INNER JOIN ums_member m ON m.id = o.member_id
            WHERE m.username = %s
            ORDER BY o.id DESC
            LIMIT 1
        """
        return self.db.fetchone(sql, (member_username,))

    def get_order_benefit_state(
        self,
        order_id,
    ):
        """查询订单优惠券、积分及金额状态"""
        self._refresh_snapshot()
        sql = """
            SELECT
                o.id AS order_id,
                o.coupon_id,
                o.total_amount,
                o.pay_amount,
                o.integration_amount,
                o.coupon_amount,
                o.use_integration,
                o.status
            FROM oms_order o
            WHERE o.id = %s
            LIMIT 1
        """
        return self.db.fetchone(sql, (order_id,))

    def get_order_state(self, order_id):
        self._refresh_snapshot()
        sql = """
            SELECT
                o.id AS order_id,
                o.order_sn,
                o.status,
                o.pay_type,
                o.pay_amount,
                o.payment_time,
                o.coupon_id,
                o.use_integration,
                o.integration_amount,
                o.delivery_company,
                o.delivery_sn,
                o.delivery_time,
                o.receive_time,
                o.receive_time AS confirm_time
            FROM oms_order o
            WHERE o.id = %s
            LIMIT 1
        """
        return self.db.fetchone(sql, (order_id,))

    def get_order_items(self, order_id):
        """查询订单商品明细"""
        self._refresh_snapshot()
        sql = """
            SELECT
                i.id AS order_item_id,
                i.order_id,
                i.product_id,
                i.product_sku_id,
                i.product_quantity,
                i.product_price,
                i.real_amount
            FROM oms_order_item i
            WHERE i.order_id = %s
            ORDER BY i.id
        """
        return self.db.fetchall(sql, (order_id,))

    def get_member_orders_after(
        self,
        member_username,
        minimum_order_id,
        status,
    ):
        """查询会员在基准订单之后创建的指定状态订单"""
        self._refresh_snapshot()
        sql = """
            SELECT
                o.id AS order_id,
                o.status
            FROM oms_order o
            INNER JOIN ums_member m ON m.id = o.member_id
            WHERE m.username = %s
              AND o.id > %s
              AND o.status = %s
            ORDER BY o.id
        """
        return self.db.fetchall(
            sql,
            (member_username, minimum_order_id, status),
        )

    def get_sku_stock_state(self, sku_id):
        """查询订单操作影响到的 SKU 库存状态"""
        self._refresh_snapshot()
        sql = """
            SELECT
                s.id AS sku_id,
                s.stock,
                s.lock_stock
            FROM pms_sku_stock s
            WHERE s.id = %s
            LIMIT 1
        """
        return self.db.fetchone(sql, (sku_id,))

    def get_latest_other_member_order_by_status(
        self,
        excluded_member_username,
        status,
    ):
        """查询其他会员最新的指定状态订单"""
        self._refresh_snapshot()
        sql = """
            SELECT
                o.id AS order_id,
                o.member_username,
                o.status,
                o.delivery_company,
                o.delivery_sn,
                o.delivery_time,
                o.receive_time,
                o.receive_time AS confirm_time
            FROM oms_order o
            WHERE o.member_username <> %s
              AND o.status = %s
            ORDER BY o.id DESC
            LIMIT 1
        """
        return self.db.fetchone(sql, (excluded_member_username, status))
