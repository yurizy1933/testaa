"""
执行中参数填充Prompt
"""
from .base import BasePrompt


class ExecuteApiPrompt(BasePrompt):
    """执行阶段AI辅助参数填充的Prompt"""

    def __init__(self):
        self._system_prompt = """你是一位 API 测试参数分析助手。根据测试用例信息、历史执行记录和当前接口信息，分析并填充当前接口执行所需的参数。

任务说明：
你需要分析历史执行记录中的响应数据，找出当前接口参数需要从哪个历史接口的响应中获取什么值，然后将真实的值填充到参数中。

例如：
- 如果历史执行记录中 run_num=2 的响应 body.msg 里有 "c_s_id": 1
- 而当前接口需要 c_s_id 参数
- 你就应该直接把 c_s_id 填充为 1

要求：
1. 分析测试用例的测试意图，理解当前接口在测试流程中的作用
2. 仔细查看历史执行记录的响应数据（body 字段），找到当前接口需要的值
3. 直接将历史响应中的真实值（数字、字符串等）填充到对应的参数位置
4. 如果某个参数在历史执行记录和可供使用的真实测试数据中没有合适的数据，需要根据测试用例的意图生成符合要求的测试数据
5. 保持原有 JSON 结构不变，只填充参数的值
6. 直接输出填充后的完整 JSON，不要有任何其他说明文字
7. 必须输出有效的 JSON 格式，不要用 markdown 包裹

输出格式示例：
{"api_url": "http://127.0.0.1:8000/api/subLearnScore/", "method": "POST", "request_body": {"c_s_id": 100, "code": "print('Hello, World!')", "c_na": "Python 基础"}, "params": {}, "headers": {}}"""

    def get_user_prompt(self, case_id: str = '', api_name: str = '',
                        precondition: str = '', testpoint: str = '',
                        expectation: str = '', execution_history: str = '',
                        current_api_info: str = '', test_data: str = '') -> str:
        """生成用户提示词"""
        return f"""测试用例信息：
- 用例 ID: {case_id}
- 接口名称：{api_name}
- 前置条件：{precondition}
- 测试点：{testpoint}
- 预期结果：{expectation}

历史执行记录：
{execution_history}

当前待执行的接口信息（包含待填充的参数模板）：
{current_api_info}

可供使用的真实测试数据：
{test_data}"""
