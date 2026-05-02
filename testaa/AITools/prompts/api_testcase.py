"""
API接口测试用例生成Prompt
"""
from .base import BasePrompt
from typing import Dict, Any, Optional, List
import json
import logging

logger = logging.getLogger(__name__)


class APITestCasePrompt(BasePrompt):
    """API接口测试用例生成Prompt"""

    def __init__(self):
        self._system_prompt = """你是一个专业的API测试工程师，擅长为API接口设计全面、可执行的测试用例。

要求：
1. 为每个接口生成至少3个测试用例：1个正常场景、1个异常场景、1个边界场景
2. 测试步骤要具体可执行，包括请求方法、请求路径、请求头、请求体等细节
3. 预期结果要具体，包括HTTP状态码、返回数据结构、关键字段值
4. 如果有参考测试数据，优先基于测试数据生成用例
5. 请确保返回的是纯JSON格式的数据，不要包含其他说明文字。"""

        self._user_prompt_template = """请为以下API接口生成测试用例。

API接口信息：
- 接口名称：{api_name}
- 接口路径：{api_path}
- 请求方法：{method}
- 入参：{request_params}
- 出参：{response_params}
- 备注：{remark}
{test_data_info}
请生成测试用例，以JSON格式返回，包含以下字段：
- test_case_name: 测试用例名称
- test_case_type: 测试类型（正常场景、异常场景、边界场景）
- preconditions: 前置条件
- test_steps: 测试步骤（详细描述，包括请求方法、URL、请求头、请求体等）
- test_data: 测试数据（JSON格式，具体的请求参数键值对）
- expected_result: 预期结果（详细描述期望的响应，包括状态码和返回数据结构）
- priority: 优先级（P0-很高、P1-高、P2-中、P3-低）

返回格式示例：
{example}

请只返回JSON格式的数据，不要包含其他说明文字。"""

        self._example_response = {
            "test_cases": [
                {
                    "test_case_name": "正常获取用户信息",
                    "test_case_type": "正常场景",
                    "preconditions": "用户已登录，存在有效的用户ID",
                    "test_steps": "1. 构造GET请求到/api/v2/user/info\\n2. 设置请求头Authorization: Bearer {token}\\n3. 请求参数携带user_id=12345\\n4. 发送请求",
                    "test_data": {"user_id": "12345"},
                    "expected_result": "HTTP状态码200，返回JSON包含user_id、username、email等字段，数据与传入user_id匹配",
                    "priority": "P0"
                },
                {
                    "test_case_name": "缺少认证token获取用户信息",
                    "test_case_type": "异常场景",
                    "preconditions": "无",
                    "test_steps": "1. 构造GET请求到/api/v2/user/info\\n2. 不设置Authorization请求头\\n3. 请求参数携带user_id=12345\\n4. 发送请求",
                    "test_data": {"user_id": "12345"},
                    "expected_result": "HTTP状态码401，返回JSON包含错误码和提示信息'未授权访问'",
                    "priority": "P1"
                },
                {
                    "test_case_name": "user_id为空获取用户信息",
                    "test_case_type": "边界场景",
                    "preconditions": "用户已登录",
                    "test_steps": "1. 构造GET请求到/api/v2/user/info\\n2. 设置请求头Authorization: Bearer {token}\\n3. 请求参数携带user_id为空字符串\\n4. 发送请求",
                    "test_data": {"user_id": ""},
                    "expected_result": "HTTP状态码400，返回JSON包含错误码和提示信息'user_id不能为空'",
                    "priority": "P2"
                }
            ]
        }

    def get_system_prompt(self) -> str:
        return self._system_prompt

    def get_user_prompt(self, **kwargs) -> str:
        api_name = kwargs.get('api_name', '未知')
        api_path = kwargs.get('api_path', '未知')
        method = kwargs.get('method', '未知')
        request_params = kwargs.get('request_params', '无')
        response_params = kwargs.get('response_params', '无')
        remark = kwargs.get('remark', '无')
        test_data = kwargs.get('test_data', None)

        # 构造测试数据部分
        test_data_info = ""
        if test_data:
            if isinstance(test_data, dict):
                test_data_str = json.dumps(test_data, ensure_ascii=False, indent=2)
            elif isinstance(test_data, str):
                test_data_str = test_data
            else:
                test_data_str = str(test_data)

            test_data_info = f"""
参考测试数据：
{test_data_str}
"""

        example_str = json.dumps(self._example_response, ensure_ascii=False, indent=2)

        return self._user_prompt_template.format(
            api_name=str(api_name) if api_name else '未知',
            api_path=str(api_path) if api_path else '未知',
            method=str(method) if method else '未知',
            request_params=str(request_params) if request_params else '无',
            response_params=str(response_params) if response_params else '无',
            remark=str(remark) if remark else '无',
            test_data_info=test_data_info,
            example=example_str
        )

    @classmethod
    def parse_response(cls, response_text: str) -> Dict[str, Any]:
        """解析AI响应，提取测试用例"""
        try:
            data = json.loads(response_text)

            if isinstance(data, dict):
                if 'test_cases' in data:
                    return data
                elif 'test_case_name' in data:
                    return {'test_cases': [data]}
                else:
                    return {'test_cases': []}

            if isinstance(data, list):
                return {'test_cases': data}

            return {'test_cases': []}

        except json.JSONDecodeError:
            import re
            # 尝试提取最外层JSON对象
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            matches = re.findall(json_pattern, response_text, re.DOTALL)

            for match in matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, dict) and 'test_cases' in data:
                        return data
                    if isinstance(data, dict) and 'test_case_name' in data:
                        return {'test_cases': [data]}
                except json.JSONDecodeError:
                    continue

            # 尝试提取JSON数组
            array_pattern = r'\[.*?\]'
            matches = re.findall(array_pattern, response_text, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, list) and len(data) > 0:
                        return {'test_cases': data}
                except json.JSONDecodeError:
                    continue

            logger.warning(f"无法从AI响应中解析测试用例: {response_text[:500]}")
            return {'test_cases': []}
