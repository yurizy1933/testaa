"""
AI工具模块 - 统一管理所有AI相关的功能

已重构为使用新的AI抽象层，同时保持向后兼容性
"""

# 导入新的AI抽象层
from .ai.legacy import (
    # 配置
    set_api_keys,
    get_api_keys,

    # HTML解析
    parse_html_with_ai,
    parse_ai_response,

    # 测试用例生成
    call_ai_job,
    generate_api_test_cases,
    parse_test_cases_response,

    # 高级功能
    get_ai_statistics,
    clear_ai_cache,
    get_ai_providers,

    # 新架构
    AIManager
)

# 为了保持向后兼容性，也可以直接从新模块导入
from .ai.core.manager import AIManager as AIManagerNew
from .ai.core.config import AIConfig, get_config


# ==================== 兼容性说明 ====================
"""
本模块已重构为使用新的AI抽象层，提供以下改进：

1. 统一的AI提供商接口 - 支持智谱AI、DeepSeek等
2. 提示词管理 - 集中管理所有AI提示词
3. 缓存机制 - 减少重复调用，提高性能
4. 监控和日志 - 追踪AI调用和成本
5. 成本追踪 - 计算和统计AI使用成本
6. 扩展性 - 易于添加新的AI提供商

向后兼容性：
- 所有旧的函数接口保持不变
- 现有代码无需修改即可使用新架构
- 逐步迁移到新API时可以保持兼容

新功能使用示例：

1. 使用新的AI管理器：
    from .ai import AIManager

    manager = AIManager(provider_name='zhipu')
    response = manager.call_chat_completion(
        messages=[
            {"role": "system", "content": "你是一个助手"},
            {"role": "user", "content": "你好"}
        ]
    )

2. 获取AI使用统计：
    from .ai.legacy import get_ai_statistics

    stats = get_ai_statistics()

3. 清空AI缓存：
    from .ai.legacy import clear_ai_cache

    clear_ai_cache()

4. 切换AI提供商：
    from .ai import AIManager

    manager = AIManager(provider_name='deepseek')
    # 或者动态切换
    manager.switch_provider('zhipu')
"""


__all__ = [
    # 兼容接口（保持向后兼容）
    'set_api_keys',
    'get_api_keys',
    'parse_html_with_ai',
    'parse_ai_response',
    'call_ai_job',
    'generate_api_test_cases',
    'parse_test_cases_response',
    'get_ai_statistics',
    'clear_ai_cache',
    'get_ai_providers',

    # 新架构接口
    'AIManager',
    'AIManagerNew',
    'AIConfig',
    'get_config'
]
