from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("data_tables", "0008_advisor_info_dividend_rate"),
    ]

    operations = [
        migrations.AlterField(
            model_name="advisorinfo",
            name="margin_call_risk",
            field=models.DecimalField(
                blank=True, db_comment="追保风险线", decimal_places=2,
                max_digits=18, null=True, verbose_name="追保风险线",
            ),
        ),
        migrations.AlterField(
            model_name="advisorinfo",
            name="force_close_risk",
            field=models.DecimalField(
                blank=True, db_comment="强平风险线", decimal_places=2,
                max_digits=18, null=True, verbose_name="强平风险线",
            ),
        ),
    ]
