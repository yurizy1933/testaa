# Generated manually to fix TestCase.api_interface foreign key

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0002_alter_apidoc_options_alter_doc_options_and_more"),
        ("AITestCases", "0002_alter_aijobmanagement_doc_alter_testcase_doc_id_and_more"),
    ]

    operations = [
        # 删除 ai_testcase_jobs 表指向旧 ApiInterface 的 FK 约束
        migrations.RunSQL(
            sql=(
                "ALTER TABLE `ai_testcase_jobs` "
                "DROP FOREIGN KEY `ai_testcase_jobs_api_interface_id_9f62aa40_fk_AITestCas`"
            ),
            reverse_sql=migrations.RunSQL.noop,
        ),
        # 删除迁移 0002 创建的临时 ApiInterface 表
        migrations.DeleteModel(
            name='ApiInterface',
        ),
        # 修复 TestCase.api_interface FK 指向 common.ApiInterface
        migrations.AlterField(
            model_name="testcase",
            name="api_interface",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="test_cases",
                to="common.apiinterface",
                verbose_name="关联接口",
            ),
        ),
    ]
