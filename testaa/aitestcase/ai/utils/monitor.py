"""
AI监控模块 - 提供AI调用监控和日志功能
"""

import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class AICallRecord:
    """AI调用记录"""
    call_id: str
    provider: str
    model: str
    messages: List[Dict[str, str]]
    start_time: float
    end_time: Optional[float] = None
    tokens_used: Optional[int] = None
    cost: Optional[float] = None
    status: str = 'running'  # running, success, error
    error_message: Optional[str] = None
    cache_hit: bool = False

    def duration(self) -> float:
        """获取调用时长（秒）"""
        if self.end_time is None:
            return 0.0
        return self.end_time - self.start_time


class AIMonitor:
    """AI监控类"""

    def __init__(self, enabled: bool = True, log_level: str = 'INFO'):
        """
        初始化监控

        Args:
            enabled: 是否启用监控
            log_level: 日志级别
        """
        self.enabled = enabled
        self.log_level = log_level
        self._calls: Dict[str, AICallRecord] = {}
        self._call_counter = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._statistics: Dict[str, Any] = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'total_tokens': 0,
            'total_cost': 0.0,
            'total_duration': 0.0,
            'by_provider': defaultdict(lambda: {
                'calls': 0,
                'tokens': 0,
                'cost': 0.0
            })
        }

        # 设置日志
        self._setup_logging()

    def _setup_logging(self):
        """设置日志"""
        self.logger = logging.getLogger('ai_monitor')
        self.logger.setLevel(getattr(logging, self.log_level.upper()))

        # 如果没有处理器，添加控制台处理器
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def log_call_start(
        self,
        provider: str,
        model: str,
        messages: List[Dict[str, str]]
    ) -> str:
        """
        记录调用开始

        Args:
            provider: 提供商名称
            model: 模型名称
            messages: 消息列表

        Returns:
            str: 调用ID
        """
        if not self.enabled:
            return f"call_{self._call_counter}"

        call_id = f"call_{self._call_counter}"
        self._call_counter += 1

        record = AICallRecord(
            call_id=call_id,
            provider=provider,
            model=model,
            messages=messages,
            start_time=time.time()
        )

        self._calls[call_id] = record
        self._statistics['total_calls'] += 1
        self._statistics['by_provider'][provider]['calls'] += 1

        self.logger.info(f"[{call_id}] AI call started: {provider}/{model}")

        return call_id

    def log_call_success(
        self,
        call_id: str,
        tokens_used: Optional[int],
        cost: Optional[float]
    ):
        """
        记录调用成功

        Args:
            call_id: 调用ID
            tokens_used: 使用的token数
            cost: 成本
        """
        if not self.enabled or call_id not in self._calls:
            return

        record = self._calls[call_id]
        record.end_time = time.time()
        record.tokens_used = tokens_used
        record.cost = cost
        record.status = 'success'

        duration = record.duration()

        # 更新统计
        self._statistics['successful_calls'] += 1
        if tokens_used:
            self._statistics['total_tokens'] += tokens_used
            self._statistics['by_provider'][record.provider]['tokens'] += tokens_used
        if cost:
            self._statistics['total_cost'] += cost
            self._statistics['by_provider'][record.provider]['cost'] += cost
        self._statistics['total_duration'] += duration

        self.logger.info(
            f"[{call_id}] AI call completed: "
            f"{duration:.2f}s, {tokens_used} tokens, ${cost:.4f}"
        )

    def log_call_error(self, call_id: str, error_message: str):
        """
        记录调用失败

        Args:
            call_id: 调用ID
            error_message: 错误信息
        """
        if not self.enabled or call_id not in self._calls:
            return

        record = self._calls[call_id]
        record.end_time = time.time()
        record.error_message = error_message
        record.status = 'error'

        duration = record.duration()

        # 更新统计
        self._statistics['failed_calls'] += 1
        self._statistics['total_duration'] += duration

        self.logger.error(
            f"[{call_id}] AI call failed after {duration:.2f}s: {error_message}"
        )

    def log_cache_hit(self, cache_key: str):
        """记录缓存命中"""
        if not self.enabled:
            return

        self._cache_hits += 1
        self.logger.debug(f"Cache hit: {cache_key}")

    def log_cache_miss(self, cache_key: str):
        """记录缓存未命中"""
        if not self.enabled:
            return

        self._cache_misses += 1
        self.logger.debug(f"Cache miss: {cache_key}")

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            Dict: 统计信息
        """
        return {
            'total_calls': self._statistics['total_calls'],
            'successful_calls': self._statistics['successful_calls'],
            'failed_calls': self._statistics['failed_calls'],
            'success_rate': (
                self._statistics['successful_calls'] / self._statistics['total_calls'] * 100
                if self._statistics['total_calls'] > 0 else 0
            ),
            'total_tokens': self._statistics['total_tokens'],
            'total_cost': self._statistics['total_cost'],
            'average_duration': (
                self._statistics['total_duration'] / self._statistics['successful_calls']
                if self._statistics['successful_calls'] > 0 else 0
            ),
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'cache_hit_rate': (
                self._cache_hits / (self._cache_hits + self._cache_misses) * 100
                if (self._cache_hits + self._cache_misses) > 0 else 0
            ),
            'by_provider': dict(self._statistics['by_provider'])
        }

    def get_call_records(self) -> List[AICallRecord]:
        """获取所有调用记录"""
        return list(self._calls.values())

    def clear_records(self):
        """清空所有记录"""
        self._calls.clear()
        self._call_counter = 0
        self._cache_hits = 0
        self._cache_misses = 0
        self._statistics = {
            'total_calls': 0,
            'successful_calls': 0,
            'failed_calls': 0,
            'total_tokens': 0,
            'total_cost': 0.0,
            'total_duration': 0.0,
            'by_provider': defaultdict(lambda: {
                'calls': 0,
                'tokens': 0,
                'cost': 0.0
            })
        }

        self.logger.info("All records cleared")


# 全局监控实例
_monitor_instance = None


def get_monitor() -> AIMonitor:
    """获取全局监控实例"""
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = AIMonitor()
    return _monitor_instance


def set_monitor(monitor: AIMonitor):
    """设置全局监控实例"""
    global _monitor_instance
    _monitor_instance = monitor
