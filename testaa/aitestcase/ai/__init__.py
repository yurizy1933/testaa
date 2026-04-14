"""
AI模块 - 统一管理所有AI相关功能
提供抽象层，支持多种AI提供商
"""

from .core.manager import AIManager
from .core.config import AIConfig

__all__ = ['AIManager', 'AIConfig']
