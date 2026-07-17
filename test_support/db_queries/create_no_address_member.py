class CreateNoAddressMember:
    """管理无地址测试会员的创建与安全清理"""

    def __init__(self, db_conn):
        self.db = db_conn

    def _refresh_snapshot(self):
        self.db.rollback()

    def _get_member_id(self, username):
        result = self.db.fetchone(
            """
            SELECT id
            FROM ums_member
            WHERE username = %s
            LIMIT 1
            """,
            (username,),
        )
        if not result:
            return None
        return int(result["id"])

    def _get_dependency_counts(self, member_id):
        result = self.db.fetchone(
            """
            SELECT
                (
                    SELECT COUNT(*)
                    FROM ums_member_receive_address
                    WHERE member_id = %s
                ) AS address_count,
                (
                    SELECT COUNT(*)
                    FROM oms_order
                    WHERE member_id = %s
                ) AS order_count
            """,
            (member_id, member_id),
        )
        return {
            "address_count": int((result or {}).get("address_count") or 0),
            "order_count": int((result or {}).get("order_count") or 0),
        }

    def _count_cart_items(self, member_id):
        result = self.db.fetchone(
            """
            SELECT COUNT(*) AS cart_count
            FROM oms_cart_item
            WHERE member_id = %s
            """,
            (member_id,),
        )
        return int((result or {}).get("cart_count") or 0)

    def create_no_address_member(
        self,
        source_username,
        target_username,
    ):
        """复制来源会员的密码哈希并创建无地址测试会员"""
        self._refresh_snapshot()
        existing_member_id = self._get_member_id(target_username)
        if existing_member_id is not None:
            dependency_counts = self._get_dependency_counts(existing_member_id)
            dependency_counts["cart_count"] = self._count_cart_items(existing_member_id)
            if any(dependency_counts.values()):
                raise RuntimeError(
                    f"已有测试会员不满足无地址、无订单、空购物车前提："
                    f"{target_username}，"
                    f"依赖数据={dependency_counts}"
                )
            return existing_member_id

        sql = """
            INSERT INTO ums_member (
                member_level_id,
                username,
                password,
                nickname,
                status,
                create_time,
                integration,
                growth
            )
            SELECT
                source.member_level_id,
                %s,
                source.password,
                %s,
                1,
                NOW(),
                0,
                0
            FROM ums_member source
            WHERE source.username = %s
              AND NOT EXISTS (
                  SELECT 1
                  FROM ums_member target
                  WHERE target.username = %s
              )
        """
        created_rows = self.db.execute(
            sql,
            (
                target_username,
                target_username,
                source_username,
                target_username,
            ),
        )
        if created_rows != 1:
            self.db.rollback()
            raise RuntimeError(
                f"无地址测试会员创建失败：source={source_username}，"
                f"target={target_username}"
            )
        self.db.commit()

        member_id = self._get_member_id(target_username)
        if member_id is None:
            raise RuntimeError(f"创建后未找到测试会员：{target_username}")
        return member_id

    def delete_no_address_member(
        self,
        member_id,
        target_username,
    ):
        """无地址且无订单时，删除测试会员的购物车和会员记录"""
        self._refresh_snapshot()
        dependency_counts = self._get_dependency_counts(member_id)
        if any(dependency_counts.values()):
            self.db.rollback()
            return False

        self.db.execute(
            "DELETE FROM oms_cart_item WHERE member_id = %s",
            (member_id,),
        )
        deleted_rows = self.db.execute(
            """
            DELETE FROM ums_member
            WHERE id = %s
              AND username = %s
            """,
            (member_id, target_username),
        )
        if deleted_rows != 1:
            self.db.rollback()
            return False

        self.db.commit()
        return True
