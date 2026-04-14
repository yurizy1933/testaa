from django.db import models
from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Config(models.Model):
    ENVIRONMENT_CHOICES = (
        ('dev', '开发环境'),
        ('test', '测试环境'),
        ('uat', 'UAT环境'),
        ('live', '生产环境'),
    )

    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    environment = models.CharField(max_length=20, choices=ENVIRONMENT_CHOICES)
    ip = models.GenericIPAddressField(null=True, blank=True)
    description = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.key