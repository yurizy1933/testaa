"""
HTML解析提示词模块
"""

import json
from typing import Dict, Any
from .base import BasePrompt


class HTMLParserPrompt(BasePrompt):
    """HTML文档解析提示词类"""

    def __init__(self):
        self._system_prompt = "你是一个专业的API文档解析助手，擅长从HTML文档中提取接口信息。重要：请只关注表格中的信息"

        self._user_prompt_template = """
请分析以下HTML文档内容，提取其中的API接口信息。

HTML内容：
{{content}}

请以JSON格式返回所有接口信息，每个接口包含以下字段：
- api_name: 接口名称
- api_path: 接口路径（必填字段，必须提供）
- method: 请求方法（GET/POST/PUT/DELETE等）
- request_params: 入参说明
- response_params: 出参说明
- remark: 备注（如果有）

前置判断：文档有效性验证
在开始解析前，请首先执行以下验证：

判断标准
如果HTML文档中同时缺失以下两类信息，则判定为非API文档：
路径信息：如 /api/xxx、/v1/xxx、/rest/xxx 等URL路径
方法信息：如 GET、POST、PUT、DELETE 等HTTP方法

返回格式示例：
{{example}}

请只返回JSON格式的数组，不要包含其他说明文字。
"""

        # 示例响应
        self._example_response = [
            {
                "api_name": "用户登录接口",
                "api_path": "/api/login",
                "method": "POST",
                "request_params": {"username": "用户名", "password": "密码"},
                "response_params": {"token": "登录令牌", "user_id": "用户ID"},
                "remark": "用户登录验证"
            }
        ]

    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return self._system_prompt

    def get_user_prompt(self, **kwargs) -> str:
        """获取用户提示词"""
        content = kwargs.get('content', '')
        example_str = json.dumps(
            self._example_response,
            ensure_ascii=False,
            indent=2
        )

        # 限制内容长度，避免超出token限制
        max_length = 8000
        if len(content) > max_length:
            content = content[:max_length] + "...[内容已截断]"

        return self._user_prompt_template.format(
            content=content,
            example=example_str
        )

    @classmethod
    def parse_response(cls, response_text: str) -> list:
        """
        解析AI响应

        Args:
            response_text: AI返回的文本

        Returns:
            list: 接口信息列表
        """
        try:
            # 尝试直接解析JSON
            data = json.loads(response_text)

            # 如果返回的是对象，检查是否有特定的字段
            if isinstance(data, dict):
                # 检查常见的字段名
                for key in ['interfaces', 'data', 'results', 'api_list', 'apis']:
                    if key in data and isinstance(data[key], list):
                        return cls._filter_valid_interfaces(data[key])

                # 如果没有找到特定字段，尝试将整个对象作为单个接口
                if 'api_name' in data or 'api_path' in data:
                    return cls._filter_valid_interfaces([data])

                return []

            # 如果是数组，直接返回（但需要过滤没有api_path的接口）
            elif isinstance(data, list):
                return cls._filter_valid_interfaces(data)

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
                        return cls._filter_valid_interfaces(data)
                except:
                    continue

            return []

    @classmethod
    def _filter_valid_interfaces(cls, interfaces: list) -> list:
        """
        过滤有效的接口

        Args:
            interfaces: 接口列表

        Returns:
            list: 有效的接口列表
        """
        return [
            iface for iface in interfaces
            if isinstance(iface, dict) and iface.get('api_path')
        ]
