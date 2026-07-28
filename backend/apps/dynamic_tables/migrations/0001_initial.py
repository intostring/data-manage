from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='TableMeta',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.SlugField(help_text='URL 标识，仅字母数字下划线', max_length=64, unique=True)),
                ('label', models.CharField(help_text='显示名称', max_length=128)),
                ('table_name', models.CharField(help_text='实际物理表名 dynamic_<key>', max_length=80)),
                ('columns', models.TextField(help_text='列定义 JSON: [{"name":"id","type":"int"}, ...]')),
                ('row_count', models.BigIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'dynamic_table_meta',
                'ordering': ['-created_at'],
            },
        ),
    ]
