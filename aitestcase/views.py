import json
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from .models import Project, Doc, TestCase, AiJobManagement, ApiDoc, ApiInterface, TestData
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.db.models import Max
from django.utils import timezone
from bs4 import BeautifulSoup
from .ai_tools import parse_html_with_ai, generate_api_test_cases

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

# @csrf_exempt
@require_http_methods(['POST'])
def update_project_view(request):
    """更新项目信息"""
    try:
        body = json.loads(request.body)
        project_id = body['project_id']
        project = get_object_or_404(Project, id=project_id)

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
def delete_project_view(request):
    """删除项目"""
    try:
        body = json.loads(request.body)
        project_id = body['project_id']
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
def upload_doc_view(request):
    """上传文档到项目"""
    try:
        project_id = request.POST['project_id']

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
def get_doc_detail_view(request):
    """获取文档详情"""
    try:
        doc_id = request.GET['id']
        doc = get_object_or_404(Doc, id=doc_id)
        data = doc_to_dict(doc)
        
        # 获取文档内容
        if doc.file_path:
            data['file_content'] = doc.doc_content
        
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
def delete_doc_view(request):
    """删除文档"""
    try:
        body = json.loads(request.body)
        doc_id = body['doc_id']
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
        # 'doc_id': testcase.doc.id,
        # 'doc_name': testcase.doc.filename,
        # 'project_id': testcase.doc.project.id,
        # 'project_name': testcase.doc.project.project_name,
        'created_time': testcase.created_time.strftime('%Y-%m-%d %H:%M:%S'),
        'updated_time': testcase.updated_time.strftime('%Y-%m-%d %H:%M:%S'),
    }

@require_http_methods(['GET'])
def get_testcases_view(request):
    """获取测试用例列表"""
    try:
        job_id = request.GET.get('job_id')
        project_id = request.GET.get('project_id')
        doc_id = request.GET.get('doc_id')
        status = request.GET.get('status', 'active')  # 默认只显示激活状态的用例
        
        # 构建查询条件
        query_params = {}
        if doc_id:
            query_params['doc_id'] = doc_id
            testcases = TestCase.objects.filter(doc_id=doc_id, job_id=job_id, status=status)
        elif project_id:
            # 如果指定了项目ID，查找该项目下所有文档的测试用例
            project_docs = Doc.objects.filter(project_id=project_id)
            testcases = TestCase.objects.filter(doc__in=project_docs, status=status)
        else:
            testcases = TestCase.objects.filter(status=status)
            
        # if not project_id or doc_id:
        #     testcases = TestCase.objects.filter(**query_params)
            
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
def get_testcase_detail_view(request):
    """获取单个测试用例详情"""
    try:
        testcase_id = request.GET.get('caseid')
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
def update_testcase_view(request):
    """更新测试用例"""
    try:
        body = json.loads(request.body)
        testcase_id = body['id']
        testcase = get_object_or_404(TestCase, id=testcase_id)
        body = json.loads(request.body)
        
        # 更新字段
        if 'name' in body:
            testcase.title = body['name']
        if 'precondition' in body:
            testcase.precondition = body['precondition']
        if 'steps' in body:
            testcase.test_steps = body['steps']
        if 'expected' in body:
            testcase.expected_result = body['expected']
        if 'level' in body:
            testcase.priority = body['level']
        
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


# AI任务管理相关视图函数
def ai_job_to_dict(ai_job):
    """将AI任务管理对象转换为字典"""
    return {
        'id': ai_job.id,
        'job_status': ai_job.job_status,
        'job_status_display': ai_job.get_job_status_display(),
        'task_start_time': ai_job.task_start_time.strftime('%Y-%m-%d %H:%M:%S') if ai_job.task_start_time else None,
        'task_complete_time': ai_job.task_complete_time.strftime('%Y-%m-%d %H:%M:%S') if ai_job.task_complete_time else None,
        'task_fail_time': ai_job.task_fail_time.strftime('%Y-%m-%d %H:%M:%S') if ai_job.task_fail_time else None,
        'doc_id': ai_job.doc.id,
        'doc_name': ai_job.doc.filename,
        'project_id': ai_job.doc.project.id,
        'project_name': ai_job.doc.project.project_name,
        'create_time': ai_job.create_time.strftime('%Y-%m-%d %H:%M:%S'),
        'update_time': ai_job.update_time.strftime('%Y-%m-%d %H:%M:%S'),
    }

