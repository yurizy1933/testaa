"""
AI配置管理模块
"""

import os
from typing import Dict, Optional


class AIConfig:
    """AI配置类"""

    # 默认配置
    DEFAULT_PROVIDER = 'zhipu'
    ENABLE_CACHE = True
    CACHE_TTL = 3600  # 缓存过期时间（秒）
    ENABLE_MONITORING = True
    LOG_LEVEL = 'INFO'

    # AI提供商API密钥（实际项目中应该从环境变量或配置文件中读取）
    API_KEYS = {
        'zhipu': os.getenv('ZHIPUAI_API_KEY', ''),
        'deepseek': os.getenv('DEEPSEEK_API_KEY', ''),
    }

    # 成本配置（每千token的成本，单位：美元）
    COSTS = {
        'zhipu': {
            'glm-4': 0.12,
            'glm-3-turbo': 0.005,
        },
        'deepseek': {
            'deepseek-chat': 0.002,
            'deepseek-coder': 0.002,
        },
    }

    # 提供商配置
    PROVIDER_CONFIGS = {
        'deepseek': {
            'base_url': os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com'),
        },
    }

    def __init__(
        self,
        default_provider: Optional[str] = None,
        enable_cache: Optional[bool] = None,
        cache_ttl: Optional[int] = None,
        enable_monitoring: Optional[bool] = None,
        log_level: Optional[str] = None,
        api_keys: Optional[Dict[str, str]] = None
    ):
        """初始化配置"""
        self.default_provider = default_provider or self.DEFAULT_PROVIDER
        self.enable_cache = enable_cache if enable_cache is not None else self.ENABLE_CACHE
        self.cache_ttl = cache_ttl if cache_ttl is not None else self.CACHE_TTL
        self.enable_monitoring = enable_monitoring if enable_monitoring is not None else self.ENABLE_MONITORING
        self.log_level = log_level or self.LOG_LEVEL
        self._api_keys = api_keys or self.API_KEYS.copy()

    def get_api_key(self, provider: str) -> str:
        """获取指定提供商的API密钥"""
        return self._api_keys.get(provider, '')

    def set_api_key(self, provider: str, api_key: str):
        """设置指定提供商的API密钥"""
        self._api_keys[provider] = api_key

    def get_cost(self, model: str) -> float:
        """获取模型成本"""
        for provider, models in self.COSTS.items():
            if model in models:
                return models[model]
        return 0.0

    def get_provider_config(self, provider: str) -> Dict:
        """获取提供商配置"""
        return self.PROVIDER_CONFIGS.get(provider, {})


# 全局配置实例
_config: Optional[AIConfig] = None


def get_config() -> AIConfig:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = AIConfig()
    return _config


def set_config(config: AIConfig):
    """设置全局配置实例"""
    global _config
    _config = config
