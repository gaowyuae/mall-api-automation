class PortalCouponHelper:
    @staticmethod
    def get_coupon_list(response):
        if not isinstance(response, dict):
            return None
        coupons = response.get("data")
        if not isinstance(coupons, list):
            return None
        if not all(isinstance(coupon, dict) for coupon in coupons):
            return None
        return coupons

    get_coupon_history = get_coupon_list

    @classmethod
    def find_coupon(cls, response, coupon_id):
        coupons = cls.get_coupon_list(response)
        if coupons is None:
            return None
        return next(
            (coupon for coupon in coupons if str(coupon.get("id")) == str(coupon_id)),
            None,
        )

    @classmethod
    def find_coupon_history(cls, response, coupon_history_id):
        histories = cls.get_coupon_history(response)
        if histories is None:
            return None
        return next(
            (
                history
                for history in histories
                if str(history.get("id")) == str(coupon_history_id)
            ),
            None,
        )

    @staticmethod
    def find_confirm_coupon_detail(confirm_data, coupon_history_id):
        """从确认单 data 中查找指定用户优惠券明细"""
        if not isinstance(confirm_data, dict):
            return None
        details = confirm_data.get("couponHistoryDetailList")
        if not isinstance(details, list):
            return None

        for detail in details:
            if not isinstance(detail, dict):
                return None
            if str(detail.get("id")) == str(coupon_history_id):
                return detail
            history = detail.get("couponHistory")
            if isinstance(history, dict) and str(history.get("id")) == str(
                coupon_history_id
            ):
                return detail
        return None

    @staticmethod
    def get_detail_coupon(detail):
        """返回确认单优惠券明细中的优惠券定义"""
        if not isinstance(detail, dict):
            return None
        coupon = detail.get("coupon")
        return coupon if isinstance(coupon, dict) else None