@require_http_methods(['GET'])
def get_ai_jobs_view(request):
    """获取AI任务管理列表，按doc_id去重，只显示最新一条"""
    try:
        doc_name = request.GET.get('doc_name')
        project_name = request.GET.get('project_name')

        # 构建基础查询
        jobs = AiJobManagement.objects.select_related('doc', 'doc__project').all()

        # 根据doc_name和project_name过滤
        if doc_name:
            jobs = jobs.filter(doc__filename__icontains=doc_name)

        if project_name:
            jobs = jobs.filter(doc__project__project_name__icontains=project_name)

        # 按doc_id去重，只保留每个doc_id的最新一条记录
        # 方法：使用聚合查询获取每个doc_id的最大create_time，然后找到对应的记录

        # 获取每个doc_id的最大create_time
        latest_times = jobs.values('doc_id').annotate(
            latest_time=Max('create_time')
        )

        # 构建查询条件：每个doc_id对应的最大create_time的记录
        # 如果同一doc_id有多条相同最大时间的记录，取id最大的
        latest_job_ids = []
        for item in latest_times:
            doc_id = item['doc_id']
            latest_time = item['latest_time']
            # 获取该doc_id在最新时间的所有记录，然后取id最大的
            latest_job = jobs.filter(
                doc_id=doc_id,
                create_time=latest_time
            ).order_by('-id').first()
            if latest_job:
                latest_job_ids.append(latest_job.id)

        # 获取去重后的任务列表，按create_time降序排列
        result_jobs = AiJobManagement.objects.filter(
            id__in=latest_job_ids
        ).select_related('doc', 'doc__project').order_by('-create_time')

        data = [ai_job_to_dict(job) for job in result_jobs]

        return JsonResponse({
            'code': 200,
            'message': '获取成功',
            'data': data,
            'total': len(data)
        })
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'获取AI任务列表失败: {str(e)}'
        }, status=500)


def call_ai_job(ai_job):
    """
    调用AI生成测试用例的任务函数
    
    Args:
        ai_job: AiJobManagement对象
        
    Returns:
        bool: 是否成功
    """
    try:
        # 更新任务状态为处理中
        ai_job.job_status = 1
        ai_job.task_start_time = timezone.now()
        ai_job.save()
        
        # TODO: 在这里实现实际的AI调用逻辑
        # 例如：调用AI API根据文档内容生成测试用例
        doc = ai_job.doc
        doc_content = doc.doc_content
        
        # 调用AI生成测试用例
        # ... AI调用逻辑 ...
        # 这里应该调用AI API，获取返回的testcase列表
        # 示例数据格式（实际应该从AI API获取）：
        test_cases = [
            {
                'testpoint': '请假时间小于当前日期，显示错误提示"请假时间只能是今天"。', 
                'operation': '1、选择请假日期小于当前日期\n2、输入请假原因\n3、提交请假', 
                'expectedresult': '提示："请假时间只能是今天"。'
            }, 
            {
                'testpoint': '请假时间大于当前日期，显示错误提示"请假时间只能是今天"。', 
                'operation': '1、选择请假日期大于当前日期\n2、输入请假原因\n3、提交请假', 
                'expectedresult': '提示："请假时间只能是今天"。'
            }
        ]
        
        # 将获取到的testcase插入到TestCase表中
        created_count = 0
        for test_case_data in test_cases:
            try:
                TestCase.objects.create(
                    title=test_case_data.get('testpoint', ''),
                    test_steps=test_case_data.get('operation', ''),
                    expected_result=test_case_data.get('expectedresult', ''),
                    precondition='',  # 前置条件可以为空
                    priority='P2',  # 默认优先级为中等
                    status='active',  # 默认状态为激活
                    job_id=ai_job,  # 关联到当前任务
                    doc_id=doc  # 关联到文档
                )
                created_count += 1
            except Exception as e:
                # 记录单个测试用例创建失败的错误，但不中断整个流程
                print(f'创建测试用例失败 (Job ID: {ai_job.id}): {str(e)}, 数据: {test_case_data}')
        
        # 如果至少创建了一个测试用例，认为任务成功
        if created_count > 0:
            # 更新任务状态为已完成
            ai_job.job_status = 2
            ai_job.task_complete_time = timezone.now()
            ai_job.save()
            print(f'AI任务执行成功 (Job ID: {ai_job.id}): 共创建 {created_count} 个测试用例')
            return True
        else:
            # 如果没有创建任何测试用例，认为任务失败
            raise Exception('未能创建任何测试用例')
        
    except Exception as e:
        # 更新任务状态为失败
        ai_job.job_status = 0  # 或者可以添加失败状态
        ai_job.task_fail_time = timezone.now()
        ai_job.save()
        
        # 记录错误日志
        print(f'AI任务执行失败 (Job ID: {ai_job.id}): {str(e)}')
        return False


