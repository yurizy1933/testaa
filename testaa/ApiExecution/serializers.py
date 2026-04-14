"""
序列化器模块 - 数据转换工具
"""

import json
from typing import List, Dict
from common.models import ApiInterface, TestData


def generate_run_list_from_interface(api_interface: ApiInterface) -> List[Dict]:
    """
    从 ApiInterface 生成 run_list

    Args:
        api_interface: API接口对象

    Returns:
        接口执行列表
    """
    run_list = [{
        'run_num': 1,
        'api_name': api_interface.api_name,
        'api_url': api_interface.api_path or '',
        'method': api_interface.method,
        'request_body': {},
        'params': {},
        'headers': {'Content-Type': 'application/json'}
    }]

    # 解析 request_params
    if api_interface.request_params:
        try:
            request_params = json.loads(api_interface.request_params)
            if api_interface.method in ['POST', 'PUT', 'PATCH']:
                run_list[0]['request_body'] = request_params
            else:
                run_list[0]['params'] = request_params
        except json.JSONDecodeError:
            pass

    return run_list


def get_test_data_from_model(test_data: TestData) -> Dict:
    """
    从 TestData 获取测试数据

    Args:
        test_data: 测试数据对象

    Returns:
        测试数据字典
    """
    return test_data.test_data_json or {}
