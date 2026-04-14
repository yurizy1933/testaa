"""
AI兼容层 - 提供与旧ai_tools.py的兼容接口
保持向后兼容性，让现有代码可以平滑过渡到新架构
"""

from .core.manager import AIManager
from .prompts.html_parser import HTMLParserPrompt
from .prompts.test_case import TestCaseGeneratorPrompt
from .prompts.api_test import APITestCaseGeneratorPrompt
from .core.config import get_config


# ==================== 配置兼容 ====================

def set_api_keys(zhipu_key=None, deepseek_key=None, openai_key=None):
    """
    设置API密钥（兼容旧接口）

    Args:
        zhipu_key: 智谱AI密钥
        deepseek_key: DeepSeek密钥
        openai_key: OpenAI密钥
    """
    config = get_config()

    if zhipu_key:
        config.api_keys['zhipu'] = zhipu_key
    if deepseek_key:
        config.api_keys['deepseek'] = deepseek_key
    if openai_key:
        config.api_keys['openai'] = openai_key


def get_api_keys():
    """
    获取所有API密钥（兼容旧接口）

    Returns:
        dict: API密钥字典
    """
    config = get_config()
    return config.api_keys


# ==================== HTML解析功能兼容 ====================

def parse_html_with_ai(content, ai_provider='zhipu'):
    """
    使用AI来解析HTML文档内容，提取接口信息（兼容旧接口）

    Args:
        content: HTML文档内容
        ai_provider: AI提供商，'zhipu' 或 'deepseek'

    Returns:
        list: 接口信息列表
    """
    try:
        manager = AIManager(provider_name=ai_provider)

        system_prompt = HTMLParserPrompt.get_system_prompt()
        user_prompt = HTMLParserPrompt.get_user_prompt(content)

        response = manager.call_with_prompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=(ai_provider == 'zhipu'),  # 智谱AI支持JSON模式
            use_cache=True
        )

        return HTMLParserPrompt.parse_response(response.content)

    except Exception as e:
        print(f'AI解析HTML失败: {str(e)}')
        return []


def parse_ai_response(response_text):
    """
    解析AI返回的响应文本，提取接口信息（兼容旧接口）

    Args:
        response_text: AI返回的文本

    Returns:
        list: 接口信息列表
    """
    return HTMLParserPrompt.parse_response(response_text)


# ==================== 文档测试用例生成功能兼容 ====================

def call_ai_job(ai_job, ai_provider='zhipu'):
    """
    调用AI生成测试用例的任务函数（兼容旧接口）

    Args:
        ai_job: AiJobManagement对象
        ai_provider: AI提供商，'zhipu' 或 'deepseek'

    Returns:
        bool: 是否成功
    """
    from django.utils import timezone
    from ..models import TestCase

    try:
        # 更新任务状态为处理中
        ai_job.job_status = 1
        ai_job.task_start_time = timezone.now()
        ai_job.save()

        # 获取文档内容
        doc = ai_job.doc
        doc_content = doc.doc_content

        manager = AIManager(provider_name=ai_provider)

        system_prompt = TestCaseGeneratorPrompt.get_system_prompt()
        user_prompt = TestCaseGeneratorPrompt.get_user_prompt(doc_content)

        response = manager.call_with_prompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=(ai_provider == 'zhipu'),
            use_cache=False  # 测试用例生成不使用缓存
        )

        # 解析AI返回的测试用例
        test_cases = TestCaseGeneratorPrompt.parse_response(response.content)

        # 将获取到的testcase插入到TestCase表中
        created_count = 0
        for test_case_data in test_cases:
            try:
                TestCase.objects.create(
                    title=test_case_data.get('testpoint', ''),
                    test_steps=test_case_data.get('operation', ''),
                    expected_result=test_case_data.get('expectedresult', ''),
                    precondition='',
                    priority='P2',
                    status='active',
                    job_id=ai_job,
                    doc=doc
                )
                created_count += 1
            except Exception as e:
                print(f'创建测试用例失败 (Job ID: {ai_job.id}): {str(e)}, 数据: {test_case_data}')

        # 如果至少创建了一个测试用例，认为任务成功
        if created_count > 0:
            ai_job.job_status = 2
            ai_job.task_complete_time = timezone.now()
            ai_job.save()
            print(f'AI任务执行成功 (Job ID: {ai_job.id}): 共创建 {created_count} 个测试用例')
            return True
        else:
            raise Exception('未能创建任何测试用例')

    except Exception as e:
        # 更新任务状态为失败
        ai_job.job_status = 0
        ai_job.task_fail_time = timezone.now()
        ai_job.save()

        print(f'AI任务执行失败 (Job ID: {ai_job.id}): {str(e)}')
        return False


