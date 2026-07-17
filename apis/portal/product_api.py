from config.settings.portal_path import PORTAL_PRODUCT_API_PATHS
from core.http_client import BaseAPI


class PortalProductAPI(BaseAPI):
    def search_product_detail(self, product_id=None, enable=True):
        payload = {
            "id": product_id
        }

        self.validate_required(
            "portal_product_detail",
            payload,
            ["id"],
            enable,
        )

        response = self.get(
            PORTAL_PRODUCT_API_PATHS["PRODUCT_DETAIL"].format(id=product_id),
        )

        self.assert_http_ok(response, "product_detail")
        return self.to_json(response)

    def product_search(
            self,
            brand_id=None,
            keyword=None,
            page_num=1,
            product_category_id=None,
            page_size=10,
            sort=0,
            enable=True,
    ):
        payload = {
            "brandId": brand_id,
            "keyword": keyword,
            "pageNum": page_num,
            "productCategoryId": product_category_id,
            "pageSize": page_size,
            "sort": sort,
        }

        self.validate_required(
            "product_search",
            {
                "pageNum": page_num,
                "pageSize": page_size,
                "sort": sort,
            },
            ["pageNum", "pageSize", "sort"],
            enable,
        )

        self.validate_any_required(
            "product_search",
            {
                "keyword": keyword,
                "productCategoryId": product_category_id,
                "brandId": brand_id,
            },
            ["keyword", "productCategoryId", "brandId"],
            enable,
        )

        response = self.get(
            path=PORTAL_PRODUCT_API_PATHS["PRODUCT_SEARCH"],
            params=payload,
        )

        self.assert_http_ok(response, "product_search")
        return self.to_json(response)


def search_product_detail(session, product_id=None, enable=True):
    return PortalProductAPI(session).search_product_detail(product_id, enable)


def product_search(
        session,
        brand_id=None,
        keyword=None,
        page_num=1,
        product_category_id=None,
        page_size=10,
        sort=0,
        enable=True,
):
    return PortalProductAPI(session).product_search(
        brand_id,
        keyword,
        page_num,
        product_category_id,
        page_size,
        sort,
        enable,
    )