@csrf_exempt
@require_http_methods(['POST'])
def run_ai_case_job(request):
    """运行AI生成测试用例任务"""
    try:
        body = json.loads(request.body)
        doc_id = body.get('doc_id')
        
        if not doc_id:
            return JsonResponse({
                'code': 400,
                'message': 'doc_id参数不能为空'
            }, status=400)
        
        # 验证文档是否存在
        try:
            doc = Doc.objects.get(id=doc_id)
        except Doc.DoesNotExist:
            return JsonResponse({
                'code': 404,
                'message': '文档不存在'
            }, status=404)
        
        # 创建AI任务记录，默认状态为0（待处理）
        ai_job = AiJobManagement.objects.create(
            doc=doc,
            job_status=0
        )
        
        # 调用AI任务函数
        success = call_ai_job(ai_job)
        
        if success:
            return JsonResponse({
                'code': 200,
                'message': 'AI任务创建并执行成功',
                'data': ai_job_to_dict(ai_job)
            })
        else:
            return JsonResponse({
                'code': 500,
                'message': 'AI任务创建成功，但执行失败',
                'data': ai_job_to_dict(ai_job)
            }, status=500)
            
    except json.JSONDecodeError:
        return JsonResponse({
            'code': 400,
            'message': '请求格式错误'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'创建AI任务失败: {str(e)}'
        }, status=500)


# ==================== 接口文档管理相关函数 ====================

def api_doc_to_dict(api_doc):
    """将接口文档对象转换为字典"""
    return {
        'id': api_doc.id,
        'filename': api_doc.filename,
        'version': api_doc.version,
        'file_content': api_doc.file_content,
        'create_time': api_doc.create_time.strftime('%Y-%m-%d %H:%M:%S'),
        'update_time': api_doc.update_time.strftime('%Y-%m-%d %H:%M:%S'),
        'project_id': api_doc.project.id,
        'project_name': api_doc.project.project_name,
        'api_count': api_doc.api_interfaces.count()
    }


@require_http_methods(['GET'])
def get_api_docs_view(request):
    """获取接口文档列表，支持按project_id查询"""
    try:
        project_id = request.GET.get('project_id')
        doc_name = request.GET.get('doc_name')
        version = request.GET.get('version')

        # 构建查询条件
        query_params = {}

        if project_id:
            query_params['project_id'] = project_id

        docs = ApiDoc.objects.filter(**query_params)

        # 支持模糊搜索文档名
        if doc_name:
            docs = docs.filter(filename__icontains=doc_name)

        # 支持精确匹配版本号
        if version:
            docs = docs.filter(version=version)

        data = [api_doc_to_dict(doc) for doc in docs]

        return JsonResponse({
            'code': 200,
            'message': '获取成功',
            'data': data,
            'total': len(data)
        })
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'获取接口文档列表失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def upload_api_doc_view(request):
    """上传接口文档到项目"""
    try:
        project_id = request.POST.get('project_id')
        version = request.POST.get('version', '1.0.0')
        file = request.FILES.get('file')

        if not file:
            return JsonResponse({
                'code': 400,
                'message': '未上传文件'
            }, status=400)

        project = get_object_or_404(Project, id=project_id)

        # 创建接口文档记录
        api_doc = ApiDoc.objects.create(
            filename=file.name,
            version=version,
            file_path=file,
            project=project
        )

        return JsonResponse({
            'code': 200,
            'message': '接口文档上传成功',
            'data': api_doc_to_dict(api_doc)
        })
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'上传接口文档失败: {str(e)}'
        }, status=500)


@require_http_methods(['GET'])
def get_api_doc_detail_view(request):
    """获取接口文档详情"""
    try:
        doc_id = request.GET.get('id')
        api_doc = get_object_or_404(ApiDoc, id=doc_id)
        data = api_doc_to_dict(api_doc)

        # 获取文档内容
        if api_doc.file_path:
            data['file_content'] = api_doc.file_content

        return JsonResponse({
            'code': 200,
            'message': '获取成功',
            'data': data
        })
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'获取接口文档详情失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def delete_api_doc_view(request):
    """删除接口文档"""
    try:
        body = json.loads(request.body)
        doc_id = body.get('doc_id')
        api_doc = get_object_or_404(ApiDoc, id=doc_id)

        # 删除文件
        if api_doc.file_path:
            api_doc.file_path.delete(save=False)

        api_doc.delete()

        return JsonResponse({
            'code': 200,
            'message': '接口文档删除成功'
        })
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'删除接口文档失败: {str(e)}'
        }, status=500)


def api_interface_to_dict(api_interface):
    """将API接口对象转换为字典"""
    return {
        'id': api_interface.id,
        'api_name': api_interface.api_name,
        'api_path': api_interface.api_path,
        'method': api_interface.method,
        'request_params': api_interface.request_params,
        'response_params': api_interface.response_params,
        'remark': api_interface.remark,
        'create_time': api_interface.create_time.strftime('%Y-%m-%d %H:%M:%S'),
        'update_time': api_interface.update_time.strftime('%Y-%m-%d %H:%M:%S'),
        'api_doc_id': api_interface.api_doc.id,
        'api_doc_name': api_interface.api_doc.filename,
        'api_doc_version': api_interface.api_doc.version,
        'project_name': api_interface.api_doc.project.project_name
    }


