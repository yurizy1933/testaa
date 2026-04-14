from django.db import models

# Create your models here.

class school(models.Model):
    id = models.AutoField(primary_key=True) #字段名id，自增，唯一
    school_name  = models.CharField(max_length=128, db_column='school_name')
    sex = models.CharField(max_length=32,db_column='sex')
    create_date = models.DateField(db_column='create_date') #时间
    create_time = models.DateTimeField(auto_created=True)
    
    #配置默认返回
    def __unicode__(self):
        return self.id

class student(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=128, db_column='name')
    sex =  models.CharField(max_length=32, db_column='sex')
    school_id = models.ForeignKey(school, db_column='school_id', on_delete=models.CASCADE) #设置外键
    birth = models.DateField(db_column='birth')
    department = models.CharField(max_length=128, db_column='department')
    address = models.CharField(max_length=128, db_column='address')

    def __unicode__(self):
        return self.id