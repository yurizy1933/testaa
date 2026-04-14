"""
API 路由定义

核心接口：apitest.getflow（流式获取接口业务流）
"""
import json
import threading
from queue import Queue
from typing import Optional

from flask import Blueprint, Response, jsonify, request

from core.engine import ApiTestEngine
from execute.engine import TestExecutionEngine
from services.kb_client import KBClient
from services.llm_service import LLMService
from services.db_service import DBService
from config.settings import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)

rpc_blueprint = Blueprint("rpc", __name__, url_prefix="/rpc")

_engine: Optional[ApiTestEngine] = None
_kb_client: Optional[KBClient] = None
_llm_service: Optional[LLMService] = None
_db_service: Optional[DBService] = None


def init_services():
    """初始化服务"""
    global _engine, _kb_client, _llm_service, _db_service

    if _engine is None:
        settings = get_settings()

        # 初始化 LLM 服务
        _llm_service = LLMService(settings.llm)

        # 初始化 KB 客户端
        kb_config = settings.knowledge_service
        _kb_client = KBClient(base_url=kb_config.get("base_url"))

        # 初始化 DB 服务
        db_config = settings.database
        _db_service = DBService(db_config)

        # 初始化引擎
        _engine = ApiTestEngine(kb_client=_kb_client, llm_service=_llm_service, db_service=_db_service)

        logger.info("服务初始化完成")

    return _engine


def get_execution_engine():
    """获取执行引擎"""
    global _kb_client, _llm_service

    if _kb_client is None or _llm_service is None:
        settings = get_settings()
        _llm_service = LLMService(settings.llm)
        kb_config = settings.knowledge_service
        _kb_client = KBClient(base_url=kb_config.get("base_url"))

    return TestExecutionEngine(kb_client=_kb_client, llm_service=_llm_service)


@rpc_blueprint.route("/", methods=["POST"])
def rpc_endpoint():
    """
    JSON-RPC 2.0 主入口

    支持方法：
    - apitest.getflow (stream=true) - 获取接口业务流
    """
    content_type = request.content_type or ""
    if "application/json" not in content_type:
        return jsonify({"error": "Content-Type must be application/json"}), 415

    raw_body = request.get_data(as_text=True)
    try:
        req_data = json.loads(raw_body)
    except json.JSONDecodeError as e:
        return jsonify({
            "jsonrpc": "2.0",
            "error": {"code": -32700, "message": f"Parse error: {e}"},
            "id": None
        }), 400

    if isinstance(req_data, list):
        return jsonify({
            "jsonrpc": "2.0",
            "error": {"code": -32600, "message": "Batch requests not supported"},
            "id": None
        }), 400

    # 提取顶层参数
    is_stream = req_data.get("stream", False)

    # 初始化服务（提前初始化以获取配置）
    init_services()

    # kb_id 和 kb_api_key 优先从请求中获取，其次从配置中获取
    settings = get_settings()
    kb_id = req_data.get("kb_id") or settings.knowledge_service.get("kb_id")
    kb_api_key = req_data.get("kb_api_key") or settings.knowledge_service.get("kb_api_key")

    method_name = req_data.get("method")
    params = req_data.get("params", {})
    request_id = req_data.get("id")

    # 注入顶层参数到 params
    if kb_id and "kb_id" not in params:
        params["kb_id"] = kb_id
    if kb_api_key and "kb_api_key" not in params:
        params["kb_api_key"] = kb_api_key

    # 方法路由
    if method_name == "apitest.getflow":
        if not is_stream:
            return jsonify({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32602,
                    "message": "apitest.getflow 只支持流式请求 (stream=true)"
                },
                "id": request_id
            }), 400
        return _handle_apitest_getflow(params, request_id)

    # 生成测试用例（流式）
    elif method_name == "testcase.generate":
        if not is_stream:
            return jsonify({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32602,
                    "message": "testcase.generate 只支持流式请求 (stream=true)"
                },
                "id": request_id
            }), 400
        return _handle_testcase_generate(params, request_id, req_data)

    # 获取接口依赖（流式）
    elif method_name == "dependency.get":
        if not is_stream:
            return jsonify({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32602,
                    "message": "dependency.get 只支持流式请求 (stream=true)"
                },
                "id": request_id
            }), 400
        return _handle_dependency_get(params, request_id)

    # 填充测试数据（流式）
    elif method_name == "testdata.fill":
        if not is_stream:
            return jsonify({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32602,
                    "message": "testdata.fill 只支持流式请求 (stream=true)"
                },
                "id": request_id
            }), 400
        return _handle_testdata_fill(params, request_id)

    # 执行测试用例（流式）
    elif method_name == "testcase.execute":
        if not is_stream:
            return jsonify({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32602,
                    "message": "testcase.execute 只支持流式请求 (stream=true)"
                },
                "id": request_id
            }), 400
        return _handle_testcase_execute(params, request_id)

    # 校验测试用例（流式）
    elif method_name == "testcase.validate":
        if not is_stream:
            return jsonify({
                "jsonrpc": "2.0",
                "error": {
                    "code": -32602,
                    "message": "testcase.validate 只支持流式请求 (stream=true)"
                },
                "id": request_id
            }), 400
        return _handle_testcase_validate(params, request_id)

    # LLM 调用接口
    elif method_name == "llm.chat":
        return _handle_llm_chat(params, request_id, is_stream)

    else:
        return jsonify({
            "jsonrpc": "2.0",
            "error": {"code": -32601, "message": f"Method not found: {method_name}"},
            "id": request_id
        }), 404


