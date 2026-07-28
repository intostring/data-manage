"""
已有表注册中心。

将 (URL key, Model, Serializer) 三元组集中注册，
ViewSet 与 Router 据此动态生成 CRUD 端点，避免为每张表写重复样板。
"""
from dataclasses import dataclass, field
from typing import Dict, Type

from rest_framework.serializers import Serializer


@dataclass
class TableEntry:
    key: str           # URL 标识
    model: Type        # Django Model
    serializer: Type[Serializer]
    label: str = ''    # 显示名（可选）


class TableRegistry:
    def __init__(self) -> None:
        self._entries: Dict[str, TableEntry] = {}

    def register(self, key: str, model: Type, serializer: Type[Serializer], label: str = '') -> None:
        self._entries[key] = TableEntry(key=key, model=model, serializer=serializer, label=label or key)

    def get(self, key: str) -> TableEntry:
        return self._entries[key]

    def all(self):
        return list(self._entries.values())

    def keys(self):
        return list(self._entries.keys())


table_registry = TableRegistry()
