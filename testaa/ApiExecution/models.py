from django.db import models
from django.utils import timezone
from common.models import ApiInterface, TestData


class ApiTestCaseExecution(models.Model):
    """API 测试用例执行记录"""

    EXECUTION_STATUS_CHOICES = [
        ('pending', '待执行'),
        ('running', '执行中'),
        ('completed', '已完成'),
        ('failed', '执行失败'),
    ]

    id = models.AutoField(primary_key=True)
    case_name = models.CharField(max_length=500, verbose_name='用例名称')

    # 关联接口
    api_interface = models.ForeignKey(
        ApiInterface,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='executions',
        verbose_name='关联接口'
    )

    # 关联测试数据
    test_data = models.ForeignKey(
        TestData,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='executions',
        verbose_name='测试数据'
    )

    # 执行配置
    base_url = models.CharField(max_length=500, verbose_name='基础URL')
    run_list = models.JSONField(verbose_name='接口执行列表')
    ai_provider = models.CharField(max_length=20, default='zhipu', verbose_name='AI提供商')

    # 用例信息
    precondition = models.TextField(blank=True, null=True, verbose_name='前置条件')
    testpoint = models.TextField(verbose_name='测试点')
    expectation = models.TextField(verbose_name='预期结果')

    # 执行状态
    status = models.CharField(
        max_length=20,
        choices=EXECUTION_STATUS_CHOICES,
        default='pending',
        verbose_name='执行状态'
    )

    # 执行结果
    execution_results = models.JSONField(null=True, blank=True, verbose_name='执行结果')
    validation_result = models.JSONField(null=True, blank=True, verbose_name='AI校验结果')

    # 统计信息
    total_interfaces = models.IntegerField(default=0, verbose_name='总接口数')
    success_count = models.IntegerField(default=0, verbose_name='成功数')
    failed_count = models.IntegerField(default=0, verbose_name='失败数')
    total_duration_ms = models.IntegerField(default=0, verbose_name='总耗时(毫秒)')

    # 时间戳
    start_time = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = 'API测试执行记录'
        verbose_name_plural = 'API测试执行记录'
        ordering = ['-create_time']
        db_table = 'api_test_case_execution'

    def __str__(self):
        return f"{self.case_name} - {self.get_status_display()}"

    @property
    def duration_seconds(self):
        """获取执行时长（秒）"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0

    def update_statistics(self):
        """更新统计信息"""
        if self.execution_results:
            results = self.execution_results.get('results', [])
            self.total_interfaces = len(results)
            self.success_count = sum(1 for r in results if r.get('success', False))
            self.failed_count = self.total_interfaces - self.success_count
            self.total_duration_ms = sum(r.get('duration_ms', 0) for r in results)
        self.save(update_fields=['total_interfaces', 'success_count', 'failed_count', 'total_duration_ms'])

