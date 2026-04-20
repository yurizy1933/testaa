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
from common.models import Project, Doc, ApiInterface
#
# logger = logging.getLogger(__name__)

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

