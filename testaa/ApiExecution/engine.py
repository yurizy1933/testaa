"""
测试执行引擎 - 业务逻辑核心

流程：
1. get_api_dependency    - 分析接口调用依赖和执行顺序
2. fill_test_data        - 填充测试数据到 run_list
3. execute_testcase      - 按 run_list 顺序执行 HTTP 请求（SSE流式）
4. validate_testcase     - AI 校验执行结果
"""
import json
import logging
from typing import Any, Dict, Generator, List, Optional

from AITools.llm.manager import AIManager
from AITools.prompts.dependency import GetDependencyPrompt
from AITools.prompts.fill_data import FillTestDataPrompt
from AITools.prompts.execute_api import ExecuteApiPrompt
from AITools.prompts.validate_testcase import ValidateTestcasePrompt
from .executor import ApiTestExecutor

logger = logging.getLogger(__name__)


class TestExecutionEngine:
    """测试执行引擎"""

    def __init__(self, ai_provider: str = 'zhipu'):
        self.ai_manager = AIManager(provider_name=ai_provider)
        self.executor: Optional[ApiTestExecutor] = None

    # ============================================================
    # 阶段 2a: 分析接口调用依赖
    # ============================================================

    def get_api_dependency(
        self,
        case_id: str = '',
        api_name: str = '',
        precondition: str = '',
        testpoint: str = '',
        expectation: str = ''
    ) -> Optional[Dict[str, Any]]:
        """
        分析接口调用依赖和执行顺序

        Returns:
            {"case_id": ..., "run_list": [...]}
        """
        try:
            prompt = GetDependencyPrompt()

            response = self.ai_manager.call_with_prompt(
                system_prompt=prompt.get_system_prompt(),
                user_prompt=prompt.get_user_prompt(
                    case_id=case_id,
                    api_name=api_name,
                    precondition=precondition,
                    testpoint=testpoint,
                    expectation=expectation
                ),
                json_mode=True,
                max_tokens=4000
            )

            if response.content:
                logger.info(f'[依赖分析] AI 原始返回 (前500字符): {response.content[:500]}')
                result = self._parse_json_with_retry(response.content)
                if result:
                    logger.info(f'[依赖分析] 解析成功，run_list 共 {len(result.get("run_list", []))} 个接口: '
                                f'{[r.get("api_url", "") for r in result.get("run_list", [])]}')
                return result

            return None

        except Exception as e:
            logger.exception('分析接口依赖失败')
            return None

    # ============================================================
    # 阶段 2b: 填充测试数据
    # ============================================================

    def fill_test_data(
        self,
        case_id: str = '',
        api_name: str = '',
        precondition: str = '',
        testpoint: str = '',
        expectation: str = '',
        dependency: Optional[Dict[str, Any]] = None,
        test_data: Optional[Dict[str, Any]] = None,
        base_url: str = 'http://127.0.0.1:8000'
    ) -> Optional[Dict[str, Any]]:
        """
        填充测试数据到依赖接口的 run_list

        Returns:
            {"case_id": ..., "run_list": [...]}
        """
        try:
            prompt = FillTestDataPrompt()

            response = self.ai_manager.call_with_prompt(
                system_prompt=prompt.get_system_prompt(),
                user_prompt=prompt.get_user_prompt(
                    case_id=case_id,
                    api_name=api_name,
                    precondition=precondition,
                    testpoint=testpoint,
                    expectation=expectation,
                    dependency_json=json.dumps(dependency, ensure_ascii=False),
                    test_data=json.dumps(test_data or {}, ensure_ascii=False),
                    base_url=base_url
                ),
                json_mode=True,
                max_tokens=4000
            )

            if response.content:
                logger.info(f'[填充数据] AI 原始返回 (前500字符): {response.content[:500]}')
                result = self._parse_json_with_retry(response.content)
                if result:
                    logger.info(f'[填充数据] 解析成功，run_list 共 {len(result.get("run_list", []))} 个接口: '
                                f'{[r.get("api_url", "") for r in result.get("run_list", [])]}')
                return result

            return None

        except Exception as e:
            logger.exception('填充测试数据失败')
            return None

    # ============================================================
    # 阶段 3: 执行测试用例（流式）
    # ============================================================

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
            run_list: 接口执行列表（阶段 2b 填充后的）
            test_data: 测试数据
            base_url: 基础URL
            case_info: 用例信息（case_id, api_name, precondition, testpoint, expectation）

        Yields:
            执行进度事件：step / result / report / error
        """
        self.executor = ApiTestExecutor(base_url=base_url)

        try:
            logger.info(f'[执行测试] base_url={base_url}, run_list='
                        f'{[{"run_num": r.get("run_num"), "method": r.get("method"), "api_url": r.get("api_url")} for r in run_list]}')

            yield {
                'type': 'step',
                'data': {'message': f'开始执行测试用例，共 {len(run_list)} 个接口'}
            }

            execute_prompt = ExecuteApiPrompt()

            for i, api_info in enumerate(run_list):
                run_num = api_info.get('run_num', i + 1)
                api_name = api_info.get('api_name', f'接口{run_num}')

                yield {
                    'type': 'step',
                    'data': {'message': f'正在执行 [{run_num}] {api_name}...'}
                }

                # 第 2 个接口开始，调用 AI 根据历史响应填充参数
                if i > 0:
                    if 'params' not in api_info:
                        api_info['params'] = {}

                    filled_api_info = self._fill_params_with_ai(
                        execute_prompt=execute_prompt,
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

                # Fail-fast: 执行失败立即停止
                if not result.success:
                    yield {
                        'type': 'step_complete',
                        'data': {'message': '接口执行失败，停止后续执行'}
                    }
                    break

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
        execute_prompt: ExecuteApiPrompt,
        case_info: Dict[str, Any],
        execution_history: List[Dict],
        current_api_info: Dict,
        test_data: Dict
    ) -> Optional[Dict[str, Any]]:
        """调用 AI 根据历史响应推断并填充当前接口的参数"""
        try:
            response = self.ai_manager.call_with_prompt(
                system_prompt=execute_prompt.get_system_prompt(),
                user_prompt=execute_prompt.get_user_prompt(
                    case_id=str(case_info.get('case_id', '')),
                    api_name=case_info.get('api_name', ''),
                    precondition=case_info.get('precondition', ''),
                    testpoint=case_info.get('testpoint', ''),
                    expectation=case_info.get('expectation', ''),
                    execution_history=json.dumps(execution_history, ensure_ascii=False),
                    current_api_info=json.dumps(current_api_info, ensure_ascii=False),
                    test_data=json.dumps(test_data, ensure_ascii=False)
                ),
                json_mode=True,
                max_tokens=4000
            )

            if response.content:
                return self._parse_json_with_retry(response.content)

            return None

        except Exception as e:
            logger.error(f'AI 填充参数失败：{e}')
            return None

    # ============================================================
    # 阶段 4: AI 校验测试结果（流式）
    # ============================================================

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
            校验进度事件：step / result / error / step_complete
        """
        try:
            validate_prompt = ValidateTestcasePrompt()

            yield {
                'type': 'step',
                'data': {'message': '正在分析执行结果...'}
            }

            response = self.ai_manager.call_with_prompt(
                system_prompt=validate_prompt.get_system_prompt(),
                user_prompt=validate_prompt.get_user_prompt(
                    case_id=str(case_info.get('case_id', '')),
                    api_name=case_info.get('api_name', ''),
                    precondition=case_info.get('precondition', ''),
                    testpoint=case_info.get('testpoint', ''),
                    expectation=case_info.get('expectation', ''),
                    execution_results=json.dumps(execution_results, ensure_ascii=False)
                ),
                json_mode=True,
                max_tokens=2000
            )

            if response.content:
                logger.info(f'[校验] AI 原始返回: {response.content[:500]}')
                validation_result = self._parse_json_with_retry(response.content)

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

    # ============================================================
    # JSON 解析工具
    # ============================================================

    def _parse_json_with_retry(self, content: str, max_retries: int = 3) -> Optional[Dict[str, Any]]:
        """解析 AI 返回的 JSON，带重试和 markdown 代码块清理"""
        import re

        for attempt in range(max_retries):
            try:
                content = content.strip()

                # 尝试提取 markdown 代码块中的 JSON
                match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if not match:
                    match = re.search(r'```\s*(.*?)\s*```', content, re.DOTALL)
                if match:
                    content = match.group(1).strip()

                result = json.loads(content)

                if isinstance(result, dict):
                    logger.info(f'JSON 解析成功 (尝试 {attempt + 1}/{max_retries})')
                    return result
                else:
                    raise json.JSONDecodeError('解析结果不是字典类型', content, 0)

            except json.JSONDecodeError as e:
                logger.warning(f'解析 JSON 失败 (尝试 {attempt + 1}/{max_retries}): {e}')
                if attempt < max_retries - 1:
                    content = self._clean_json_content(content)

        logger.error(f'解析 JSON 失败，已重试 {max_retries} 次')
        return None

    def _clean_json_content(self, content: str) -> str:
        """尝试从内容中提取 { 到 } 之间的 JSON"""
        start = content.find('{')
        end = content.rfind('}') + 1
        if start != -1 and end > start:
            return content[start:end]
        return content
