"""
获取接口依赖关系Prompt
"""
from .base import BasePrompt


class GetDependencyPrompt(BasePrompt):
    """分析接口调用依赖和执行顺序的Prompt"""

    def __init__(self):
        self._system_prompt = """请根据测试用例的需求帮我梳理接口文档，并且判断执行这个接口测试用例，需要依赖的接口和执行顺序。

要求：
1、请严格按照以下 json 格式生成，其中 case_id 为用例 ID，run_list 为执行接口测试用例所需的所有接口，run_num 为执行顺序，api_name 为执行接口的中文名，api_url 为实际执行接口的 url，method 为 HTTP 方法。

例如：
{
  "case_id": 1,
  "run_list": [
    {
      "run_num": 1,
      "api_name": "创建订单接口",
      "api_url": "/api/v1/order/create",
      "method": "POST",
      "request_body": {"item_id": 12345, "quantity": 1},
      "description": "创建订单，后续查询依赖此订单 ID"
    },
    {
      "run_num": 2,
      "api_name": "查询订单详情接口",
      "api_url": "/api/v1/order/detail",
      "method": "GET",
      "params": {"order_id": "<从步骤1响应中提取>"},
      "description": "主接口测试"
    }
  ]
}

注意：
1、run_list 必须包含所有需要依赖的接口，包括主接口本身
2、api_url 必须是完整的接口路径，不包含域名
3、method 必须是标准的 HTTP 方法（GET/POST/PUT/DELETE 等）
4、只有当测试用例的前置条件、测试点或接口名称中明确包含"登录/鉴权/授权/认证/Token"等字样时，才需要添加登录接口；否则不要添加登录步骤
5、根据前置条件和测试点，智能推断每个接口需要的请求参数
6、只需要 json 的内容，不需要其他任何描述"""

    def get_user_prompt(self, case_id: str = '', api_name: str = '',
                        precondition: str = '', testpoint: str = '',
                        expectation: str = '') -> str:
        """生成用户提示词"""
        return f"""测试用例信息：
- 用例 ID: {case_id}
- 接口名称：{api_name}
- 前置条件：{precondition}
- 测试点：{testpoint}
- 预期结果：{expectation}"""
