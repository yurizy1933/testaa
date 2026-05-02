"""
AI抽象基类 - 定义所有AI提供商必须实现的接口
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class AIResponse:
    """AI响应数据类"""
    content: str
    model: str
    tokens_used: Optional[int] = None
    cost: Optional[float] = None
    provider: str = ""
    raw_response: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'content': self.content,
            'model': self.model,
            'tokens_used': self.tokens_used,
            'cost': self.cost,
            'provider': self.provider
        }


class AIProvider(ABC):
    """AI提供商抽象基类"""

    def __init__(self, api_key: str, **kwargs):
        self.api_key = api_key
        self.kwargs = kwargs
        self._client = None

    @property
    @abstractmethod
    def name(self) -> str:
        """提供商名称"""
        pass

    @property
    @abstractmethod
    def default_model(self) -> str:
        """默认模型"""
        pass

    @abstractmethod
    def call_chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        json_mode: bool = False,
        **kwargs
    ) -> AIResponse:
        """
        调用聊天完成接口

        Args:
            messages: 消息列表
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            json_mode: 是否强制JSON模式
            **kwargs: 其他参数

        Returns:
            AIResponse: AI响应对象
        """
        pass

    @abstractmethod
    def supports_json_mode(self, model: str) -> bool:
        """
        检查模型是否支持JSON模式

        Args:
            model: 模型名称

        Returns:
            bool: 是否支持JSON模式
        """
        pass

    @abstractmethod
    def get_cost_per_1k_tokens(self, model: str) -> float:
        """
        获取每千token的成本

        Args:
            model: 模型名称

        Returns:
            float: 每千token的成本（美元）
        """
        pass

    def calculate_cost(self, tokens: int, model: str) -> float:
        """
        计算成本

        Args:
            tokens: 使用的token数
            model: 模型名称

        Returns:
            float: 成本（美元）
        """
        if tokens is None:
            return 0.0
        cost_per_1k = self.get_cost_per_1k_tokens(model)
        return (tokens / 1000) * cost_per_1k

    def validate_messages(self, messages: List[Dict[str, str]]) -> bool:
        """
        验证消息格式

        Args:
            messages: 消息列表

        Returns:
            bool: 是否有效
        """
        if not messages:
            return False

        for msg in messages:
            if not isinstance(msg, dict):
                return False
            if 'role' not in msg or 'content' not in msg:
                return False

        return True
