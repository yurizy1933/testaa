from django.contrib import admin
from .models import Project, Doc, TestCase, AiJobManagement

# Register your models here.

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['id', 'project_name', 'owner', 'description_preview', 'doc_count', 'create_time']
    list_filter = ['create_time', 'owner']
    search_fields = ['project_name', 'description', 'owner']
    readonly_fields = ['create_time', 'update_time']
    list_editable = ['owner']
    
    def description_preview(self, obj):
        """显示描述预览"""
        if obj.description:
            return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
        return '无描述'
    description_preview.short_description = '描述预览'
    
    def doc_count(self, obj):
        """显示文档数量"""
        return obj.docs.count()
    doc_count.short_description = '文档数量'
    
    fieldsets = (
        ('基本信息', {
            'fields': ('project_name', 'owner', 'description')
        }),
        ('时间信息', {
            'fields': ('create_time', 'update_time'),
            'classes': ('collapse',)
        }),
    )

@admin.register(Doc)
class DocAdmin(admin.ModelAdmin):
    list_display = ['id', 'filename', 'project', 'is_case_generated', 'create_time']
    list_filter = ['is_case_generated', 'project', 'create_time']
    search_fields = ['filename', 'file_content', 'project__project_name']
    readonly_fields = ['create_time', 'update_time', 'file_content_preview']
    list_editable = ['is_case_generated']
    
    def file_content_preview(self, obj):
        """显示文件内容预览"""
        if obj.file_content:
            return obj.file_content[:200] + '...' if len(obj.file_content) > 200 else obj.file_content
        return '无内容'
    file_content_preview.short_description = '内容预览'
    
    fieldsets = (
        ('基本信息', {
            'fields': ('filename', 'project', 'file_path')
        }),
        ('内容信息', {
            'fields': ('file_content', 'file_content_preview', 'is_case_generated')
        }),
        ('时间信息', {
            'fields': ('create_time', 'update_time'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_generated', 'mark_as_not_generated']
    
    def mark_as_generated(self, request, queryset):
        """批量标记为已生成用例"""
        queryset.update(is_case_generated=True)
        self.message_user(request, f'已将 {queryset.count()} 个文档标记为已生成用例')
    mark_as_generated.short_description = '标记为已生成用例'
    
    def mark_as_not_generated(self, request, queryset):
        """批量标记为未生成用例"""
        queryset.update(is_case_generated=False)
        self.message_user(request, f'已将 {queryset.count()} 个文档标记为未生成用例')
    mark_as_not_generated.short_description = '标记为未生成用例'

@admin.register(AiJobManagement)
class AiJobManagementAdmin(admin.ModelAdmin):
    list_display = ['id', 'doc', 'job_status', 'task_start_time', 'task_complete_time', 'task_fail_time', 'create_time']
    list_filter = ['job_status', 'create_time', 'task_start_time']
    search_fields = ['doc__filename', 'doc__project__project_name']
    readonly_fields = ['create_time', 'update_time']
    list_editable = ['job_status']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('doc', 'job_status')
        }),
        ('任务时间', {
            'fields': ('task_start_time', 'task_complete_time', 'task_fail_time')
        }),
        ('时间信息', {
            'fields': ('create_time', 'update_time'),
            'classes': ('collapse',)
        }),
    )

@admin.register(TestCase)
class TestCaseAdmin(admin.ModelAdmin):
    list_display = ['id', 'title_preview', 'doc_id', 'job_id', 'project_name', 'priority', 'status', 'created_time']
    list_filter = ['status', 'priority', 'created_time', 'job_id__job_status']
    search_fields = ['title', 'precondition', 'test_steps', 'expected_result', 'doc__filename', 'job_id__id']
    readonly_fields = ['created_time', 'updated_time']
    list_editable = ['status', 'priority']
    
    def title_preview(self, obj):
        """显示标题预览"""
        return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
    title_preview.short_description = '标题预览'
    
    def project_name(self, obj):
        """显示项目名称"""
        return obj.doc.project.project_name
    project_name.short_description = '所属项目'
    
    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'doc_id', 'job_id', 'priority', 'status')
        }),
        ('测试内容', {
            'fields': ('precondition', 'test_steps', 'expected_result')
        }),
        ('时间信息', {
            'fields': ('created_time', 'updated_time'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['soft_delete_selected', 'restore_selected']
    
    def soft_delete_selected(self, request, queryset):
        """批量软删除"""
        count = 0
        for testcase in queryset:
            if testcase.status != 'deleted':
                testcase.soft_delete()
                count += 1
        self.message_user(request, f'已软删除 {count} 个测试用例')
    soft_delete_selected.short_description = '批量软删除'
    
    def restore_selected(self, request, queryset):
        """批量恢复"""
        count = 0
        for testcase in queryset:
            if testcase.status == 'deleted':
                testcase.restore()
                count += 1
        self.message_user(request, f'已恢复 {count} 个测试用例')
    restore_selected.short_description = '批量恢复'
