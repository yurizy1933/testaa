"""
API执行模块视图层
"""

import json
import logging
from django.conf import settings
from django.http import StreamingHttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import ApiTestCaseExecution
from .engine import TestExecutionEngine
from .serializers import generate_run_list_from_interface, get_test_data_from_model
from common.models import ApiInterface, TestData

logger = logging.getLogger(__name__)


def _duration_ms(execution):
    """优先使用统计耗时，缺失时用开始/结束时间推算。"""
    if execution.total_duration_ms:
        return int(execution.total_duration_ms)
    if execution.start_time and execution.end_time:
        return int((execution.end_time - execution.start_time).total_seconds() * 1000)
    return None


def _duration_display(duration_ms):
    if duration_ms is None:
        return '-'
    if duration_ms >= 1000:
        return f'{duration_ms / 1000:.2f}s'
    return f'{duration_ms}ms'


@csrf_exempt
@require_http_methods(['POST'])
def create_execution_view(request):
    """
    创建执行任务

    Request:
        - base_url: 基础URL（必填）
        - testpoint: 测试点（必填）
        - expectation: 预期结果（必填）
        - run_list: 接口执行列表（可选，不传则从 api_interface_id 生成）
        - api_interface_id: 接口ID（可选，用于生成 run_list）
        - test_data_id: 测试数据ID（可选）
        - case_name: 用例名称（可选，默认使用接口名称）
        - precondition: 前置条件（可选）
        - ai_provider: AI提供商（可选，默认zhipu）

    Response:
        - code: 响应码
        - message: 响应消息
        - data:
            - execution_id: 执行任务ID
            - case_name: 用例名称
            - status: 执行状态
    """
    try:
        body = json.loads(request.body)

        # 验证必填字段
        required_fields = ['base_url', 'testpoint', 'expectation']
        missing_fields = [field for field in required_fields if field not in body]
        if missing_fields:
            return JsonResponse({
                'code': 400,
                'message': f'缺少必填字段: {", ".join(missing_fields)}'
            }, status=400)

        # 获取关联对象
        api_interface = None
        test_data = None

        if 'api_interface_id' in body:
            api_interface = get_object_or_404(ApiInterface, id=body['api_interface_id'])

        if 'test_data_id' in body:
            test_data = get_object_or_404(TestData, id=body['test_data_id'])

        # 生成或使用传入的 run_list
        if 'run_list' in body:
            run_list = body['run_list']
        elif api_interface:
            run_list = generate_run_list_from_interface(api_interface)
        else:
            return JsonResponse({
                'code': 400,
                'message': '请提供 run_list 或 api_interface_id'
            }, status=400)

        # 获取测试数据
        test_data_json = get_test_data_from_model(test_data) if test_data else {}

        # 创建执行记录
        default_case_name = api_interface.api_name if api_interface else 'API测试用例'
        execution = ApiTestCaseExecution.objects.create(
            case_name=body.get('case_name', default_case_name),
            api_interface=api_interface,
            test_data=test_data,
            base_url=body['base_url'],
            run_list=run_list,
            ai_provider=body.get('ai_provider', 'zhipu'),
            precondition=body.get('precondition', ''),
            testpoint=body['testpoint'],
            expectation=body['expectation']
        )

        logger.info(f"创建执行任务成功: ID={execution.id}, 用例名={execution.case_name}")

        return JsonResponse({
            'code': 200,
            'message': '执行任务创建成功',
            'data': {
                'execution_id': execution.id,
                'case_name': execution.case_name,
                'status': execution.status
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'code': 400,
            'message': '请求格式错误'
        }, status=400)
    except Exception as e:
        logger.error(f"创建执行任务失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'code': 500,
            'message': f'创建执行任务失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def dependency_get_stream_view(request):
    """
    分析接口调用依赖（SSE 流式）

    Request:
        - case_id: 用例ID（可选）
        - api_name: 接口名称（必填）
        - precondition: 前置条件（可选）
        - testpoint: 测试点（必填）
        - expectation: 预期结果（必填）
        - ai_provider: AI提供商（可选，默认zhipu）

    Response:
        SSE 流式响应，最终返回 {"case_id": ..., "run_list": [...]}
    """
    try:
        body = json.loads(request.body)

        required_fields = ['api_name', 'testpoint', 'expectation']
        missing_fields = [f for f in required_fields if f not in body]
        if missing_fields:
            return JsonResponse({
                'code': 400,
                'message': f'缺少必填字段: {", ".join(missing_fields)}'
            }, status=400)

        engine = TestExecutionEngine(ai_provider=body.get('ai_provider', 'zhipu'))

        def event_generator():
            yield f"data: {json.dumps({'type': 'step', 'data': {'message': '正在分析接口调用依赖...'}}, ensure_ascii=False)}\n\n"

            result = engine.get_api_dependency(
                case_id=str(body.get('case_id', '')),
                api_name=body['api_name'],
                precondition=body.get('precondition', ''),
                testpoint=body['testpoint'],
                expectation=body['expectation']
            )

            if result:
                yield f"data: {json.dumps({'type': 'result', 'data': result}, ensure_ascii=False)}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'data': {'message': 'AI 分析依赖失败，请重试'}}, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'type': 'step_complete', 'data': {'message': '依赖分析完成'}}, ensure_ascii=False)}\n\n"

        response = StreamingHttpResponse(
            event_generator(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response

    except json.JSONDecodeError:
        return JsonResponse({'code': 400, 'message': '请求格式错误'}, status=400)
    except Exception as e:
        logger.error(f"依赖分析失败: {str(e)}", exc_info=True)
        return JsonResponse({'code': 500, 'message': f'依赖分析失败: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def fill_test_data_stream_view(request):
    """
    填充测试数据（SSE 流式）

    Request:
        - api_name: 接口名称（必填）
        - testpoint: 测试点（必填）
        - expectation: 预期结果（必填）
        - dependency: 依赖分析结果（必填，dependency.get 返回的结果）
        - test_data: 测试数据（可选，默认 {}）
        - base_url: 基座URL（可选，默认 http://127.0.0.1:8000）
        - case_id: 用例ID（可选）
        - precondition: 前置条件（可选）
        - ai_provider: AI提供商（可选，默认zhipu）

    Response:
        SSE 流式响应，最终返回 {"case_id": ..., "run_list": [...]}（带填充后的参数）
    """
    try:
        body = json.loads(request.body)

        required_fields = ['api_name', 'testpoint', 'expectation', 'dependency']
        missing_fields = [f for f in required_fields if f not in body]
        if missing_fields:
            return JsonResponse({
                'code': 400,
                'message': f'缺少必填字段: {", ".join(missing_fields)}'
            }, status=400)

        engine = TestExecutionEngine(ai_provider=body.get('ai_provider', 'zhipu'))

        # 解析依赖和测试数据（支持字符串或对象）
        dependency = body['dependency']
        if isinstance(dependency, str):
            dependency = json.loads(dependency)

        test_data = body.get('test_data', {})
        if isinstance(test_data, str):
            test_data = json.loads(test_data)

        def event_generator():
            yield f"data: {json.dumps({'type': 'step', 'data': {'message': '正在调用 AI 填充测试数据...'}}, ensure_ascii=False)}\n\n"

            result = engine.fill_test_data(
                case_id=str(body.get('case_id', '')),
                api_name=body['api_name'],
                precondition=body.get('precondition', ''),
                testpoint=body['testpoint'],
                expectation=body['expectation'],
                dependency=dependency,
                test_data=test_data,
                base_url=body.get('base_url', 'http://127.0.0.1:8000')
            )

            if result:
                yield f"data: {json.dumps({'type': 'result', 'data': result}, ensure_ascii=False)}\n\n"
            else:
                yield f"data: {json.dumps({'type': 'error', 'data': {'message': 'AI 填充数据失败，请重试'}}, ensure_ascii=False)}\n\n"

            yield f"data: {json.dumps({'type': 'step_complete', 'data': {'message': '测试数据填充完成'}}, ensure_ascii=False)}\n\n"

        response = StreamingHttpResponse(
            event_generator(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response

    except json.JSONDecodeError:
        return JsonResponse({'code': 400, 'message': '请求格式错误'}, status=400)
    except Exception as e:
        logger.error(f"测试数据填充失败: {str(e)}", exc_info=True)
        return JsonResponse({'code': 500, 'message': f'填充测试数据失败: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def execute_testcase_stream_view(request):
    """
    一键执行测试用例（全流程 SSE 流式）

    Request（至少提供 api_interface_id 或 api_name）:
        - test_case_id: 测试用例ID（推荐传入，关联执行记录到用例）
        - api_interface_id: 接口ID（推荐，自动获取 api_name/api_path/method）
        - api_name: 接口名称（如果没有 api_interface_id 则必填）
        - base_url: 基础URL（必填）
        - testpoint: 测试点（可选，默认取 api_name）
        - expectation / expected_result: 预期结果（可选）
        - test_data_id: 测试数据ID（可选）
        - precondition: 前置条件（可选）
        - title: 用例名称（可选，默认取 api_name）
        - ai_provider: AI提供商（可选，默认 zhipu）

    Response: SSE 流式，事件类型：
        - step: 阶段进度
        - result: 依赖分析/数据填充/接口执行/校验 结果
        - report: 执行报告
        - complete: 全流程完成（含 execution_id）
        - error: 错误信息
    """
    try:
        body = json.loads(request.body)

        # === 解析关联对象 ===
        api_interface = None
        test_data_obj = None
        test_case_obj = None

        if 'test_case_id' in body:
            from AITestCases.models import TestCase as TC
            test_case_obj = get_object_or_404(TC, id=body['test_case_id'])

        if 'api_interface_id' in body:
            api_interface = get_object_or_404(ApiInterface, id=body['api_interface_id'])
        if 'test_data_id' in body:
            test_data_obj = get_object_or_404(TestData, id=body['test_data_id'])

        # === 推导参数（兼容 TestCase 模型字段名） ===
        # api_name: 优先直接用，其次从 api_interface 取，最后用 title 兜底
        api_name = body.get('api_name') or (api_interface.api_name if api_interface else None) or body.get('title', 'API测试用例')

        # testpoint: 优先直接用，其次用 test_steps，最后用 api_name 兜底
        testpoint = body.get('testpoint') or body.get('test_steps') or api_name

        # expectation: 兼容 expected_result 字段名
        expectation = body.get('expectation') or body.get('expected_result', '')

        # title 用于展示名
        title = body.get('title') or api_name

        precondition = body.get('precondition', '')
        base_url = (body.get('base_url') or '').strip() or getattr(settings, 'API_TEST_BASE_URL', 'http://127.0.0.1:8000')
        case_id = body.get('case_id', '')
        ai_provider = body.get('ai_provider', 'zhipu')

        test_data_json = test_data_obj.test_data_json if test_data_obj else {}

        test_data_json = test_data_obj.test_data_json if test_data_obj else {}

        engine = TestExecutionEngine(ai_provider=ai_provider)

        def event_generator():
            execution = None

            try:
                # ================================================
                # [1/4] 分析接口调用依赖
                # ================================================
                yield f"data: {json.dumps({'type': 'step', 'data': {'message': '[1/4] 正在分析接口调用依赖...'}}, ensure_ascii=False)}\n\n"

                dependency = engine.get_api_dependency(
                    case_id=str(case_id),
                    api_name=api_name,
                    precondition=precondition,
                    testpoint=testpoint,
                    expectation=expectation
                )

                if dependency:
                    yield f"data: {json.dumps({'type': 'result', 'data': {'phase': 'dependency', 'dependency': dependency}}, ensure_ascii=False)}\n\n"
                    # 从 dependency 中提取 run_list
                    run_list = dependency.get('run_list', [])
                else:
                    yield f"data: {json.dumps({'type': 'error', 'data': {'message': '[1/4] AI 分析依赖失败，使用默认 run_list'}}, ensure_ascii=False)}\n\n"
                    # 使用默认 run_list
                    if api_interface:
                        run_list = generate_run_list_from_interface(api_interface)
                    else:
                        run_list = [{
                            'run_num': 1,
                            'api_name': api_name,
                            'api_url': api_interface.api_path if api_interface else '/',
                            'method': api_interface.method if api_interface else 'GET',
                            'request_body': {},
                            'params': {},
                            'headers': {'Content-Type': 'application/json'}
                        }]

                # ================================================
                # [2/4] 填充测试数据
                # ================================================
                yield f"data: {json.dumps({'type': 'step', 'data': {'message': '[2/4] 正在填充测试数据...'}}, ensure_ascii=False)}\n\n"

                filled = engine.fill_test_data(
                    case_id=str(case_id),
                    api_name=api_name,
                    precondition=precondition,
                    testpoint=testpoint,
                    expectation=expectation,
                    dependency=dependency or {},
                    test_data=test_data_json,
                    base_url=base_url
                )

                if filled:
                    yield f"data: {json.dumps({'type': 'result', 'data': {'phase': 'fill_data', 'filled_data': filled}}, ensure_ascii=False)}\n\n"
                    if 'run_list' in filled:
                        run_list = filled['run_list']
                else:
                    yield f"data: {json.dumps({'type': 'error', 'data': {'message': '[2/4] AI 填充数据失败，使用原始参数'}}, ensure_ascii=False)}\n\n"

                # ================================================
                # 创建执行记录
                # ================================================
                execution = ApiTestCaseExecution.objects.create(
                    case_name=title,
                    test_case=test_case_obj,
                    api_interface=api_interface,
                    test_data=test_data_obj,
                    base_url=base_url,
                    run_list=run_list,
                    ai_provider=ai_provider,
                    precondition=precondition,
                    testpoint=testpoint,
                    expectation=expectation,
                    status='running',
                    start_time=timezone.now()
                )

                yield f"data: {json.dumps({'type': 'step', 'data': {'message': f'执行记录已创建 (ID: {execution.id})'}}, ensure_ascii=False)}\n\n"

                case_info = {
                    'case_id': str(execution.id),
                    'api_name': api_name,
                    'precondition': precondition,
                    'testpoint': testpoint,
                    'expectation': expectation
                }

                # ================================================
                # [3/4] 执行测试
                # ================================================
                yield f"data: {json.dumps({'type': 'step', 'data': {'message': f'[3/4] 开始执行，共 {len(run_list)} 个接口'}}, ensure_ascii=False)}\n\n"

                final_results = []
                for event in engine.execute_testcase(
                    run_list=run_list,
                    test_data=test_data_json,
                    base_url=base_url,
                    case_info=case_info
                ):
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                    if event['type'] == 'result':
                        final_results.append(event['data'])
                    elif event['type'] == 'report':
                        execution.execution_results = event['data']
                        execution.end_time = timezone.now()
                        execution.status = 'completed'
                        execution.save()
                        execution.update_statistics()

                # ================================================
                # [4/4] AI 校验
                # ================================================
                if final_results:
                    yield f"data: {json.dumps({'type': 'step', 'data': {'message': '[4/4] 正在 AI 校验...'}}, ensure_ascii=False)}\n\n"

                    for validation_event in engine.validate_testcase(
                        case_info=case_info,
                        execution_results=final_results
                    ):
                        yield f"data: {json.dumps(validation_event, ensure_ascii=False)}\n\n"

                        if validation_event['type'] == 'result':
                            execution.validation_result = validation_event['data']
                            execution.save(update_fields=['validation_result'])

                # 完成
                yield f"data: {json.dumps({'type': 'complete', 'data': {'execution_id': execution.id, 'status': execution.status}}, ensure_ascii=False)}\n\n"

            except Exception as e:
                logger.exception('全流程执行异常')
                if execution:
                    execution.status = 'failed'
                    execution.end_time = timezone.now()
                    execution.save(update_fields=['status', 'end_time'])
                yield f"data: {json.dumps({'type': 'error', 'data': {'message': f'执行失败：{str(e)}'}}, ensure_ascii=False)}\n\n"

        response = StreamingHttpResponse(
            event_generator(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'
        return response

    except json.JSONDecodeError:
        return JsonResponse({'code': 400, 'message': '请求格式错误'}, status=400)
    except Exception as e:
        logger.error(f"执行测试用例失败: {str(e)}", exc_info=True)
        return JsonResponse({'code': 500, 'message': f'执行失败: {str(e)}'}, status=500)


@require_http_methods(['GET'])
def get_execution_view(request):
    """
    获取执行记录详情

    Query Parameters:
        - execution_id: 执行任务ID（必填）

    Response:
        - code: 响应码
        - message: 响应消息
        - data: 执行记录详情
    """
    try:
        execution_id = request.GET.get('execution_id')

        if not execution_id:
            return JsonResponse({
                'code': 400,
                'message': 'execution_id 参数不能为空'
            }, status=400)

        execution = get_object_or_404(
            ApiTestCaseExecution.objects.select_related('test_case', 'api_interface', 'test_data'),
            id=execution_id
        )
        duration_ms = _duration_ms(execution)

        return JsonResponse({
            'code': 200,
            'message': '获取成功',
            'data': {
                'id': execution.id,
                'case_name': execution.case_name,
                'test_case_id': execution.test_case_id,
                'api_interface_name': execution.api_interface.api_name if execution.api_interface else None,
                'test_data_name': execution.test_data.test_name if execution.test_data else None,
                'base_url': execution.base_url,
                'status': execution.status,
                'execution_results': execution.execution_results,
                'validation_result': execution.validation_result,
                'total_interfaces': execution.total_interfaces,
                'success_count': execution.success_count,
                'failed_count': execution.failed_count,
                'duration_ms': duration_ms,
                'duration_display': _duration_display(duration_ms),
                'duration_seconds': execution.duration_seconds,
                'created_at': execution.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                'create_time': execution.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                'start_time': execution.start_time.strftime('%Y-%m-%d %H:%M:%S') if execution.start_time else None,
                'end_time': execution.end_time.strftime('%Y-%m-%d %H:%M:%S') if execution.end_time else None,
            }
        })

    except Exception as e:
        logger.error(f"获取执行记录失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'code': 500,
            'message': f'获取失败: {str(e)}'
        }, status=500)


@require_http_methods(['GET'])
def list_executions_view(request):
    """
    获取执行记录列表

    Query Parameters:
        - status: 状态过滤（可选）
        - api_interface_id: 接口ID过滤（可选）
        - test_case_id: 测试用例ID过滤（可选）
        - page: 页码（可选，默认1）
        - page_size: 每页数量（可选，默认10）

    Response:
        - code: 响应码
        - message: 响应消息
        - data: 执行记录列表
        - pagination: 分页信息
    """
    try:
        # 查询参数
        status_filter = request.GET.get('status')
        api_interface_id = request.GET.get('api_interface_id')
        test_case_id = request.GET.get('test_case_id')
        case_name = request.GET.get('case_name')

        # 构建查询
        query = {}
        if status_filter:
            query['status'] = status_filter
        if api_interface_id:
            query['api_interface_id'] = api_interface_id
        if test_case_id:
            query['test_case_id'] = test_case_id

        executions = (ApiTestCaseExecution.objects
                      .filter(**query)
                      .select_related('test_case', 'api_interface')
                      .order_by('-create_time'))

        if case_name:
            executions = executions.filter(case_name__icontains=case_name)

        # 分页
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))

        from django.core.paginator import Paginator
        paginator = Paginator(executions, page_size)
        page_obj = paginator.get_page(page)

        data = []
        for execution in page_obj:
            duration_ms = _duration_ms(execution)
            data.append({
                'id': execution.id,
                'case_name': execution.case_name,
                'test_case_id': execution.test_case_id,
                'api_interface_name': execution.api_interface.api_name if execution.api_interface else None,
                'case_type': 'api' if execution.api_interface_id else 'doc',
                'status': execution.status,
                'total_interfaces': execution.total_interfaces,
                'success_count': execution.success_count,
                'failed_count': execution.failed_count,
                'duration_ms': duration_ms,
                'duration_display': _duration_display(duration_ms),
                'duration_seconds': execution.duration_seconds,
                'created_at': execution.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                'create_time': execution.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                'start_time': execution.start_time.strftime('%Y-%m-%d %H:%M:%S') if execution.start_time else None,
                'end_time': execution.end_time.strftime('%Y-%m-%d %H:%M:%S') if execution.end_time else None,
            })

        return JsonResponse({
            'code': 200,
            'message': '获取成功',
            'data': data,
            'pagination': {
                'total': paginator.count,
                'page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages
            }
        })

    except Exception as e:
        logger.error(f"获取执行列表失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'code': 500,
            'message': f'获取失败: {str(e)}'
        }, status=500)
