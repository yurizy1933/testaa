"""
AI核心模块 - 提供抽象层基础功能
"""

from .base import AIProvider, AIResponse
from .manager import AIManager
from .config import AIConfig

__all__ = ['AIProvider', 'AIResponse', 'AIManager', 'AIConfig']
