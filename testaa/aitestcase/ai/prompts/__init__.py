"""
AI提示词模块 - 统一管理所有AI提示词
"""

from .html_parser import HTMLParserPrompt
from .test_case import TestCaseGeneratorPrompt
from .api_test import APITestCaseGeneratorPrompt

__all__ = [
    'HTMLParserPrompt',
    'TestCaseGeneratorPrompt',
    'APITestCaseGeneratorPrompt'
]
