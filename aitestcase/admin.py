from django.contrib import admin
from .models import Project, TestCase

# Register your models here.

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'create_time']
    list_filter = ['create_time']
    search_fields = ['name', 'desc']
    readonly_fields = ['create_time']

@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'project', 'priority', 'status', 'created_time']
    list_filter = ['status', 'priority', 'project', 'created_time']
    search_fields = ['title', 'precondition', 'test_steps', 'expected_result']
    readonly_fields = ['created_time', 'updated_time']
    list_editable = ['status', 'priority']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'project', 'priority', 'status')
        }),
        ('测试内容', {
            'fields': ('precondition', 'test_steps', 'expected_result')
        }),
        ('时间信息', {
            'fields': ('created_time', 'updated_time'),
            'classes': ('collapse',)
        }),
    )
