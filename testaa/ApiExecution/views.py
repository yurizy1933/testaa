"""
API执行模块视图层
"""

import json
import logging
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


@csrf_exempt
@require_http_methods(['POST'])
def create_execution_view(request):
    """
    创建执行任务

    Request:
        - api_interface_id: 接口ID（必填）
        - test_data_id: 测试数据ID（可选）
        - base_url: 基础URL（必填）
        - testpoint: 测试点（必填）
        - expectation: 预期结果（必填）
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
        required_fields = ['api_interface_id', 'base_url', 'testpoint', 'expectation']
        missing_fields = [field for field in required_fields if field not in body]
        if missing_fields:
            return JsonResponse({
                'code': 400,
                'message': f'缺少必填字段: {", ".join(missing_fields)}'
            }, status=400)

        # 获取关联对象
        api_interface = get_object_or_404(ApiInterface, id=body['api_interface_id'])

        test_data = None
        if 'test_data_id' in body:
            test_data = get_object_or_404(TestData, id=body['test_data_id'])

        # 生成 run_list
        run_list = generate_run_list_from_interface(api_interface)

        # 获取测试数据
        test_data_json = get_test_data_from_model(test_data) if test_data else {}

        # 创建执行记录
        execution = ApiTestCaseExecution.objects.create(
            case_name=body.get('case_name', api_interface.api_name),
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
def execute_testcase_stream_view(request):
    """
    流式执行测试用例

    Request:
        - execution_id: 执行任务ID（必填）

    Response:
        SSE (Server-Sent Events) 流式响应，事件类型包括：
        - step: 执行步骤
        - result: 接口执行结果
        - report: 执行报告
        - error: 错误信息
    """
    try:
        body = json.loads(request.body)
        execution_id = body.get('execution_id')

        if not execution_id:
            return JsonResponse({
                'code': 400,
                'message': 'execution_id 参数不能为空'
            }, status=400)

        # 获取执行记录
        execution = get_object_or_404(ApiTestCaseExecution, id=execution_id)

        # 检查状态
        if execution.status == 'running':
            return JsonResponse({
                'code': 400,
                'message': '该任务正在执行中'
            }, status=400)

        # 创建引擎
        engine = TestExecutionEngine(ai_provider=execution.ai_provider)

        # 更新状态为执行中
        execution.status = 'running'
        execution.start_time = timezone.now()
        execution.save(update_fields=['status', 'start_time'])

        # 准备用例信息
        case_info = {
            'case_id': str(execution.id),
            'api_name': execution.api_interface.api_name if execution.api_interface else '',
            'precondition': execution.precondition,
            'testpoint': execution.testpoint,
            'expectation': execution.expectation
        }

        def event_generator():
            """事件生成器"""
            try:
                # 执行测试用例
                final_results = []

                for event in engine.execute_testcase(
                    run_list=execution.run_list,
                    test_data=execution.test_data.test_data_json if execution.test_data else {},
                    base_url=execution.base_url,
                    case_info=case_info
                ):
                    # 发送事件
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

                    # 收集结果
                    if event['type'] == 'result':
                        final_results.append(event['data'])
                    elif event['type'] == 'report':
                        # 保存执行结果
                        execution.execution_results = event['data']
                        execution.end_time = timezone.now()
                        execution.status = 'completed'
                        execution.save()

                        # 更新统计信息
                        execution.update_statistics()

                # 如果没有错误，执行 AI 校验
                if final_results and execution.status == 'completed':
                    yield f"data: {json.dumps({'type': 'step', 'data': {'message': '开始 AI 校验...'}}, ensure_ascii=False)}\n\n"

                    validation_results = []
                    for validation_event in engine.validate_testcase(
                        case_info=case_info,
                        execution_results=final_results
                    ):
                        yield f"data: {json.dumps(validation_event, ensure_ascii=False)}\n\n"

                        if validation_event['type'] == 'result':
                            validation_results.append(validation_event['data'])

                    # 保存校验结果
                    if validation_results:
                        execution.validation_result = validation_results[0]
                        execution.save(update_fields=['validation_result'])

            except Exception as e:
                # 发生异常，更新状态
                execution.status = 'failed'
                execution.end_time = timezone.now()
                execution.save(update_fields=['status', 'end_time'])

                # 发送错误事件
                yield f"data: {json.dumps({'type': 'error', 'data': {'message': str(e)}}, ensure_ascii=False)}\n\n"

        # 返回流式响应
        response = StreamingHttpResponse(
            event_generator(),
            content_type='text/event-stream'
        )
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'

        return response

    except json.JSONDecodeError:
        return JsonResponse({
            'code': 400,
            'message': '请求格式错误'
        }, status=400)
    except Exception as e:
        logger.error(f"执行测试用例失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'code': 500,
            'message': f'执行失败: {str(e)}'
        }, status=500)


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

        execution = get_object_or_404(ApiTestCaseExecution, id=execution_id)

        return JsonResponse({
            'code': 200,
            'message': '获取成功',
            'data': {
                'id': execution.id,
                'case_name': execution.case_name,
                'api_interface_name': execution.api_interface.api_name if execution.api_interface else None,
                'test_data_name': execution.test_data.test_name if execution.test_data else None,
                'base_url': execution.base_url,
                'status': execution.status,
                'execution_results': execution.execution_results,
                'validation_result': execution.validation_result,
                'total_interfaces': execution.total_interfaces,
                'success_count': execution.success_count,
                'failed_count': execution.failed_count,
                'duration_seconds': execution.duration_seconds,
                'create_time': execution.create_time.strftime('%Y-%m-%d %H:%M:%S'),
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

        # 构建查询
        query = {}
        if status_filter:
            query['status'] = status_filter
        if api_interface_id:
            query['api_interface_id'] = api_interface_id

        executions = ApiTestCaseExecution.objects.filter(**query).order_by('-create_time')

        # 分页
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))

        from django.core.paginator import Paginator
        paginator = Paginator(executions, page_size)
        page_obj = paginator.get_page(page)

        data = []
        for exec in page_obj:
            data.append({
                'id': exec.id,
                'case_name': exec.case_name,
                'api_interface_name': exec.api_interface.api_name if exec.api_interface else None,
                'status': exec.status,
                'total_interfaces': exec.total_interfaces,
                'success_count': exec.success_count,
                'failed_count': exec.failed_count,
                'duration_seconds': exec.duration_seconds,
                'create_time': exec.create_time.strftime('%Y-%m-%d %H:%M:%S'),
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

