"""
API接口测试用例生成提示词模块
"""

import json
from typing import Dict, Any, Optional


class APITestCaseGeneratorPrompt:
    """API接口测试用例生成提示词类"""

    # 系统提示词
    SYSTEM_PROMPT = "你是一个专业的API测试工程师，擅长为API接口设计全面、可执行的测试用例。请确保返回的是纯JSON格式的数据。"

    # 用户提示词模板
    USER_PROMPT_TEMPLATE = """
请为以下API接口生成测试用例。

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
- test_steps: 测试步骤（详细描述，包括如何构造请求、发送请求等）
- test_data: 测试数据（JSON格式，具体的请求参数值）
- expected_result: 预期结果（详细描述期望的响应结果）
- priority: 优先级（P0-很高、P1-高、P2-中、P3-低）

要求：
1. 生成至少3个测试用例：1个正常场景、1个异常场景、1个边界场景
2. 如果有参考测试数据，请基于测试数据生成测试用例
3. 测试步骤要具体可执行，包括请求URL、请求方法、请求头、请求体等
4. 预期结果要具体，包括状态码、返回数据结构等
5. test_data字段必须是有效的JSON格式

返回格式示例：
{example}

请只返回JSON格式的数据，不要包含其他说明文字。
"""

    # 示例响应
    EXAMPLE_RESPONSE = {
        "test_cases": [
            {
                "test_case_name": "正常登录测试",
                "test_case_type": "正常场景",
                "preconditions": "用户已注册",
                "test_steps": "1. 构造POST请求到/api/login\n2. 设置Content-Type为application/json\n3. 请求体包含username和password\n4. 发送请求",
                "test_data": {"username": "testuser", "password": "123456"},
                "expected_result": "HTTP状态码200，返回token和用户信息",
                "priority": "P0"
            },
            {
                "test_case_name": "密码错误测试",
                "test_case_type": "异常场景",
                "preconditions": "用户已注册",
                "test_steps": "1. 构造POST请求到/api/login\n2. 使用错误的密码\n3. 发送请求",
                "test_data": {"username": "testuser", "password": "wrongpassword"},
                "expected_result": "HTTP状态码401，返回错误提示信息",
                "priority": "P1"
            }
        ]
    }

    @classmethod
    def get_prompt(
        cls,
        api_name: str,
        api_path: str,
        method: str,
        request_params: str,
        response_params: str,
        remark: str,
        test_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        获取完整的提示词

        Args:
            api_name: 接口名称
            api_path: 接口路径
            method: 请求方法
            request_params: 入参说明
            response_params: 出参说明
            remark: 备注
            test_data: 测试数据（可选）

        Returns:
            str: 完整的提示词
        """
        # 构造测试数据部分
        test_data_info = ""
        if test_data:
            if isinstance(test_data, dict):
                test_data_str = json.dumps(test_data, ensure_ascii=False, indent=2)
            else:
                test_data_str = str(test_data)
            test_data_info = f"""
参考测试数据：
{test_data_str}
"""

        example_str = json.dumps(
            cls.EXAMPLE_RESPONSE,
            ensure_ascii=False,
            indent=2
        )

        return cls.USER_PROMPT_TEMPLATE.format(
            api_name=api_name or '未知',
            api_path=api_path or '未知',
            method=method or '未知',
            request_params=request_params or '无',
            response_params=response_params or '无',
            remark=remark or '无',
            test_data_info=test_data_info,
            example=example_str
        )

    @classmethod
    def get_system_prompt(cls) -> str:
        """获取系统提示词"""
        return cls.SYSTEM_PROMPT

    @classmethod
    def get_user_prompt(
        cls,
        api_name: str,
        api_path: str,
        method: str,
        request_params: str,
        response_params: str,
        remark: str,
        test_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """获取用户提示词"""
        return cls.get_prompt(
            api_name, api_path, method, request_params,
            response_params, remark, test_data
        )

    @classmethod
    def parse_response(cls, response_text: str) -> Dict[str, Any]:
        """
        解析AI响应

        Args:
            response_text: AI返回的文本

        Returns:
            Dict: 包含测试用例列表的字典
        """
        try:
            # 尝试直接解析JSON
            data = json.loads(response_text)

            # 检查是否有test_cases字段
            if isinstance(data, dict):
                if 'test_cases' in data:
                    return data
                else:
                    # 如果没有test_cases字段，尝试将整个对象作为单个测试用例
                    if 'test_case_name' in data:
                        return {'test_cases': [data]}
                    else:
                        return {'test_cases': []}

            # 如果是数组，直接包装成test_cases格式
            elif isinstance(data, list):
                return {'test_cases': data}

            return {'test_cases': []}

        except json.JSONDecodeError:
            # 如果直接解析失败，尝试提取JSON部分
            import re
            json_pattern = r'\{.*?\}'
            matches = re.findall(json_pattern, response_text, re.DOTALL)

            for match in matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, dict) and 'test_cases' in data:
                        return data
                except:
                    continue

            return {'test_cases': []}
