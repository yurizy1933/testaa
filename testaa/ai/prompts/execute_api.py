"""
API执行参数填充提示词模块
"""

import json
from typing import Dict, Any, Optional
from .base import BasePrompt


class ExecuteApiPrompt(BasePrompt):
    """API执行参数填充提示词"""

    def __init__(self):
        self._system_prompt = "你是一位专业的API测试参数分析助手。"

        self._user_prompt_template = """
请分析以下接口执行历史和当前接口信息，智能填充当前接口的参数。

## 当前用例信息
- 用例ID: {{case_id}}
- 接口名称: {{api_name}}
- 前置条件: {{precondition}}
- 测试点: {{testpoint}}
- 预期结果: {{expectation}}

## 接口执行历史
{{execution_history}}

## 当前接口信息
{{current_api_info}}

## 测试数据
{{test_data}}

## 要求
1. 根据执行历史中的响应数据，智能填充当前接口需要的参数
2. 如果参数可以从历史响应中获取，直接使用
3. 如果需要测试数据，从测试数据中获取
4. 返回JSON格式，包含需要填充的字段和值

请返回如下格式的JSON：
```json
{
  "request_body": {...},
  "params": {...},
  "headers": {...}
}
```
"""

    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return self._system_prompt

    def get_user_prompt(self, **kwargs) -> str:
        """获取用户提示词"""
        return self._user_prompt_template.format(**kwargs)
