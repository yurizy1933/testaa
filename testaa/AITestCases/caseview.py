"""
测试用例管理视图层
"""

import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.core.paginator import Paginator

from .models import TestCase, ApiInterface, AiJobManagement
from common.models import CommonDoc, Project


def serialize_testcase(testcase):
    """序列化测试用例对象"""
    data = {
        'id': testcase.id,
        'title': testcase.title,
        'precondition': testcase.precondition,
        'test_steps': testcase.test_steps,
        'expected_result': testcase.expected_result,
        'priority': testcase.priority,
        'status': testcase.status,
        'created_time': testcase.created_time.strftime('%Y-%m-%d %H:%M:%S') if testcase.created_time else None,
        'updated_time': testcase.updated_time.strftime('%Y-%m-%d %H:%M:%S') if testcase.updated_time else None,
    }

    # 关联对象
    if testcase.doc_id:
        data['doc_id'] = testcase.doc_id.id
        data['doc_filename'] = testcase.doc_id.filename

    if testcase.api_interface:
        data['api_interface_id'] = testcase.api_interface.id
        data['api_interface_name'] = testcase.api_interface.api_name

    if testcase.job_id:
        data['job_id'] = testcase.job_id.id
        data['job_status'] = testcase.job_id.job_status

    return data


@csrf_exempt
@require_http_methods(['POST'])
def create_testcase_view(request):
    """
    创建测试用例

    Request:
        - title: 用例标题（必填）
        - precondition: 前置条件（可选）
        - test_steps: 测试步骤（必填）
        - expected_result: 预期结果（必填）
        - priority: 优先级（可选，默认P2）
        - doc_id: 文档ID（可选）
        - api_interface_id: API接口ID（可选）
        - job_id: 任务ID（可选）
    """
    try:
        body = json.loads(request.body)

        # 验证必填字段
        required_fields = ['title', 'test_steps', 'expected_result']
        missing_fields = [field for field in required_fields if field not in body]
        if missing_fields:
            return JsonResponse({
                'code': 400,
                'message': f'缺少必填字段: {", ".join(missing_fields)}'
            }, status=400)

        # 验证优先级
        priority = body.get('priority', 'P2')
        valid_priorities = ['P0', 'P1', 'P2', 'P3']
        if priority not in valid_priorities:
            return JsonResponse({
                'code': 400,
                'message': f'优先级无效，可选值: {", ".join(valid_priorities)}'
            }, status=400)

        # 获取关联对象
        doc = None
        if 'doc_id' in body:
            doc = get_object_or_404(CommonDoc, id=body['doc_id'])

        api_interface = None
        if 'api_interface_id' in body:
            api_interface = get_object_or_404(ApiInterface, id=body['api_interface_id'])

        job = None
        if 'job_id' in body:
            job = get_object_or_404(AiJobManagement, id=body['job_id'])

        # 创建测试用例
        testcase = TestCase.objects.create(
            title=body['title'],
            precondition=body.get('precondition', ''),
            test_steps=body['test_steps'],
            expected_result=body['expected_result'],
            priority=priority,
            doc_id=doc,
            api_interface=api_interface,
            job_id=job,
            status='active'
        )

        return JsonResponse({
            'code': 200,
            'message': '创建成功',
            'data': serialize_testcase(testcase)
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'code': 400,
            'message': '请求格式错误'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'创建失败: {str(e)}'
        }, status=500)


@require_http_methods(['GET'])
def get_testcases_view(request):
    """
    获取测试用例列表

    Query Parameters:
        - project_id: 项目ID（可选）
        - doc_id: 文档ID（可选）
        - api_interface_id: API接口ID（可选）
        - job_id: 任务ID（可选）
        - status: 状态过滤（可选：active/deleted）
        - priority: 优先级过滤（可选：P0/P1/P2/P3）
        - keyword: 关键词搜索（可选，搜索标题）
        - page: 页码（可选，默认1）
        - page_size: 每页数量（可选，默认10）
    """
    try:
        # 查询参数
        project_id = request.GET.get('project_id')
        doc_id = request.GET.get('doc_id')
        api_interface_id = request.GET.get('api_interface_id')
        job_id = request.GET.get('job_id')
        status_filter = request.GET.get('status')
        priority_filter = request.GET.get('priority')
        keyword = request.GET.get('keyword')

        # 构建查询
        query = {}

        if project_id:
            # 通过文档ID过滤
            doc_ids = CommonDoc.objects.filter(project_id=project_id).values_list('id', flat=True)
            query['doc_id__in'] = doc_ids

        if doc_id:
            query['doc_id'] = doc_id

        if api_interface_id:
            query['api_interface_id'] = api_interface_id

        if job_id:
            query['job_id'] = job_id

        if status_filter:
            query['status'] = status_filter

        if priority_filter:
            query['priority'] = priority_filter

        testcases = TestCase.objects.filter(**query)

        # 关键词搜索
        if keyword:
            testcases = testcases.filter(title__icontains=keyword)

        testcases = testcases.order_by('-created_time')

        # 分页
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))

        paginator = Paginator(testcases, page_size)
        page_obj = paginator.get_page(page)

        data = [serialize_testcase(tc) for tc in page_obj]

        return JsonResponse({
            'code': 200,
            'message': '获取成功',
            'data': data,
            'pagination': {
                'total': paginator.count,
                'page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'has_next': page_obj.has_next(),
                'has_prev': page_obj.has_previous()
            }
        })

    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'获取失败: {str(e)}'
        }, status=500)


