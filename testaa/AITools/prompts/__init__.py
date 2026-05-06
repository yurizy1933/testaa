"""
Prompt统一管理模块
"""
from .base import BasePrompt
from .api_testcase import APITestCasePrompt
from .html_parser import HTMLParserPrompt
from .dependency import GetDependencyPrompt
from .fill_data import FillTestDataPrompt
from .execute_api import ExecuteApiPrompt
from .validate_testcase import ValidateTestcasePrompt
