import json
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from .models import Project, Doc, TestCase, AiJobManagement
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from django.db.models import Max
from django.utils import timezone

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