# """
# AI测试用例模块视图层
# """

import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from .models import TestCase, AiJobManagement
from .serializers import serialize_testcase, serialize_ai_job
from .services import TestCaseService, AiJobService
from common.models import Project, Doc, ApiInterface
#
# logger = logging.getLogger(__name__)
#
#
# @csrf_exempt
# @require_http_methods(['POST'])
# def create_testcase_view(request):
#     """
#     创建测试用例
#
#     Request:
#         - title: 用例标题（必填）
#         - precondition: 前置条件（可选）
#         - test_steps: 测试步骤（必填）
#         - expected_result: 预期结果（必填）
#         - priority: 优先级（可选，默认P2）
#         - doc_id: 文档ID（可选）
#         - api_interface_id: API接口ID（可选）
#         - job_id: 任务ID（可选）
#     """
#     try:
#         body = json.loads(request.body)
#
#         # 验证必填字段
#         required_fields = ['title', 'test_steps', 'expected_result']
#         missing_fields = [field for field in required_fields if field not in body]
#         if missing_fields:
#             return JsonResponse({
#                 'code': 400,
#                 'message': f'缺少必填字段: {", ".join(missing_fields)}'
#             }, status=400)
#
#         # 获取关联对象
#         doc = None
#         if 'doc_id' in body:
#             doc = get_object_or_404(Doc, id=body['doc_id'])
#
#         api_interface = None
#         if 'api_interface_id' in body:
#             api_interface = get_object_or_404(ApiInterface, id=body['api_interface_id'])
#
#         job = None
#         if 'job_id' in body:
#             job = get_object_or_404(AiJobManagement, id=body['job_id'])
#
#         # 创建测试用例
#         testcase = TestCase.objects.create(
#             title=body['title'],
#             precondition=body.get('precondition', ''),
#             test_steps=body['test_steps'],
#             expected_result=body['expected_result'],
#             priority=body.get('priority', 'P2'),
#             doc_id=doc,
#             api_interface=api_interface,
#             job_id=job,
#             status='active'
#         )
#
#         logger.info(f"创建测试用例成功: ID={testcase.id}, 标题={testcase.title}")
#
#         return JsonResponse({
#             'code': 200,
#             'message': '创建成功',
#             'data': {'testcase_id': testcase.id}
#         })
#
#     except json.JSONDecodeError:
#         return JsonResponse({
#             'code': 400,
#             'message': '请求格式错误'
#         }, status=400)
#     except Exception as e:
#         logger.error(f"创建测试用例失败: {str(e)}", exc_info=True)
#         return JsonResponse({
#             'code': 500,
#             'message': f'创建失败: {str(e)}'
#         }, status=500)
#
#
# @require_http_methods(['GET'])
# def get_testcases_view(request):
#     """
#     获取测试用例列表
#
#     Query Parameters:
#         - project_id: 项目ID（可选）
#         - api_interface_id: API接口ID（可选）
#         - status: 状态过滤（可选）
#         - page: 页码（可选，默认1）
#         - page_size: 每页数量（可选，默认10）
#     """
#     try:
#         # 查询参数
#         project_id = request.GET.get('project_id')
#         api_interface_id = request.GET.get('api_interface_id')
#         status_filter = request.GET.get('status')
#
#         # 构建查询
#         query = {'status': 'active'}  # 默认只查询激活状态的用例
#
#         if api_interface_id:
#             query['api_interface_id'] = api_interface_id
#         if project_id:
#             # 通过文档ID过滤
#             doc_ids = Doc.objects.filter(project_id=project_id).values_list('id', flat=True)
#             query['doc_id__in'] = doc_ids
#         if status_filter:
#             query['status'] = status_filter
#
#         testcases = TestCase.objects.filter(**query).order_by('-created_time')
#
#         # 分页
#         page = int(request.GET.get('page', 1))
#         page_size = int(request.GET.get('page_size', 10))
#
#         from django.core.paginator import Paginator
#         paginator = Paginator(testcases, page_size)
#         page_obj = paginator.get_page(page)
#
#         data = [serialize_testcase(tc) for tc in page_obj]
#
#         return JsonResponse({
#             'code': 200,
#             'message': '获取成功',
#             'data': data,
#             'pagination': {
#                 'total': paginator.count,
#                 'page': page,
#                 'page_size': page_size,
#                 'total_pages': paginator.num_pages
#             }
#         })
#
#     except Exception as e:
#         logger.error(f"获取测试用例列表失败: {str(e)}", exc_info=True)
#         return JsonResponse({
#             'code': 500,
#             'message': f'获取失败: {str(e)}'
#         }, status=500)
#
#
# @require_http_methods(['GET'])
# def get_testcase_detail_view(request):
#     """
#     获取测试用例详情
#
#     Query Parameters:
#         - testcase_id: 测试用例ID（必填）
#     """
#     try:
#         testcase_id = request.GET.get('testcase_id')
#
#         if not testcase_id:
#             return JsonResponse({
#                 'code': 400,
#                 'message': 'testcase_id 参数不能为空'
#             }, status=400)
#
#         testcase = get_object_or_404(TestCase, id=testcase_id)
#
#         return JsonResponse({
#             'code': 200,
#             'message': '获取成功',
#             'data': serialize_testcase(testcase)
#         })
#
#     except Exception as e:
#         logger.error(f"获取测试用例详情失败: {str(e)}", exc_info=True)
#         return JsonResponse({
#             'code': 500,
#             'message': f'获取失败: {str(e)}'
#         }, status=500)
#
#
# @csrf_exempt
# @require_http_methods(['POST'])
# def generate_testcases_view(request):
#     """
#     生成测试用例（AI）
#
#     Request:
#         - api_interface_id: API接口ID（必填）
#         - ai_provider: AI提供商（可选，默认zhipu）
#     """
#     try:
#         body = json.loads(request.body)
#
#         api_interface_id = body.get('api_interface_id')
#         if not api_interface_id:
#             return JsonResponse({
#                 'code': 400,
#                 'message': 'api_interface_id 参数不能为空'
#             }, status=400)
#
#         # 获取API接口
#         api_interface = get_object_or_404(ApiInterface, id=api_interface_id)
#         ai_provider = body.get('ai_provider', 'zhipu')
#
#         # 生成测试用例
#         service = TestCaseService(ai_provider=ai_provider)
#         testcases_data = service.generate_testcases_from_api_interface(api_interface)
#
#         # 创建测试用例
#         created_testcases = service.create_testcases(
#             testcases_data,
#             api_interface=api_interface
#         )
#
#         return JsonResponse({
#             'code': 200,
#             'message': f'成功生成 {len(created_testcases)} 个测试用例',
#             'data': {
#                 'count': len(created_testcases),
#                 'testcases': [serialize_testcase(tc) for tc in created_testcases]
#             }
#         })
#
#     except json.JSONDecodeError:
#         return JsonResponse({
#             'code': 400,
#             'message': '请求格式错误'
#         }, status=400)
#     except Exception as e:
#         logger.error(f"生成测试用例失败: {str(e)}", exc_info=True)
#         return JsonResponse({
#             'code': 500,
#             'message': f'生成失败: {str(e)}'
#         }, status=500)
#
#
# @csrf_exempt
# @require_http_methods(['POST'])
# def update_testcase_view(request):
#     """
#     更新测试用例
#
#     Request:
#         - testcase_id: 测试用例ID（必填）
#         - title: 用例标题（可选）
#         - precondition: 前置条件（可选）
#         - test_steps: 测试步骤（可选）
#         - expected_result: 预期结果（可选）
#         - priority: 优先级（可选）
#     """
#     try:
#         body = json.loads(request.body)
#
#         testcase_id = body.get('testcase_id')
#         if not testcase_id:
#             return JsonResponse({
#                 'code': 400,
#                 'message': 'testcase_id 参数不能为空'
#             }, status=400)
#
#         testcase = get_object_or_404(TestCase, id=testcase_id)
#
#         # 更新字段
#         if 'title' in body:
#             testcase.title = body['title']
#         if 'precondition' in body:
#             testcase.precondition = body['precondition']
#         if 'test_steps' in body:
#             testcase.test_steps = body['test_steps']
#         if 'expected_result' in body:
#             testcase.expected_result = body['expected_result']
#         if 'priority' in body:
#             testcase.priority = body['priority']
#
#         testcase.save()
#
#         logger.info(f"更新测试用例成功: ID={testcase.id}")
#
#         return JsonResponse({
#             'code': 200,
#             'message': '更新成功',
#             'data': serialize_testcase(testcase)
#         })
#
#     except json.JSONDecodeError:
#         return JsonResponse({
#             'code': 400,
#             'message': '请求格式错误'
#         }, status=400)
#     except Exception as e:
#         logger.error(f"更新测试用例失败: {str(e)}", exc_info=True)
#         return JsonResponse({
#             'code': 500,
#             'message': f'更新失败: {str(e)}'
#         }, status=500)
#
#
# @csrf_exempt
# @require_http_methods(['POST'])
# def delete_testcase_view(request):
#     """
#     删除测试用例（软删除）
#
#     Request:
#         - testcase_id: 测试用例ID（必填）
#     """
#     try:
#         body = json.loads(request.body)
#
#         testcase_id = body.get('testcase_id')
#         if not testcase_id:
#             return JsonResponse({
#                 'code': 400,
#                 'message': 'testcase_id 参数不能为空'
#             }, status=400)
#
#         testcase = get_object_or_404(TestCase, id=testcase_id)
#         testcase.soft_delete()
#
#         logger.info(f"删除测试用例成功: ID={testcase.id}")
#
#         return JsonResponse({
#             'code': 200,
#             'message': '删除成功'
#         })
#
#     except json.JSONDecodeError:
#         return JsonResponse({
#             'code': 400,
#             'message': '请求格式错误'
#         }, status=400)
#     except Exception as e:
#         logger.error(f"删除测试用例失败: {str(e)}", exc_info=True)
#         return JsonResponse({
#             'code': 500,
#             'message': f'删除失败: {str(e)}'
#         }, status=500)
#
#
# @csrf_exempt
# @require_http_methods(['POST'])
# def run_ai_job_view(request):
#     """
#     运行AI生成任务
#
#     Request:
#         - doc_id: 文档ID（必填）
#         - project_id: 项目ID（必填）
#         - ai_provider: AI提供商（可选，默认zhipu）
#     """
#     try:
#         body = json.loads(request.body)
#
#         doc_id = body.get('doc_id')
#         project_id = body.get('project_id')
#
#         if not doc_id or not project_id:
#             return JsonResponse({
#                 'code': 400,
#                 'message': 'doc_id 和 project_id 参数不能为空'
#             }, status=400)
#
#         # 获取文档和项目
#         doc = get_object_or_404(Doc, id=doc_id)
#         project = get_object_or_404(Project, id=project_id)
#         ai_provider = body.get('ai_provider', 'zhipu')
#
#         # 创建任务
#         job_service = AiJobService()
#         job = job_service.create_job(doc)
#         job_service.start_job(job)
#
#         try:
#             # TODO: 实现实际的文档解析和用例生成逻辑
#             # 这里暂时只创建一个示例任务
#
#             job_service.complete_job(job)
#
#             return JsonResponse({
#                 'code': 200,
#                 'message': '任务执行成功',
#                 'data': {
#                     'job_id': job.id,
#                     'status': 'completed'
#                 }
#             })
#
#         except Exception as e:
#             job_service.fail_job(job, str(e))
#             raise
#
#     except json.JSONDecodeError:
#         return JsonResponse({
#             'code': 400,
#             'message': '请求格式错误'
#         }, status=400)
#     except Exception as e:
#         logger.error(f"运行AI任务失败: {str(e)}", exc_info=True)
#         return JsonResponse({
#             'code': 500,
#             'message': f'执行失败: {str(e)}'
#         }, status=500)
#
#
@require_http_methods(['GET'])
def get_ai_jobs_view(request):
    """
    获取AI任务列表

    Query Parameters:
        - project_id: 项目ID（可选）
        - status: 任务状态（可选）
        - page: 页码（可选，默认1）
        - page_size: 每页数量（可选，默认10）
    """
    try:
        # 查询参数
        project_id = request.GET.get('project_id')
        status_filter = request.GET.get('status')

        # 构建查询
        query = {}

        if project_id:
            doc_ids = Doc.objects.filter(project_id=project_id).values_list('id', flat=True)
            query['doc_id__in'] = doc_ids

        if status_filter:
            status_map = {'pending': 0, 'processing': 1, 'completed': 2}
            query['job_status'] = status_map.get(status_filter.lower())

        jobs = AiJobManagement.objects.filter(**query).order_by('-create_time')

        # 分页
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))

        from django.core.paginator import Paginator
        paginator = Paginator(jobs, page_size)
        page_obj = paginator.get_page(page)

        data = [serialize_ai_job(job) for job in page_obj]

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
        logger.error(f"获取AI任务列表失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'code': 500,
            'message': f'获取失败: {str(e)}'
        }, status=500)