@require_http_methods(['GET'])
def get_api_interfaces_view(request):
    """获取API接口列表，支持按api_doc_id、project_id查询"""
    try:
        api_doc_id = request.GET.get('api_doc_id')
        project_id = request.GET.get('project_id')
        api_name = request.GET.get('api_name')
        method = request.GET.get('method')

        # 构建查询条件
        query_params = {}

        if api_doc_id:
            query_params['api_doc_id'] = api_doc_id

        interfaces = ApiInterface.objects.filter(**query_params)

        # 如果指定了项目ID，查找该项目下所有文档的接口
        if project_id and not api_doc_id:
            project_docs = ApiDoc.objects.filter(project_id=project_id)
            interfaces = ApiInterface.objects.filter(api_doc__in=project_docs)

        # 支持模糊搜索接口名
        if api_name:
            interfaces = interfaces.filter(api_name__icontains=api_name)

        # 支持精确匹配请求方法
        if method:
            interfaces = interfaces.filter(method=method)

        data = [api_interface_to_dict(iface) for iface in interfaces]

        return JsonResponse({
            'code': 200,
            'message': '获取成功',
            'data': data,
            'total': len(data)
        })
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'获取API接口列表失败: {str(e)}'
        }, status=500)


@require_http_methods(['GET'])
def get_api_interface_detail_view(request):
    """获取单个API接口详情"""
    try:
        interface_id = request.GET.get('id')
        api_interface = get_object_or_404(ApiInterface, id=interface_id)
        data = api_interface_to_dict(api_interface)

        return JsonResponse({
            'code': 200,
            'message': '获取成功',
            'data': data
        })
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'获取API接口详情失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def parse_api_doc_view(request):
    """解析接口文档内容，提取接口信息"""
    try:
        body = json.loads(request.body)
        doc_id = body.get('doc_id')
        use_ai = body.get('use_ai', True)  # 是否使用AI解析
        ai_provider = body.get('ai_provider', 'zhipu')  # AI提供商：zhipu/deepseek

        if not doc_id:
            return JsonResponse({
                'code': 400,
                'message': 'doc_id参数不能为空'
            }, status=400)

        api_doc = get_object_or_404(ApiDoc, id=doc_id)

        # 检查是否为HTML文件
        is_html = api_doc.filename.lower().endswith('.html')

        # 获取文档内容
        doc_content = api_doc.file_content

        if not doc_content and api_doc.file_path:
            # 如果没有内容但有文件，读取文件内容
            try:
                if is_html:
                    # HTML文件以文本方式读取
                    with open(api_doc.file_path.path, 'r', encoding='utf-8') as f:
                        doc_content = f.read()
                else:
                    # 其他格式的文件以二进制方式读取（暂不支持DOC文件）
                    with open(api_doc.file_path.path, 'rb') as f:
                        doc_content = f.read().decode('utf-8', errors='ignore')

                api_doc.file_content = doc_content
                api_doc.save(update_fields=['file_content'])
            except Exception as e:
                return JsonResponse({
                    'code': 500,
                    'message': f'读取文档文件失败: {str(e)}'
                }, status=500)

        if not doc_content:
            return JsonResponse({
                'code': 400,
                'message': '文档内容为空'
            }, status=400)

        if not is_html:
            return JsonResponse({
                'code': 400,
                'message': '当前仅支持HTML格式文件的解析'
            }, status=400)

        # 解析HTML文档内容，提取接口信息
        if use_ai:
            # 使用AI解析
            interfaces_data = parse_html_with_ai(doc_content, ai_provider)
        else:
            # 使用传统解析
            interfaces_data = parse_html_doc_content(doc_content)

        # 清空该文档下已有的接口
        ApiInterface.objects.filter(api_doc=api_doc).delete()

        # 创建新的接口记录
        created_count = 0
        for interface_data in interfaces_data:
            try:
                ApiInterface.objects.create(
                    api_doc=api_doc,
                    api_name=interface_data.get('api_name', ''),
                    api_path=interface_data.get('api_path', ''),
                    method=interface_data.get('method', 'GET'),
                    request_params=interface_data.get('request_params', ''),
                    response_params=interface_data.get('response_params', ''),
                    remark=interface_data.get('remark', '')
                )
                created_count += 1
            except Exception as e:
                # 记录单个接口创建失败的错误，但不中断整个流程
                print(f'创建API接口失败 (Doc ID: {api_doc.id}): {str(e)}, 数据: {interface_data}')

        return JsonResponse({
            'code': 200,
            'message': f'接口文档解析成功，共提取 {created_count} 个接口',
            'data': {
                'doc_id': api_doc.id,
                'parsed_count': created_count,
                'interfaces': interfaces_data,
                'parse_method': 'ai' if use_ai else 'traditional'
            }
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'code': 400,
            'message': '请求格式错误'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'解析接口文档失败: {str(e)}'
        }, status=500)


