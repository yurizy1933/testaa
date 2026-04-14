import json
from django.http import JsonResponse, HttpResponseNotAllowed, FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import get_object_or_404
from .models import Project, CommonDoc


def project_to_dict(project):
    """将Project对象转换为字典"""
    return {
        'id': project.id,
        'project_name': project.project_name,
        'description': project.description,
        'owner': project.owner,
        'create_time': project.create_time.strftime('%Y-%m-%d %H:%M:%S'),
        'update_time': project.update_time.strftime('%Y-%m-%d %H:%M:%S')
    }


def get_project_view(request):
    """获取项目列表"""
    if request.method == 'GET':
        projects = Project.objects.all()
        data = [project_to_dict(p) for p in projects]
        return JsonResponse(data, safe=False)
    else:
        return HttpResponseNotAllowed(['GET'])


@require_http_methods(['GET'])
def get_project_detail_view(request):
    """获取项目详情"""
    try:
        project_id = request.GET.get('id')
        if not project_id:
            return JsonResponse({
                'code': 400,
                'message': '项目ID不能为空'
            }, status=400)

        project = get_object_or_404(Project, id=project_id)

        return JsonResponse({
            'code': 200,
            'message': '获取成功',
            'data': project_to_dict(project)
        })
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'获取项目详情失败: {str(e)}'
        }, status=500)


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


@require_http_methods(['POST'])
def update_project_view(request):
    """更新项目信息"""
    try:
        body = json.loads(request.body)
        project_id = body.get('project_id')
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
        project_id = body.get('project_id')
        project = get_object_or_404(Project, id=project_id)

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


# ==================== 统一文档管理视图 ====================

def doc_to_dict(doc):
    """将CommonDoc对象转换为字典（不包含内容）"""
    return {
        'id': doc.id,
        'doc_type': doc.doc_type,
        'doc_type_display': doc.get_doc_type_display(),
        'file_type': doc.file_type,
        'file_type_display': doc.get_file_type_display(),
        'filename': doc.filename,
        'version': doc.version,
        'is_processed': doc.is_processed,
        'create_time': doc.create_time.strftime('%Y-%m-%d %H:%M:%S'),
        'update_time': doc.update_time.strftime('%Y-%m-%d %H:%M:%S'),
        'project_id': doc.project.id,
        'project_name': doc.project.project_name
    }


@require_http_methods(['GET'])
def get_docs_view(request):
    """获取文档列表（不返回内容），支持按project_id、doc_type、file_type查询"""
    try:
        project_id = request.GET.get('project_id')
        doc_type = request.GET.get('doc_type')
        file_type = request.GET.get('file_type')
        filename = request.GET.get('filename')
        version = request.GET.get('version')

        # 构建查询条件
        query_params = {}

        if project_id:
            query_params['project_id'] = project_id
        if doc_type:
            query_params['doc_type'] = doc_type
        if file_type:
            query_params['file_type'] = file_type

        # 使用 select_related 优化查询，避免 N+1 问题
        # 使用 only() 只选择必要字段，避免加载大字段 file_content
        docs = (CommonDoc.objects
                .filter(**query_params)
                .select_related('project')
                .only('id', 'doc_type', 'file_type', 'filename', 'version',
                      'is_processed', 'create_time', 'update_time', 'project'))

        # 支持模糊搜索文件名
        if filename:
            docs = docs.filter(filename__icontains=filename)

        # 支持精确匹配版本号
        if version:
            docs = docs.filter(version=version)

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


@require_http_methods(['GET'])
def get_doc_detail_view(request):
    """获取文档详情（包含内容）"""
    try:
        doc_id = request.GET.get('id')
        if not doc_id:
            return JsonResponse({
                'code': 400,
                'message': '缺少文档ID'
            }, status=400)

        doc = get_object_or_404(CommonDoc, id=doc_id)
        data = doc_to_dict(doc)

        # 如果内容为空，尝试从文件解析
        if not doc.file_content and doc.file_path:
            data['file_content'] = doc.doc_content
        else:
            data['file_content'] = doc.file_content

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
def upload_doc_view(request):
    """上传文档到项目"""
    try:
        project_id = request.POST.get('project_id')
        doc_type = request.POST.get('doc_type')
        file_type = request.POST.get('file_type')
        version = request.POST.get('version', '1.0.0')
        file = request.FILES.get('file')

        if not file:
            return JsonResponse({
                'code': 400,
                'message': '未上传文件'
            }, status=400)

        if not project_id:
            return JsonResponse({
                'code': 400,
                'message': '缺少项目ID'
            }, status=400)

        if not doc_type:
            return JsonResponse({
                'code': 400,
                'message': '缺少文档类型（doc_type）'
            }, status=400)

        # 如果没有提供 file_type，从文件名中提取
        if not file_type:
            filename = file.name.lower()
            if filename.endswith('.docx'):
                file_type = 'docx'
            elif filename.endswith('.doc'):
                file_type = 'doc'
            elif filename.endswith('.xlsx'):
                file_type = 'xlsx'
            elif filename.endswith('.xls'):
                file_type = 'xls'
            elif filename.endswith('.html'):
                file_type = 'html'
            elif filename.endswith('.htm'):
                file_type = 'htm'
            elif filename.endswith('.pdf'):
                file_type = 'pdf'
            elif filename.endswith('.md'):
                file_type = 'md'
            elif filename.endswith('.txt'):
                file_type = 'txt'
            else:
                return JsonResponse({
                    'code': 400,
                    'message': '无法识别文件类型，请手动指定 file_type'
                }, status=400)

        project = get_object_or_404(Project, id=project_id)

        # 创建文档记录
        doc = CommonDoc.objects.create(
            doc_type=doc_type,
            file_type=file_type,
            filename=file.name,
            version=version,
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


@csrf_exempt
@require_http_methods(['POST'])
def delete_doc_view(request):
    """删除文档"""
    try:
        body = json.loads(request.body)
        doc_id = body.get('doc_id')
        if not doc_id:
            return JsonResponse({
                'code': 400,
                'message': '缺少文档ID'
            }, status=400)

        doc = get_object_or_404(CommonDoc, id=doc_id)

        # 删除文件
        if doc.file_path:
            try:
                doc.file_path.delete(save=False)
            except Exception as e:
                # 文件删除失败不影响记录删除
                pass

        # 删除记录
        doc.delete()

        return JsonResponse({
            'code': 200,
            'message': '文档删除成功'
        })
    except json.JSONDecodeError:
        return JsonResponse({
            'code': 400,
            'message': '请求格式错误'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'删除文档失败: {str(e)}'
        }, status=500)


@require_http_methods(['GET'])
def download_doc_view(request):
    """下载文档"""
    try:
        doc_id = request.GET.get('id')
        if not doc_id:
            return JsonResponse({
                'code': 400,
                'message': '缺少文档ID'
            }, status=400)

        doc = get_object_or_404(CommonDoc, id=doc_id)

        if not doc.file_path:
            return JsonResponse({
                'code': 404,
                'message': '文件不存在'
            }, status=404)

        # 返回文件
        response = FileResponse(doc.file_path.open('rb'))
        response['Content-Disposition'] = f'attachment; filename="{doc.filename}"'
        return response

    except Exception as e:
        return JsonResponse({
            'code': 500,
            'message': f'下载文档失败: {str(e)}'
        }, status=500)
