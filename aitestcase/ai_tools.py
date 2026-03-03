"""
AI工具模块
统一管理所有AI相关的功能
"""

import json
import re
from zhipuai import ZhipuAI
from openai import OpenAI


# ==================== 配置信息 ====================

# AI API配置
ZHIPU_API_KEY = "4198d249d529406f8b9571bc10aa2142.Qvg8SQRV9GiKweid"
DEEPSEEK_API_KEY = 'sk-ae89b4e492104945ae83c6a2647410c9'
DEEPSEEK_BASE_URL = "https://api.deepseek.com"


# ==================== HTML解析功能 ====================

def parse_html_with_ai(content, ai_provider='zhipu'):
    """
    使用AI来解析HTML文档内容，提取接口信息
    支持智谱AI和DeepSeek

    Args:
        content: HTML文档内容
        ai_provider: AI提供商，'zhipu' 或 'deepseek'

    Returns:
        list: 接口信息列表
    """
    try:
        # 限制内容长度，避免超出AI的token限制
        max_length = 8000
        if len(content) > max_length:
            content = content[:max_length] + "...[内容已截断]"

        # 构造AI提示词
        prompt = f"""
请分析以下HTML文档内容，提取其中的API接口信息。

HTML内容：
{content}

请以JSON格式返回所有接口信息，每个接口包含以下字段：
- api_name: 接口名称
- api_path: 接口路径（必填字段，必须提供）
- method: 请求方法（GET/POST/PUT/DELETE等）
- request_params: 入参说明
- response_params: 出参说明
- remark: 备注（如果有）

前置判断：文档有效性验证
在开始解析前，请首先执行以下验证：

判断标准
如果HTML文档中同时缺失以下两类信息，则判定为非API文档：
路径信息：如 /api/xxx、/v1/xxx、/rest/xxx 等URL路径
方法信息：如 GET、POST、PUT、DELETE 等HTTP方法

返回格式示例：
[
  {{
    "api_name": "用户登录接口",
    "api_path": "/api/login",
    "method": "POST",
    "request_params": {{"username": "用户名", "password": "密码"}},
    "response_params": {{"token": "登录令牌", "user_id": "用户ID"}},
    "remark": "用户登录验证"
  }}
]

请只返回JSON格式的数组，不要包含其他说明文字。
"""

        interfaces = []

        if ai_provider == 'zhipu':
            # 使用智谱AI解析
            client = ZhipuAI(api_key=ZHIPU_API_KEY)
            response = client.chat.completions.create(
                model="glm-4",
                messages=[
                    {"role": "system", "content": "你是一个专业的API文档解析助手，擅长从HTML文档中提取接口信息。重要：请只关注表格中的信息"},
                    {"role": "user", "content": prompt}
                ],
                response_format={'type': 'json_object'}
            )

            # 解析AI返回的JSON结果
            result_text = response.choices[0].message.content
            print(result_text)
            interfaces = parse_ai_response(result_text)

        return interfaces

    except Exception as e:
        print(f'AI解析HTML失败: {str(e)}')
        # 如果AI解析失败，返回空列表（让调用方降级到传统解析）
        return []


def parse_ai_response(response_text):
    """
    解析AI返回的响应文本，提取接口信息

    Args:
        response_text: AI返回的文本

    Returns:
        list: 接口信息列表
    """
    try:
        # 尝试直接解析JSON
        data = json.loads(response_text)

        # 如果返回的是对象，检查是否有特定的字段
        if isinstance(data, dict):
            # 检查常见的字段名
            if 'interfaces' in data:
                interfaces = data['interfaces']
            elif 'data' in data:
                interfaces = data['data']
            elif 'results' in data:
                interfaces = data['results']
            elif 'api_list' in data:
                interfaces = data['api_list']
            elif 'apis' in data:
                interfaces = data['apis']
            else:
                # 如果没有找到特定字段，尝试将整个对象作为单个接口
                if 'api_name' in data or 'api_path' in data:
                    interfaces = [data]
                else:
                    interfaces = []

            # 过滤掉没有api_path的接口
            return [iface for iface in interfaces if isinstance(iface, dict) and iface.get('api_path')]

        # 如果是数组，直接返回（但需要过滤没有api_path的接口）
        elif isinstance(data, list):
            return [iface for iface in data if isinstance(iface, dict) and iface.get('api_path')]

        return []

    except json.JSONDecodeError:
        # 如果直接解析失败，尝试提取JSON部分
        try:
            # 尝试从文本中提取JSON部分
            json_pattern = r'\[.*?\]'
            matches = re.findall(json_pattern, response_text, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, list):
                        # 过滤掉没有api_path的接口
                        return [iface for iface in data if isinstance(iface, dict) and iface.get('api_path')]
                except:
                    continue

            return []
        except Exception:
            return []
    except Exception:
        return []


# ==================== API接口测试用例生成功能 ====================

