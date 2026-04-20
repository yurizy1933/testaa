"""
AI测试用例模块路由配置
"""

from django.urls import path
from . import views, caseview

urlpatterns = [
    # 测试用例管理（新增）
    path('create', caseview.create_testcase_view),
    path('get', caseview.get_testcases_view),
    path('detail', caseview.get_testcase_detail_view),
    path('update', caseview.update_testcase_view),
    path('delete', caseview.delete_testcase_view),
    path('batch_delete', caseview.batch_delete_testcase_view),

    # AI任务管理
    path('ai_job/get', views.get_ai_jobs_view),
]
