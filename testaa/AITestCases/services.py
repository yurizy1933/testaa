"""
AI测试用例生成服务层
"""
import logging
import threading
from typing import Dict
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone

from common.models import ApiInterface, TestData, CommonDoc
from .models import TestCase, AiJobManagement
from AITools.parsers.api_testcase import APITestCaseGenerator

logger = logging.getLogger(__name__)


class TestCaseGeneratorService:
    """测试用例生成服务"""

    def generate_async(
        self,
        api_interface_id: str,
        doc_id: str,
        ai_provider: str = 'zhipu',
        test_data_id: str = None
    ) -> Dict:
        """
        异步生成测试用例：创建 Job 并启动后台线程执行

        Args:
            api_interface_id: API接口ID
            doc_id: 文档ID
            ai_provider: AI提供商（zhipu / deepseek）
            test_data_id: 测试数据ID（可选）

        Returns:
            Dict: {job_id, status: 'pending'}
        """
        api_interface = get_object_or_404(ApiInterface, id=api_interface_id)
        doc = get_object_or_404(CommonDoc, id=doc_id)

        test_data = None
        if test_data_id:
            test_data = get_object_or_404(TestData, id=test_data_id)

        # 创建 Job（status=0 pending）
        job = AiJobManagement.objects.create(
            job_status=0,  # 待处理
            doc=doc
        )
        logger.info(f"Job 创建 - ID: {job.id}, 接口: {api_interface.api_name}")

        # 启动后台线程执行生成
        thread = threading.Thread(
            target=self._run_generation,
            args=(job.id, api_interface_id, ai_provider, test_data_id),
            daemon=True
        )
        thread.start()

        return {
            'job_id': job.id,
            'status': 'pending'
        }

    def _run_generation(
        self,
        job_id: int,
        api_interface_id: str,
        ai_provider: str,
        test_data_id: str = None
    ):
        """
        后台执行生成任务（运行在独立线程中）

        流程：status 0→1 → AI调用 → 保存 → status 1→2
        失败时：status → 0，记录失败时间
        """
        job = AiJobManagement.objects.get(id=job_id)

        try:
            # 更新为处理中
            job.job_status = 1
            job.task_start_time = timezone.now()
            job.save()

            # 获取数据
            api_interface = ApiInterface.objects.get(id=api_interface_id)
            test_data = None
            if test_data_id:
                test_data = TestData.objects.get(id=test_data_id)

            # 调用AI
            generator = APITestCaseGenerator(ai_provider=ai_provider)
            result = generator.generate(api_interface, test_data)
            test_cases = result['test_cases']

            # 保存到数据库
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
                            doc_id=job.doc,
                            api_interface=api_interface,
                            status='active'
                        )
                        saved_count += 1
                    except Exception as e:
                        logger.error(f"保存测试用例失败: {e}, 用例: {tc.get('test_case_name')}")
                        continue

            # 更新为已完成
            job.job_status = 2
            job.task_complete_time = timezone.now()
            job.save()

            logger.info(f"Job {job_id} 完成 - 生成: {len(test_cases)} 个, 保存: {saved_count} 个, "
                        f"tokens: {result.get('tokens_used')}, cost: {result.get('cost')}")

        except Exception as e:
            job.job_status = 0
            job.task_fail_time = timezone.now()
            job.save()
            logger.error(f"Job {job_id} 失败: {str(e)}")
