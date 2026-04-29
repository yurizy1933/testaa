# Generated manually to fix TestCase.api_interface foreign key

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0002_alter_apidoc_options_alter_doc_options_and_more"),
        ("AITestCases", "0002_alter_aijobmanagement_doc_alter_testcase_doc_id_and_more"),
    ]

    operations = [
        # Remove the ApiInterface model created in migration 0002
        migrations.DeleteModel(
            name='ApiInterface',
        ),
        # Update the TestCase.api_interface foreign key to point to common.apiinterface
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
