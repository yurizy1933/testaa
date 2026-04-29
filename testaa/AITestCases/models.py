from django.db import models
from common.models import Project, CommonDoc, ApiInterface


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
        'AiJobManagement',
        on_delete=models.CASCADE,
        related_name='test_cases_by_job',
        verbose_name='关联任务',
        null=True,
        blank=True
    )
    doc_id = models.ForeignKey(
        CommonDoc,
        on_delete=models.CASCADE,
        related_name='test_cases',
        verbose_name='关联文档',
        null=True,
        blank=True
    )
    # 新增：关联API接口
    api_interface = models.ForeignKey(
        ApiInterface,
        on_delete=models.CASCADE,
        related_name='test_cases',
        verbose_name='关联接口',
        null=True,
        blank=True
    )
    created_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '测试用例'
        verbose_name_plural = '测试用例'
        ordering = ['-created_time']
        db_table = 'ai_testcase_cases'

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
        CommonDoc,
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
        db_table = 'ai_testcase_jobs'

    def __str__(self):
        return f"任务-{self.id}-{self.get_job_status_display()}"
