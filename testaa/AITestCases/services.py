"""
AI测试用例业务逻辑
"""

import logging
from typing import List, Dict, Any
from django.utils import timezone
from aitestcase.ai.core.manager import AIManager
from aitestcase.ai.prompts.api_test import APITestCaseGeneratorPrompt
from .models import TestCase, AiJobManagement

logger = logging.getLogger(__name__)


class TestCaseService:
    """测试用例服务类"""

    def __init__(self, ai_provider: str = 'zhipu'):
        """
        初始化服务

        Args:
            ai_provider: AI提供商名称
        """
        self.ai_manager = AIManager(provider_name=ai_provider)

    def generate_testcases_from_api_interface(
        self,
        api_interface,
        test_data: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        为API接口生成测试用例

        Args:
            api_interface: API接口对象
            test_data: 测试数据

        Returns:
            生成的测试用例列表
        """
        try:
            # 创建提示词
            prompt = APITestCaseGeneratorPrompt()

            # 调用AI生成测试用例
            response = self.ai_manager.call_with_prompt(
                system_prompt=prompt.get_system_prompt(),
                user_prompt=prompt.get_user_prompt(
                    api_name=api_interface.api_name,
                    api_path=api_interface.api_path or '',
                    method=api_interface.method,
                    request_params=api_interface.request_params or '',
                    response_params=api_interface.response_params or '',
                    remark=api_interface.remark or '',
                    test_data=test_data
                ),
                json_mode=True
            )

            # 解析响应
            if response.content:
                result = prompt.parse_response(response.content)
                return result.get('test_cases', [])

            return []

        except Exception as e:
            logger.error(f"生成测试用例失败: {str(e)}", exc_info=True)
            return []

    def create_testcases(
        self,
        testcases_data: List[Dict[str, Any]],
        doc=None,
        api_interface=None,
        job=None
    ) -> List[TestCase]:
        """
        创建测试用例

        Args:
            testcases_data: 测试用例数据列表
            doc: 关联文档
            api_interface: 关联API接口
            job: 关联任务

        Returns:
            创建的测试用例列表
        """
        created_testcases = []

        for testcase_data in testcases_data:
            testcase = TestCase.objects.create(
                title=testcase_data.get('test_case_name', ''),
                precondition=testcase_data.get('preconditions', ''),
                test_steps=testcase_data.get('test_steps', ''),
                expected_result=testcase_data.get('expected_result', ''),
                priority=self._map_priority(testcase_data.get('priority', 'P2')),
                doc_id=doc,
                api_interface=api_interface,
                job_id=job,
                status='active'
            )
            created_testcases.append(testcase)

        logger.info(f"创建了 {len(created_testcases)} 个测试用例")
        return created_testcases

    def _map_priority(self, priority_str: str) -> str:
        """
        映射优先级

        Args:
            priority_str: 优先级字符串

        Returns:
            映射后的优先级
        """
        priority_map = {
            'P0': 'P0',
            'P1': 'P1',
            'P2': 'P2',
            'P3': 'P3',
            '很高': 'P0',
            '高': 'P1',
            '中': 'P2',
            '低': 'P3',
        }
        return priority_map.get(priority_str, 'P2')


class AiJobService:
    """AI任务服务类"""

    def create_job(self, doc) -> AiJobManagement:
        """
        创建AI任务

        Args:
            doc: 关联文档

        Returns:
            创建的AI任务
        """
        job = AiJobManagement.objects.create(
            doc=doc,
            job_status=0  # 待处理
        )
        logger.info(f"创建AI任务: ID={job.id}, 文档={doc.filename}")
        return job

    def start_job(self, job: AiJobManagement):
        """
        开始执行任务

        Args:
            job: AI任务
        """
        job.job_status = 1  # 处理中
        job.task_start_time = timezone.now()
        job.save(update_fields=['job_status', 'task_start_time'])
        logger.info(f"AI任务开始执行: ID={job.id}")

    def complete_job(self, job: AiJobManagement):
        """
        完成任务

        Args:
            job: AI任务
        """
        job.job_status = 2  # 已完成
        job.task_complete_time = timezone.now()
        job.save(update_fields=['job_status', 'task_complete_time'])
        logger.info(f"AI任务完成: ID={job.id}")

    def fail_job(self, job: AiJobManagement, error_msg: str = ''):
        """
        任务失败

        Args:
            job: AI任务
            error_msg: 错误信息
        """
        job.job_status = 0  # 待处理（重置状态）
        job.task_fail_time = timezone.now()
        job.save(update_fields=['job_status', 'task_fail_time'])
        logger.error(f"AI任务失败: ID={job.id}, 错误: {error_msg}")
