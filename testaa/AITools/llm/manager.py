"""
AI管理器 - 统一管理AI调用
"""

import hashlib
import logging
from typing import Dict, List, Optional
from .base import AIProvider, AIResponse
from .config import AIConfig, get_config


logger = logging.getLogger(__name__)


class AIManager:
    """AI管理器 - 统一管理所有AI调用"""

    def __init__(self, provider_name: Optional[str] = None, config: Optional[AIConfig] = None):
        self.config = config or get_config()
        self.provider_name = provider_name or self.config.default_provider
        self.provider = self._get_provider(self.provider_name)

    def _get_provider(self, provider_name: str) -> AIProvider:
        """获取提供商实例"""
        from .providers import get_provider_factory

        factory = get_provider_factory(provider_name)
        api_key = self.config.get_api_key(provider_name)
        extra_kwargs = self.config.get_provider_config(provider_name)
        return factory(api_key, **extra_kwargs)

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
        if not self.provider.validate_messages(messages):
            raise ValueError("Invalid message format")

        if model is None:
            model = self.provider.default_model

        logger.info(f"Calling AI provider: {self.provider_name}, model: {model}")

        try:
            response = self.provider.call_chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
                **kwargs
            )

            if response.tokens_used:
                response.cost = self.provider.calculate_cost(response.tokens_used, model)

            logger.info(f"AI call successful, tokens used: {response.tokens_used}, cost: {response.cost}")

            return response

        except Exception as e:
            logger.error(f"AI call failed: {str(e)}")
            raise

    def call_with_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        json_mode: bool = False,
        **kwargs
    ) -> AIResponse:
        """
        使用系统提示词和用户提示词调用AI

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大token数
            json_mode: 是否强制JSON模式
            **kwargs: 其他参数

        Returns:
            AIResponse: AI响应对象
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        return self.call_chat_completion(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            json_mode=json_mode,
            **kwargs
        )

    def switch_provider(self, provider_name: str):
        """切换提供商"""
        self.provider_name = provider_name
        self.provider = self._get_provider(provider_name)
