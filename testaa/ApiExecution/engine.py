"""
测试执行引擎 - 业务逻辑核心
"""

import json
import logging
from typing import Generator, Dict, Any, List, Optional
from ai.core.manager import AIManager
from ai.prompts.execute_api import ExecuteApiPrompt
from ai.prompts.validate_testcase import ValidateTestcasePrompt
from .executor import ApiTestExecutor

logger = logging.getLogger(__name__)


class TestExecutionEngine:
    """测试执行引擎"""

    def __init__(self, ai_provider: str = 'zhipu'):
        """
        初始化执行引擎

        Args:
            ai_provider: AI提供商名称
        """
        self.ai_manager = AIManager(provider_name=ai_provider)
        self.executor: Optional[ApiTestExecutor] = None

    def execute_testcase(
        self,
        run_list: List[Dict],
        test_data: Dict,
        base_url: str,
        case_info: Dict[str, Any]
    ) -> Generator[Dict, None, None]:
        """
        执行测试用例（流式）

        Args:
            run_list: 接口执行列表
            test_data: 测试数据
            base_url: 基础URL
            case_info: 用例信息（包含 case_id, api_name, precondition, testpoint, expectation）

        Yields:
            执行进度事件
        """
        self.executor = ApiTestExecutor(base_url=base_url)

        try:
            yield {
                'type': 'step',
                'data': {'message': f'开始执行测试用例，共 {len(run_list)} 个接口'}
            }

            # 创建提示词实例
            execute_prompt = ExecuteApiPrompt()

            # 遍历执行每个接口
            for i, api_info in enumerate(run_list):
                run_num = api_info.get('run_num', i + 1)
                api_name = api_info.get('api_name', f'接口{run_num}')

                yield {
                    'type': 'step',
                    'data': {'message': f'正在执行 [{run_num}] {api_name}...'}
                }

                # 如果不是第一个接口，调用 AI 填充参数
                if i > 0:
                    if 'params' not in api_info:
                        api_info['params'] = {}

                    filled_api_info = self._fill_params_with_ai(
                        prompt=execute_prompt,
                        case_info=case_info,
                        execution_history=self.executor.get_history(),
                        current_api_info=api_info,
                        test_data=test_data
                    )

                    if filled_api_info:
                        api_info.update(filled_api_info)
                        yield {
                            'type': 'step',
                            'data': {'message': f'AI 智能填充参数完成'}
                        }

                # 执行接口
                result = self.executor.execute_api(api_info)

                # 返回执行结果
                yield {
                    'type': 'result',
                    'data': {
                        'run_num': result.run_num,
                        'api_name': result.api_name,
                        'api_url': result.api_url,
                        'method': result.method,
                        'request': result.request,
                        'response': result.response,
                        'status_code': result.status_code,
                        'success': result.success,
                        'duration_ms': result.duration_ms,
                        'error': result.error
                    }
                }

                # 如果执行失败，立即停止
                if not result.success:
                    yield {
                        'type': 'step_complete',
                        'data': {'message': f'接口执行失败，停止后续执行'}
                    }
                    break

            # 执行完成
            yield {
                'type': 'step_complete',
                'data': {'message': '测试用例执行完成'}
            }

            # 返回执行报告
            history = self.executor.get_history()
            success_count = sum(1 for h in history if h.get('success', False))
            total_count = len(history)

            yield {
                'type': 'report',
                'data': {
                    'case_id': case_info.get('case_id'),
                    'total': total_count,
                    'success': success_count,
                    'failed': total_count - success_count,
                    'results': history
                }
            }

        except Exception as e:
            logger.exception('测试执行异常')
            yield {
                'type': 'error',
                'data': {'message': f'执行失败：{str(e)}'}
            }

    def _fill_params_with_ai(
        self,
        prompt: ExecuteApiPrompt,
        case_info: Dict[str, Any],
        execution_history: List[Dict],
        current_api_info: Dict,
        test_data: Dict
    ) -> Optional[Dict[str, Any]]:
        """
        调用 AI 填充接口参数

        Args:
            prompt: 提示词对象
            case_info: 用例信息
            execution_history: 执行历史
            current_api_info: 当前接口信息
            test_data: 测试数据

        Returns:
            填充后的参数信息
        """
        try:
            # 使用提示词对象调用 AI
            response = self.ai_manager.call_with_prompt(
                system_prompt=prompt.get_system_prompt(),
                user_prompt=prompt.get_user_prompt(
                    case_id=case_info.get('case_id', ''),
                    api_name=case_info.get('api_name', ''),
                    precondition=case_info.get('precondition', ''),
                    testpoint=case_info.get('testpoint', ''),
                    expectation=case_info.get('expectation', ''),
                    execution_history=json.dumps(execution_history, ensure_ascii=False),
                    current_api_info=json.dumps(current_api_info, ensure_ascii=False),
                    test_data=json.dumps(test_data, ensure_ascii=False)
                ),
                json_mode=True
            )

            # 解析响应
            if response.content:
                return self._parse_ai_response(response.content)

            return None

        except Exception as e:
            logger.error(f'AI 填充参数失败：{e}')
            return None

    def _parse_ai_response(self, content: str) -> Optional[Dict[str, Any]]:
        """
        解析 AI 返回的 JSON

        Args:
            content: AI 响应内容

        Returns:
            解析后的字典
        """
        try:
            content = content.strip()

            # 尝试提取 markdown 代码块中的 JSON
            import re
            match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if match:
                content = match.group(1).strip()

            filled_info = json.loads(content)

            if isinstance(filled_info, dict):
                return filled_info
            return None

        except json.JSONDecodeError as e:
            logger.error(f'解析 AI 响应 JSON 失败：{e}')
            return None

    def validate_testcase(
        self,
        case_info: Dict[str, Any],
        execution_results: List[Dict]
    ) -> Generator[Dict, None, None]:
        """
        AI 校验测试结果（流式）

        Args:
            case_info: 用例信息
            execution_results: 执行结果列表

        Yields:
            校验进度事件
        """
        try:
            # 创建提示词实例
            validate_prompt = ValidateTestcasePrompt()

            yield {
                'type': 'step',
                'data': {'message': '正在分析执行结果...'}
            }

            # 调用 AI
            response = self.ai_manager.call_with_prompt(
                system_prompt=validate_prompt.get_system_prompt(),
                user_prompt=validate_prompt.get_user_prompt(
                    case_id=case_info.get('case_id', ''),
                    api_name=case_info.get('api_name', ''),
                    precondition=case_info.get('precondition', ''),
                    testpoint=case_info.get('testpoint', ''),
                    expectation=case_info.get('expectation', ''),
                    execution_results=json.dumps(execution_results, ensure_ascii=False)
                ),
                json_mode=True
            )

            # 解析响应
            if response.content:
                validation_result = self._parse_ai_response(response.content)

                if validation_result:
                    yield {
                        'type': 'result',
                        'data': validation_result
                    }
                else:
                    yield {
                        'type': 'error',
                        'data': {'message': '无法解析校验结果'}
                    }
            else:
                yield {
                    'type': 'error',
                    'data': {'message': 'AI 响应为空'}
                }

            yield {
                'type': 'step_complete',
                'data': {'message': '测试校验完成'}
            }

        except Exception as e:
            logger.exception('测试校验异常')
            yield {
                'type': 'error',
                'data': {'message': f'校验失败：{str(e)}'}
            }
