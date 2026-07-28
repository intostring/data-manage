import json

from django.db import models


class TableMeta(models.Model):
    """动态上传表的元信息记录。

    实际数据存储在 dynamic_<key> 表中（由 services.py 原生 SQL 建表）。
    """
    key = models.SlugField(max_length=64, unique=True, help_text='URL 标识，仅字母数字下划线')
    label = models.CharField(max_length=128, help_text='显示名称')
    table_name = models.CharField(max_length=80, help_text='实际物理表名 dynamic_<key>')
    columns = models.TextField(help_text='列定义 JSON: [{"name":"id","type":"int"}, ...]')
    row_count = models.BigIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = True
        db_table = 'dynamic_table_meta'
        ordering = ['-created_at']

    def get_columns(self):
        return json.loads(self.columns)

    def set_columns(self, cols):
        self.columns = json.dumps(cols, ensure_ascii=False)

    def __str__(self):
        return f'{self.label} ({self.table_name})'
