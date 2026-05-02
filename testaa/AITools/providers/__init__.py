"""
AI提供商模块 - 实现各种AI提供商
"""

from .zhipu import ZhipuProvider
from .deepseek import DeepSeekProvider

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


__all__ = [
    'ZhipuProvider',
    'DeepSeekProvider',
    'get_provider_factory',
    'register_provider',
    'get_available_providers'
]
