from api_support.common.response_helper import ApiResponseHelper


def verify_response_dict(response):
    """校验接口响应为字典并返回响应"""
    assert isinstance(response, dict), (
        f"接口响应应为字典，实际类型为：{type(response).__name__}"
    )
    return response


def verify_business_code(response, expected_code):
    """校验接口响应中的业务状态码"""
    response_data = verify_response_dict(response)
    actual_code = ApiResponseHelper.get_code(response_data)
    assert actual_code is not None, f"接口响应缺少业务 code：{response_data}"
    assert actual_code == expected_code, (
        f"业务 code 应为 {expected_code}，实际为 {actual_code}：{response_data}"
    )


def verify_business_failure(response, success_code=200):
    """校验接口业务处理失败"""
    response_data = verify_response_dict(response)
    actual_code = ApiResponseHelper.get_code(response_data)
    assert actual_code is not None, f"接口响应缺少业务 code：{response_data}"
    assert actual_code != success_code, (
        f"业务请求应失败，但实际返回成功 code={actual_code}：{response_data}"
    )


def verify_login_not_authorized(response, data_name):
    """校验伪造 token 登录时的 data 符合预期"""
    response_data = verify_response_dict(response)
    data = ApiResponseHelper.get_data(response_data)
    assert data == "Full authentication is required to access this resource", (
        f"{data_name} data 应符合预期，实际为：{data}"
    )


def verify_data_not_empty(response, data_name):
    """校验接口响应中的 data 不为空"""
    response_data = verify_response_dict(response)
    data = ApiResponseHelper.get_data(response_data)
    assert data not in (None, "", [], {}), f"{data_name} data 不应为空，实际为：{data}"
    return data


def verify_data_empty(response, data_name):
    """校验接口响应中的 data 为空"""
    response_data = verify_response_dict(response)
    data = ApiResponseHelper.get_data(response_data)
    assert data in (None, "", [], {}), f"{data_name} data 应为空，实际为：{data}"


def verify_message_contains_any(
    response,
    expected_keywords,
):
    """校验错误信息包含任一预期关键词"""
    response_data = verify_response_dict(response)
    message = ApiResponseHelper.get_message(response_data)
    normalized_message = message.casefold()
    normalized_keywords = [
        str(keyword).casefold() for keyword in expected_keywords if str(keyword)
    ]
    assert normalized_keywords, "错误信息关键词配置不能为空"
    assert any(keyword in normalized_message for keyword in normalized_keywords), (
        f"错误信息应包含任一关键词 {expected_keywords}，实际为：{message}"
    )
