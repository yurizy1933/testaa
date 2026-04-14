"""
测试结果校验提示词模块
"""

import json
from typing import Dict, Any, Optional
from .base import BasePrompt


class ValidateTestcasePrompt(BasePrompt):
    """测试结果校验提示词"""

    def __init__(self):
        self._system_prompt = "你是一位专业的API测试结果校验助手。"

        self._user_prompt_template = """
请分析以下测试执行结果，校验是否符合预期。

## 用例信息
- 用例ID: {{case_id}}
- 接口名称: {{api_name}}
- 前置条件: {{precondition}}
- 测试点: {{testpoint}}
- 预期结果: {{expectation}}

## 执行结果
{{execution_results}}

## 校验要求
1. 检查每个接口的响应是否符合预期
2. 验证业务逻辑是否正确
3. 检查是否有异常或错误
4. 给出总体评价和改进建议

请返回如下格式的JSON：
```json
{
  "overall_result": "pass/fail",
  "summary": "总体评价",
  "details": [
    {
      "run_num": 1,
      "api_name": "...",
      "result": "pass/fail",
      "issues": ["..."],
      "suggestions": ["..."]
    }
  ]
}
```
"""

    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return self._system_prompt

    def get_user_prompt(self, **kwargs) -> str:
        """获取用户提示词"""
        return self._user_prompt_template.format(**kwargs)
