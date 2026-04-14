"""
AI提示词模块 - 统一管理所有AI提示词
"""

from .base import BasePrompt
from .html_parser import HTMLParserPrompt
from .api_testcase import APITestCaseGeneratorPrompt
from .execute_api import ExecuteApiPrompt
from .validate_testcase import ValidateTestcasePrompt

__all__ = [
    'BasePrompt',
    'HTMLParserPrompt',
    'APITestCaseGeneratorPrompt',
    'ExecuteApiPrompt',
    'ValidateTestcasePrompt'
]
