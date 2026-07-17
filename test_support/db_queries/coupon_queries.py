

class CouponQueries:
    """封装订单优惠券场景所需的只读查询"""

    def __init__(self, db_conn):
        self.db = db_conn

    def _refresh_snapshot(self):
        self.db.rollback()

    def get_coupon_history_state(
        self,
        coupon_history_id,
    ):
        """查询指定用户优惠券历史的使用状态"""
        self._refresh_snapshot()
        sql = """
            SELECT
                h.id,
                h.coupon_id,
                h.member_id,
                h.use_status,
                h.use_time,
                h.order_id
            FROM sms_coupon_history h
            WHERE h.id = %s
            LIMIT 1
        """
        return self.db.fetchone(sql, (coupon_history_id,))

    def get_coupon_history_by_reference(
        self,
        coupon_history_reference,
    ):
        """按券码引用查询优惠券历史及所属会员"""
        self._refresh_snapshot()
        sql = """
            SELECT
                h.id,
                h.coupon_id,
                h.member_id,
                h.coupon_code,
                h.use_status,
                h.use_time,
                h.order_id,
                c.amount AS coupon_amount,
                c.min_point,
                c.use_type,
                c.start_time,
                c.end_time,
                m.username AS member_username
            FROM sms_coupon_history h
            INNER JOIN sms_coupon c ON c.id = h.coupon_id
            INNER JOIN ums_member m ON m.id = h.member_id
            WHERE h.coupon_code = %s
            LIMIT 1
        """
        return self.db.fetchone(sql, (coupon_history_reference,))

    def get_member_coupon_history_by_reference(
        self,
        member_username,
        coupon_history_reference,
    ):
        """按券码引用查询当前会员的优惠券历史"""
        self._refresh_snapshot()
        sql = """
            SELECT
                h.id,
                h.coupon_id,
                h.member_id,
                h.coupon_code,
                h.use_status,
                h.use_time,
                h.order_id,
                c.amount AS coupon_amount,
                c.min_point,
                c.use_type,
                c.start_time,
                c.end_time,
                m.username AS member_username
            FROM sms_coupon_history h
            INNER JOIN sms_coupon c ON c.id = h.coupon_id
            INNER JOIN ums_member m ON m.id = h.member_id
            WHERE m.username = %s
              AND h.coupon_code = %s
            LIMIT 1
        """
        return self.db.fetchone(sql, (member_username, coupon_history_reference))

    def get_available_member_coupon_history_by_reference(
        self,
        member_username,
        coupon_history_reference,
        coupon_amount,
        minimum_amount,
        use_type,
    ):
        """按券码引用查询当前会员满足金额条件且当前有效的未使用优惠券历史"""
        self._refresh_snapshot()
        sql = """
            SELECT
                h.id,
                h.coupon_id,
                h.member_id,
                h.coupon_code,
                h.use_status,
                h.use_time,
                h.order_id,
                c.amount AS coupon_amount,
                c.min_point,
                c.use_type,
                c.start_time,
                c.end_time,
                m.username AS member_username
            FROM sms_coupon_history h
            INNER JOIN sms_coupon c ON c.id = h.coupon_id
            INNER JOIN ums_member m ON m.id = h.member_id
            WHERE m.username = %s
              AND h.coupon_code = %s
              AND h.use_status = 0
              AND c.amount = %s
              AND c.min_point = %s
              AND c.use_type = %s
              AND c.start_time <= NOW()
              AND c.end_time >= NOW()
            LIMIT 1
        """
        return self.db.fetchone(
            sql,
            (
                member_username,
                coupon_history_reference,
                coupon_amount,
                minimum_amount,
                use_type,
            ),
        )

    def get_available_member_coupon_history(
        self,
        member_username,
        coupon_amount,
        minimum_amount,
        use_type,
    ):
        """查询会员满足金额条件且当前有效的未使用优惠券历史"""
        self._refresh_snapshot()
        sql = """
            SELECT
                h.id,
                h.coupon_id,
                h.member_id,
                h.use_status,
                h.use_time,
                h.order_id,
                c.amount AS coupon_amount,
                c.min_point,
                c.use_type,
                c.start_time,
                c.end_time,
                m.username AS member_username
            FROM sms_coupon_history h
            INNER JOIN sms_coupon c ON c.id = h.coupon_id
            INNER JOIN ums_member m ON m.id = h.member_id
            WHERE m.username = %s
              AND h.use_status = 0
              AND c.amount = %s
              AND c.min_point = %s
              AND c.use_type = %s
              AND c.start_time <= NOW()
              AND c.end_time >= NOW()
            ORDER BY h.id
            LIMIT 1
        """
        return self.db.fetchone(
            sql,
            (member_username, coupon_amount, minimum_amount, use_type),
        )
