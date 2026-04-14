"""
AI配置管理模块 - 统一管理AI相关配置
"""

import os
from typing import Dict, Any
from dataclasses import dataclass, field


@dataclass
class AIConfig:
    """AI配置类"""

    # 默认提供商
    default_provider: str = 'zhipu'

    # API密钥配置
    api_keys: Dict[str, str] = field(default_factory=dict)

    # 模型配置
    models: Dict[str, str] = field(default_factory=dict)

    # 成本配置（每千token，美元）
    costs: Dict[str, float] = field(default_factory=dict)

    # 缓存配置
    enable_cache: bool = True
    cache_ttl: int = 3600  # 缓存时间（秒）

    # 监控配置
    enable_monitoring: bool = True
    log_level: str = 'INFO'

    def __post_init__(self):
        """初始化后处理，加载环境变量"""
        self._load_from_env()
        self._load_defaults()

    def _load_from_env(self):
        """从环境变量和配置文件加载配置"""
        # 智谱AI配置
        if not self.api_keys.get('zhipu'):
            self.api_keys['zhipu'] = os.getenv('ZHIPU_API_KEY', self._load_from_file('ZHIPU_API_KEY'))

        # DeepSeek配置
        if not self.api_keys.get('deepseek'):
            self.api_keys['deepseek'] = os.getenv('DEEPSEEK_API_KEY', self._load_from_file('DEEPSEEK_API_KEY'))

        # OpenAI配置
        if not self.api_keys.get('openai'):
            self.api_keys['openai'] = os.getenv('OPENAI_API_KEY', self._load_from_file('OPENAI_API_KEY'))

        # 默认提供商
        if os.getenv('AI_DEFAULT_PROVIDER'):
            self.default_provider = os.getenv('AI_DEFAULT_PROVIDER')

    def _load_from_file(self, key_name: str) -> str:
        """
        从配置文件加载API密钥

        Args:
            key_name: 密钥名称

        Returns:
            密钥值
        """
        try:
            from ..api_keys import ZHIPU_API_KEY, DEEPSEEK_API_KEY, OPENAI_API_KEY

            key_mapping = {
                'ZHIPU_API_KEY': ZHIPU_API_KEY,
                'DEEPSEEK_API_KEY': DEEPSEEK_API_KEY,
                'OPENAI_API_KEY': OPENAI_API_KEY
            }

            return key_mapping.get(key_name, '')
        except (ImportError, AttributeError):
            return ''

    def _load_defaults(self):
        """加载默认配置"""
        # 默认模型
        default_models = {
            'zhipu': 'glm-4',
            'deepseek': 'deepseek-chat',
            'openai': 'gpt-4'
        }
        for provider, model in default_models.items():
            if provider not in self.models or not self.models[provider]:
                self.models[provider] = model

        # 默认成本（美元/千token）
        default_costs = {
            'glm-4': 0.12,  # 智谱AI
            'deepseek-chat': 0.14,  # DeepSeek
            'gpt-4': 30.0,  # OpenAI GPT-4
            'gpt-3.5-turbo': 0.002,  # OpenAI GPT-3.5
        }
        for model, cost in default_costs.items():
            if model not in self.costs:
                self.costs[model] = cost

    def get_api_key(self, provider: str) -> str:
        """获取指定提供商的API密钥"""
        return self.api_keys.get(provider, '')

    def get_model(self, provider: str) -> str:
        """获取指定提供商的默认模型"""
        return self.models.get(provider, self.get_default_model(provider))

    def get_default_model(self, provider: str) -> str:
        """获取提供商的默认模型"""
        defaults = {
            'zhipu': 'glm-4',
            'deepseek': 'deepseek-chat',
            'openai': 'gpt-4'
        }
        return defaults.get(provider, 'glm-4')

    def get_cost(self, model: str) -> float:
        """获取指定模型的成本"""
        return self.costs.get(model, 0.0)

    def update_config(self, **kwargs):
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)


# 全局配置实例
_config_instance = None


def get_config() -> AIConfig:
    """获取全局配置实例"""
    global _config_instance
    if _config_instance is None:
        _config_instance = AIConfig()
    return _config_instance


def set_config(config: AIConfig):
    """设置全局配置实例"""
    global _config_instance
    _config_instance = config
