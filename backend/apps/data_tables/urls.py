from django.urls import path, include
from rest_framework.routers import DefaultRouter

from . import views
from .registry import table_registry
from . import serializers  # 触发注册：执行 serializers.py 中的 table_registry.register() 调用

router = DefaultRouter()

# 为每张已注册表动态生成 ViewSet 子类并注册路由
for entry in table_registry.all():
    def _make_viewset(model=entry.model, serializer=entry.serializer):
        class _VS(views.DynamicModelViewSet):
            pass
        _VS.model = model
        _VS.serializer_class = serializer
        # 表无 id 字段时，使用模型 Meta.ordering 作为默认排序，避免按 id 排序报错
        if not any(f.name == 'id' for f in model._meta.fields):
            _VS.ordering = list(model._meta.ordering) if model._meta.ordering else None
        return _VS

    router.register(entry.key, _make_viewset(), basename=f'table-{entry.key}')

urlpatterns = [
    path('', views.list_tables, name='list-tables'),
    path('<str:key>/columns/', views.table_columns, name='table-columns'),
    path('<str:key>/export/', views.table_export, name='table-export'),
    path('<str:key>/import/', views.table_import, name='table-import'),
    path('<str:key>/template/', views.table_template, name='table-template'),
    path('', include(router.urls)),
]