def _handle_apitest_getflow(params: dict, request_id) -> Response:
    """处理 apitest.getflow 流式请求"""

    queue = Queue()

    def run_handler():
        try:
            for event in _engine.get_flow(
                kb_id=params.get("kb_id"),
                query=params.get("query", "请分析这个接口的业务流"),
                kb_api_key=params.get("kb_api_key")
            ):
                # 包装为 JSON-RPC 格式
                rpc_event = {
                    "jsonrpc": "2.0",
                    "method": "apitest.progress",
                    "params": event,
                    "id": request_id
                }
                queue.put(f"data: {json.dumps(rpc_event, ensure_ascii=False)}\n\n")

            queue.put(None)  # 结束标记

        except Exception as e:
            logger.exception("流式处理异常")
            rpc_event = {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)},
                "id": request_id
            }
            queue.put(f"data: {json.dumps(rpc_event, ensure_ascii=False)}\n\n")
            queue.put(None)

    def thread_target():
        run_handler()

    thread = threading.Thread(target=thread_target, daemon=True)
    thread.start()

    def generate():
        while True:
            item = queue.get()
            if item is None:
                break
            yield item

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


def _handle_testcase_generate(params: dict, request_id, raw_data: dict) -> Response:
    """处理 testcase.generate 流式请求"""

    queue = Queue()

    def run_handler():
        try:
            for event in _engine.generate_testcase(
                kb_id=params.get("kb_id"),
                query=params.get("query", "对文档中的接口设计接口测试用例"),
                kb_api_key=params.get("kb_api_key"),
                save_to_db=raw_data.get("save_to_db", False),
                knowledge_id=params.get("knowledge_id")
            ):
                # 包装为 JSON-RPC 格式
                rpc_event = {
                    "jsonrpc": "2.0",
                    "method": "testcase.progress",
                    "params": event,
                    "id": request_id
                }
                queue.put(f"data: {json.dumps(rpc_event, ensure_ascii=False)}\n\n")

            queue.put(None)  # 结束标记

        except Exception as e:
            logger.exception("测试用例生成异常")
            rpc_event = {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)},
                "id": request_id
            }
            queue.put(f"data: {json.dumps(rpc_event, ensure_ascii=False)}\n\n")
            queue.put(None)

    def thread_target():
        run_handler()

    thread = threading.Thread(target=thread_target, daemon=True)
    thread.start()

    def generate():
        while True:
            item = queue.get()
            if item is None:
                break
            yield item

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