def parse_html_doc_content(content):
    """
    解析HTML文档内容，提取接口信息
    支持常见的HTML格式接口文档解析
    """
    interfaces = []

    try:
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(content, 'html.parser')

        # 尝试不同的HTML结构来提取接口信息
        # 方法1: 查找表格（table）结构
        tables = soup.find_all('table')
        if tables:
            for table in tables:
                # 获取表头
                headers = []
                thead = table.find('thead')
                if thead:
                    header_rows = thead.find_all('tr')
                    if header_rows:
                        headers = [th.get_text(strip=True) for th in header_rows[0].find_all(['th', 'td'])]

                # 获取表格内容
                tbody = table.find('tbody')
                if not tbody:
                    tbody = table

                rows = tbody.find_all('tr')
                for row in rows:
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        # 尝试从表格中提取接口信息
                        interface = extract_interface_from_table_row(cells, headers)
                        # extract_interface_from_table_row已经检查了api_path，这里只需要检查interface不为None
                        if interface:
                            interfaces.append(interface)

        # 方法2: 查找列表（ul/ol）结构
        if not interfaces:
            lists = soup.find_all(['ul', 'ol'])
            for lst in lists:
                items = lst.find_all('li')
                current_interface = None
                for item in items:
                    text = item.get_text(strip=True)
                    if is_interface_start(text):
                        if current_interface:
                            # 只有有api_path的接口才添加到列表
                            if current_interface.get('api_path'):
                                interfaces.append(current_interface)
                        current_interface = create_interface_from_text(text)
                    elif current_interface:
                        update_interface_from_text(current_interface, text)

                # 添加最后一个接口，只有有api_path的接口才添加到列表
                if current_interface and current_interface.get('api_path'):
                    interfaces.append(current_interface)

        # 方法3: 查找div结构
        if not interfaces:
            divs = soup.find_all('div')
            current_interface = None
            for div in divs:
                text = div.get_text(strip=True)
                if is_interface_start(text):
                    if current_interface:
                        # 只有有api_path的接口才添加到列表
                        if current_interface.get('api_path'):
                            interfaces.append(current_interface)
                    current_interface = create_interface_from_text(text)
                elif current_interface and len(text) < 500:  # 避免太长的文本块
                    update_interface_from_text(current_interface, text)

            # 添加最后一个接口，只有有api_path的接口才添加到列表
            if current_interface and current_interface.get('api_path'):
                interfaces.append(current_interface)

    except Exception as e:
        # 如果HTML解析失败，尝试按行解析
        interfaces = parse_text_content(content)

    return interfaces


def extract_interface_from_table_row(cells, headers):
    """从表格行中提取接口信息"""
    # 如果有表头，根据表头映射
    if headers:
        interface = {
            'api_name': '',
            'api_path': '',
            'method': 'GET',
            'request_params': '',
            'response_params': '',
            'remark': ''
        }

        # 建立表头到字段的映射
        field_map = {}
        for i, header in enumerate(headers):
            if i < len(cells):
                cell_text = cells[i].get_text(strip=True)
                if '接口名' in header or '接口名称' in header:
                    interface['api_name'] = cell_text
                elif '方法' in header or 'Method' in header.lower():
                    method = cell_text.upper()
                    if method in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']:
                        interface['method'] = method
                elif '路径' in header or 'URL' in header or 'url' in header.lower():
                    interface['api_path'] = cell_text
                elif '入参' in header or '请求参数' in header or '参数' in header:
                    interface['request_params'] = cell_text
                elif '出参' in header or '响应参数' in header or '返回参数' in header:
                    interface['response_params'] = cell_text
                elif '备注' in header or '说明' in header or '描述' in header:
                    interface['remark'] = cell_text

        # 如果没有明确的表头，尝试根据内容推断
        if not interface['api_name'] and len(cells) >= 1:
            interface['api_name'] = cells[0].get_text(strip=True)

        # 必须有api_path才认为是有效接口
        return interface if interface['api_name'] and interface['api_path'] else None

    # 如果没有表头，假设第一列是接口名
    if len(cells) >= 1:
        interface = {
            'api_name': cells[0].get_text(strip=True),
            'api_path': cells[1].get_text(strip=True) if len(cells) > 1 else '',
            'method': 'GET',
            'request_params': '',
            'response_params': '',
            'remark': ''
        }
        # 必须有api_path才认为是有效接口
        return interface if interface['api_name'] and interface['api_path'] else None

    return None


def is_interface_start(text):
    """判断是否是接口定义的开始"""
    keywords = ['接口名称', '接口名', 'API', 'api']
    return any(keyword in text for keyword in keywords)


