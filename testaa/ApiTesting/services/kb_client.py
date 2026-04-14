"""
Knowledge 服务客户端
"""
import json
from typing import Any, Dict, Generator, Optional

import requests

from utils.logger import get_logger

logger = get_logger(__name__)


class KBError(Exception):
    """Knowledge 服务调用错误"""
    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class KBClient:
    """Knowledge Service 客户端"""

    def __init__(
        self,
        base_url: str,
        kb_api_key: Optional[str] = None
    ):
        self.base_url = base_url
        self.kb_api_key = kb_api_key

    def _request(
        self,
        method: str,
        params: Dict[str, Any],
        stream: bool = False
    ) -> Dict[str, Any]:
        """发送 JSON-RPC 请求"""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": 1,
        }

        if self.kb_api_key:
            payload["kb_api_key"] = self.kb_api_key
        if stream:
            payload["stream"] = True

        response = requests.post(
            f"{self.base_url}/rpc/",
            json=payload,
            stream=stream,
            headers={"Content-Type": "application/json"},
            timeout=120
        )

        if stream:
            return self._parse_stream(response)

        result = response.json()
        if "error" in result:
            raise KBError(
                code=result["error"].get("code", -32603),
                message=result["error"].get("message", "Unknown error")
            )
        return result.get("result", {})

    def _parse_stream(self, response) -> Generator[Dict[str, Any], None, None]:
        """解析 SSE 流式响应"""
        for line in response.iter_lines():
            if line:
                line_str = line.decode("utf-8")
                if line_str.startswith("data: "):
                    try:
                        event = json.loads(line_str[6:])
                        yield event
                    except json.JSONDecodeError:
                        continue

    # ==================== 会话管理 ====================

    def create_session(self, kb_id: str, kb_api_key: Optional[str] = None) -> Dict[str, Any]:
        """创建知识库会话"""
        old_key = self.kb_api_key
        if kb_api_key:
            self.kb_api_key = kb_api_key

        try:
            result = self._request("session.create", {"kb_id": kb_id})
            return result
        finally:
            self.kb_api_key = old_key

    def destroy_session(self, session_id: str, kb_api_key: Optional[str] = None) -> Dict[str, Any]:
        """销毁知识库会话"""
        old_key = self.kb_api_key
        if kb_api_key:
            self.kb_api_key = kb_api_key

        try:
            result = self._request("session.destroy", {"session_id": session_id})
            return result
        finally:
            self.kb_api_key = old_key

    # ==================== 流式问答 ====================

    def chat_stream(
        self,
        query: str,
        session_id: str,
        kb_id: str,
        kb_api_key: Optional[str] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        调用 kb.chat 流式问答

        Yields:
            事件字典（直接透传 Knowledge 服务的事件）
        """
        old_key = self.kb_api_key
        if kb_api_key:
            self.kb_api_key = kb_api_key

        try:
            params = {
                "query": query,
                "session_id": session_id,
                "kb_id": kb_id,
            }

            payload = {
                "jsonrpc": "2.0",
                "method": "kb.chat",
                "params": params,
                "id": 1,
                "stream": True,
            }

            if self.kb_api_key:
                payload["kb_api_key"] = self.kb_api_key

            response = requests.post(
                f"{self.base_url}/rpc/",
                json=payload,
                stream=True,
                headers={"Content-Type": "application/json"},
                timeout=120
            )
            response.raise_for_status()

            for line in response.iter_lines():
                if line:
                    line_str = line.decode("utf-8")
                    if line_str.startswith("data: "):
                        try:
                            event = json.loads(line_str[6:])
                            yield event
                        except json.JSONDecodeError:
                            continue

        finally:
            self.kb_api_key = old_key
