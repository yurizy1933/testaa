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

## 关键判断标准

1. 完整接口定义：必须同时包含接口路径、HTTP方法、至少一种参数信息（入参或出参）
2. 目录链接：仅有接口名称或简介，缺少具体参数、方法等详细信息
3. 存储价值：只有具备可执行信息的接口才有存储价值

## 过滤标准（必须全部满足）

- 有明确的api_path（如：/api/v2/xxx, v2.xxx.xxx）
- 有HTTP方法（GET/POST/PUT/DELETE等）
- 有api_name接口名称
- 至少有入参或出参中的一种信息

## 拒绝存储

- 只有接口名称的目录链接
- 缺少参数详情的简介
- 无法确定HTTP方法的引用
- 概念性说明而无具体接口定义

## 参数提取要求（重要）

对每个参数必须提取以下信息（从文档中能获取多少就提取多少）：

### 入参（request_params）
每个入参用对象描述，包含：
- name: 参数名称（必填）
- type: 参数类型（string / integer / boolean / array / object，必填）
- required: 是否必填（true / false，必填）
- location: 传参位置（query / body / header / path / form，必填）
- description: 参数含义说明（必填）
- constraints: 约束条件，如取值范围、长度限制、格式要求等（如有）
- default: 默认值（如有）
- example: 示例值（如有）
- children: 嵌套子字段（仅当type为object或array时，描述内部结构。array类型描述元素结构）

### 出参（response_params）
每个出参用对象描述，包含：
- name: 字段名称（必填）
- type: 字段类型（string / integer / boolean / array / object，必填）
- description: 字段含义说明（必填）
- constraints: 约束条件，如枚举值、取值范围等（如有）
- children: 嵌套子字段（仅当type为object或array时，递归描述子字段结构）"""

        self._user_prompt_template = """请分析以下HTML文档内容，提取完整的API接口信息。

HTML内容：
{content}

请以JSON格式返回所有完整接口信息，每个接口包含以下字段：
- api_name: 接口名称（必填）
- api_path: 接口路径（必填，如：/api/v2/xxx, v2.xxx.xxx）
- method: 请求方法（必填，GET/POST/PUT/DELETE等）
- request_params: 入参列表（数组格式，每个参数包含 name/type/required/location/description/constraints/default/example/children，至少需要一个）
- response_params: 出参列表（数组格式，每个参数包含 name/type/description/constraints/children，至少需要一个）
- remark: 备注（可选，接口的补充说明）

返回格式示例：
{example}

重要：
1. 请只返回JSON格式的数组，不要包含其他说明文字
2. 参数必须使用数组格式，每个参数一个独立对象
3. 确保每个接口都有完整的参数信息（类型、是否必填、描述、约束等）
4. 对于嵌套对象/数组，使用children递归描述子字段"""

        # 示例响应 - 展示结构化参数格式
        self._example_response = [
            {
                "api_name": "获取开放营销活动添加产品",
                "api_path": "/api/v2/ams/get_open_campaign_added_product",
                "method": "GET",
                "request_params": [
                    {
                        "name": "campaign_id",
                        "type": "integer",
                        "required": True,
                        "location": "query",
                        "description": "活动ID",
                        "constraints": "正整数",
                        "default": None,
                        "example": "12345",
                        "children": None
                    },
                    {
                        "name": "page_size",
                        "type": "integer",
                        "required": False,
                        "location": "query",
                        "description": "每页返回数量",
                        "constraints": "1-100，默认20",
                        "default": 20,
                        "example": "20",
                        "children": None
                    },
                    {
                        "name": "page",
                        "type": "integer",
                        "required": False,
                        "location": "query",
                        "description": "页码",
                        "constraints": ">=1，默认1",
                        "default": 1,
                        "example": "1",
                        "children": None
                    }
                ],
                "response_params": [
                    {
                        "name": "code",
                        "type": "integer",
                        "description": "响应状态码，0表示成功",
                        "constraints": "0成功，非0失败",
                        "children": None
                    },
                    {
                        "name": "data",
                        "type": "object",
                        "description": "响应数据",
                        "constraints": None,
                        "children": [
                            {
                                "name": "product_list",
                                "type": "array",
                                "description": "产品列表",
                                "constraints": None,
                                "children": [
                                    {
                                        "name": "product_id",
                                        "type": "integer",
                                        "description": "产品ID",
                                        "constraints": None,
                                        "children": None
                                    },
                                    {
                                        "name": "product_name",
                                        "type": "string",
                                        "description": "产品名称",
                                        "constraints": None,
                                        "children": None
                                    },
                                    {
                                        "name": "max_exchange_rate",
                                        "type": "number",
                                        "description": "最大汇率",
                                        "constraints": ">0",
                                        "children": None
                                    }
                                ]
                            },
                            {
                                "name": "total_count",
                                "type": "integer",
                                "description": "总数量",
                                "constraints": None,
                                "children": None
                            }
                        ]
                    },
                    {
                        "name": "message",
                        "type": "string",
                        "description": "提示信息",
                        "constraints": None,
                        "children": None
                    }
                ],
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
        request_params = interface.get('request_params')
        response_params = interface.get('response_params')

        has_request = bool(request_params) and (
            (isinstance(request_params, list) and len(request_params) > 0) or
            (isinstance(request_params, str) and request_params.strip())
        )
        has_response = bool(response_params) and (
            (isinstance(response_params, list) and len(response_params) > 0) or
            (isinstance(response_params, str) and response_params.strip())
        )

        return has_request or has_response
