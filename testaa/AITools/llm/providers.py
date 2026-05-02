"""
AI提供商实现 - ZhipuAI / DeepSeek
"""

from typing import Dict, List, Any
from .base import AIProvider


class ZhipuProvider(AIProvider):
    """智谱AI提供商类"""

    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key, **kwargs)
        try:
            from zhipuai import ZhipuAI
            self._client = ZhipuAI(api_key=api_key)
        except ImportError:
            raise ImportError("zhipuai package is required for ZhipuAI provider")

    @property
    def name(self) -> str:
        return "zhipu"

    @property
    def default_model(self) -> str:
        return "glm-4"

    def _handle_json_mode(
        self,
        messages: List[Dict[str, str]],
        request_params: Dict[str, Any],
        model: str
    ) -> None:
        if self.supports_json_mode(model):
            request_params["response_format"] = {"type": "json_object"}

    def supports_json_mode(self, model: str) -> bool:
        return model.startswith('glm-4')


class DeepSeekProvider(AIProvider):
    """DeepSeek提供商类"""

    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com", **kwargs):
        super().__init__(api_key, **kwargs)
        self.base_url = base_url

        try:
            from openai import OpenAI
            self._client = OpenAI(
                api_key=api_key,
                base_url=base_url
            )
        except ImportError:
            raise ImportError("openai package is required for DeepSeek provider")

    @property
    def name(self) -> str:
        return "deepseek"

    @property
    def default_model(self) -> str:
        return "deepseek-chat"

    def _handle_json_mode(
        self,
        messages: List[Dict[str, str]],
        request_params: Dict[str, Any],
        model: str
    ) -> None:
        json_instruction = {"role": "system", "content": "请确保只返回JSON格式的数据，不要包含其他说明文字。"}
        if messages[0]['role'] == 'system':
            messages[0]['content'] = json_instruction['content'] + "\n\n" + messages[0]['content']
        else:
            messages.insert(0, json_instruction)

    def supports_json_mode(self, model: str) -> bool:
        return False


# 提供商工厂
_provider_factories = {
    'zhipu': lambda api_key, **kwargs: ZhipuProvider(api_key, **kwargs),
    'deepseek': lambda api_key, **kwargs: DeepSeekProvider(api_key, **kwargs),
}


def get_provider_factory(provider_name: str):
    """获取提供商工厂函数"""
    factory = _provider_factories.get(provider_name.lower())
    if factory is None:
        raise ValueError(f"Unknown provider: {provider_name}")
    return factory


def register_provider(name: str, factory):
    """注册新的提供商"""
    _provider_factories[name.lower()] = factory


def get_available_providers() -> list:
    """获取所有可用的提供商"""
    return list(_provider_factories.keys())
