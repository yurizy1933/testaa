"""
HTML文档解析Prompt
"""
from .base import BasePrompt
from typing import List
import json


class HTMLParserPrompt(BasePrompt):
    """HTML文档解析Prompt"""

    def __init__(self):
        self._system_prompt = """你是一个专业的API文档解析专家，擅长从HTML文档中提取完整接口信息。

关键判断标准：
1. 完整接口定义：必须同时包含接口路径、HTTP方法、至少一种参数信息（入参或出参）
2. 目录链接：仅有接口名称或简介，缺少具体参数、方法等详细信息
3. 存储价值：只有具备可执行信息的接口才有存储价值

过滤标准（必须全部满足）：
- 有明确的api_path（如：/api/v2/xxx, v2.xxx.xxx）
- 有HTTP方法（GET/POST/PUT/DELETE等）
- 有api_name接口名称
- 至少有入参或出参中的一种信息

拒绝存储：
- 只有接口名称的目录链接
- 缺少参数详情的简介
- 无法确定HTTP方法的引用
- 概念性说明而无具体接口定义"""

        self._user_prompt_template = """请分析以下HTML文档内容，提取完整的API接口信息。

HTML内容：
{content}

请以JSON格式返回所有完整接口信息，每个接口包含以下字段：
- api_name: 接口名称（必填）
- api_path: 接口路径（必填，如：/api/v2/xxx, v2.xxx.xxx）
- method: 请求方法（必填，GET/POST/PUT/DELETE等）
- request_params: 入参说明（JSON格式或文本描述，至少需要一个）
- response_params: 出参说明（JSON格式或文本描述，至少需要一个）
- remark: 备注（可选）

返回格式示例：
{example}

重要：请只返回JSON格式的数组，不要包含其他说明文字。确保每个接口都有完整的参数信息。"""

        # 示例响应
        self._example_response = [
            {
                "api_name": "获取开放营销活动添加产品",
                "api_path": "/api/v2/ams/get_open_campaign_added_product",
                "method": "GET",
                "request_params": {"campaign_id": "活动ID", "page_size": "页面大小"},
                "response_params": {"product_list": "产品列表", "total_count": "总数"},
                "remark": "获取已添加到开放营销活动的产品列表"
            }
        ]

    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return self._system_prompt

    def get_user_prompt(self, **kwargs) -> str:
        """获取用户提示词"""
        content = kwargs.get('content', '')
        example_str = json.dumps(self._example_response, ensure_ascii=False, indent=2)

        # 限制内容长度
        max_length = 8000
        if len(content) > max_length:
            content = content[:max_length] + "...[内容已截断]"

        return self._user_prompt_template.format(content=content, example=example_str)

    @classmethod
    def parse_response(cls, response_text: str) -> list:
        """解析AI响应"""
        try:
            # 尝试直接解析JSON
            data = json.loads(response_text)

            # 处理各种JSON结构
            if isinstance(data, list):
                return cls._filter_valid_interfaces(data)
            elif isinstance(data, dict):
                # 检查常见的数据字段
                for key in ['interfaces', 'data', 'results', 'api_list', 'apis']:
                    if key in data and isinstance(data[key], list):
                        return cls._filter_valid_interfaces(data[key])
                return []
            return []

        except json.JSONDecodeError:
            # 尝试从文本中提取JSON
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
        """过滤有效接口"""
        return [
            iface for iface in interfaces
            if isinstance(iface, dict) and cls._is_complete_interface(iface)
        ]

    @classmethod
    def _is_complete_interface(cls, interface: dict) -> bool:
        """判断接口是否完整"""
        # 检查必需字段
        if not interface.get('api_path') or not interface.get('method') or not interface.get('api_name'):
            return False

        # 检查参数完整性
        has_request = interface.get('request_params') and str(interface.get('request_params')).strip()
        has_response = interface.get('response_params') and str(interface.get('response_params')).strip()

        return has_request or has_response
