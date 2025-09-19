import json
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from .models import Project, Doc, TestCase
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404

def project_to_dict(project):
    return {
        'id': project.id,
        'project_name': project.project_name,
        'description': project.description,
        'owner': project.owner,
        'create_time': project.create_time.strftime('%Y-%m-%d %H:%M:%S'),
        'update_time': project.update_time.strftime('%Y-%m-%d %H:%M:%S'),
        'doc_count': project.docs.count()
    }

def get_project_view(request):
    if request.method == 'GET':
        projects = Project.objects.all()
        data = [project_to_dict(p) for p in projects]
        return JsonResponse(data, safe=False)
    else:
        return HttpResponseNotAllowed(['GET'])

@csrf_exempt
@require_http_methods(['POST'])
def create_project_view(request):
    """创建项目"""
    try:
        body = json.loads(request.body)
        project_name = body.get('project_name')
        description = body.get('description', '')
        owner = body.get('owner', '')
        
        if not project_name:
            return JsonResponse({
                'code': 400,
                'message': '项目名称不能为空'
            }, status=400)
        
        # 检查项目名称是否已存在
        if Project.objects.filter(project_name=project_name).exists():
            return JsonResponse({
                'code': 400,
                'message': '项目名称已存在'
            }, status=400)
        
        project = Project.objects.create(
            project_name=project_name,
            description=description,
            owner=owner
        )
        
        return JsonResponse({
            'code': 200,
            'message': '项目创建成功',
            'data': project_to_dict(project)
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'code': 400,
            'message': '请求格式错误'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'创建项目失败: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(['POST'])
def update_project_view(request, project_id):
    """更新项目信息"""
    try:
        project = get_object_or_404(Project, id=project_id)
        body = json.loads(request.body)
        
        # 更新字段
        if 'project_name' in body:
            new_name = body['project_name']
            if new_name and new_name != project.project_name:
                # 检查新名称是否已存在
                if Project.objects.filter(project_name=new_name).exists():
                    return JsonResponse({
                        'code': 400,
                        'message': '项目名称已存在'
                    }, status=400)
                project.project_name = new_name
        
        if 'description' in body:
            project.description = body['description']
        if 'owner' in body:
            project.owner = body['owner']
        
        project.save()
        
        return JsonResponse({
            'code': 200,
            'message': '项目更新成功',
            'data': project_to_dict(project)
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'code': 400,
            'message': '请求格式错误'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'更新项目失败: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(['POST'])
def delete_project_view(request, project_id):
    """删除项目"""
    try:
        project = get_object_or_404(Project, id=project_id)
        
        # 检查项目下是否有文档
        if project.docs.exists():
            return JsonResponse({
                'code': 400,
                'message': '项目下有文档，无法删除'
            }, status=400)
        
        project.delete()
        
        return JsonResponse({
            'code': 200,
            'message': '项目删除成功'
        })
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'删除项目失败: {str(e)}'
        }, status=500)

# 文档相关函数
def doc_to_dict(doc):
    """将文档对象转换为字典"""
    return {
        'id': doc.id,
        'filename': doc.filename,
        'file_content': doc.file_content,
        'create_time': doc.create_time.strftime('%Y-%m-%d %H:%M:%S'),
        'update_time': doc.update_time.strftime('%Y-%m-%d %H:%M:%S'),
        'is_case_generated': doc.is_case_generated,
        'project_id': doc.project.id,
        'project_name': doc.project.project_name
    }

@require_http_methods(['GET'])
def get_docs_view(request):
    """获取文档列表，支持按project_id和doc_name查询"""
    try:
        project_id = request.GET.get('project_id')
        doc_name = request.GET.get('doc_name')
        
        # 构建查询条件
        query_params = {}
        
        if project_id:
            query_params['project_id'] = project_id
            
        if doc_name:
            # 支持模糊搜索文档名
            docs = Doc.objects.filter(**query_params).filter(filename__icontains=doc_name)
        else:
            docs = Doc.objects.all()
        
        data = [doc_to_dict(doc) for doc in docs]
        
        return JsonResponse({
            'code': 200,
            'message': '获取成功',
            'data': data,
            'total': len(data)
        })
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'获取文档列表失败: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(['POST'])
def upload_doc_view(request, project_id):
    """上传文档到项目"""
    try:
        project = get_object_or_404(Project, id=project_id)
        file = request.FILES.get('file')
        
        if not file:
            return JsonResponse({
                'code': 400,
                'message': '未上传文件'
            }, status=400)
        
        # 创建文档记录
        doc = Doc.objects.create(
            filename=file.name,
            file_path=file,
            project=project
        )
        
        return JsonResponse({
            'code': 200,
            'message': '文档上传成功',
            'data': doc_to_dict(doc)
        })
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'上传文档失败: {str(e)}'
        }, status=500)

@require_http_methods(['GET'])
def get_doc_detail_view(request, doc_id):
    """获取文档详情"""
    try:
        doc = get_object_or_404(Doc, id=doc_id)
        data = doc_to_dict(doc)
        
        # 获取文档内容
        if doc.file_path:
            data['content'] = doc.doc_content
        
        return JsonResponse({
            'code': 200,
            'message': '获取成功',
            'data': data
        })
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'获取文档详情失败: {str(e)}'
        }, status=500)

@csrf_exempt
@require_http_methods(['POST'])
def delete_doc_view(request, doc_id):
    """删除文档"""
    try:
        doc = get_object_or_404(Doc, id=doc_id)
        
        # 删除文件
        if doc.file_path:
            doc.file_path.delete(save=False)
        
        doc.delete()
        
        return JsonResponse({
            'code': 200,
            'message': '文档删除成功'
        })
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'删除文档失败: {str(e)}'
        }, status=500)


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
        'doc_id': testcase.doc.id,
        'doc_name': testcase.doc.filename,
        'project_id': testcase.doc.project.id,
        'project_name': testcase.doc.project.project_name,
        'created_time': testcase.created_time.strftime('%Y-%m-%d %H:%M:%S'),
        'updated_time': testcase.updated_time.strftime('%Y-%m-%d %H:%M:%S'),
    }

@require_http_methods(['GET'])
def get_testcases_view(request):
    """获取测试用例列表"""
    try:
        project_id = request.GET.get('project_id')
        doc_id = request.GET.get('doc_id')
        status = request.GET.get('status', 'active')  # 默认只显示激活状态的用例
        
        # 构建查询条件
        query_params = {}
        if doc_id:
            query_params['doc_id'] = doc_id
        elif project_id:
            # 如果指定了项目ID，查找该项目下所有文档的测试用例
            project_docs = Doc.objects.filter(project_id=project_id)
            testcases = TestCase.objects.filter(doc__in=project_docs, status=status)
        else:
            testcases = TestCase.objects.filter(status=status)
            
        if not project_id or doc_id:
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
        required_fields = ['title', 'test_steps', 'expected_result', 'doc_id']
        for field in required_fields:
            if not body.get(field):
                return JsonResponse({
                    'code': 400,
                    'message': f'{field}字段不能为空'
                }, status=400)
        
        # 验证文档是否存在
        try:
            doc = Doc.objects.get(id=body['doc_id'])
        except Doc.DoesNotExist:
            return JsonResponse({
                'code': 404,
                'message': '关联文档不存在'
            }, status=404)
        
        # 创建测试用例
        testcase = TestCase.objects.create(
            title=body['title'],
            precondition=body.get('precondition', ''),
            test_steps=body['test_steps'],
            expected_result=body['expected_result'],
            priority=body.get('priority', 'medium'),
            doc=doc
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