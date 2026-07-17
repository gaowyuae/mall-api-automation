from core.logkit import get_logger

support_logger = get_logger("api_support.portal.member")


class PortalMemberHelper:
    @staticmethod
    def get_member(response):
        """返回会员信息字典"""
        if not isinstance(response, dict):
            support_logger.warning(
                "会员信息响应类型不对，实际是 %s",
                type(response).__name__,
                extra={"event": "api_support.portal.member.invalid"},
            )
            return {}

        data = response.get("data") or {}
        if not isinstance(data, dict):
            support_logger.warning(
                "会员信息 data 不是字典，实际是 %s",
                type(data).__name__,
                extra={"event": "api_support.portal.member.data_invalid"},
            )
            return {}

        member = data.get("member")
        return member if isinstance(member, dict) else data

    @classmethod
    def get_integration(cls, response):
        """返回会员当前积分"""
        member = cls.get_member(response)
        return member.get("integration")
