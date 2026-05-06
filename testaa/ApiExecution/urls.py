"""
API执行模块路由配置
"""

from django.urls import path
from . import views, dataviews, api_interface_views

urlpatterns = [
    # === 核心接口 ===
    path('apirun/execute', views.execute_testcase_stream_view),
    path('apirun/get', views.get_execution_view),
    path('apirun/list', views.list_executions_view),

    # === 调试接口（按需取消注释） ===
    # path('dependency', views.dependency_get_stream_view, name='dependency_get'),
    # path('fill_data', views.fill_test_data_stream_view, name='fill_test_data'),
    # path('create', views.create_execution_view, name='create_execution'),

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
