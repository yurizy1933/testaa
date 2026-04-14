"""
AI缓存模块 - 提供AI响应缓存功能
"""

import time
import hashlib
from typing import Optional, Dict, Any
from collections import OrderedDict


class AICache:
    """AI响应缓存类"""

    def __init__(self, enabled: bool = True, ttl: int = 3600, max_size: int = 1000):
        """
        初始化缓存

        Args:
            enabled: 是否启用缓存
            ttl: 缓存生存时间（秒）
            max_size: 最大缓存条目数
        """
        self.enabled = enabled
        self.ttl = ttl
        self.max_size = max_size
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()

    def get(self, key: str) -> Optional['AIResponse']:
        """
        获取缓存

        Args:
            key: 缓存键

        Returns:
            AIResponse: 缓存的响应，如果不存在或过期则返回None
        """
        if not self.enabled:
            return None

        cached_item = self._cache.get(key)

        if cached_item is None:
            return None

        # 检查是否过期
        if time.time() - cached_item['timestamp'] > self.ttl:
            self._cache.pop(key)
            return None

        # 更新访问顺序（LRU）
        self._cache.move_to_end(key)

        return cached_item['response']

    def set(self, key: str, response: 'AIResponse'):
        """
        设置缓存

        Args:
            key: 缓存键
            response: AI响应对象
        """
        if not self.enabled:
            return

        # 如果缓存已满，删除最旧的条目
        if len(self._cache) >= self.max_size and key not in self._cache:
            self._cache.popitem(last=False)

        # 添加缓存条目
        self._cache[key] = {
            'response': response,
            'timestamp': time.time()
        }

    def clear(self):
        """清空缓存"""
        self._cache.clear()

    def delete(self, key: str):
        """删除指定缓存"""
        if key in self._cache:
            self._cache.pop(key)

    def size(self) -> int:
        """获取缓存大小"""
        return len(self._cache)

    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            'enabled': self.enabled,
            'size': len(self._cache),
            'max_size': self.max_size,
            'ttl': self.ttl
        }


# 全局缓存实例
_cache_instance = None


def get_cache() -> AICache:
    """获取全局缓存实例"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = AICache()
    return _cache_instance


def set_cache(cache: AICache):
    """设置全局缓存实例"""
    global _cache_instance
    _cache_instance = cache
