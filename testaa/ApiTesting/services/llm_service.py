"""
LLM 模型调用服务

负责调用外部 LLM API (DeepSeek/Qwen/OpenAI)
"""
import json
import os
from typing import Any, Dict, Generator, List, Optional

import requests

from utils.logger import get_logger

logger = get_logger(__name__)


class LLMService:
    """LLM 服务"""

    def __init__(self, config: Dict[str, Any]):
        self.provider = config.get("provider", "deepseek")
        self.base_url = config.get("base_url", "")
        self.api_key = config.get("api_key") or os.getenv(f"{self.provider.upper()}_API_KEY")
        self.model = config.get("model", "deepseek-chat")
        self.max_tokens = config.get("max_tokens", 4096)
        self.temperature = config.get("temperature", 0.7)

        # 不同 provider 的端点
        self.endpoints = {
            "deepseek": "/chat/completions",
            "qwen": "/chat/completions",
            "openai": "/v1/chat/completions",
        }

    def _build_body(
        self,
        messages: List[Dict[str, str]],
        stream: bool = False
    ) -> Dict[str, Any]:
        """构建请求体"""
        return {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "stream": stream,
        }

    def chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        同步调用 LLM

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            **kwargs: 额外参数

        Returns:
            {
                "content": "LLM 回答内容",
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, ...},
                "finish_reason": "stop"
            }
        """
        url = f"{self.base_url}{self.endpoints.get(self.provider, '/chat/completions')}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = self._build_body(messages, stream=False)
        body.update(kwargs)

        response = requests.post(url, headers=headers, json=body, timeout=60)
        response.raise_for_status()
        result = response.json()

        content = result["choices"][0]["message"]["content"]
        return {
            "content": content,
            "usage": result.get("usage", {}),
            "finish_reason": result["choices"][0].get("finish_reason"),
            "raw": result
        }

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Generator[str, None, None]:
        """
        流式调用 LLM

        Args:
            messages: 消息列表
            **kwargs: 额外参数

        Yields:
            回答内容片段
        """
        url = f"{self.base_url}{self.endpoints.get(self.provider, '/chat/completions')}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = self._build_body(messages, stream=True)
        body.update(kwargs)

        response = requests.post(url, headers=headers, json=body, timeout=120, stream=True)
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                line_str = line.decode("utf-8")
                if line_str.startswith("data: "):
                    if line_str == "data: [DONE]":
                        break
                    try:
                        chunk = json.loads(line_str[6:])
                        delta = chunk["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError):
                        continue
