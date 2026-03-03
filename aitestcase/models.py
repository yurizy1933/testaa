
# Create your models here.
from django.db import models
from docx import Document

class Project(models.Model):
    """项目模型"""
    id = models.AutoField(primary_key=True)
    project_name = models.CharField(max_length=200, verbose_name='项目名称', default='')
    description = models.TextField(blank=True, null=True, verbose_name='项目描述')
    owner = models.CharField(max_length=100,default='', verbose_name='项目负责人')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '项目'
        verbose_name_plural = '项目'

        ordering = ['-create_time']

    def __str__(self):
        return self.project_name

class Doc(models.Model):
    """文档模型"""
    id = models.AutoField(primary_key=True)
    filename = models.CharField(max_length=500, verbose_name='文件名')
    file_content = models.TextField(blank=True, null=True, verbose_name='文件内容')
    file_path = models.FileField(upload_to='docs/', blank=True, null=True, verbose_name='文件路径')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    is_case_generated = models.BooleanField(default=False, verbose_name='是否已生成用例')
    project = models.ForeignKey(
        Project, 
        on_delete=models.CASCADE, 
        related_name='docs',
        verbose_name='所属项目'
    )

    class Meta:
        verbose_name = '文档'
        verbose_name_plural = '文档'
        ordering = ['-create_time']

    def __str__(self):
        return f"{self.filename} - {self.project.project_name}"

    @property
    def doc_content(self):
        """获取文档内容"""
        if self.file_content:
            return self.file_content
        elif self.file_path:
            try:
                doc_path = self.file_path.path
                document = Document(doc_path)
                # 提取所有段落文本
                content = '\n'.join([para.text for para in document.paragraphs])
                # 将解析的内容保存到file_content字段
                self.file_content = content
                self.save(update_fields=['file_content'])
                return content
            except Exception as e:
                return f'文档解析失败: {e}'
        return ''

    def mark_case_generated(self):
        """标记为已生成用例"""
        self.is_case_generated = True
        self.save(update_fields=['is_case_generated'])


class AiJobManagement(models.Model):
    """AI任务管理模型"""
    JOB_STATUS_CHOICES = [
        (0, '待处理'),
        (1, '处理中'),
        (2, '已完成'),
    ]
    
    id = models.AutoField(primary_key=True)
    job_status = models.IntegerField(
        choices=JOB_STATUS_CHOICES,
        default=0,
        verbose_name='任务状态'
    )
    task_start_time = models.DateTimeField(verbose_name='任务开始时间', null=True, blank=True)
    task_complete_time = models.DateTimeField(verbose_name='任务完成时间', null=True, blank=True)
    task_fail_time = models.DateTimeField(verbose_name='任务失败时间', null=True, blank=True)
    doc = models.ForeignKey(
        Doc,
        on_delete=models.CASCADE,
        related_name='ai_jobs',
        verbose_name='关联文档'
    )
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = 'AI任务管理'
        verbose_name_plural = 'AI任务管理'
        ordering = ['-create_time']
        db_table = 'ai_job_management'

    def __str__(self):
        return f"任务-{self.id}-{self.get_job_status_display()}"


class TestCase(models.Model):
    """测试用例模型"""
    STATUS_CHOICES = [
        ('active', '激活'),
        ('deleted', '删除'),
    ]
    
    PRIORITY_CHOICES = [
        ('P0', '很高'),
        ('P1', '高'),
        ('P2', '中'),
        ('P3', '低'),
    ]
    
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=500, verbose_name='用例标题')
    precondition = models.TextField(blank=True, verbose_name='前置条件')
    test_steps = models.TextField(verbose_name='测试步骤')
    expected_result = models.TextField(verbose_name='预期结果')
    priority = models.CharField(
        max_length=10, 
        choices=PRIORITY_CHOICES, 
        default='medium',
        verbose_name='优先级'
    )
    status = models.CharField(
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='active',
        verbose_name='用例状态'
    )
    job_id = models.ForeignKey(
        AiJobManagement,
        on_delete=models.CASCADE,
        related_name='test_cases_by_job',
        verbose_name='关联任务',
        null=True,
        blank=True
    )
    doc_id = models.ForeignKey(
        Doc, 
        on_delete=models.CASCADE, 
        related_name='test_cases',
        verbose_name='关联文档',
        null=True,
        blank=True
    )
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '测试用例'
        verbose_name_plural = '测试用例'
        ordering = ['-created_time']
    
    def __str__(self):
        return f"{self.title} - {self.doc.filename}"
    
    def soft_delete(self):
        """软删除测试用例"""
        self.status = 'deleted'
        self.save()
    
    def restore(self):
        """恢复测试用例"""
        self.status = 'active'
        self.save()


class ApiDoc(models.Model):
    """接口文档模型"""
    id = models.AutoField(primary_key=True)
    filename = models.CharField(max_length=500, verbose_name='文件名')
    version = models.CharField(max_length=50, default='1.0.0', verbose_name='版本号')
    file_content = models.TextField(blank=True, null=True, verbose_name='文件内容')
    file_path = models.FileField(upload_to='api_docs/', blank=True, null=True, verbose_name='文件路径')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='api_docs',
        verbose_name='所属项目'
    )

    class Meta:
        verbose_name = '接口文档'
        verbose_name_plural = '接口文档'
        ordering = ['-create_time']

    def __str__(self):
        return f"{self.filename} - v{self.version} - {self.project.project_name}"


class ApiInterface(models.Model):
    """API接口模型"""
    METHOD_CHOICES = [
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('DELETE', 'DELETE'),
        ('PATCH', 'PATCH'),
        ('HEAD', 'HEAD'),
        ('OPTIONS', 'OPTIONS'),
    ]

    id = models.AutoField(primary_key=True)
    api_name = models.CharField(max_length=500, verbose_name='接口名称')
    api_path = models.CharField(max_length=1000, blank=True, null=True, verbose_name='接口路径')
    method = models.CharField(max_length=10, choices=METHOD_CHOICES, verbose_name='请求方法')
    request_params = models.TextField(blank=True, null=True, verbose_name='入参')
    response_params = models.TextField(blank=True, null=True, verbose_name='出参')
    remark = models.TextField(blank=True, null=True, verbose_name='备注')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    api_doc = models.ForeignKey(
        ApiDoc,
        on_delete=models.CASCADE,
        related_name='api_interfaces',
        verbose_name='所属文档'
    )

    class Meta:
        verbose_name = 'API接口'
        verbose_name_plural = 'API接口'
        ordering = ['-create_time']

    def __str__(self):
        return f"{self.method} {self.api_name}"


class TestData(models.Model):
    """测试数据模型"""
    id = models.AutoField(primary_key=True)
    test_name = models.CharField(max_length=500, verbose_name='测试数据名称')
    test_data_json = models.JSONField(verbose_name='测试数据JSON')
    description = models.TextField(blank=True, null=True, verbose_name='描述')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    api_interface = models.ForeignKey(
        ApiInterface,
        on_delete=models.CASCADE,
        related_name='test_data',
        verbose_name='所属接口'
    )

    class Meta:
        verbose_name = '测试数据'
        verbose_name_plural = '测试数据'
        ordering = ['-create_time']

    def __str__(self):
        return f"{self.test_name} - {self.api_interface.api_name}"