def create_interface_from_text(text):
    """从文本创建接口对象"""
    interface = {
        'api_name': '',
        'api_path': '',
        'method': 'GET',
        'request_params': '',
        'response_params': '',
        'remark': ''
    }

    # 尝试提取接口名
    if '：' in text:
        parts = text.split('：')
        if len(parts) >= 2:
            interface['api_name'] = parts[-1].strip()
    elif ':' in text:
        parts = text.split(':')
        if len(parts) >= 2:
            interface['api_name'] = parts[-1].strip()
    else:
        interface['api_name'] = text

    # 检查是否包含请求方法
    methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
    for method in methods:
        if method in text.upper():
            interface['method'] = method
            break

    # 尝试提取路径
    if '/' in text:
        path_part = text.split('/')[-1].strip()
        if path_part:
            interface['api_path'] = '/' + path_part

    return interface


def update_interface_from_text(interface, text):
    """根据文本更新接口信息"""
    if '请求方法' in text or 'Method' in text or 'method' in text:
        method = text.split('：')[-1].split(':')[-1].strip().upper()
        methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
        if method in methods:
            interface['method'] = method
    elif '接口路径' in text or '路径' in text or 'URL' in text or 'url' in text:
        path = text.split('：')[-1].split(':')[-1].strip()
        interface['api_path'] = path
    elif '入参' in text or '请求参数' in text or '参数' in text:
        params = text.split('：')[-1].split(':')[-1].strip()
        interface['request_params'] = params
    elif '出参' in text or '响应参数' in text or '返回参数' in text:
        params = text.split('：')[-1].split(':')[-1].strip()
        interface['response_params'] = params
    elif '备注' in text or '说明' in text or '描述' in text:
        remark = text.split('：')[-1].split(':')[-1].strip()
        interface['remark'] = remark


def parse_text_content(content):
    """将内容按行解析（作为HTML解析的备选方案）"""
    interfaces = []
    lines = content.split('\n')

    current_interface = None

    for line in lines:
        line = line.strip()

        # 跳过空行
        if not line:
            continue

        # 尝试识别接口定义
        if is_interface_start(line):
            if current_interface:
                # 只有有api_path的接口才添加到列表
                if current_interface.get('api_path'):
                    interfaces.append(current_interface)
            current_interface = create_interface_from_text(line)

        elif current_interface:
            update_interface_from_text(current_interface, line)

    # 添加最后一个接口，只有有api_path的接口才添加到列表
    if current_interface and current_interface.get('api_path'):
        interfaces.append(current_interface)

    return interfaces


# def parse_html_with_ai(content, ai_provider='zhipu'):
#     """
#     使用AI来解析HTML文档内容，提取接口信息
#     支持智谱AI和DeepSeek
#
#     Args:
#         content: HTML文档内容
#         ai_provider: AI提供商，'zhipu' 或 'deepseek'
#
#     Returns:
#         list: 接口信息列表
#     """
#     try:
#         # 限制内容长度，避免超出AI的token限制
#         max_length = 8000
#         if len(content) > max_length:
#             content = content[:max_length] + "...[内容已截断]"
#
#         # 构造AI提示词
#         prompt = f"""
# 请分析以下HTML文档内容，提取其中的API接口信息。
#
# HTML内容：
# {content}
#
# 请以JSON格式返回所有接口信息，每个接口包含以下字段：
# - api_name: 接口名称
# - api_path: 接口路径（必填字段，必须提供）
# - method: 请求方法（GET/POST/PUT/DELETE等）
# - request_params: 入参说明
# - response_params: 出参说明
# - remark: 备注（如果有）
#
# 重要要求：
# 前置判断：文档有效性验证
# 在开始解析前，请首先执行以下验证：
#
#  判断标准
# 如果HTML文档中同时缺失以下两类信息，则判定为非API文档：
# 路径信息：如 /api/xxx、/v1/xxx、/rest/xxx 等URL路径
# 方法信息：如 GET、POST、PUT、DELETE 等HTTP方法
#
# 返回格式示例：
# [
#   {{
#     "api_name": "用户登录接口",
#     "api_path": "/api/login",
#     "method": "POST",
#     "request_params": {{"username": "用户名", "password": "密码"}},
#     "response_params": {{"token": "登录令牌", "user_id": "用户ID"}},
#     "remark": "用户登录验证"
#   }}
# ]
#
# 请只返回JSON格式的数组，不要包含其他说明文字。
# """
#
#         interfaces = []
#
#         if ai_provider == 'zhipu':
#             # 使用智谱AI解析
#             client = ZhipuAI(api_key="4198d249d529406f8b9571bc10aa2142.Qvg8SQRV9GiKweid")
#             response = client.chat.completions.create(
#                 model="glm-4",
#                 messages=[
#                     {"role": "system", "content": "你是一个专业的API文档解析助手，擅长从HTML文档中提取接口信息。重要：请只关注表格中的信息"},
#                     {"role": "user", "content": prompt}
#                 ],
#                 response_format={'type': 'json_object'}
#             )
#
#             # 解析AI返回的JSON结果
#             result_text = response.choices[0].message.content
#             print(result_text)
#             interfaces = parse_ai_response(result_text)
#
#         return interfaces
#
#     except Exception as e:
#         print(f'AI解析HTML失败: {str(e)}')
#         # 如果AI解析失败，降级到传统解析
#         return parse_html_doc_content(content)
#
#
# def parse_ai_response(response_text):
#     """
#     解析AI返回的响应文本，提取接口信息
#
#     Args:
#         response_text: AI返回的文本
#
#     Returns:
#         list: 接口信息列表
#     """
#     try:
#         # 尝试直接解析JSON
#         data = json.loads(response_text)
#
#         # 如果返回的是对象，检查是否有特定的字段
#         if isinstance(data, dict):
#             # 检查常见的字段名
#             if 'interfaces' in data:
#                 interfaces = data['interfaces']
#             elif 'data' in data:
#                 interfaces = data['data']
#             elif 'results' in data:
#                 interfaces = data['results']
#             elif 'api_list' in data:
#                 interfaces = data['api_list']
#             elif 'apis' in data:
#                 interfaces = data['apis']
#             else:
#                 # 如果没有找到特定字段，尝试将整个对象作为单个接口
#                 if 'api_name' in data or 'api_path' in data:
#                     interfaces = [data]
#                 else:
#                     interfaces = []
#
#             # 过滤掉没有api_path的接口
#             return [iface for iface in interfaces if isinstance(iface, dict) and iface.get('api_path')]
#
#         # 如果是数组，直接返回（但需要过滤没有api_path的接口）
#         elif isinstance(data, list):
#             return [iface for iface in data if isinstance(iface, dict) and iface.get('api_path')]
#
#         return []
#
#     except json.JSONDecodeError:
#         # 如果直接解析失败，尝试提取JSON部分
#         try:
#             # 尝试从文本中提取JSON部分
#             import re
#             json_pattern = r'\[.*?\]'
#             matches = re.findall(json_pattern, response_text, re.DOTALL)
#             for match in matches:
#                 try:
#                     data = json.loads(match)
#                     if isinstance(data, list):
#                         # 过滤掉没有api_path的接口
#                         return [iface for iface in data if isinstance(iface, dict) and iface.get('api_path')]
#                 except:
#                     continue
#
#             return []
#         except Exception:
#             return []


