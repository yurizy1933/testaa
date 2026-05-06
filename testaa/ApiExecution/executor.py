"""
API测试执行器 - 负责执行HTTP请求并收集结果
"""

import time
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import requests

logger = logging.getLogger(__name__)


@dataclass
class ApiTestResult:
    """API测试结果数据类"""
    run_num: int
    api_name: str
    api_url: str
    method: str
    request: Dict[str, Any]
    response: Optional[Dict[str, Any]]
    status_code: int
    success: bool
    duration_ms: float
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'run_num': self.run_num,
            'api_name': self.api_name,
            'api_url': self.api_url,
            'method': self.method,
            'request': self.request,
            'response': self.response,
            'status_code': self.status_code,
            'success': self.success,
            'duration_ms': self.duration_ms,
            'error': self.error
        }


class ApiTestExecutor:
    """API测试执行器"""

    def __init__(self, base_url: str = '', timeout: int = 30):
        """
        初始化执行器

        Args:
            base_url: 基础URL
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()
        self.execution_history: List[Dict[str, Any]] = []

    def execute_api(self, api_info: Dict[str, Any]) -> ApiTestResult:
        """
        执行单个API请求

        Args:
            api_info: API信息字典，包含：
                - run_num: 执行序号
                - api_name: API名称
                - api_url: API路径
                - method: 请求方法
                - request_body: 请求体
                - params: URL参数
                - headers: 请求头

        Returns:
            ApiTestResult: 执行结果
        """
        run_num = api_info.get('run_num', 1)
        api_name = api_info.get('api_name', f'API{run_num}')
        api_url = api_info.get('api_url', '')
        method = api_info.get('method', 'GET').upper()

        # 构建完整URL
        if api_url and not api_url.startswith(('http://', 'https://')):
            full_url = f"{self.base_url}/{api_url.lstrip('/')}"
        elif api_url:
            full_url = api_url
        else:
            full_url = self.base_url

        # 准备请求参数
        request_body = api_info.get('request_body', {})
        params = api_info.get('params', {})
        headers = api_info.get('headers', {})

        # 记录请求信息
        request_info = {
            'url': full_url,
            'method': method,
            'body': request_body,
            'params': params,
            'headers': headers
        }

        # 记录开始时间
        start_time = time.time()

        try:
            # 根据请求方法发送请求
            if method in ['POST', 'PUT', 'PATCH']:
                response = self.session.post(
                    full_url,
                    json=request_body,
                    params=params,
                    headers=headers,
                    timeout=self.timeout
                )
            elif method == 'GET':
                response = self.session.get(
                    full_url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout
                )
            elif method == 'DELETE':
                response = self.session.delete(
                    full_url,
                    json=request_body,
                    params=params,
                    headers=headers,
                    timeout=self.timeout
                )
            elif method == 'HEAD':
                response = self.session.head(
                    full_url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout
                )
            elif method == 'OPTIONS':
                response = self.session.options(
                    full_url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # 计算执行时间
            duration_ms = (time.time() - start_time) * 1000

            # 尝试解析响应
            response_data = None
            try:
                if response.content:
                    response_data = response.json()
            except:
                response_data = response.text

            # 判断是否成功（2xx状态码）
            success = 200 <= response.status_code < 300

            # 创建结果对象
            result = ApiTestResult(
                run_num=run_num,
                api_name=api_name,
                api_url=full_url,
                method=method,
                request=request_info,
                response=response_data,
                status_code=response.status_code,
                success=success,
                duration_ms=duration_ms
            )

            # 添加到历史记录
            self.execution_history.append(result.to_dict())

            if success:
                logger.info(f"API执行成功: {method} {full_url} - {response.status_code} - {duration_ms:.2f}ms")
            else:
                logger.warning(f"API返回非2xx: {method} {full_url} - {response.status_code} - {duration_ms:.2f}ms")

            return result

        except requests.exceptions.Timeout:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"请求超时（{self.timeout}秒）"

            result = ApiTestResult(
                run_num=run_num,
                api_name=api_name,
                api_url=full_url,
                method=method,
                request=request_info,
                response=None,
                status_code=0,
                success=False,
                duration_ms=duration_ms,
                error=error_msg
            )

            self.execution_history.append(result.to_dict())
            logger.error(f"API执行超时: {method} {full_url}")

            return result

        except requests.exceptions.RequestException as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"请求异常: {str(e)}"

            result = ApiTestResult(
                run_num=run_num,
                api_name=api_name,
                api_url=full_url,
                method=method,
                request=request_info,
                response=None,
                status_code=0,
                success=False,
                duration_ms=duration_ms,
                error=error_msg
            )

            self.execution_history.append(result.to_dict())
            logger.error(f"API执行异常: {method} {full_url} - {str(e)}")

            return result

    def get_history(self) -> List[Dict[str, Any]]:
        """
        获取执行历史记录

        Returns:
            执行历史记录列表
        """
        return self.execution_history.copy()

    def clear_history(self):
        """清除执行历史记录"""
        self.execution_history.clear()

    def close(self):
        """关闭会话"""
        self.session.close()
