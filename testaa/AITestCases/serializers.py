"""
测试用例序列化器
"""

from typing import Dict, Any
from .models import TestCase, AiJobManagement


def serialize_testcase(testcase: TestCase) -> Dict[str, Any]:
    """
    序列化测试用例

    Args:
        testcase: 测试用例对象

    Returns:
        序列化后的字典
    """
    return {
        'id': testcase.id,
        'title': testcase.title,
        'precondition': testcase.precondition,
        'test_steps': testcase.test_steps,
        'expected_result': testcase.expected_result,
        'priority': testcase.priority,
        'status': testcase.status,
        'doc_id': testcase.doc_id_id,
        'doc_type': testcase.doc_id.doc_type if testcase.doc_id else None,
        'api_interface_id': testcase.api_interface_id,
        'job_id': testcase.job_id_id,
        'created_time': testcase.created_time.strftime('%Y-%m-%d %H:%M:%S'),
        'updated_time': testcase.updated_time.strftime('%Y-%m-%d %H:%M:%S'),
    }


def serialize_ai_job(job: AiJobManagement) -> Dict[str, Any]:
    """
    序列化AI任务

    Args:
        job: AI任务对象

    Returns:
        序列化后的字典
    """
    return {
        'id': job.id,
        'job_status': job.job_status,
        'job_status_display': job.get_job_status_display(),
        'doc_id': job.doc_id,
        'doc_type': job.doc.doc_type if job.doc else None,
        'doc_filename': job.doc.filename if job.doc else None,
        'task_start_time': job.task_start_time.strftime('%Y-%m-%d %H:%M:%S') if job.task_start_time else None,
        'task_complete_time': job.task_complete_time.strftime('%Y-%m-%d %H:%M:%S') if job.task_complete_time else None,
        'task_fail_time': job.task_fail_time.strftime('%Y-%m-%d %H:%M:%S') if job.task_fail_time else None,
        'create_time': job.create_time.strftime('%Y-%m-%d %H:%M:%S'),
        'update_time': job.update_time.strftime('%Y-%m-%d %H:%M:%S'),
    }
