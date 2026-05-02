"""
AI测试用例生成服务层
"""
import logging
from typing import Dict
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone

from common.models import ApiInterface, TestData, CommonDoc
from .models import TestCase, AiJobManagement
from AITools.generators.api_testcase import APITestCaseGenerator

logger = logging.getLogger(__name__)


class TestCaseGeneratorService:
    """测试用例生成服务"""

    def generate(
        self,
        api_interface_id: str,
        ai_provider: str = 'zhipu',
        test_data_id: str = None,
        doc_id: str = None
    ) -> Dict:
        """
        调用大模型生成测试用例并保存到数据库

        Args:
            api_interface_id: API接口ID
            ai_provider: AI提供商（zhipu / deepseek）
            test_data_id: 测试数据ID（可选）
            doc_id: 文档ID（可选，提供时会创建AiJobManagement记录）

        Returns:
            Dict: {saved_count, test_cases, model, tokens_used, cost, job_id?}
        """
        api_interface = get_object_or_404(ApiInterface, id=api_interface_id)

        test_data = None
        if test_data_id:
            test_data = get_object_or_404(TestData, id=test_data_id)

        doc = None
        job = None
        if doc_id:
            doc = get_object_or_404(CommonDoc, id=doc_id)
            job = AiJobManagement.objects.create(
                job_status=1,  # 处理中
                task_start_time=timezone.now(),
                doc=doc
            )
            logger.info(f"AI任务创建 - Job ID: {job.id}, 接口: {api_interface.api_name}")

        try:
            # 调用AI生成测试用例
            generator = APITestCaseGenerator(ai_provider=ai_provider)
            result = generator.generate(api_interface, test_data)
            test_cases = result['test_cases']

            # 批量保存到数据库
            saved_count = 0
            with transaction.atomic():
                for tc in test_cases:
                    try:
                        TestCase.objects.create(
                            title=tc.get('test_case_name', ''),
                            precondition=tc.get('preconditions', ''),
                            test_steps=tc.get('test_steps', ''),
                            expected_result=tc.get('expected_result', ''),
                            priority=tc.get('priority', 'P2'),
                            job_id=job,
                            doc_id=doc,
                            api_interface=api_interface,
                            status='active'
                        )
                        saved_count += 1
                    except Exception as e:
                        logger.error(f"保存测试用例失败: {e}, 用例: {tc.get('test_case_name')}")
                        continue

            # 更新任务状态
            if job:
                job.job_status = 2
                job.task_complete_time = timezone.now()
                job.save()

            logger.info(f"测试用例生成完成 - 接口: {api_interface.api_name}, "
                        f"生成: {len(test_cases)} 个, 保存: {saved_count} 个")

            response = {
                'saved_count': saved_count,
                'test_cases': test_cases,
                'model': result.get('model'),
                'tokens_used': result.get('tokens_used'),
                'cost': result.get('cost')
            }
            if job:
                response['job_id'] = job.id
            return response

        except Exception as e:
            if job:
                job.job_status = 0
                job.task_fail_time = timezone.now()
                job.save()
            logger.error(f"测试用例生成失败: {str(e)}")
            raise
