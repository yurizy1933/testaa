# Generated manually to allow api_interface to be nullable

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("common", "0002_alter_apidoc_options_alter_doc_options_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="testdata",
            name="api_interface",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="test_data",
                to="common.apiinterface",
                verbose_name="所属接口",
            ),
        ),
    ]
