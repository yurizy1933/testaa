"""
AI测试用例模块路由配置
"""

from django.urls import path
from . import views

urlpatterns = [
    # 测试用例管理
    # path('create', views.create_testcase_view, name='create_testcase'),
    # path('get', views.get_testcases_view, name='get_testcases'),
    # path('detail', views.get_testcase_detail_view, name='get_testcase_detail'),
    # path('generate', views.generate_testcases_view, name='generate_testcases'),
    # path('update', views.update_testcase_view, name='update_testcase'),
    # path('delete', views.delete_testcase_view, name='delete_testcase'),
    #
    # # AI任务管理
    # path('ai_job/run', views.run_ai_job_view, name='run_ai_job'),
    path('ai_job/get', views.get_ai_jobs_view, name='get_ai_jobs'),
]
