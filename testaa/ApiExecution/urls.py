"""
API执行模块路由配置
"""

from django.urls import path
from . import views, dataviews, api_interface_views

urlpatterns = [
    # 执行记录管理
    # path('create', views.create_execution_view, name='create_execution'),
    # path('execute', views.execute_testcase_stream_view, name='execute_testcase'),
    # path('get', views.get_execution_view, name='get_execution'),
    # path('list', views.list_executions_view, name='list_executions'),

    # 测试数据管理
    path('test_data/get', dataviews.get_test_data_list),
    path('test_data/detail', dataviews.get_test_data_detail),
    path('test_data/create', dataviews.create_test_data),
    path('test_data/update', dataviews.update_test_data),
    path('test_data/delete', dataviews.delete_test_data),

    # API接口管理
    path('api_interface/get', api_interface_views.get_api_interface_list),
    path('api_interface/detail', api_interface_views.get_api_interface_detail),
    path('api_interface/create', api_interface_views.create_api_interface),
    path('api_interface/update', api_interface_views.update_api_interface),
    path('api_interface/delete', api_interface_views.delete_api_interface),
]
