"""
AI管理器 - 统一管理AI调用
"""

import json
import hashlib
import logging
from typing import Dict, List, Any, Optional
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
        from ..providers import get_provider_factory

        factory = get_provider_factory(provider_name)
        api_key = self.config.get_api_key(provider_name)
        # 传入配置中的额外参数（如果有）
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
        # 验证消息格式
        if not self.provider.validate_messages(messages):
            raise ValueError("Invalid message format")

        # 使用默认模型
        if model is None:
            model = self.provider.default_model

        logger.info(f"Calling AI provider: {self.provider_name}, model: {model}")

        try:
            # 调用AI提供商
            response = self.provider.call_chat_completion(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                json_mode=json_mode,
                **kwargs
            )

            # 计算成本
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

    def parse_json_response(
        self,
        response: str,
        expected_keys: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        解析JSON响应

        Args:
            response: AI响应文本
            expected_keys: 期望的键列表（用于验证）

        Returns:
            Dict: 解析后的JSON对象
        """
        try:
            # 尝试直接解析JSON
            data = json.loads(response)

            # 如果指定了期望的键，验证是否存在
            if expected_keys:
                for key in expected_keys:
                    if key not in data:
                        raise ValueError(f"Missing expected key: {key}")

            return data

        except json.JSONDecodeError:
            # 如果直接解析失败，尝试提取JSON部分
            return self._extract_json_from_text(response)

    def _extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """从文本中提取JSON对象"""
        import re

        # 尝试提取JSON对象
        json_pattern = r'\{.*?\}'
        matches = re.findall(json_pattern, text, re.DOTALL)

        for match in matches:
            try:
                data = json.loads(match)
                return data
            except:
                continue

        # 尝试提取JSON数组
        array_pattern = r'\[.*?\]'
        matches = re.findall(array_pattern, text, re.DOTALL)

        for match in matches:
            try:
                data = json.loads(match)
                return {"data": data}
            except:
                continue

        return {}

    def switch_provider(self, provider_name: str):
        """切换提供商"""
        self.provider_name = provider_name
        self.provider = self._get_provider(provider_name)
