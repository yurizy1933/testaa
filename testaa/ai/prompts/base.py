"""
提示词基类
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BasePrompt(ABC):
    """提示词基类"""

    def __init__(self):
        self._system_prompt = ""
        self._user_prompt_template = ""

    @abstractmethod
    def get_system_prompt(self) -> str:
        """获取系统提示词"""
        pass

    @abstractmethod
    def get_user_prompt(self, **kwargs) -> str:
        """获取用户提示词（支持变量替换）"""
        pass

    def format_prompt(self, **kwargs) -> tuple:
        """格式化完整的提示词"""
        return self.get_system_prompt(), self.get_user_prompt(**kwargs)

    def _replace_variables(self, template: str, variables: Dict[str, Any]) -> str:
        """替换提示词中的变量"""
        for key, value in variables.items():
            placeholder = "{{" + key + "}}"
            template = template.replace(placeholder, str(value))
        return template
