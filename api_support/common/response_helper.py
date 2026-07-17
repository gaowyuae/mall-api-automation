class ApiResponseHelper:
    @staticmethod
    def get_code(response):
        return response.get("code") if isinstance(response, dict) else None

    @staticmethod
    def get_data(response):
        return response.get("data") if isinstance(response, dict) else None

    @staticmethod
    def get_message(response):
        if not isinstance(response, dict):
            return ""
        return str(response.get("message") or "")
