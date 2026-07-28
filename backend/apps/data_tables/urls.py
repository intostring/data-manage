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
        # 动态生成 FilterSet 并设为类属性，DRF 的 DjangoFilterBackend 直接读取此属性
        _VS.filterset_class = views._make_filterset(model)
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
