"""
API测试用例生成器 - 调用大模型生成接口测试用例
"""
from AITools.llm.manager import AIManager
from AITools.prompts.api_testcase import APITestCasePrompt
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class APITestCaseGenerator:
    """API测试用例生成器"""

    def __init__(self, ai_provider: str = 'zhipu'):
        self.ai_manager = AIManager(provider_name=ai_provider)
        self.prompt = APITestCasePrompt()

    def generate(self, api_interface, test_data=None) -> Dict:
        """
        调用大模型生成API接口测试用例

        Args:
            api_interface: ApiInterface 对象（来自 common.models）
            test_data: TestData 对象（可选，来自 common.models）

        Returns:
            Dict: {
                'test_cases': [...],
                'model': str,
                'tokens_used': int,
                'cost': float
            }
        """
        try:
            # 提取接口信息
            api_name = api_interface.api_name or ''
            api_path = api_interface.api_path or ''
            method = api_interface.method or 'GET'
            request_params = api_interface.request_params or ''
            response_params = api_interface.response_params or ''
            remark = api_interface.remark or ''

            # 提取测试数据
            test_data_dict = None
            if test_data:
                test_data_dict = test_data.test_data_json

            # 获取提示词
            system_prompt = self.prompt.get_system_prompt()
            user_prompt = self.prompt.get_user_prompt(
                api_name=api_name,
                api_path=api_path,
                method=method,
                request_params=request_params,
                response_params=response_params,
                remark=remark,
                test_data=test_data_dict
            )

            logger.info(f"API测试用例生成开始 - 接口: {api_name}, 路径: {api_path}, "
                        f"Provider: {self.ai_manager.provider_name}")

            # 调用AI（max_tokens 调大以适应生成多个用例）
            response = self.ai_manager.call_with_prompt(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                json_mode=True,
                max_tokens=16000
            )

            # 解析响应
            logger.debug(f"AI原始响应: {response.content[:500]}")
            result = self.prompt.parse_response(response.content)
            test_cases = result.get('test_cases', [])
            logger.info(f"API测试用例生成完成 - 生成 {len(test_cases)} 个用例, "
                        f"tokens: {response.tokens_used}, cost: {response.cost}")

            return {
                'test_cases': test_cases,
                'model': response.model,
                'tokens_used': response.tokens_used,
                'cost': response.cost
            }

        except Exception as e:
            logger.error(f"API测试用例生成失败: {str(e)}")
            raise
