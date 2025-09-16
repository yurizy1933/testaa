import json
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from .models import Project, TestCase
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404

def project_to_dict(project):
    return {
        'id': project.id,
        'name': project.name,
        'desc': project.desc,
        'docContent': project.docContent
    }

def get_project_view(request):
    if request.method == 'GET':
        projects = Project.objects.all()
        data = [project_to_dict(p) for p in projects]
        return JsonResponse(data, safe=False)
    else:
        return HttpResponseNotAllowed(['GET'])

# @csrf_exempt
@require_http_methods(['POST'])
def create_project_view(request):
    body = json.loads(request.body)
    name = body.get('name')
    desc = body.get('desc', '')
    file = request.FILES.get('file')
    if not name:
        return JsonResponse({'message': '项目名称不能为空'}, status=400)
    project = Project.objects.create(name=name, desc=desc)
    if file:
        project.doc = file
        project.save()
    return JsonResponse({'message': '项目创建成功', 'id': project.id, 'data': project_to_dict(project)})

# @csrf_exempt
# def create_project_view(request):
#     if request.method == 'POST':
#         try:
#             body = json.loads(request.body)
#             name = body.get('name')
#             desc = body.get('desc', '')
#             project = Project.objects.create(name=name, desc=desc)
#             return JsonResponse({'message': '项目创建成功', 'id': project.id})
#         except Exception as e:
#             return JsonResponse({'message': f'创建项目失败: {str(e)}'}, status=400)
#     else:
#         return HttpResponseNotAllowed(['POST'])

# @csrf_exempt
@require_http_methods(['POST'])
def upload_doc_view(request, project_id):
    try:
        project = Project.objects.get(pk=project_id)
    except Project.DoesNotExist:
        return JsonResponse({'message': '项目不存在'}, status=404)
    file = request.FILES.get('file')
    if not file:
        return JsonResponse({'message': '未上传文件'}, status=400)
    project.doc = file
    project.save()
    return JsonResponse({'data': {'content': project.docContent}})

# 测试用例相关视图函数
def testcase_to_dict(testcase):
    """将测试用例对象转换为字典"""
    return {
        'id': testcase.id,
        'title': testcase.title,
        'precondition': testcase.precondition,
        'test_steps': testcase.test_steps,
        'expected_result': testcase.expected_result,
        'priority': testcase.priority,
        'priority_display': testcase.get_priority_display(),
        'status': testcase.status,
        'status_display': testcase.get_status_display(),
        'project_id': testcase.project.id,
        'project_name': testcase.project.name,
        'created_time': testcase.created_time.strftime('%Y-%m-%d %H:%M:%S'),
        'updated_time': testcase.updated_time.strftime('%Y-%m-%d %H:%M:%S'),
    }

@require_http_methods(['GET'])
def get_testcases_view(request):
    """获取测试用例列表"""
    try:
        project_id = request.GET.get('project_id')
        status = request.GET.get('status', 'active')  # 默认只显示激活状态的用例
        
        # 构建查询条件
        query_params = {}
        if project_id:
            query_params['project_id'] = project_id
        if status:
            query_params['status'] = status
        
        testcases = TestCase.objects.filter(**query_params)
        data = [testcase_to_dict(tc) for tc in testcases]
        
        return JsonResponse({
            'code': 200,
            'message': '获取成功',
            'data': data,
            'total': len(data)
        })
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'获取测试用例失败: {str(e)}'
        }, status=500)

@require_http_methods(['GET'])
def get_testcase_detail_view(request, testcase_id):
    """获取单个测试用例详情"""
    try:
        testcase = get_object_or_404(TestCase, id=testcase_id)
        data = testcase_to_dict(testcase)
        
        return JsonResponse({
            'code': 200,
            'message': '获取成功',
            'data': data
        })
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'获取测试用例详情失败: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(['POST'])
def create_testcase_view(request):
    """创建测试用例"""
    try:
        body = json.loads(request.body)
        
        # 验证必填字段
        required_fields = ['title', 'test_steps', 'expected_result', 'project_id']
        for field in required_fields:
            if not body.get(field):
                return JsonResponse({
                    'code': 400,
                    'message': f'{field}字段不能为空'
                }, status=400)
        
        # 验证项目是否存在
        try:
            project = Project.objects.get(id=body['project_id'])
        except Project.DoesNotExist:
            return JsonResponse({
                'code': 404,
                'message': '关联项目不存在'
            }, status=404)
        
        # 创建测试用例
        testcase = TestCase.objects.create(
            title=body['title'],
            precondition=body.get('precondition', ''),
            test_steps=body['test_steps'],
            expected_result=body['expected_result'],
            priority=body.get('priority', 'medium'),
            project=project
        )
        
        data = testcase_to_dict(testcase)
        
        return JsonResponse({
            'code': 200,
            'message': '测试用例创建成功',
            'data': data
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'code': 400,
            'message': '请求格式错误'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'创建测试用例失败: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(['POST'])
def update_testcase_view(request, testcase_id):
    """更新测试用例"""
    try:
        testcase = get_object_or_404(TestCase, id=testcase_id)
        body = json.loads(request.body)
        
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
            testcase.priority = body['priority']
        
        testcase.save()
        data = testcase_to_dict(testcase)
        
        return JsonResponse({
            'code': 200,
            'message': '测试用例更新成功',
            'data': data
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'code': 400,
            'message': '请求格式错误'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'更新测试用例失败: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(['POST'])
def delete_testcase_view(request, testcase_id):
    """删除测试用例（软删除）"""
    try:
        testcase = get_object_or_404(TestCase, id=testcase_id)
        
        # 执行软删除
        testcase.soft_delete()
        
        return JsonResponse({
            'code': 200,
            'message': '测试用例删除成功'
        })
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'删除测试用例失败: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(['POST'])
def restore_testcase_view(request, testcase_id):
    """恢复测试用例"""
    try:
        testcase = get_object_or_404(TestCase, id=testcase_id)
        
        # 恢复测试用例
        testcase.restore()
        data = testcase_to_dict(testcase)
        
        return JsonResponse({
            'code': 200,
            'message': '测试用例恢复成功',
            'data': data
        })
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'恢复测试用例失败: {str(e)}'
        }, status=500)