def _handle_dependency_get(params: dict, request_id) -> Response:
    """处理 dependency.get 流式请求"""

    queue = Queue()

    def run_handler():
        try:
            for event in _engine.get_api_dependency(
                case_id=params.get("case_id", ""),
                api_name=params.get("api_name", ""),
                precondition=params.get("precondition", ""),
                testpoint=params.get("testpoint", ""),
                expectation=params.get("expectation", ""),
                kb_id=params.get("kb_id"),
                kb_api_key=params.get("kb_api_key")
            ):
                # 包装为 JSON-RPC 格式
                rpc_event = {
                    "jsonrpc": "2.0",
                    "method": "dependency.progress",
                    "params": event,
                    "id": request_id
                }
                queue.put(f"data: {json.dumps(rpc_event, ensure_ascii=False)}\n\n")

            queue.put(None)  # 结束标记

        except Exception as e:
            logger.exception("获取接口依赖异常")
            rpc_event = {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)},
                "id": request_id
            }
            queue.put(f"data: {json.dumps(rpc_event, ensure_ascii=False)}\n\n")
            queue.put(None)

    def thread_target():
        run_handler()

    thread = threading.Thread(target=thread_target, daemon=True)
    thread.start()

    def generate():
        while True:
            item = queue.get()
            if item is None:
                break
            yield item

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


def _handle_testdata_fill(params: dict, request_id) -> Response:
    """处理 testdata.fill 流式请求"""

    queue = Queue()

    def run_handler():
        try:
            # 解析依赖数据
            dependency = params.get("dependency", {})
            if isinstance(dependency, str):
                dependency = json.loads(dependency)

            # 解析测试数据
            test_data = params.get("test_data", {})
            if isinstance(test_data, str):
                test_data = json.loads(test_data)

            for event in _engine.fill_test_data(
                case_id=params.get("case_id", ""),
                api_name=params.get("api_name", ""),
                precondition=params.get("precondition", ""),
                testpoint=params.get("testpoint", ""),
                expectation=params.get("expectation", ""),
                dependency=dependency,
                test_data=test_data,
                kb_id=params.get("kb_id"),
                kb_api_key=params.get("kb_api_key"),
                base_url=params.get("base_url", "http://127.0.0.1:8000")
            ):
                # 包装为 JSON-RPC 格式
                rpc_event = {
                    "jsonrpc": "2.0",
                    "method": "testdata.progress",
                    "params": event,
                    "id": request_id
                }
                queue.put(f"data: {json.dumps(rpc_event, ensure_ascii=False)}\n\n")

            queue.put(None)  # 结束标记

        except Exception as e:
            logger.exception("填充测试数据异常")
            rpc_event = {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)},
                "id": request_id
            }
            queue.put(f"data: {json.dumps(rpc_event, ensure_ascii=False)}\n\n")
            queue.put(None)

    def thread_target():
        run_handler()

    thread = threading.Thread(target=thread_target, daemon=True)
    thread.start()

    def generate():
        while True:
            item = queue.get()
            if item is None:
                break
            yield item

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


def _handle_llm_chat(params: dict, request_id, is_stream: bool) -> Response:
    """处理 llm.chat 请求"""

    queue = Queue()

    def run_handler():
        try:
            for event in _engine.llm_chat(
                query=params.get("query", ""),
                system_message=params.get("system_message"),
                stream=is_stream
            ):
                # 包装为 JSON-RPC 格式
                if is_stream:
                    rpc_event = {
                        "jsonrpc": "2.0",
                        "method": "llm.progress",
                        "params": event,
                        "id": request_id
                    }
                    queue.put(f"data: {json.dumps(rpc_event, ensure_ascii=False)}\n\n")
                else:
                    # 同步返回
                    rpc_event = {
                        "jsonrpc": "2.0",
                        "result": event,
                        "id": request_id
                    }
                    queue.put(rpc_event)

            queue.put(None)  # 结束标记

        except Exception as e:
            logger.exception("LLM 调用异常")
            if is_stream:
                rpc_event = {
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": str(e)},
                    "id": request_id
                }
                queue.put(f"data: {json.dumps(rpc_event, ensure_ascii=False)}\n\n")
            else:
                queue.put({
                    "jsonrpc": "2.0",
                    "error": {"code": -32603, "message": str(e)},
                    "id": request_id
                })
            queue.put(None)

    def thread_target():
        run_handler()

    thread = threading.Thread(target=thread_target, daemon=True)
    thread.start()

    if is_stream:
        # 流式响应
        def generate():
            while True:
                item = queue.get()
                if item is None:
                    break
                yield item

        return Response(
            generate(),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )
    else:
        # 同步响应
        result = queue.get()
        return jsonify(result)


