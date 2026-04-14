"""
API 测试执行器 - 通用执行框架

支持：
- HTTP/HTTPS 协议
- GET/POST/PUT/DELETE 等方法
- Session/Cookie 自动管理
- 实时执行结果返回
"""
import requests
import time
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict


@dataclass
class ExecutionResult:
    """单次执行结果"""
    run_num: int
    api_name: str
    api_url: str
    method: str
    request: Dict[str, Any]
    response: Optional[Dict[str, Any]]
    status_code: Optional[int]
    success: bool
    duration_ms: int
    error: Optional[str] = None


@dataclass
class ExecutionReport:
    """执行报告"""
    case_id: str
    execution_results: List[ExecutionResult]
    summary: Dict[str, int]


class ApiTestExecutor:
    """API 测试执行器"""

    def __init__(self, base_url: str = ""):
        """
        初始化执行器

        Args:
            base_url: 基座 URL，如 http://127.0.0.1:8000
        """
        self.base_url = base_url
        self.session = requests.Session()  # 自动管理 Cookie/Session
        self.execution_history: List[ExecutionResult] = []

    def execute_api(self, api_info: Dict[str, Any]) -> ExecutionResult:
        """
        执行单个接口

        Args:
            api_info: 接口信息，包含 api_url, method, request_body 等

        Returns:
            执行结果
        """
        start_time = time.time()

        # 构造完整 URL
        api_url = api_info.get("api_url", "")
        if not api_url.startswith("http"):
            # 这里做了特殊处理，去掉前缀/api
            api_url = self.base_url + api_url
        
        # 特殊处理：去掉 /api 前缀（适配 Django 项目路由）
        api_url = api_url.replace("/api/", "/", 1)

        method = api_info.get("method", "GET").upper()
        request_body = api_info.get("request_body", {})
        headers = api_info.get("headers", {})
        # 兼容 params 和 query_params 两种字段
        params = api_info.get("params", api_info.get("query_params", {}))

        # 准备请求
        request_data = {
            "method": method,
            "url": api_url,
            "body": request_body,
            "params": params,
            "headers": headers
        }

        try:
            # 发送请求
            if method == "GET":
                response = self.session.get(api_url, params=params, headers=headers, timeout=30)
            elif method == "POST":
                # 根据 Content-Type 决定发送格式
                content_type = headers.get("Content-Type", "")
                if "application/json" in content_type:
                    response = self.session.post(api_url, json=request_body, params=params, headers=headers, timeout=30)
                else:
                    response = self.session.post(api_url, data=request_body, params=params, headers=headers, timeout=30)
            elif method == "PUT":
                response = self.session.put(api_url, json=request_body, params=params, headers=headers, timeout=30)
            elif method == "DELETE":
                response = self.session.delete(api_url, params=params, headers=headers, timeout=30)
            else:
                response = self.session.request(method, api_url, json=request_body, params=params, headers=headers, timeout=30)

            # 解析响应
            duration_ms = int((time.time() - start_time) * 1000)

            try:
                response_body = response.json()
            except:
                response_body = {"text": response.text}

            response_data = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response_body
            }

            # 判断是否成功（HTTP 状态码 2xx）
            success = 200 <= response.status_code < 300

            result = ExecutionResult(
                run_num=api_info.get("run_num", 0),
                api_name=api_info.get("api_name", ""),
                api_url=api_url,
                method=method,
                request=request_data,
                response=response_data,
                status_code=response.status_code,
                success=success,
                duration_ms=duration_ms
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            result = ExecutionResult(
                run_num=api_info.get("run_num", 0),
                api_name=api_info.get("api_name", ""),
                api_url=api_url,
                method=method,
                request=request_data,
                response=None,
                status_code=None,
                success=False,
                duration_ms=duration_ms,
                error=str(e)
            )

        # 记录执行历史
        self.execution_history.append(result)

        return result

    def get_history(self) -> List[Dict[str, Any]]:
        """获取执行历史（用于 AI 分析）"""
        history = []
        for result in self.execution_history:
            history.append({
                "run_num": result.run_num,
                "api_name": result.api_name,
                "request": result.request,
                "response": result.response,
                "status_code": result.status_code,
                "success": result.success
            })
        return history

    def clear_history(self):
        """清空执行历史"""
        self.execution_history = []
        self.session = requests.Session()
