"""
已有表注册中心。

将 (URL key, Model, Serializer) 三元组集中注册，
ViewSet 与 Router 据此动态生成 CRUD 端点，避免为每张表写重复样板。
"""
from dataclasses import dataclass, field
from typing import Dict, List, Type

from django.db import models
from rest_framework.serializers import Serializer


# Django 字段类型 → 前端展示用类型映射
FIELD_TYPE_MAP = {
    models.CharField: 'str',
    models.TextField: 'text',
    models.IntegerField: 'int',
    models.BigIntegerField: 'int',
    models.SmallIntegerField: 'int',
    models.PositiveIntegerField: 'int',
    models.AutoField: 'int',
    models.BigAutoField: 'int',
    models.FloatField: 'float',
    models.DecimalField: 'float',
    models.BooleanField: 'bool',
    models.DateTimeField: 'datetime',
    models.DateField: 'date',
    models.TimeField: 'datetime',
}


def _field_type(field) -> str:
    """根据 Django model 字段推断展示类型"""
    for cls, t in FIELD_TYPE_MAP.items():
        if isinstance(field, cls):
            return t
    return 'str'


@dataclass
class TableEntry:
    key: str           # URL 标识
    model: Type        # Django Model
    serializer: Type[Serializer]
    label: str = ''    # 显示名（可选）
    group: str = 'mom' # 分组：mom / fof

    def get_columns(self) -> List[dict]:
        """返回字段元信息列表：[{name, label, type}]

        label 优先取 db_comment（阿里云表已配置中文注释），其次 verbose_name，最后用字段名。
        """
        cols = []
        for f in self.model._meta.fields:
            label = getattr(f, 'db_comment', None) or getattr(f, 'verbose_name', None) or f.name
            # verbose_name 可能是空字符串
            if not label:
                label = f.name
            cols.append({
                'name': f.name,
                'label': str(label),
                'type': _field_type(f),
                'primary_key': f.primary_key,
            })
        return cols


class TableRegistry:
    def __init__(self) -> None:
        self._entries: Dict[str, TableEntry] = {}

    def register(self, key: str, model: Type, serializer: Type[Serializer], label: str = '', group: str = 'mom') -> None:
        self._entries[key] = TableEntry(key=key, model=model, serializer=serializer, label=label or key, group=group)

    def get(self, key: str) -> TableEntry:
        return self._entries[key]

    def all(self):
        return list(self._entries.values())

    def keys(self):
        return list(self._entries.keys())


table_registry = TableRegistry()
