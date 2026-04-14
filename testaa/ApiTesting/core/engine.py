"""
接口业务流引擎

核心流程：自动创建会话 → 调用 kb.chat 流式问答 → 自动销毁会话
"""
import json
import os
import re
from typing import Any, Dict, Generator, List, Optional

from services.kb_client import KBClient, KBError
from services.llm_service import LLMService
from services.db_service import DBService
from utils.logger import get_logger

logger = get_logger(__name__)

# 提示词目录
PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")


class ApiTestEngine:
    """接口测试引擎"""

    def __init__(self, kb_client: KBClient, llm_service: Optional[LLMService] = None, db_service: Optional[DBService] = None):
        self.kb_client = kb_client
        self.llm = llm_service
        self.db = db_service
        self._content_buffer = ""  # 用于累积流式响应的内容

    def _create_event(
        self,
        step: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建进度事件"""
        return {"type": step, "data": data}

    def get_flow(
        self,
        kb_id: str,
        query: str,
        kb_api_key: Optional[str] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        获取接口业务流（核心方法）

        流程：
        1. 自动创建会话
        2. 调用 kb.chat 流式问答
        3. 自动销毁会话

        Args:
            kb_id: 知识库 ID
            query: 查询问题
            kb_api_key: API 密钥

        Yields:
            事件字典（透传 kb.chat 的事件）
        """
        session_id = None

        try:
            # ==================== Step 1: 创建会话 ====================
            logger.info(f"正在创建会话，kb_id={kb_id}")

            session_result = self.kb_client.create_session(kb_id, kb_api_key)
            session_id = session_result.get("id")

            if not session_id:
                yield self._create_event(
                    "error",
                    {"message": "创建会话失败"}
                )
                return

            logger.info(f"会话创建成功：session_id={session_id}")

            yield self._create_event(
                "session",
                {"action": "created", "session_id": session_id}
            )

            # ==================== Step 2: 调用 kb.chat 流式问答 ====================
            logger.info(f"开始调用 kb.chat，session_id={session_id}, query={query[:50]}...")

            # 调用流式问答，直接透传事件
            for event in self.kb_client.chat_stream(
                query=query,
                session_id=session_id,
                kb_id=kb_id,
                kb_api_key=kb_api_key
            ):
                yield event

            logger.info(f"kb.chat 完成，session_id={session_id}")

        except KBError as e:
            logger.error(f"Knowledge 服务调用失败：{e}")
            yield self._create_event(
                "error",
                {"message": f"知识库服务调用失败：{e.message}"}
            )
        except Exception as e:
            logger.exception("业务流获取失败")
            yield self._create_event(
                "error",
                {"message": f"生成失败：{str(e)}"}
            )

        finally:
            # ==================== Step 3: 销毁会话 ====================
            if session_id:
                try:
                    logger.info(f"正在销毁会话：session_id={session_id}")
                    self.kb_client.destroy_session(session_id, kb_api_key)
                    logger.info(f"会话已销毁：session_id={session_id}")
                except Exception as e:
                    logger.error(f"销毁会话失败：{e}")

    def generate_testcase(
        self,
        kb_id: str,
        query: str = "对文档中的接口设计接口测试用例",
        kb_api_key: Optional[str] = None,
        save_to_db: bool = False,
        knowledge_id: Optional[str] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        生成接口测试用例（流式）

        流程：
        1. 加载提示词
        2. 自动创建会话
        3. 调用 kb.chat 流式问答
        4. 自动销毁会话
        5. 可选：保存到数据库

        Args:
            kb_id: 知识库 ID
            query: 查询问题（可选，默认使用提示词）
            kb_api_key: API 密钥
            save_to_db: 是否保存到数据库
            knowledge_id: 知识库 ID（用于关联文档）

        Yields:
            事件字典（透传 kb.chat 的事件）
        """
        session_id = None
        self._content_buffer = ""  # 重置缓冲区

        try:
            # ==================== Step 1: 加载提示词 ====================
            prompt_path = os.path.join(PROMPTS_DIR, "generate_testcase.txt")
            with open(prompt_path, "r", encoding="utf-8") as f:
                system_prompt = f.read()

            # 提示词始终使用，用户 query 作为补充说明
            if query and query != "对文档中的接口设计接口测试用例":
                final_query = system_prompt + "\n\n额外要求：" + query
            else:
                final_query = system_prompt

            logger.info(f"提示词加载完成，prompt_path={prompt_path}")

            # ==================== Step 2: 创建会话 ====================
            logger.info(f"正在创建会话，kb_id={kb_id}")

            session_result = self.kb_client.create_session(kb_id, kb_api_key)
            session_id = session_result.get("id")

            if not session_id:
                yield self._create_event(
                    "error",
                    {"message": "创建会话失败"}
                )
                return

            logger.info(f"会话创建成功：session_id={session_id}")

            yield self._create_event(
                "session",
                {"action": "created", "session_id": session_id}
            )

            # ==================== Step 3: 调用 kb.chat 流式问答 ====================
            logger.info(f"开始调用 kb.chat，session_id={session_id}, query={final_query[:50]}...")

            # 调用流式问答，直接透传事件并累积内容
            for event in self.kb_client.chat_stream(
                query=final_query,
                session_id=session_id,
                kb_id=kb_id,
                kb_api_key=kb_api_key
            ):
                # 累积 chunk 内容用于后续解析
                if event.get("type") == "chunk":
                    content = event.get("data", {}).get("content", "")
                    self._content_buffer += content
                yield event

            logger.info(f"kb.chat 完成，session_id={session_id}")

            # ==================== Step 4: 保存到数据库 ====================
            if save_to_db and self.db and self.db.enabled:
                logger.info("开始保存测试用例到数据库")
                test_cases = self._parse_test_cases(self._content_buffer)
                if test_cases:
                    # 根据 knowledge_id 查找文档
                    document_id = None
                    if knowledge_id:
                        doc = self.db.get_document_by_knowledge_id(knowledge_id)
                        if doc:
                            document_id = doc.get("id")

                    count = self.db.save_test_cases(test_cases, document_id, knowledge_id)
                    logger.info(f"保存测试用例完成，共保存 {count} 条")
                    yield self._create_event(
                        "saved",
                        {"count": count, "document_id": document_id}
                    )
                else:
                    logger.warning("未解析到有效的测试用例")
                    yield self._create_event(
                        "error",
                        {"message": "未解析到有效的测试用例"}
                    )

        except KBError as e:
            logger.error(f"Knowledge 服务调用失败：{e}")
            yield self._create_event(
                "error",
                {"message": f"知识库服务调用失败：{e.message}"}
            )
        except Exception as e:
            logger.exception("生成测试用例失败")
            yield self._create_event(
                "error",
                {"message": f"生成失败：{str(e)}"}
            )

        finally:
            # ==================== Step 5: 销毁会话 ====================
            if session_id:
                try:
                    logger.info(f"正在销毁会话：session_id={session_id}")
                    self.kb_client.destroy_session(session_id, kb_api_key)
                    logger.info(f"会话已销毁：session_id={session_id}")
                except Exception as e:
                    logger.error(f"销毁会话失败：{e}")

    def _parse_test_cases(self, content: str) -> List[Dict[str, Any]]:
        """
        解析 LLM 返回的测试用例 JSON

        Args:
            content: LLM 返回的内容

        Returns:
            测试用例列表
        """
        try:
            # 尝试直接解析 JSON
            content = content.strip()

            # 提取 markdown 代码块中的 JSON
            match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if match:
                content = match.group(1).strip()

            # 尝试解析 JSON 数组
            test_cases = json.loads(content)
            if isinstance(test_cases, list):
                return test_cases
            return []
        except json.JSONDecodeError as e:
            logger.error(f"解析测试用例 JSON 失败：{e}")
            return []

    def get_api_dependency(
        self,
        case_id: str,
        api_name: str,
        precondition: str,
        testpoint: str,
        expectation: str,
        kb_id: str,
        kb_api_key: Optional[str] = None
    ) -> Generator[Dict[str, Any], None, None]:
        """
        获取接口依赖和执行顺序（流式）- 不存库版本

        Args:
            case_id: 用例 ID
            api_name: 接口名称
            precondition: 前置条件
            testpoint: 测试点
            expectation: 预期结果
            kb_id: 知识库 ID
            kb_api_key: API 密钥

        Yields:
            事件字典
        """
        self._content_buffer = ""
        session_id = None

        try:
            # Step 1: 加载提示词
            yield self._create_event(
                "step",
                {"message": "正在加载相关信息..."}
            )

            prompt_path = os.path.join(PROMPTS_DIR, "get_dependency.txt")
            with open(prompt_path, "r", encoding="utf-8") as f:
                system_prompt = f.read()

            # 替换提示词中的变量
            prompt = system_prompt.replace("{{case_id}}", case_id)
            prompt = prompt.replace("{{api_name}}", api_name)
            prompt = prompt.replace("{{precondition}}", precondition)
            prompt = prompt.replace("{{testpoint}}", testpoint)
            prompt = prompt.replace("{{expectation}}", expectation)

            # # Step 2: 创建会话
            # yield self._create_event(
            #     "step",
            #     {"message": "正在创建知识库会话..."}
            # )

            session_result = self.kb_client.create_session(kb_id, kb_api_key)
            session_id = session_result.get("id")

            if not session_id:
                yield self._create_event(
                    "error",
                    {"message": "创建会话失败"}
                )
                return

            # yield self._create_event(
            #     "step",
            #     {"message": "正在调用 AI 分析接口依赖关系..."}
            # )

            # Step 3: 调用 kb.chat 流式问答
            full_response = ""
            for event in self.kb_client.chat_stream(
                query=prompt,
                session_id=session_id,
                kb_id=kb_id,
                kb_api_key=kb_api_key
            ):
                # 累积 chunk 内容
                if event.get("type") == "chunk":
                    content = event.get("data", {}).get("content", "")
                    full_response += content
                    yield self._create_event(
                        "chunk",
                        {"content": content}
                    )
                else:
                    # 透传其他事件
                    yield event

            # yield self._create_event(
            #     "step_complete",
            #     {"message": "第一阶段分析完成"}
            # )

            # Step 4: 解析返回的 JSON
            dependency_info = self._parse_dependency(full_response)
            if not dependency_info:
                yield self._create_event(
                    "error",
                    {"message": "无法解析依赖关系 JSON"}
                )
                return

            yield self._create_event(
                "result",
                {"dependency": dependency_info}
            )

        except Exception as e:
            logger.exception("获取接口依赖失败")
            yield self._create_event(
                "error",
                {"message": f"获取依赖失败：{str(e)}"}
            )

        finally:
            # 销毁会话
            if session_id:
                try:
                    self.kb_client.destroy_session(session_id, kb_api_key)
                except Exception as e:
                    logger.error(f"销毁会话失败：{e}")

    def _parse_dependency(self, content: str) -> Optional[Dict[str, Any]]:
        """
        解析依赖关系 JSON（带重试机制）

        Args:
            content: LLM 返回的内容

        Returns:
            依赖关系字典
        """
        max_retries = 3

        for attempt in range(max_retries):
            try:
                content = content.strip()

                # 尝试多种 markdown 代码块格式
                # 1. ```json ... ```
                match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if match:
                    content = match.group(1).strip()
                else:
                    # 2. ``` ... ``` (不带 json 标识)
                    match = re.search(r'```\s*(.*?)\s*```', content, re.DOTALL)
                    if match:
                        content = match.group(1).strip()

                dependency = json.loads(content)

                # 验证解析结果是否为字典类型
                if isinstance(dependency, dict):
                    logger.info(f"JSON 解析成功 (尝试 {attempt + 1}/{max_retries})")
                    return dependency
                else:
                    raise json.JSONDecodeError("解析结果不是字典类型", content, 0)

            except json.JSONDecodeError as e:
                logger.warning(f"解析依赖 JSON 失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    # 重试前可以稍微清理一下内容
                    content = self._clean_json_content(content)
                    continue
                logger.error(f"解析依赖 JSON 失败，已重试 {max_retries} 次")
                return None

        return None

    def _clean_json_content(self, content: str) -> str:
        """
        清理 JSON 内容，尝试提取有效的 JSON 部分

        Args:
            content: 原始内容

        Returns:
            清理后的内容
        """
        # 尝试直接找到 { 和 } 之间的内容
        start = content.find('{')
        end = content.rfind('}') + 1

        if start != -1 and end > start:
            return content[start:end]

        return content

    def fill_test_data(
        self,
        case_id: str,
        api_name: str,
        precondition: str,
        testpoint: str,
        expectation: str,
        dependency: Dict[str, Any],
        test_data: Dict[str, Any],
        kb_id: str,
        kb_api_key: Optional[str] = None,
        base_url: str = "http://127.0.0.1:8000"
    ) -> Generator[Dict[str, Any], None, None]:
        """
        填充测试数据（流式）

        Args:
            case_id: 用例 ID
            api_name: 接口名称
            precondition: 前置条件
            testpoint: 测试点
            expectation: 预期结果
            dependency: 第一阶段返回的依赖分析结果
            test_data: 真实测试数据
            kb_id: 知识库 ID
            kb_api_key: API 密钥
            base_url: 基座 URL

        Yields:
            事件字典
        """
        self._content_buffer = ""
        session_id = None

        try:
            # Step 1: 加载提示词
            yield self._create_event(
                "step",
                {"message": "正在处理相关信息..."}
            )

            prompt_path = os.path.join(PROMPTS_DIR, "fill_test_data.txt")
            with open(prompt_path, "r", encoding="utf-8") as f:
                system_prompt = f.read()

            # 替换提示词中的变量
            prompt = system_prompt.replace("{{case_id}}", str(case_id))
            prompt = prompt.replace("{{api_name}}", api_name)
            prompt = prompt.replace("{{precondition}}", precondition)
            prompt = prompt.replace("{{testpoint}}", testpoint)
            prompt = prompt.replace("{{expectation}}", expectation)
            prompt = prompt.replace("{{dependency_json}}", json.dumps(dependency, ensure_ascii=False))
            prompt = prompt.replace("{{test_data}}", json.dumps(test_data, ensure_ascii=False))
            prompt = prompt.replace("{{base_url}}", base_url)
            prompt = prompt.replace("{{test_data}}", json.dumps(test_data, ensure_ascii=False))

            # # Step 2: 创建会话
            # yield self._create_event(
            #     "step",
            #     {"message": "正在创建知识库会话..."}
            # )

            session_result = self.kb_client.create_session(kb_id, kb_api_key)
            session_id = session_result.get("id")

            if not session_id:
                yield self._create_event(
                    "error",
                    {"message": "创建会话失败"}
                )
                return

            # yield self._create_event(
            #     "step",
            #     {"message": "正在调用 AI 填充测试数据..."}
            # )

            # Step 3: 调用 kb.chat 流式问答
            full_response = ""
            for event in self.kb_client.chat_stream(
                query=prompt,
                session_id=session_id,
                kb_id=kb_id,
                kb_api_key=kb_api_key
            ):
                # 累积 chunk 内容
                if event.get("type") == "chunk":
                    content = event.get("data", {}).get("content", "")
                    full_response += content
                    yield self._create_event(
                        "chunk",
                        {"content": content}
                    )
                else:
                    # 透传其他事件
                    yield event

            # yield self._create_event(
            #     "step_complete",
            #     {"message": "第二阶段分析完成"}
            # )

            # Step 4: 解析返回的 JSON
            filled_data = self._parse_filled_data(full_response)
            if not filled_data:
                yield self._create_event(
                    "error",
                    {"message": "无法解析填充后的数据 JSON"}
                )
                return

            yield self._create_event(
                "result",
                {"filled_data": filled_data}
            )

        except Exception as e:
            logger.exception("填充测试数据失败")
            yield self._create_event(
                "error",
                {"message": f"填充数据失败：{str(e)}"}
            )

        finally:
            # 销毁会话
            if session_id:
                try:
                    self.kb_client.destroy_session(session_id, kb_api_key)
                except Exception as e:
                    logger.error(f"销毁会话失败：{e}")

    def _parse_filled_data(self, content: str) -> Optional[Dict[str, Any]]:
        """
        解析填充后的测试数据 JSON（带重试机制）

        Args:
            content: LLM 返回的内容

        Returns:
            填充后的数据字典
        """
        max_retries = 3

        for attempt in range(max_retries):
            try:
                content = content.strip()

                # 尝试多种 markdown 代码块格式
                # 1. ```json ... ```
                match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
                if match:
                    content = match.group(1).strip()
                else:
                    # 2. ``` ... ``` (不带 json 标识)
                    match = re.search(r'```\s*(.*?)\s*```', content, re.DOTALL)
                    if match:
                        content = match.group(1).strip()

                filled_data = json.loads(content)

                # 验证解析结果是否为字典类型
                if isinstance(filled_data, dict):
                    logger.info(f"JSON 解析成功 (尝试 {attempt + 1}/{max_retries})")
                    return filled_data
                else:
                    raise json.JSONDecodeError("解析结果不是字典类型", content, 0)

            except json.JSONDecodeError as e:
                logger.warning(f"解析填充数据 JSON 失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    # 重试前可以稍微清理一下内容
                    content = self._clean_json_content(content)
                    continue
                logger.error(f"解析填充数据 JSON 失败，已重试 {max_retries} 次")
                return None

        return None

    def llm_chat(
        self,
        query: str,
        system_message: Optional[str] = None,
        stream: bool = False
    ) -> Generator[Dict[str, Any], None, None]:
        """
        直接调用 LLM 模型

        Args:
            query: 用户问题
            system_message: 系统提示词（可选）
            stream: 是否流式返回

        Yields:
            事件字典
        """
        if not self.llm:
            yield self._create_event(
                "error",
                {"message": "LLM 服务未初始化"}
            )
            return

        try:
            messages: List[Dict[str, str]] = []

            if system_message:
                messages.append({"role": "system", "content": system_message})

            messages.append({"role": "user", "content": query})

            logger.info(f"开始调用 LLM，query={query[:50]}...")

            if stream:
                # 流式调用
                for chunk in self.llm.chat_stream(messages):
                    yield self._create_event(
                        "chunk",
                        {"content": chunk}
                    )
                logger.info("LLM 流式调用完成")
            else:
                # 同步调用
                result = self.llm.chat(messages)
                yield self._create_event(
                    "result",
                    {
                        "content": result["content"],
                        "usage": result.get("usage", {}),
                        "finish_reason": result.get("finish_reason")
                    }
                )
                logger.info(f"LLM 同步调用完成，usage={result.get('usage', {})}")

        except Exception as e:
            logger.exception("LLM 调用失败")
            yield self._create_event(
                "error",
                {"message": f"LLM 调用失败：{str(e)}"}
            )
