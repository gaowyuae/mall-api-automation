

class CatalogQueries:
    """封装商品和 SKU 场景所需的只读查询"""

    def __init__(self, db_conn):
        """初始化商品数据库查询"""
        self.db = db_conn

    def _refresh_snapshot(self):
        self.db.rollback()

    def find_on_sale_sku_by_stock(
        self,
        stock,
    ):
        """查询一个指定库存的有效上架商品 SKU"""
        self._refresh_snapshot()
        sql = """
            SELECT
                p.id AS product_id,
                p.name AS product_name,
                p.publish_status,
                p.delete_status,
                s.id AS sku_id,
                s.sku_code,
                s.price,
                s.stock,
                s.lock_stock,
                s.sp_data
            FROM pms_product p
            INNER JOIN pms_sku_stock s ON s.product_id = p.id
            WHERE p.publish_status = 1
              AND p.delete_status = 0
              AND s.stock = %s
            ORDER BY p.id, s.id
            LIMIT 1
        """
        return self.db.fetchone(sql, (stock,))

    def get_on_sale_sku(self, product_id, sku_id):
        """按商品和 SKU 查询有效上架的目标库存记录"""
        self._refresh_snapshot()
        sql = """
            SELECT
                p.id AS product_id,
                p.name AS product_name,
                p.publish_status,
                p.delete_status,
                s.id AS sku_id,
                s.sku_code,
                s.price,
                s.stock,
                s.lock_stock,
                s.sp_data
            FROM pms_product p
            INNER JOIN pms_sku_stock s ON s.product_id = p.id
            WHERE p.id = %s
              AND s.id = %s
              AND p.publish_status = 1
              AND p.delete_status = 0
            LIMIT 1
        """
        return self.db.fetchone(sql, (product_id, sku_id))

    def get_catalog_state(self):
        """返回商品及 SKU 数量和关键状态汇总快照"""
        self._refresh_snapshot()
        product_sql = """
            SELECT
                COUNT(*) AS product_count,
                COALESCE(SUM(publish_status), 0) AS publish_status_sum,
                COALESCE(SUM(delete_status), 0) AS delete_status_sum
            FROM pms_product
        """
        sku_sql = """
            SELECT
                COUNT(*) AS sku_count,
                COALESCE(SUM(stock), 0) AS stock_sum,
                COALESCE(SUM(lock_stock), 0) AS lock_stock_sum
            FROM pms_sku_stock
        """
        return {
            **(self.db.fetchone(product_sql) or {}),
            **(self.db.fetchone(sku_sql) or {}),
        }