# ==================== API接口测试用例生成功能兼容 ====================

def generate_api_test_cases(api_interface, ai_provider='zhipu', test_data=None):
    """
    使用AI生成API接口的测试用例（兼容旧接口）

    Args:
        api_interface: ApiInterface对象或接口信息字典
        ai_provider: AI提供商，'zhipu' 或 'deepseek'
        test_data: 测试数据（如果有），用于生成更精确的测试用例

    Returns:
        dict: 包含测试用例数据的字典
    """
    try:
        # 构建接口信息
        if hasattr(api_interface, '__dict__'):
            # 如果是模型对象
            interface_info = {
                'api_name': api_interface.api_name,
                'api_path': api_interface.api_path,
                'method': api_interface.method,
                'request_params': api_interface.request_params,
                'response_params': api_interface.response_params,
                'remark': api_interface.remark
            }
        else:
            # 如果是字典
            interface_info = api_interface

        manager = AIManager(provider_name=ai_provider)

        system_prompt = APITestCaseGeneratorPrompt.get_system_prompt()
        user_prompt = APITestCaseGeneratorPrompt.get_user_prompt(
            api_name=interface_info.get('api_name', '未知'),
            api_path=interface_info.get('api_path', '未知'),
            method=interface_info.get('method', '未知'),
            request_params=interface_info.get('request_params', '无'),
            response_params=interface_info.get('response_params', '无'),
            remark=interface_info.get('remark', '无'),
            test_data=test_data
        )

        response = manager.call_with_prompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=(ai_provider == 'zhipu'),
            use_cache=False
        )

        return APITestCaseGeneratorPrompt.parse_response(response.content)

    except Exception as e:
        print(f'AI生成测试用例失败: {str(e)}')
        return {
            'error': str(e),
            'test_cases': []
        }


def parse_test_cases_response(response_text):
    """
    解析AI返回的测试用例响应（兼容旧接口）

    Args:
        response_text: AI返回的文本

    Returns:
        dict: 包含测试用例列表的字典
    """
    return APITestCaseGeneratorPrompt.parse_response(response_text)


# ==================== 高级功能（新增） ====================

def get_ai_statistics():
    """
    获取AI使用统计信息

    Returns:
        dict: 统计信息
    """
    config = get_config()
    return config.get_cost()


def clear_ai_cache():
    """清空AI缓存"""
    from .utils.cache import get_cache

    cache = get_cache()
    cache.clear()


def get_ai_providers():
    """
    获取所有可用的AI提供商

    Returns:
        list: 提供商列表
    """
    from .providers import get_available_providers
    return get_available_providers()


# ==================== 导出兼容接口 ====================

__all__ = [
    # 配置
    'set_api_keys',
    'get_api_keys',

    # HTML解析
    'parse_html_with_ai',
    'parse_ai_response',

    # 测试用例生成
    'call_ai_job',
    'generate_api_test_cases',
    'parse_test_cases_response',

    # 高级功能
    'get_ai_statistics',
    'clear_ai_cache',
    'get_ai_providers',

    # 新架构
    'AIManager'
]
