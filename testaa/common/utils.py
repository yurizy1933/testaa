"""
工具函数模块
"""

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def parse_json_safely(json_str: str) -> Optional[Dict[str, Any]]:
    """
    安全解析JSON字符串

    Args:
        json_str: JSON字符串

    Returns:
        解析后的字典，失败返回None
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Failed to parse JSON: {e}")
        return None


def format_datetime(dt: datetime, format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    格式化日期时间

    Args:
        dt: 日期时间对象
        format_str: 格式字符串

    Returns:
        格式化后的字符串
    """
    if dt is None:
        return ''
    return dt.strftime(format_str)


def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    从文本中提取JSON对象

    Args:
        text: 包含JSON的文本

    Returns:
        解析后的字典，失败返回None
    """
    import re

    # 尝试提取JSON对象
    json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_pattern, text, re.DOTALL)

    for match in matches:
        try:
            data = json.loads(match)
            return data
        except:
            continue

    # 尝试提取JSON数组
    array_pattern = r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]'
    matches = re.findall(array_pattern, text, re.DOTALL)

    for match in matches:
        try:
            data = json.loads(match)
            return {'data': data}
        except:
            continue

    return None


def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> List[str]:
    """
    验证必填字段

    Args:
        data: 数据字典
        required_fields: 必填字段列表

    Returns:
        缺失的字段列表
    """
    missing_fields = []
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == '':
            missing_fields.append(field)

    return missing_fields


def build_response(code: int = 200, message: str = '', data: Any = None) -> Dict[str, Any]:
    """
    构建标准响应格式

    Args:
        code: 响应码
        message: 响应消息
        data: 响应数据

    Returns:
        标准响应字典
    """
    response = {
        'code': code,
        'message': message
    }

    if data is not None:
        response['data'] = data

    return response