# ==================== 测试数据管理相关函数 ====================

def test_data_to_dict(test_data):
    """将测试数据对象转换为字典"""
    return {
        'id': test_data.id,
        'test_name': test_data.test_name,
        'test_data_json': test_data.test_data_json,
        'description': test_data.description,
        'create_time': test_data.create_time.strftime('%Y-%m-%d %H:%M:%S'),
        'update_time': test_data.update_time.strftime('%Y-%m-%d %H:%M:%S'),
        'api_interface_id': test_data.api_interface.id,
        'api_name': test_data.api_interface.api_name,
        'api_path': test_data.api_interface.api_path,
        'method': test_data.api_interface.method,
        'project_name': test_data.api_interface.api_doc.project.project_name,
        'api_doc_id': test_data.api_interface.api_doc.id,
        'api_doc_name': test_data.api_interface.api_doc.filename
    }


@require_http_methods(['GET'])
def get_test_data_view(request):
    """获取测试数据列表，支持按api_interface_id、project_id、api_doc_id查询"""
    try:
        api_interface_id = request.GET.get('api_interface_id')
        project_id = request.GET.get('project_id')
        api_doc_id = request.GET.get('api_doc_id')
        test_name = request.GET.get('test_name')

        # 构建查询条件
        query_params = {}

        if api_interface_id:
            query_params['api_interface_id'] = api_interface_id

        test_data_list = TestData.objects.filter(**query_params)

        # 如果指定了api_doc_id，查找该文档下所有接口的测试数据
        if api_doc_id and not api_interface_id:
            interface_ids = ApiInterface.objects.filter(api_doc_id=api_doc_id).values_list('id', flat=True)
            test_data_list = test_data_list.filter(api_interface_id__in=interface_ids)

        # 如果指定了project_id，查找该项目下所有文档接口的测试数据
        if project_id and not api_interface_id and not api_doc_id:
            doc_ids = ApiDoc.objects.filter(project_id=project_id).values_list('id', flat=True)
            interface_ids = ApiInterface.objects.filter(api_doc_id__in=doc_ids).values_list('id', flat=True)
            test_data_list = test_data_list.filter(api_interface_id__in=interface_ids)

        # 支持模糊搜索测试数据名称
        if test_name:
            test_data_list = test_data_list.filter(test_name__icontains=test_name)

        data = [test_data_to_dict(td) for td in test_data_list]

        return JsonResponse({
            'code': 200,
            'message': '获取成功',
            'data': data,
            'total': len(data)
        })
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'获取测试数据列表失败: {str(e)}'
        }, status=500)


