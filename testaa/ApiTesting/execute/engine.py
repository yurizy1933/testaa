"""
测试执行引擎

核心功能：
1. 执行测试用例（按 run_list 顺序执行）
2. 每次执行前调用 AI 分析是否需要填充参数
3. 流式返回执行结果
"""
import json
import os
from typing import Any, Dict, Generator, List, Optional

from services.kb_client import KBClient
from services.llm_service import LLMService
from .executor import ApiTestExecutor, ExecutionResult, ExecutionReport
from utils.logger import get_logger

logger = get_logger(__name__)

# 提示词目录
PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")


class TestExecutionEngine:
    """测试执行引擎"""

    def __init__(self, kb_client: KBClient, llm_service: LLMService):
        self.kb_client = kb_client
        self.llm = llm_service

    def execute_testcase(
        self,
        case_id: str,
        api_name: str,
        precondition: str,
        testpoint: str,
        expectation: str,
        run_list: List[Dict[str, Any]],
        test_data: Dict[str, Any],
        base_url: str,
        kb_id: str,
        kb_api_key: Optional[str] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        执行测试用例（流式）

        Args:
            case_id: 用例 ID
            api_name: 接口名称
            precondition: 前置条件
            testpoint: 测试点
            expectation: 预期结果
            run_list: 接口执行列表（第二阶段返回的）
            test_data: 真实测试数据
            base_url: 基座 URL
            kb_id: 知识库 ID
            kb_api_key: API 密钥

        Yields:
            执行结果事件
        """
        executor = ApiTestExecutor(base_url=base_url)

        try:
            # # Step 1: 加载提示词
            # yield self._create_event(
            #     "step",
            #     {"message": "正在加载提示词模板..."}
            # )

            prompt_path = os.path.join(PROMPTS_DIR, "execute_api.txt")
            with open(prompt_path, "r", encoding="utf-8") as f:
                system_prompt = f.read()

            # Step 2: 开始执行
            yield self._create_event(
                "step",
                {"message": f"开始执行测试用例，共 {len(run_list)} 个接口"}
            )

            # 遍历执行每个接口
            for i, api_info in enumerate(run_list):
                run_num = api_info.get("run_num", i + 1)
                api_name = api_info.get("api_name", f"接口{run_num}")

                yield self._create_event(
                    "step",
                    {"message": f"正在执行 [{run_num}] {api_name}..."}
                )

                # 如果是第一个接口，直接使用第二阶段的参数
                # 如果不是第一个接口，调用 AI 分析填充参数
                if i > 0:
                    # yield self._create_event(
                    #     "step",
                    #     {"message": f"正在分析接口依赖关系..."}
                    # )

                    # 确保 api_info 中有 params 字段（用于 GET 请求）
                    if "params" not in api_info:
                        api_info["params"] = {}

                    # 调用 AI 填充参数
                    filled_api_info = self._fill_params_with_ai(
                        system_prompt=system_prompt,
                        case_id=case_id,
                        api_name=api_name,
                        precondition=precondition,
                        testpoint=testpoint,
                        expectation=expectation,
                        execution_history=executor.get_history(),
                        current_api_info=api_info,
                        test_data=test_data,
                        kb_id=kb_id,
                        kb_api_key=kb_api_key
                    )

                    if filled_api_info:
                        # 合并填充的参数
                        api_info.update(filled_api_info)

                # 执行接口
                result = executor.execute_api(api_info)

                # 返回执行结果
                yield self._create_event(
                    "result",
                    {
                        "run_num": result.run_num,
                        "api_name": result.api_name,
                        "api_url": result.api_url,
                        "method": result.method,
                        "request": result.request,
                        "response": result.response,
                        "status_code": result.status_code,
                        "success": result.success,
                        "duration_ms": result.duration_ms,
                        "error": result.error
                    }
                )

                # 如果执行失败，立即停止
                if not result.success:
                    yield self._create_event(
                        "step_complete",
                        {"message": f"接口执行失败，停止后续执行"}
                    )
                    break

            # Step 3: 执行完成
            yield self._create_event(
                "step_complete",
                {"message": "测试用例执行完成"}
            )

            # 返回执行报告摘要
            history = executor.get_history()
            success_count = sum(1 for h in history if h.get("success", False))
            total_count = len(history)

            yield self._create_event(
                "report",
                {
                    "case_id": case_id,
                    "total": total_count,
                    "success": success_count,
                    "failed": total_count - success_count,
                    "results": history
                }
            )

        except Exception as e:
            logger.exception("测试执行异常")
            yield self._create_event(
                "error",
                {"message": f"执行失败：{str(e)}"}
            )

    def _fill_params_with_ai(
        self,
        system_prompt: str,
        case_id: str,
        api_name: str,
        precondition: str,
        testpoint: str,
        expectation: str,
        execution_history: List[Dict[str, Any]],
        current_api_info: Dict[str, Any],
        test_data: Dict[str, Any],
        kb_id: str,
        kb_api_key: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        调用 AI 填充接口参数（通过 KB Client）

        Args:
            system_prompt: 提示词模板
            case_id: 用例 ID
            api_name: 接口名称
            precondition: 前置条件
            testpoint: 测试点
            expectation: 预期结果
            execution_history: 历史执行记录
            current_api_info: 当前接口信息
            test_data: 真实测试数据
            kb_id: 知识库 ID
            kb_api_key: API 密钥

        Returns:
            填充后的接口信息
        """
        ai_session_id = None
        try:
            # 为每次 AI 调用创建独立的会话
            session_result = self.kb_client.create_session(kb_id, kb_api_key)
            ai_session_id = session_result.get("id")

            if not ai_session_id:
                logger.error("创建会话失败")
                return None

            # 替换提示词中的变量
            prompt = system_prompt.replace("{{case_id}}", str(case_id))
            prompt = prompt.replace("{{api_name}}", api_name)
            prompt = prompt.replace("{{precondition}}", precondition)
            prompt = prompt.replace("{{testpoint}}", testpoint)
            prompt = prompt.replace("{{expectation}}", expectation)
            prompt = prompt.replace("{{execution_history}}", json.dumps(execution_history, ensure_ascii=False))
            prompt = prompt.replace("{{current_api_info}}", json.dumps(current_api_info, ensure_ascii=False))
            prompt = prompt.replace("{{test_data}}", json.dumps(test_data, ensure_ascii=False))

            # 调用 kb.chat_stream 获取 AI 响应
            full_response = ""
            for event in self.kb_client.chat_stream(
                query=prompt,
                session_id=ai_session_id,
                kb_id=kb_id,
                kb_api_key=kb_api_key
            ):
                if event.get("type") == "chunk":
                    content = event.get("data", {}).get("content", "")
                    full_response += content

            # 解析返回的 JSON
            filled_info = self._parse_ai_response(full_response)

            return filled_info

        except Exception as e:
            logger.error(f"AI 填充参数失败：{e}")
            logger.exception("详细异常栈")
            return None

        finally:
            # 销毁会话
            if ai_session_id:
                try:
                    self.kb_client.destroy_session(ai_session_id, kb_api_key)
                except Exception as e:
                    logger.error(f"销毁会话失败：{e}")

    def _parse_ai_response(self, content: str) -> Optional[Dict[str, Any]]:
        """解析 AI 返回的 JSON"""
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
            logger.error(f"解析 AI 响应 JSON 失败：{e}")
            return None

    def _create_event(self, step: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建进度事件"""
        return {"type": step, "data": data}

    def validate_testcase(
        self,
        case_id: str,
        api_name: str,
        precondition: str,
        testpoint: str,
        expectation: str,
        execution_results: List[Dict[str, Any]],
        kb_id: str,
        kb_api_key: Optional[str] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        校验测试用例（流式）

        Args:
            case_id: 用例 ID
            api_name: 接口名称
            precondition: 前置条件
            testpoint: 测试点
            expectation: 预期结果
            execution_results: 执行结果列表（第三阶段返回的）
            kb_id: 知识库 ID
            kb_api_key: API 密钥

        Yields:
            校验结果事件
        """
        ai_session_id = None

        try:
            # # Step 1: 加载提示词
            # yield self._create_event(
            #     "step",
            #     {"message": "正在加载校验规则..."}
            # )

            prompt_path = os.path.join(PROMPTS_DIR, "validate_testcase.txt")
            with open(prompt_path, "r", encoding="utf-8") as f:
                system_prompt = f.read()

            # Step 2: 创建 KB 会话
            session_result = self.kb_client.create_session(kb_id, kb_api_key)
            ai_session_id = session_result.get("id")

            if not ai_session_id:
                yield self._create_event(
                    "error",
                    {"message": "创建会话失败"}
                )
                return

            # Step 3: 替换提示词中的变量
            prompt = system_prompt.replace("{{case_id}}", str(case_id))
            prompt = prompt.replace("{{api_name}}", api_name)
            prompt = prompt.replace("{{precondition}}", precondition)
            prompt = prompt.replace("{{testpoint}}", testpoint)
            prompt = prompt.replace("{{expectation}}", expectation)
            prompt = prompt.replace("{{execution_results}}", json.dumps(execution_results, ensure_ascii=False))

            # Step 4: 调用 kb.chat_stream 获取 AI 响应
            yield self._create_event(
                "step",
                {"message": "正在分析执行结果..."}
            )

            full_response = ""
            for event in self.kb_client.chat_stream(
                query=prompt,
                session_id=ai_session_id,
                kb_id=kb_id,
                kb_api_key=kb_api_key
            ):
                if event.get("type") == "chunk":
                    content = event.get("data", {}).get("content", "")
                    full_response += content
                    # 流式返回 chunk
                    yield self._create_event(
                        "chunk",
                        {"content": content}
                    )

            # Step 5: 解析返回的 JSON
            validation_result = self._parse_ai_response(full_response)

            if validation_result:
                yield self._create_event(
                    "result",
                    validation_result
                )
            else:
                yield self._create_event(
                    "error",
                    {"message": "无法解析校验结果"}
                )

            yield self._create_event(
                "step_complete",
                {"message": "测试校验完成"}
            )

        except Exception as e:
            logger.exception("测试校验异常")
            yield self._create_event(
                "error",
                {"message": f"校验失败：{str(e)}"}
            )

        finally:
            # 销毁会话
            if ai_session_id:
                try:
                    self.kb_client.destroy_session(ai_session_id, kb_api_key)
                except Exception as e:
                    logger.error(f"销毁会话失败：{e}")
