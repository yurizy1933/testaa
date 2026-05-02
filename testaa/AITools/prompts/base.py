"""
Prompt基类
"""
from typing import Dict, Any
import json


class BasePrompt:
    """Prompt基类"""

    def __init__(self):
        self._system_prompt = ""
        self._user_prompt_template = ""
        self._example_response = {}

    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        return self._system_prompt

    def get_user_prompt(self, **kwargs) -> str:
        """获取用户提示词"""
        return self._user_prompt_template.format(**kwargs)

    @classmethod
    def parse_response(cls, response_text: str) -> Any:
        """解析AI响应（子类实现）"""
        raise NotImplementedError
