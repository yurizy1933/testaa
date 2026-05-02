"""
JSON解析工具函数
"""
import json
import re
from typing import Any, List, Dict, Optional


def parse_json(text: str) -> Any:
    """
    解析JSON文本，自动处理各种格式

    优先尝试直接解析，失败后从文本中提取JSON对象或数组
    """
    # 1. 尝试直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. 尝试提取JSON对象
    result = extract_json_objects(text)
    if result:
        return result[0]

    # 3. 尝试提取JSON数组
    result = extract_json_arrays(text)
    if result:
        return result[0]

    return None


def extract_json_objects(text: str) -> List[Dict]:
    """从文本中提取所有JSON对象"""
    matches = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    results = []
    for match in matches:
        try:
            results.append(json.loads(match))
        except json.JSONDecodeError:
            continue
    return results


def extract_json_arrays(text: str) -> List[List]:
    """从文本中提取所有JSON数组"""
    matches = re.findall(r'\[.*?\]', text, re.DOTALL)
    results = []
    for match in matches:
        try:
            data = json.loads(match)
            if isinstance(data, list):
                results.append(data)
        except json.JSONDecodeError:
            continue
    return results


def find_json_with_keys(text: str, keys: List[str]) -> Optional[Dict]:
    """从文本中查找包含指定key的JSON对象"""
    objects = extract_json_objects(text)
    for obj in objects:
        if any(key in obj for key in keys):
            return obj
    return None


def find_json_array(text: str, min_items: int = 1) -> Optional[List]:
    """从文本中查找JSON数组（至少包含指定数量元素）"""
    arrays = extract_json_arrays(text)
    for arr in arrays:
        if len(arr) >= min_items:
            return arr
    return None