def _handle_testcase_execute(params: dict, request_id) -> Response:
    """处理 testcase.execute 流式请求"""

    queue = Queue()
    engine = get_execution_engine()

    def run_handler():
        try:
            # 解析依赖数据（第二阶段返回的 run_list）
            run_list = params.get("run_list", [])
            if isinstance(run_list, str):
                run_list = json.loads(run_list)

            # 解析测试数据
            test_data = params.get("test_data", {})
            if isinstance(test_data, str):
                test_data = json.loads(test_data)

            for event in engine.execute_testcase(
                case_id=params.get("case_id", ""),
                api_name=params.get("api_name", ""),
                precondition=params.get("precondition", ""),
                testpoint=params.get("testpoint", ""),
                expectation=params.get("expectation", ""),
                run_list=run_list,
                test_data=test_data,
                base_url=params.get("base_url", "http://127.0.0.1:8000"),
                kb_id=params.get("kb_id"),
                kb_api_key=params.get("kb_api_key")
            ):
                # 包装为 JSON-RPC 格式
                rpc_event = {
                    "jsonrpc": "2.0",
                    "method": "testcase.execute.progress",
                    "params": event,
                    "id": request_id
                }
                queue.put(f"data: {json.dumps(rpc_event, ensure_ascii=False)}\n\n")

            queue.put(None)  # 结束标记

        except Exception as e:
            logger.exception("测试执行异常")
            rpc_event = {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)},
                "id": request_id
            }
            queue.put(f"data: {json.dumps(rpc_event, ensure_ascii=False)}\n\n")
            queue.put(None)

    def thread_target():
        run_handler()

    thread = threading.Thread(target=thread_target, daemon=True)
    thread.start()

    def generate():
        while True:
            item = queue.get()
            if item is None:
                break
            yield item

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


def _handle_testcase_validate(params: dict, request_id) -> Response:
    """处理 testcase.validate 流式请求"""

    queue = Queue()
    engine = get_execution_engine()

    def run_handler():
        try:
            # 解析执行结果
            execution_results = params.get("execution_results", [])
            if isinstance(execution_results, str):
                execution_results = json.loads(execution_results)

            for event in engine.validate_testcase(
                case_id=params.get("case_id", ""),
                api_name=params.get("api_name", ""),
                precondition=params.get("precondition", ""),
                testpoint=params.get("testpoint", ""),
                expectation=params.get("expectation", ""),
                execution_results=execution_results,
                kb_id=params.get("kb_id"),
                kb_api_key=params.get("kb_api_key")
            ):
                # 包装为 JSON-RPC 格式
                rpc_event = {
                    "jsonrpc": "2.0",
                    "method": "testcase.validate.progress",
                    "params": event,
                    "id": request_id
                }
                queue.put(f"data: {json.dumps(rpc_event, ensure_ascii=False)}\n\n")

            queue.put(None)  # 结束标记

        except Exception as e:
            logger.exception("测试校验异常")
            rpc_event = {
                "jsonrpc": "2.0",
                "error": {"code": -32603, "message": str(e)},
                "id": request_id
            }
            queue.put(f"data: {json.dumps(rpc_event, ensure_ascii=False)}\n\n")
            queue.put(None)

    def thread_target():
        run_handler()

    thread = threading.Thread(target=thread_target, daemon=True)
    thread.start()

    def generate():
        while True:
            item = queue.get()
            if item is None:
                break
            yield item

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


# ==================== 健康检查 ====================

@rpc_blueprint.route("/health", methods=["GET"])
def health():
    """健康检查"""
    return jsonify({
        "jsonrpc": "2.0",
        "result": {"status": "ok"},
        "id": None
    })


@rpc_blueprint.route("/status", methods=["GET"])
def status():
    """服务状态"""
    return jsonify({
        "service": "api-testing",
        "version": "1.0.0",
        "json_rpc_version": "2.0",
        "endpoints": [
            "POST /rpc/ - apitest.getflow (stream=true) - 获取接口业务流",
            "POST /rpc/ - testcase.generate (stream=true) - 生成接口测试用例",
            "POST /rpc/ - dependency.get (stream=true) - 获取接口依赖",
            "POST /rpc/ - llm.chat (stream=true/false) - LLM 对话",
            "GET  /rpc/health - 健康检查",
            "GET  /rpc/status - 服务状态"
        ]
    })
