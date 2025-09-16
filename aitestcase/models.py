
# Create your models here.
from django.db import models
from docx import Document

class Project(models.Model):
    id = models.AutoField(primary_key=True)  # 字段名id，自增，唯一
    name = models.CharField(max_length=200)
    desc = models.TextField(blank=True)
    doc = models.FileField(upload_to='docs/', blank=True, null=True)
    create_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    #
    # @property
    # def docContent(self):
    #     if self.doc:
    #         try:
    #             with self.doc.open('rb') as f:
    #                 # 这里只做简单文本读取，实际可用python-docx等库解析docx内容
    #                 return f.read().decode(errors='ignore')
    #         except Exception:
    #             return ''
    #     return ''
    @property
    def docContent(self):
        if self.doc:
            try:
                doc_path = self.doc.path
                document = Document(doc_path)
                # 提取所有段落文本
                return '\n'.join([para.text for para in document.paragraphs])
            except Exception as e:
                return f'文档解析失败: {e}'
        return ''

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
    project = models.ForeignKey(
        Project, 
        on_delete=models.CASCADE, 
        related_name='test_cases',
        verbose_name='关联项目'
    )
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')
    
    class Meta:
        verbose_name = '测试用例'
        verbose_name_plural = '测试用例'
        ordering = ['-created_time']
    
    def __str__(self):
        return f"{self.title} - {self.project.name}"
    
    def soft_delete(self):
        """软删除测试用例"""
        self.status = 'deleted'
        self.save()
    
    def restore(self):
        """恢复测试用例"""
        self.status = 'active'
        self.save()