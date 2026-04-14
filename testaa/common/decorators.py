"""
装饰器模块
"""

from functools import wraps
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)


def json_response(func):
    """
    统一JSON响应装饰器
    自动捕获异常并返回JSON格式的错误响应
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            # 如果返回值已经是JsonResponse，直接返回
            if isinstance(result, JsonResponse):
                return result

            # 如果返回的是dict，包装成成功的JSON响应
            if isinstance(result, dict):
                return JsonResponse({
                    'code': 200,
                    'message': '操作成功',
                    'data': result
                })

            # 其他情况，直接返回
            return result

        except Exception as e:
            logger.error(f"Error in {func.__name__}: {str(e)}", exc_info=True)
            return JsonResponse({
                'code': 500,
                'message': f'操作失败: {str(e)}'
            }, status=500)

    return wrapper


def log_execution(func):
    """
    日志记录装饰器
    记录函数的执行时间和参数
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"Executing {func.__name__} with args={args}, kwargs={kwargs}")

        import time
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"Finished {func.__name__} in {execution_time:.2f}s")
            return result

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Failed {func.__name__} after {execution_time:.2f}s: {str(e)}", exc_info=True)
            raise

    return wrapper
