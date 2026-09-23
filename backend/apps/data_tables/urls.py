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
        if entry.key == 'perf_risk_indicators':
            _VS.ordering = ['pid', 'id']
        # 表无 id 字段时，使用真实主键字段排序，避免按 id 排序报错
        elif not any(f.name == 'id' for f in model._meta.fields):
            _VS.ordering = [f'-{model._meta.pk.name}']
        return _VS

    router.register(entry.key, _make_viewset(), basename=f'table-{entry.key}')

urlpatterns = [
    path('', views.list_tables, name='list-tables'),
    path('<str:key>/columns/', views.table_columns, name='table-columns'),
    path('<str:key>/export/', views.table_export, name='table-export'),
    path('<str:key>/import/', views.table_import, name='table-import'),
    path('<str:key>/template/', views.table_template, name='table-template'),
    path('advisor/performance/', views.advisor_performance, name='advisor-performance'),
    path('sector/varieties/', views.sector_varieties, name='sector-varieties'),
    path('sector/board/', views.sector_board, name='sector-board'),
    path('sector/bk-latest/', views.sector_bk_latest, name='sector-bk-latest'),
    path('sector/bk-margin/', views.sector_bk_margin, name='sector-bk-margin'),
    path('sector/bk-net-risk/', views.sector_bk_net_risk, name='sector-bk-net-risk'),
    path('sector/bk-detail-tree/', views.sector_bk_detail_tree, name='sector-bk-detail-tree'),
    path('sector/position-overview/', views.sector_position_overview, name='sector-position-overview'),
    path('position/variety-advisor-long-short/', views.variety_advisor_long_short, name='variety-advisor-long-short'),
    path('trade/advisor-overview/', views.advisor_trade_overview, name='advisor-trade-overview'),
    path('variety/top-margin/', views.variety_top_margin, name='variety-top-margin'),
    path('variety/top-net-risk/', views.variety_top_net_risk, name='variety-top-net-risk'),
    path('sector/pnl/', views.sector_pnl, name='sector-pnl'),
    path('sector/pnl-ranking/', views.sector_pnl_ranking, name='sector-pnl-ranking'),
    path('option/pnl/', views.option_pnl, name='option-pnl'),
    path('sector/contract-kline/', views.sector_contract_kline, name='sector-contract-kline'),
    path('sector/advisor-variety/', views.sector_advisor_variety, name='sector-advisor-variety'),
    path('', include(router.urls)),
]
