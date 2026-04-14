"""
文档测试用例生成提示词模块
"""

import json
from typing import Dict, Any, Optional


class TestCaseGeneratorPrompt:
    """文档测试用例生成提示词类"""

    # 系统提示词
    SYSTEM_PROMPT = "你是一个专业的测试用例生成助手，擅长根据文档内容生成测试用例。"

    # 用户提示词模板
    USER_PROMPT_TEMPLATE = """
请根据以下文档内容生成测试用例。

文档内容：
{content}

请以JSON格式返回所有测试用例，每个测试用例包含以下字段：
- testpoint: 测试点
- operation: 操作步骤
- expectedresult: 预期结果

返回格式示例：
{example}

请只返回JSON格式的数组，不要包含其他说明文字。
"""

    # 示例响应
    EXAMPLE_RESPONSE = [
        {
            "testpoint": "请假时间小于当前日期，显示错误提示\"请假时间只能是今天\"。",
            "operation": "1、选择请假日期小于当前日期\n2、输入请假原因\n3、提交请假",
            "expectedresult": "提示：\"请假时间只能是今天\"。"
        },
        {
            "testpoint": "请假时间大于当前日期，显示错误提示\"请假时间只能是今天\"。",
            "operation": "1、选择请假日期大于当前日期\n2、输入请假原因\n3、提交请假",
            "expectedresult": "提示：\"请假时间只能是今天\"。"
        }
    ]

    @classmethod
    def get_prompt(cls, content: str) -> str:
        """
        获取完整的提示词

        Args:
            content: 文档内容

        Returns:
            str: 完整的提示词
        """
        # 限制内容长度，避免超出token限制
        max_length = 8000
        if len(content) > max_length:
            content = content[:max_length] + "...[内容已截断]"

        example_str = json.dumps(
            cls.EXAMPLE_RESPONSE,
            ensure_ascii=False,
            indent=2
        )

        return cls.USER_PROMPT_TEMPLATE.format(
            content=content,
            example=example_str
        )

    @classmethod
    def get_system_prompt(cls) -> str:
        """获取系统提示词"""
        return cls.SYSTEM_PROMPT

    @classmethod
    def get_user_prompt(cls, content: str) -> str:
        """获取用户提示词"""
        return cls.get_prompt(content)

    @classmethod
    def parse_response(cls, response_text: str) -> list:
        """
        解析AI响应

        Args:
            response_text: AI返回的文本

        Returns:
            list: 测试用例列表
        """
        try:
            # 尝试直接解析JSON
            data = json.loads(response_text)

            # 如果返回的是对象，检查是否有特定的字段
            if isinstance(data, dict):
                # 检查常见的字段名
                for key in ['test_cases', 'testcases', 'data', 'results']:
                    if key in data and isinstance(data[key], list):
                        return data[key]

                # 如果没有找到特定字段，尝试将整个对象作为单个测试用例
                if 'testpoint' in data:
                    return [data]

                return []

            # 如果是数组，直接返回
            elif isinstance(data, list):
                return data

            return []

        except json.JSONDecodeError:
            # 如果直接解析失败，尝试提取JSON部分
            import re
            json_pattern = r'\[.*?\]'
            matches = re.findall(json_pattern, response_text, re.DOTALL)

            for match in matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, list):
                        return data
                except:
                    continue

            return []
