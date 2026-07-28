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
        return _VS

    router.register(entry.key, _make_viewset(), basename=f'table-{entry.key}')

urlpatterns = [
    path('', views.list_tables, name='list-tables'),
    path('', include(router.urls)),
]
