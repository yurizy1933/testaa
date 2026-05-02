"""
API接口测试用例生成Prompt
"""
from .base import BasePrompt
from typing import Dict, Any, Optional, List
import json
import logging

logger = logging.getLogger(__name__)


class APITestCasePrompt(BasePrompt):
    """API接口测试用例生成Prompt"""

    def __init__(self):
        self._system_prompt = """
        你是一个专业的API测试工程师，擅长为API接口设计全面、可执行的测试用例。

## 测试用例设计方法论

请严格按照以下步骤设计测试用例，确保覆盖全面：

### 第一步：分析接口入参
首先列出该接口的所有入参，分析每个参数的类型、是否必填、取值范围、格式要求。

### 第二步：逐个参数生成校验用例（核心步骤）
对每个入参，按以下维度逐一设计用例：
1. **正常值**：使用合法的参数值，验证接口正常返回
2. **边界值**：测试参数的最小值/最大值/最大长度/最小长度
3. **类型错误**：传入错误的类型（如数字字段传字符串、布尔字段传数字）
4. **空值/null**：必填参数传空字符串或null、必填参数缺失
5. **格式校验**：邮箱/手机号/日期等有格式要求的参数，传入错误格式
6. **特殊字符**：传入SQL注入字符（如 ' OR '1'='1）、XSS脚本、路径遍历字符等

**命名规范**：所有参数校验类用例的 test_case_name 必须以"[参数校验]"开头，如：
- "[参数校验] campaign_id 传入空字符串"
- "[参数校验] page_size 传入负数"

### 第三步：参数组合场景
- 多个参数同时为空的组合
- 多个参数同时为边界的组合
- 互斥参数的组合

### 第四步：业务场景测试（重要）
- 所有参数合法的正常业务流程
- 所有参数合法的异常业务流程
- 条件分支覆盖（不同参数取值触发不同业务逻辑）

### 第五步：安全与异常测试
- 未认证/未授权访问
- 请求体超大/超长参数值
- HTTP方法篡改
- 重复提交

## 数量要求
- 用例数量必须与接口复杂度成正比
- 简单接口（1-2个入参）：至少5-8条用例
- 中等接口（3-5个入参）：至少10-15条用例
- 复杂接口（5个以上入参）：至少15-25条用例
- **只生成1条用例是不可接受的**，必须覆盖上述所有维度

## 优先级规则（重要）
- **P0（很高）**：仅限核心主流程正常场景，1-2 条即可
- **P1（高）**：所有参数校验类用例（边界值、类型错误、空值、格式校验、特殊字符等）
- **P2（中）**：参数组合场景、条件分支场景
- **P3（低）**：极端异常场景、安全测试

## 输出要求
1. 测试步骤控制在2-3句话内，直奔主题，不要展开背景说明
2. 预期结果控制在1-2句话内，只写状态码和关键字段
3. 如果有参考测试数据，优先基于测试数据生成用例
4. 返回纯JSON格式，不要包含其他说明文字
5. **每条用例必须简洁**，这样才能生成足够数量的用例覆盖所有维度"""

        self._user_prompt_template = """请为以下API接口生成全面的测试用例，严格遵循设计方法论，覆盖所有入参的校验维度。

API接口信息：
- 接口名称：{api_name}
- 接口路径：{api_path}
- 请求方法：{method}
- 入参：{request_params}
- 出参：{response_params}
- 备注：{remark}
{test_data_info}
请以JSON格式返回，包含 test_cases 数组。每条用例包含以下字段：
- test_case_name: 测试用例名称（需体现测试的参数和场景）
- test_case_type: 测试类型（正常场景、异常场景、边界场景、安全场景）
- preconditions: 前置条件
- test_steps: 测试步骤（详细描述，包括请求方法、URL、请求头、请求体等）
- test_data: 测试数据（JSON格式，具体的请求参数键值对）
- expected_result: 预期结果（详细描述期望的响应，包括状态码和返回数据结构）
- priority: 优先级（P0-很高、P1-高、P2-中、P3-低）

单条用例字段格式参考：
{example}

请只返回JSON格式的数据，不要包含其他说明文字。记住：必须对所有入参进行逐参数校验，用例数量要与接口复杂度匹配。"""

        self._example_response = {
            "test_case_name": "[参数校验] user_id 传入空字符串",
            "test_case_type": "异常场景",
            "preconditions": "用户已登录",
            "test_steps": "1. 构造GET请求到/api/v2/user/info\\n2. 设置请求头Authorization: Bearer {token}\\n3. 请求参数携带user_id为空字符串\\n4. 发送请求",
            "test_data": {"user_id": ""},
            "expected_result": "HTTP状态码400，返回JSON包含错误码和提示信息'user_id不能为空'",
            "priority": "P1"
        }

    def get_system_prompt(self) -> str:
        return self._system_prompt

    def get_user_prompt(self, **kwargs) -> str:
        api_name = kwargs.get('api_name', '未知')
        api_path = kwargs.get('api_path', '未知')
        method = kwargs.get('method', '未知')
        request_params = kwargs.get('request_params', '无')
        response_params = kwargs.get('response_params', '无')
        remark = kwargs.get('remark', '无')
        test_data = kwargs.get('test_data', None)

        # 构造测试数据部分
        test_data_info = ""
        if test_data:
            if isinstance(test_data, dict):
                test_data_str = json.dumps(test_data, ensure_ascii=False, indent=2)
            elif isinstance(test_data, str):
                test_data_str = test_data
            else:
                test_data_str = str(test_data)

            test_data_info = f"""
参考测试数据：
{test_data_str}
"""

        example_str = json.dumps(self._example_response, ensure_ascii=False, indent=2)

        return self._user_prompt_template.format(
            api_name=str(api_name) if api_name else '未知',
            api_path=str(api_path) if api_path else '未知',
            method=str(method) if method else '未知',
            request_params=str(request_params) if request_params else '无',
            response_params=str(response_params) if response_params else '无',
            remark=str(remark) if remark else '无',
            test_data_info=test_data_info,
            example=example_str
        )

    @classmethod
    def parse_response(cls, response_text: str) -> Dict[str, Any]:
        """解析AI响应，提取测试用例"""
        try:
            data = json.loads(response_text)

            if isinstance(data, dict):
                if 'test_cases' in data:
                    return data
                elif 'test_case_name' in data:
                    return {'test_cases': [data]}
                else:
                    return {'test_cases': []}

            if isinstance(data, list):
                return {'test_cases': data}

            return {'test_cases': []}

        except json.JSONDecodeError:
            import re
            # 尝试提取最外层JSON对象
            json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
            matches = re.findall(json_pattern, response_text, re.DOTALL)

            for match in matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, dict) and 'test_cases' in data:
                        return data
                    if isinstance(data, dict) and 'test_case_name' in data:
                        return {'test_cases': [data]}
                except json.JSONDecodeError:
                    continue

            # 尝试提取JSON数组
            array_pattern = r'\[.*?\]'
            matches = re.findall(array_pattern, response_text, re.DOTALL)
            for match in matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, list) and len(data) > 0:
                        return {'test_cases': data}
                except json.JSONDecodeError:
                    continue

            logger.warning(f"无法从AI响应中解析测试用例: {response_text[:500]}")
            return {'test_cases': []}
