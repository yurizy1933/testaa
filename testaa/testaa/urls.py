"""
URL configuration for testaa project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from DailyTest import views as login_views
from aitestplatformlogin import views as platform_login
from aitestcase import views as testcase_views
from common import views as common_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('add_school', login_views.add_school),
    path('get_all_student', login_views.get_all_student),
    path('login', platform_login.aiplatform_login),
    path('check_user', platform_login.is_ok_request),

    # Common模块项目管理路由
    path('project/get', common_views.get_project_view),
    path('project/detail', common_views.get_project_detail_view),
    path('project/create', common_views.create_project_view),
    path('project/update', common_views.update_project_view),
    path('project/delete', common_views.delete_project_view),

    # Common模块统一文档管理路由
    path('common/doc/get', common_views.get_docs_view),
    path('common/doc/detail', common_views.get_doc_detail_view),
    path('common/doc/upload', common_views.upload_doc_view),
    path('common/doc/delete', common_views.delete_doc_view),
    path('common/doc/download', common_views.download_doc_view),

    # Common模块HTML API解析路由
    path('common/api/parse/sync', common_views.parse_html_sync_view),
    path('common/api/parse/async', common_views.parse_html_async_view),
    path('common/api/parse/job/status', common_views.parse_job_status_view),

    path('ai_job/get', testcase_views.get_ai_jobs_view),
    path('ai_job/run', testcase_views.run_ai_case_job),

    # 新模块路由
    # AI测试用例模块路由
    path('testcase/', include('AITestCases.urls')),

    # API执行模块路由
    path('apicommon/', include('ApiExecution.urls')),
]
