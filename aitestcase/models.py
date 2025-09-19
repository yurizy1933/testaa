
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
    doc = models.ForeignKey(
        Doc, 
        on_delete=models.CASCADE, 
        related_name='test_cases',
        verbose_name='关联文档',
        default=''
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