def generate_api_test_cases(api_interface, ai_provider='zhipu', test_data=None):
    """
    使用AI生成API接口的测试用例

    Args:
        api_interface: ApiInterface对象或接口信息字典
        ai_provider: AI提供商，'zhipu' 或 'deepseek'
        test_data: 测试数据（如果有），用于生成更精确的测试用例

    Returns:
        dict: 包含测试用例数据的字典
    """
    try:
        # 构建接口信息
        if hasattr(api_interface, '__dict__'):
            # 如果是模型对象
            interface_info = {
                'api_name': api_interface.api_name,
                'api_path': api_interface.api_path,
                'method': api_interface.method,
                'request_params': api_interface.request_params,
                'response_params': api_interface.response_params,
                'remark': api_interface.remark
            }
        else:
            # 如果是字典
            interface_info = api_interface

        # 构造测试数据部分
        test_data_info = ""
        if test_data:
            if isinstance(test_data, dict):
                test_data_str = json.dumps(test_data, ensure_ascii=False, indent=2)
            elif hasattr(test_data, 'test_data_json'):
                test_data_str = json.dumps(test_data.test_data_json, ensure_ascii=False, indent=2)
            else:
                test_data_str = str(test_data)
            test_data_info = f"""
参考测试数据：
{test_data_str}
"""

        # 构造AI提示词
        prompt = f"""
请为以下API接口生成测试用例。

API接口信息：
- 接口名称：{interface_info.get('api_name', '未知')}
- 接口路径：{interface_info.get('api_path', '未知')}
- 请求方法：{interface_info.get('method', '未知')}
- 入参：{interface_info.get('request_params', '无')}
- 出参：{interface_info.get('response_params', '无')}
- 备注：{interface_info.get('remark', '无')}
{test_data_info}
请生成测试用例，以JSON格式返回，包含以下字段：
- test_case_name: 测试用例名称
- test_case_type: 测试类型（正常场景、异常场景、边界场景）
- preconditions: 前置条件
- test_steps: 测试步骤（详细描述，包括如何构造请求、发送请求等）
- test_data: 测试数据（JSON格式，具体的请求参数值）
- expected_result: 预期结果（详细描述期望的响应结果）
- priority: 优先级（P0-很高、P1-高、P2-中、P3-低）

要求：
1. 生成至少3个测试用例：1个正常场景、1个异常场景、1个边界场景
2. 如果有参考测试数据，请基于测试数据生成测试用例
3. 测试步骤要具体可执行，包括请求URL、请求方法、请求头、请求体等
4. 预期结果要具体，包括状态码、返回数据结构等
5. test_data字段必须是有效的JSON格式

返回格式示例：
{{
  "test_cases": [
    {{
      "test_case_name": "正常登录测试",
      "test_case_type": "正常场景",
      "preconditions": "用户已注册",
      "test_steps": "1. 构造POST请求到/api/login\\n2. 设置Content-Type为application/json\\n3. 请求体包含username和password\\n4. 发送请求",
      "test_data": {{"username": "testuser", "password": "123456"}},
      "expected_result": "HTTP状态码200，返回token和用户信息",
      "priority": "P0"
    }},
    {{
      "test_case_name": "密码错误测试",
      "test_case_type": "异常场景",
      "preconditions": "用户已注册",
      "test_steps": "1. 构造POST请求到/api/login\\n2. 使用错误的密码\\n3. 发送请求",
      "test_data": {{"username": "testuser", "password": "wrongpassword"}},
      "expected_result": "HTTP状态码401，返回错误提示信息",
      "priority": "P1"
    }}
  ]
}}

请只返回JSON格式的数据，不要包含其他说明文字。
"""

        test_cases = []

        if ai_provider == 'zhipu':
            # 使用智谱AI生成测试用例
            client = ZhipuAI(api_key=ZHIPU_API_KEY)
            response = client.chat.completions.create(
                model="glm-4",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的API测试工程师，擅长为API接口设计全面、可执行的测试用例。请确保返回的是纯JSON格式的数据。"
                    },
                    {"role": "user", "content": prompt}
                ],
                response_format={'type': 'json_object'}
            )

            # 解析AI返回的JSON结果
            result_text = response.choices[0].message.content
            print(f"AI生成的测试用例: {result_text}")
            test_cases = parse_test_cases_response(result_text)

        elif ai_provider == 'deepseek':
            # 使用DeepSeek生成测试用例
            deepseek_client = OpenAI(
                api_key=DEEPSEEK_API_KEY,
                base_url=DEEPSEEK_BASE_URL
            )

            response = deepseek_client.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的API测试工程师，擅长为API接口设计全面、可执行的测试用例。请确保返回的是纯JSON格式的数据。"
                    },
                    {"role": "user", "content": prompt}
                ]
            )

            # 解析AI返回的JSON结果
            result_text = response.choices[0].message.content
            print(f"AI生成的测试用例: {result_text}")
            test_cases = parse_test_cases_response(result_text)

        return test_cases

    except Exception as e:
        print(f'AI生成测试用例失败: {str(e)}')
        return {
            'error': str(e),
            'test_cases': []
        }


def parse_test_cases_response(response_text):
    """
    解析AI返回的测试用例响应

    Args:
        response_text: AI返回的文本

    Returns:
        dict: 包含测试用例列表的字典
    """
    try:
        # 尝试直接解析JSON
        data = json.loads(response_text)

        # 检查是否有test_cases字段
        if isinstance(data, dict):
            if 'test_cases' in data:
                return data
            else:
                # 如果没有test_cases字段，尝试将整个对象作为单个测试用例
                if 'test_case_name' in data:
                    return {'test_cases': [data]}
                else:
                    return {'test_cases': []}

        # 如果是数组，直接包装成test_cases格式
        elif isinstance(data, list):
            return {'test_cases': data}

        return {'test_cases': []}

    except json.JSONDecodeError:
        # 如果直接解析失败，尝试提取JSON部分
        try:
            # 尝试从文本中提取JSON部分
            json_pattern = r'\{.*?\}'
            matches = re.findall(json_pattern, response_text, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, dict) and 'test_cases' in data:
                        return data
                except:
                    continue

            return {'test_cases': []}
        except Exception:
            return {'test_cases': []}
    except Exception:
        return {'test_cases': []}