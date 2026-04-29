"""
API接口管理视图层
"""

import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from common.models import ApiInterface

logger = logging.getLogger(__name__)


@require_http_methods(['GET'])
def get_api_interface_list(request):
    """
    获取API接口列表

    Query Parameters:
        - api_doc_id: 所属文档ID过滤（可选）
        - method: 请求方法过滤（可选）
        - api_name: 接口名称模糊搜索（可选）
        - page: 页码（可选，默认1）
        - page_size: 每页数量（可选，默认10）

    Response:
        - code: 响应码
        - message: 响应消息
        - data: API接口列表
        - pagination: 分页信息
    """
    try:
        # 查询参数
        api_doc_id = request.GET.get('api_doc_id')
        method = request.GET.get('method')
        api_name = request.GET.get('api_name')

        # 构建查询
        query = {}
        if api_doc_id:
            query['api_doc_id'] = api_doc_id
        if method:
            query['method'] = method

        api_interface_list = ApiInterface.objects.filter(**query)

        # 名称模糊搜索
        if api_name:
            api_interface_list = api_interface_list.filter(api_name__icontains=api_name)

        # 按创建时间倒序
        api_interface_list = api_interface_list.order_by('-create_time')

        # 分页
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))

        paginator = Paginator(api_interface_list, page_size)
        page_obj = paginator.get_page(page)

        data = []
        for item in page_obj:
            data.append({
                'id': item.id,
                'api_name': item.api_name,
                'api_path': item.api_path,
                'method': item.method,
                'request_params': item.request_params,
                'response_params': item.response_params,
                'remark': item.remark,
                'api_doc_id': item.api_doc.id if item.api_doc else None,
                'api_doc_filename': item.api_doc.filename if item.api_doc else None,
                'create_time': item.create_time.strftime('%Y-%m-%d %H:%M:%S') if item.create_time else None,
                'update_time': item.update_time.strftime('%Y-%m-%d %H:%M:%S') if item.update_time else None,
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
        logger.error(f"获取API接口列表失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'code': 500,
            'message': f'获取失败: {str(e)}'
        }, status=500)


@require_http_methods(['GET'])
def get_api_interface_detail(request):
    """
    获取API接口详情

    Query Parameters:
        - id: API接口ID（必填）

    Response:
        - code: 响应码
        - message: 响应消息
        - data: API接口详情
    """
    try:
        api_interface_id = request.GET.get('id')

        if not api_interface_id:
            return JsonResponse({
                'code': 400,
                'message': 'id 参数不能为空'
            }, status=400)

        api_interface = get_object_or_404(ApiInterface, id=api_interface_id)

        return JsonResponse({
            'code': 200,
            'message': '获取成功',
            'data': {
                'id': api_interface.id,
                'api_name': api_interface.api_name,
                'api_path': api_interface.api_path,
                'method': api_interface.method,
                'request_params': api_interface.request_params,
                'response_params': api_interface.response_params,
                'remark': api_interface.remark,
                'api_doc_id': api_interface.api_doc.id if api_interface.api_doc else None,
                'api_doc_filename': api_interface.api_doc.filename if api_interface.api_doc else None,
                'create_time': api_interface.create_time.strftime('%Y-%m-%d %H:%M:%S') if api_interface.create_time else None,
                'update_time': api_interface.update_time.strftime('%Y-%m-%d %H:%M:%S') if api_interface.update_time else None,
            }
        })

    except Exception as e:
        logger.error(f"获取API接口详情失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'code': 500,
            'message': f'获取失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def create_api_interface(request):
    """
    创建API接口

    Request:
        - api_name: 接口名称（必填）
        - api_path: 接口路径（可选）
        - method: 请求方法（必填，GET/POST/PUT/DELETE/PATCH/HEAD/OPTIONS）
        - request_params: 入参（可选）
        - response_params: 出参（可选）
        - remark: 备注（可选）
        - api_doc_id: 所属文档ID（必填）

    Response:
        - code: 响应码
        - message: 响应消息
        - data: 创建的API接口信息
    """
    try:
        body = json.loads(request.body)

        # 验证必填字段
        required_fields = ['api_name', 'method', 'api_doc_id']
        missing_fields = [field for field in required_fields if field not in body]
        if missing_fields:
            return JsonResponse({
                'code': 400,
                'message': f'缺少必填字段: {", ".join(missing_fields)}'
            }, status=400)

        # 验证请求方法
        valid_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
        if body['method'] not in valid_methods:
            return JsonResponse({
                'code': 400,
                'message': f'无效的请求方法，必须是: {", ".join(valid_methods)}'
            }, status=400)

        # 验证文档是否存在
        from common.models import ApiDoc
        api_doc = get_object_or_404(ApiDoc, id=body['api_doc_id'])

        # 创建API接口
        api_interface = ApiInterface.objects.create(
            api_name=body['api_name'],
            api_path=body.get('api_path', ''),
            method=body['method'],
            request_params=body.get('request_params', ''),
            response_params=body.get('response_params', ''),
            remark=body.get('remark', ''),
            api_doc=api_doc
        )

        logger.info(f"创建API接口成功: ID={api_interface.id}, 名称={api_interface.api_name}")

        return JsonResponse({
            'code': 200,
            'message': '创建成功',
            'data': {
                'id': api_interface.id,
                'api_name': api_interface.api_name
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'code': 400,
            'message': '请求格式错误'
        }, status=400)
    except Exception as e:
        logger.error(f"创建API接口失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'code': 500,
            'message': f'创建失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def update_api_interface(request):
    """
    更新API接口

    Request:
        - id: API接口ID（必填）
        - api_name: 接口名称（可选）
        - api_path: 接口路径（可选）
        - method: 请求方法（可选）
        - request_params: 入参（可选）
        - response_params: 出参（可选）
        - remark: 备注（可选）

    Response:
        - code: 响应码
        - message: 响应消息
        - data: 更新的API接口ID
    """
    try:
        body = json.loads(request.body)

        # 验证必填字段
        if 'id' not in body:
            return JsonResponse({
                'code': 400,
                'message': '缺少必填字段: id'
            }, status=400)

        # 获取API接口
        api_interface = get_object_or_404(ApiInterface, id=body['id'])

        # 更新字段
        update_fields = []
        if 'api_name' in body:
            api_interface.api_name = body['api_name']
            update_fields.append('api_name')
        if 'api_path' in body:
            api_interface.api_path = body['api_path']
            update_fields.append('api_path')
        if 'method' in body:
            # 验证请求方法
            valid_methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
            if body['method'] not in valid_methods:
                return JsonResponse({
                    'code': 400,
                    'message': f'无效的请求方法，必须是: {", ".join(valid_methods)}'
                }, status=400)
            api_interface.method = body['method']
            update_fields.append('method')
        if 'request_params' in body:
            api_interface.request_params = body['request_params']
            update_fields.append('request_params')
        if 'response_params' in body:
            api_interface.response_params = body['response_params']
            update_fields.append('response_params')
        if 'remark' in body:
            api_interface.remark = body['remark']
            update_fields.append('remark')

        if update_fields:
            api_interface.save(update_fields=update_fields)
            logger.info(f"更新API接口成功: ID={api_interface.id}, 更新字段={update_fields}")

        return JsonResponse({
            'code': 200,
            'message': '更新成功',
            'data': {
                'id': api_interface.id
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'code': 400,
            'message': '请求格式错误'
        }, status=400)
    except Exception as e:
        logger.error(f"更新API接口失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'code': 500,
            'message': f'更新失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def delete_api_interface(request):
    """
    删除API接口

    Request:
        - id: API接口ID（必填）

    Response:
        - code: 响应码
        - message: 响应消息
        - data: 空对象
    """
    try:
        body = json.loads(request.body)

        # 验证必填字段
        if 'id' not in body:
            return JsonResponse({
                'code': 400,
                'message': '缺少必填字段: id'
            }, status=400)

        # 获取并删除API接口
        api_interface = get_object_or_404(ApiInterface, id=body['id'])
        api_name = api_interface.api_name
        api_interface.delete()

        logger.info(f"删除API接口成功: ID={body['id']}, 名称={api_name}")

        return JsonResponse({
            'code': 200,
            'message': '删除成功',
            'data': {}
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'code': 400,
            'message': '请求格式错误'
        }, status=400)
    except Exception as e:
        logger.error(f"删除API接口失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'code': 500,
            'message': f'删除失败: {str(e)}'
        }, status=500)
