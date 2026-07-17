
from api_support.common.response_helper import ApiResponseHelper
from core.logkit import get_logger

support_logger = get_logger("api_support.portal.product")


class PortalProductHelper:
    """整理商品搜索、详情和 SKU 数据"""

    @staticmethod
    def get_search_data(response):
        data = ApiResponseHelper.get_data(response)
        return data if isinstance(data, dict) else None

    @classmethod
    def get_search_products(cls, response):
        search_data = cls.get_search_data(response)
        if search_data is None:
            return None

        products = search_data.get("list")
        return products if isinstance(products, list) else None

    @staticmethod
    def get_detail_data(response):
        data = ApiResponseHelper.get_data(response)
        return data if isinstance(data, dict) else None

    @classmethod
    def get_product(cls, response):
        detail_data = cls.get_detail_data(response)
        if detail_data is None:
            return None

        product = detail_data.get("product")
        if isinstance(product, dict):
            return product
        return detail_data

    @classmethod
    def get_sku_list(cls, response):
        detail_data = cls.get_detail_data(response)
        if detail_data is None:
            return None

        sku_list = detail_data.get("skuStockList")
        return sku_list if isinstance(sku_list, list) else None

    @staticmethod
    def find_sku_in_list(sku_list, sku_id):
        if not isinstance(sku_list, list):
            return None

        return next(
            (
                sku
                for sku in sku_list
                if isinstance(sku, dict) and str(sku.get("id")) == str(sku_id)
            ),
            None,
        )

    @classmethod
    def find_sku(cls, response, sku_id):
        sku_list = cls.get_sku_list(response)
        return cls.find_sku_in_list(sku_list, sku_id)

    @classmethod
    def get_product_snapshot(
        cls,
        product_api,
        product_id=None,
        product_sku_id=None,
    ):
        """查询商品详情并整理加入购物车所需字段"""
        try:
            detail = product_api.search_product_detail(product_id=product_id)
        except Exception as exc:
            support_logger.warning(
                "商品快照没取到，product_id=%s，sku_id=%s，原因=%s",
                product_id,
                product_sku_id,
                type(exc).__name__,
                extra={"event": "api_support.portal.product.snapshot_failed"},
            )
            return {}

        product = cls.get_product(detail)
        if not product:
            support_logger.warning(
                "商品详情里没有 product，product_id=%s",
                product_id,
                extra={"event": "api_support.portal.product.missing"},
            )
            return {}

        sku = cls.find_sku(detail, product_sku_id) or {}
        if not sku:
            support_logger.warning(
                "商品 %s 没找到 SKU %s，快照只使用商品基础信息",
                product_id,
                product_sku_id,
                extra={"event": "api_support.portal.product.sku_missing"},
            )

        snapshot = {
            "price": sku.get("price", product.get("price")),
            "productPic": product.get("pic"),
            "productName": product.get("name"),
            "productSubTitle": product.get("subTitle"),
            "productSkuCode": sku.get("skuCode"),
            "productCategoryId": product.get("productCategoryId"),
            "productBrand": product.get("brandName"),
            "productSn": product.get("productSn"),
            "productAttr": sku.get("spData"),
        }
        return {key: value for key, value in snapshot.items() if value is not None}
