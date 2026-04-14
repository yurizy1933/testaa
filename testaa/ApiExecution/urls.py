"""
API执行模块路由配置
"""

from django.urls import path
from . import views

urlpatterns = [
    path('create', views.create_execution_view, name='create_execution'),
    path('execute', views.execute_testcase_stream_view, name='execute_testcase'),
    path('get', views.get_execution_view, name='get_execution'),
    path('list', views.list_executions_view, name='list_executions'),
]
