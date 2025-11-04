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
from django.urls import path
from ailoginTest import views as login_views
from aitestplatformlogin import views as platform_login
from aitestcase import views as testcase_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('add_school', login_views.add_school),
    path('get_all_student', login_views.get_all_student),
    path('login', platform_login.aiplatform_login),
    path('check_user', platform_login.is_ok_request),

    path('project/get', testcase_views.get_project_view),
    path('project/create', testcase_views.create_project_view),
    path('project/update', testcase_views.update_project_view),
    path('project/delete', testcase_views.delete_project_view),

    path('doc/get', testcase_views.get_docs_view),
    path('doc/create', testcase_views.upload_doc_view),
    path('doc/detail', testcase_views.get_doc_detail_view),
    path('doc/delete', testcase_views.delete_doc_view),

    path('testcase/get', testcase_views.get_testcases_view),
    path('testcase/detail', testcase_views.get_testcase_detail_view),
    path('testcase/update', testcase_views.update_testcase_view),
    path('testcase/delete', testcase_views.delete_testcase_view),

    path('ai_job/get', testcase_views.get_ai_jobs_view),
    path('ai_job/run', testcase_views.run_ai_case_job),
]
