"""
测试数据管理视图层
"""

import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404
from common.models import TestData, ApiInterface

logger = logging.getLogger(__name__)


@require_http_methods(['GET'])
def get_test_data_list(request):
    """
    获取测试数据列表

    Query Parameters:
        - api_interface_id: 接口ID过滤（可选）
        - is_public: 是否公共参数过滤（可选）
        - test_name: 测试数据名称模糊搜索（可选）
        - page: 页码（可选，默认1）
        - page_size: 每页数量（可选，默认10）

    Response:
        - code: 响应码
        - message: 响应消息
        - data: 测试数据列表
        - pagination: 分页信息
    """
    try:
        # 查询参数
        api_interface_id = request.GET.get('api_interface_id')
        is_public = request.GET.get('is_public')
        test_data_name = request.GET.get('test_data_name')

        # 构建查询
        query = {}
        if api_interface_id:
            query['api_interface_id'] = api_interface_id
        if is_public is not None:
            query['is_public'] = is_public.lower() == 'true'

        test_data_list = TestData.objects.filter(**query)

        # 名称模糊搜索
        if test_data_name:
            test_data_list = test_data_list.filter(test_name__icontains=test_data_name)

        # 按创建时间倒序
        test_data_list = test_data_list.order_by('-create_time')

        # 分页
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 10))

        paginator = Paginator(test_data_list, page_size)
        page_obj = paginator.get_page(page)

        data = []
        for item in page_obj:
            data.append({
                'id': item.id,
                'test_data_name': item.test_name,
                'test_data_json': item.test_data_json,
                'description': item.description,
                'is_public': item.is_public,
                'api_interface_name': item.api_interface.api_name if item.api_interface else None,
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
        logger.error(f"获取测试数据列表失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'code': 500,
            'message': f'获取失败: {str(e)}'
        }, status=500)


@require_http_methods(['GET'])
def get_test_data_detail(request):
    """
    获取测试数据详情

    Query Parameters:
        - id: 测试数据ID（必填）

    Response:
        - code: 响应码
        - message: 响应消息
        - data: 测试数据详情
    """
    try:
        test_data_id = request.GET.get('id')

        if not test_data_id:
            return JsonResponse({
                'code': 400,
                'message': 'id 参数不能为空'
            }, status=400)

        test_data = get_object_or_404(TestData, id=test_data_id)

        return JsonResponse({
            'code': 200,
            'message': '获取成功',
            'data': {
                'id': test_data.id,
                'test_name': test_data.test_name,
                'test_data_json': test_data.test_data_json,
                'description': test_data.description,
                'is_public': test_data.is_public,
                'api_interface_id': test_data.api_interface.id if test_data.api_interface else None,
                'api_interface_name': test_data.api_interface.api_name if test_data.api_interface else None,
                'create_time': test_data.create_time.strftime('%Y-%m-%d %H:%M:%S') if test_data.create_time else None,
                'update_time': test_data.update_time.strftime('%Y-%m-%d %H:%M:%S') if test_data.update_time else None,
            }
        })

    except Exception as e:
        logger.error(f"获取测试数据详情失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'code': 500,
            'message': f'获取失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def create_test_data(request):
    """
    创建测试数据

    Request:
        - test_name: 测试数据名称（必填）
        - test_data_json: 测试数据JSON（必填）
        - description: 描述（可选）
        - is_public: 是否公共参数（可选，默认false）
        - api_interface_id: 所属接口ID（公共参数时可选）

    Response:
        - code: 响应码
        - message: 响应消息
        - data: 创建的测试数据信息
    """
    try:
        body = json.loads(request.body)

        # 验证必填字段
        required_fields = ['test_data_name', 'test_data_json']
        missing_fields = [field for field in required_fields if field not in body]
        if missing_fields:
            return JsonResponse({
                'code': 400,
                'message': f'缺少必填字段: {", ".join(missing_fields)}'
            }, status=400)

        is_public = body.get('is_public', False)
        api_interface = None
        api_interface_id = body.get('api_interface_id')

        # 如果不是公共参数，必须提供接口ID
        if not is_public and not api_interface_id:
            return JsonResponse({
                'code': 400,
                'message': '非公共参数必须提供 api_interface_id'
            }, status=400)

        # 如果提供了接口ID，验证接口是否存在
        if api_interface_id:
            api_interface = get_object_or_404(ApiInterface, id=api_interface_id)

        # 创建测试数据
        test_data = TestData.objects.create(
            test_name=body['test_data_name'],
            test_data_json=body['test_data_json'],
            description=body.get('description', ''),
            is_public=is_public,
            api_interface=api_interface
        )

        logger.info(f"创建测试数据成功: ID={test_data.id}, 名称={test_data.test_name}")

        return JsonResponse({
            'code': 200,
            'message': '创建成功',
            'data': {
                'id': test_data.id,
                'test_name': test_data.test_name
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'code': 400,
            'message': '请求格式错误'
        }, status=400)
    except Exception as e:
        logger.error(f"创建测试数据失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'code': 500,
            'message': f'创建失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def update_test_data(request):
    """
    更新测试数据

    Request:
        - id: 测试数据ID（必填）
        - test_name: 测试数据名称（可选）
        - test_data_json: 测试数据JSON（可选）
        - description: 描述（可选）
        - is_public: 是否公共参数（可选）

    Response:
        - code: 响应码
        - message: 响应消息
        - data: 更新的测试数据ID
    """
    try:
        body = json.loads(request.body)

        # 验证必填字段
        if 'id' not in body:
            return JsonResponse({
                'code': 400,
                'message': '缺少必填字段: id'
            }, status=400)

        # 获取测试数据
        test_data = get_object_or_404(TestData, id=body['id'])

        # 更新字段
        update_fields = []
        if 'test_name' in body:
            test_data.test_name = body['test_name']
            update_fields.append('test_name')
        if 'test_data_json' in body:
            test_data.test_data_json = body['test_data_json']
            update_fields.append('test_data_json')
        if 'description' in body:
            test_data.description = body['description']
            update_fields.append('description')
        if 'is_public' in body:
            test_data.is_public = body['is_public']
            update_fields.append('is_public')

        if update_fields:
            test_data.save(update_fields=update_fields)
            logger.info(f"更新测试数据成功: ID={test_data.id}, 更新字段={update_fields}")

        return JsonResponse({
            'code': 200,
            'message': '更新成功',
            'data': {
                'id': test_data.id
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'code': 400,
            'message': '请求格式错误'
        }, status=400)
    except Exception as e:
        logger.error(f"更新测试数据失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'code': 500,
            'message': f'更新失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def delete_test_data(request):
    """
    删除测试数据

    Request:
        - id: 测试数据ID（必填）

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

        # 获取并删除测试数据
        test_data = get_object_or_404(TestData, id=body['id'])
        test_name = test_data.test_name
        test_data.delete()

        logger.info(f"删除测试数据成功: ID={body['id']}, 名称={test_name}")

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
        logger.error(f"删除测试数据失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'code': 500,
            'message': f'删除失败: {str(e)}'
        }, status=500)