@require_http_methods(['GET'])
def get_test_data_detail_view(request):
    """获取单个测试数据详情"""
    try:
        test_data_id = request.GET.get('id')
        test_data = get_object_or_404(TestData, id=test_data_id)
        data = test_data_to_dict(test_data)

        return JsonResponse({
            'code': 200,
            'message': '获取成功',
            'data': data
        })
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'获取测试数据详情失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def create_test_data_view(request):
    """创建测试数据"""
    try:
        body = json.loads(request.body)

        # 验证必填字段
        required_fields = ['test_data_json', 'api_interface_id']
        for field in required_fields:
            if not body.get(field):
                return JsonResponse({
                    'code': 400,
                    'message': f'{field}字段不能为空'
                }, status=400)

        # 验证API接口是否存在
        try:
            api_interface = ApiInterface.objects.get(id=body['api_interface_id'])
        except ApiInterface.DoesNotExist:
            return JsonResponse({
                'code': 404,
                'message': '关联的API接口不存在'
            }, status=404)

        # 创建测试数据
        test_data = TestData.objects.create(
            test_name=body['test_name'],
            test_data_json=body['test_data_json'],
            description=body.get('description', ''),
            api_interface=api_interface
        )

        data = test_data_to_dict(test_data)

        return JsonResponse({
            'code': 200,
            'message': '测试数据创建成功',
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
            'message': f'创建测试数据失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def update_test_data_view(request):
    """更新测试数据"""
    try:
        body = json.loads(request.body)
        test_data_id = body.get('id')
        test_data = get_object_or_404(TestData, id=test_data_id)

        # 更新字段
        if 'test_name' in body:
            test_data.test_name = body['test_name']
        if 'test_data_json' in body:
            test_data.test_data_json = body['test_data_json']
        if 'description' in body:
            test_data.description = body['description']

        # 如果更新了API接口，验证接口是否存在
        if 'api_interface_id' in body:
            try:
                api_interface = ApiInterface.objects.get(id=body['api_interface_id'])
                test_data.api_interface = api_interface
            except ApiInterface.DoesNotExist:
                return JsonResponse({
                    'code': 404,
                    'message': '关联的API接口不存在'
                }, status=404)

        test_data.save()
        data = test_data_to_dict(test_data)

        return JsonResponse({
            'code': 200,
            'message': '测试数据更新成功',
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
            'message': f'更新测试数据失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def delete_test_data_view(request):
    """删除测试数据"""
    try:
        body = json.loads(request.body)
        test_data_id = body.get('test_data_id')
        test_data = get_object_or_404(TestData, id=test_data_id)

        test_data.delete()

        return JsonResponse({
            'code': 200,
            'message': '测试数据删除成功'
        })
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'删除测试数据失败: {str(e)}'
        }, status=500)


# ==================== AI生成API测试用例相关函数 ====================

@csrf_exempt
@require_http_methods(['POST'])
def generate_api_test_cases_view(request):
    """使用AI生成API接口测试用例"""
    try:
        body = json.loads(request.body)

        # 验证必填字段
        api_interface_id = body.get('api_interface_id')
        if not api_interface_id:
            return JsonResponse({
                'code': 400,
                'message': 'api_interface_id参数不能为空'
            }, status=400)

        # 验证API接口是否存在
        try:
            api_interface = ApiInterface.objects.get(id=api_interface_id)
        except ApiInterface.DoesNotExist:
            return JsonResponse({
                'code': 404,
                'message': 'API接口不存在'
            }, status=404)

        # 可选参数
        ai_provider = body.get('ai_provider', 'zhipu')  # 默认使用智谱AI
        test_data_id = body.get('test_data_id')  # 可选的测试数据ID

        # 如果提供了测试数据ID，获取测试数据
        test_data = None
        if test_data_id:
            try:
                test_data = TestData.objects.get(id=test_data_id)
            except TestData.DoesNotExist:
                pass  # 测试数据不存在也可以，不影响生成测试用例

        # 调用AI生成测试用例
        result = generate_api_test_cases(api_interface, ai_provider, test_data)

        # 检查是否生成成功
        if 'error' in result:
            return JsonResponse({
                'code': 500,
                'message': f'生成测试用例失败: {result["error"]}',
                'data': result
            }, status=500)

        # 返回生成的测试用例
        test_cases = result.get('test_cases', [])

        return JsonResponse({
            'code': 200,
            'message': f'成功生成 {len(test_cases)} 个测试用例',
            'data': {
                'api_interface_id': api_interface.id,
                'api_name': api_interface.api_name,
                'api_path': api_interface.api_path,
                'method': api_interface.method,
                'ai_provider': ai_provider,
                'test_cases_count': len(test_cases),
                'test_cases': test_cases
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'code': 400,
            'message': '请求格式错误'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'生成API测试用例失败: {str(e)}'
        }, status=500)
    except Exception:
        return []