@require_http_methods(['GET'])
def get_testcase_detail_view(request):
    """
    获取测试用例详情

    Query Parameters:
        - id: 测试用例ID（必填）
    """
    try:
        testcase_id = request.GET.get('id')

        if not testcase_id:
            return JsonResponse({
                'code': 400,
                'message': 'id 参数不能为空'
            }, status=400)

        testcase = get_object_or_404(TestCase, id=testcase_id)

        return JsonResponse({
            'code': 200,
            'message': '获取成功',
            'data': serialize_testcase(testcase)
        })

    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'获取失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def update_testcase_view(request):
    """
    更新测试用例

    Request:
        - id: 测试用例ID（必填）
        - title: 用例标题（可选）
        - precondition: 前置条件（可选）
        - test_steps: 测试步骤（可选）
        - expected_result: 预期结果（可选）
        - priority: 优先级（可选）
        - doc_id: 文档ID（可选）
        - api_interface_id: API接口ID（可选）
        - job_id: 任务ID（可选）
        - status: 状态（可选：active/deleted）
    """
    try:
        body = json.loads(request.body)

        testcase_id = body.get('id')
        if not testcase_id:
            return JsonResponse({
                'code': 400,
                'message': 'id 参数不能为空'
            }, status=400)

        testcase = get_object_or_404(TestCase, id=testcase_id)

        # 更新字段
        if 'title' in body:
            testcase.title = body['title']
        if 'precondition' in body:
            testcase.precondition = body['precondition']
        if 'test_steps' in body:
            testcase.test_steps = body['test_steps']
        if 'expected_result' in body:
            testcase.expected_result = body['expected_result']
        if 'priority' in body:
            valid_priorities = ['P0', 'P1', 'P2', 'P3']
            if body['priority'] in valid_priorities:
                testcase.priority = body['priority']
        if 'status' in body:
            valid_statuses = ['active', 'deleted']
            if body['status'] in valid_statuses:
                testcase.status = body['status']

        # 更新关联对象
        if 'doc_id' in body:
            if body['doc_id']:
                doc = get_object_or_404(CommonDoc, id=body['doc_id'])
                testcase.doc_id = doc
            else:
                testcase.doc_id = None

        if 'api_interface_id' in body:
            if body['api_interface_id']:
                api_interface = get_object_or_404(ApiInterface, id=body['api_interface_id'])
                testcase.api_interface = api_interface
            else:
                testcase.api_interface = None

        if 'job_id' in body:
            if body['job_id']:
                job = get_object_or_404(AiJobManagement, id=body['job_id'])
                testcase.job_id = job
            else:
                testcase.job_id = None

        testcase.save()

        return JsonResponse({
            'code': 200,
            'message': '更新成功',
            'data': serialize_testcase(testcase)
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'code': 400,
            'message': '请求格式错误'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'更新失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def delete_testcase_view(request):
    """
    删除测试用例（软删除）

    Request:
        - id: 测试用例ID（必填）
    """
    try:
        body = json.loads(request.body)

        testcase_id = body.get('id')
        if not testcase_id:
            return JsonResponse({
                'code': 400,
                'message': 'id 参数不能为空'
            }, status=400)

        testcase = get_object_or_404(TestCase, id=testcase_id)
        testcase.soft_delete()

        return JsonResponse({
            'code': 200,
            'message': '删除成功'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'code': 400,
            'message': '请求格式错误'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'删除失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def batch_delete_testcase_view(request):
    """
    批量删除测试用例（软删除）

    Request:
        - ids: 测试用例ID列表（必填）
    """
    try:
        body = json.loads(request.body)

        ids = body.get('ids', [])
        if not ids or not isinstance(ids, list):
            return JsonResponse({
                'code': 400,
                'message': 'ids 参数必须是列表'
            }, status=400)

        testcases = TestCase.objects.filter(id__in=ids)
        count = testcases.count()
        testcases.update(status='deleted')

        return JsonResponse({
            'code': 200,
            'message': f'成功删除 {count} 个测试用例'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'code': 400,
            'message': '请求格式错误'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'批量删除失败: {str(e)}'
        }, status=500)
