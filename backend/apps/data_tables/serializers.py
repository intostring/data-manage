from rest_framework import serializers

from .models import (
    FutMarketData,
    FutMarketStats,
    FutSectorIndex,
    FutSymbolInfo,
    MomAccountRecord,
    MomProductInfo,
    OptMarketData,
    OptRiskStats,
    PerfProducts,
    PerfRiskIndicators,
    QuotesDynamic,
    QuotesStatic,
    RhAdvisors,
    RhFunds,
    RhOrders,
    RhPositions,
    RhTrades,
)
from .registry import table_registry


class MomAccountRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = MomAccountRecord
        fields = '__all__'


class MomProductInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MomProductInfo
        fields = '__all__'


class PerfProductsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerfProducts
        fields = '__all__'


class PerfRiskIndicatorsSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerfRiskIndicators
        fields = '__all__'


class QuotesDynamicSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotesDynamic
        fields = '__all__'


class QuotesStaticSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuotesStatic
        fields = '__all__'


class RhAdvisorsSerializer(serializers.ModelSerializer):
    class Meta:
        model = RhAdvisors
        fields = '__all__'


class RhFundsSerializer(serializers.ModelSerializer):
    class Meta:
        model = RhFunds
        fields = '__all__'


class RhOrdersSerializer(serializers.ModelSerializer):
    class Meta:
        model = RhOrders
        fields = '__all__'


class RhPositionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = RhPositions
        fields = '__all__'


class RhTradesSerializer(serializers.ModelSerializer):
    class Meta:
        model = RhTrades
        fields = '__all__'


class FutSymbolInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = FutSymbolInfo
        fields = '__all__'


class FutSectorIndexSerializer(serializers.ModelSerializer):
    class Meta:
        model = FutSectorIndex
        fields = '__all__'


class FutMarketDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = FutMarketData
        fields = '__all__'


class FutMarketStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FutMarketStats
        fields = '__all__'


class OptRiskStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptRiskStats
        fields = '__all__'


class OptMarketDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptMarketData
        fields = '__all__'


table_registry.register('mom_account_record', MomAccountRecord, MomAccountRecordSerializer, 'MOM账户记录', 'mom')
table_registry.register('mom_product_info', MomProductInfo, MomProductInfoSerializer, 'MOM产品信息', 'mom')
table_registry.register('perf_products', PerfProducts, PerfProductsSerializer, '绩效产品', 'performance')
table_registry.register('perf_risk_indicators', PerfRiskIndicators, PerfRiskIndicatorsSerializer, '风险指标', 'performance')
table_registry.register('quotes_dynamic', QuotesDynamic, QuotesDynamicSerializer, '动态语录', 'quotes')
table_registry.register('quotes_static', QuotesStatic, QuotesStaticSerializer, '静态语录', 'quotes')
table_registry.register('rh_advisors', RhAdvisors, RhAdvisorsSerializer, '投顾账户', 'rh')
table_registry.register('rh_funds', RhFunds, RhFundsSerializer, '权益信息', 'rh')
table_registry.register('rh_orders', RhOrders, RhOrdersSerializer, '委托信息', 'rh')
table_registry.register('rh_positions', RhPositions, RhPositionsSerializer, '持仓信息', 'rh')
table_registry.register('rh_trades', RhTrades, RhTradesSerializer, '成交信息', 'rh')
table_registry.register('fut_symbol_info', FutSymbolInfo, FutSymbolInfoSerializer, '期货品种信息', 'futures')
table_registry.register('fut_sector_index', FutSectorIndex, FutSectorIndexSerializer, '期货板块指数', 'futures')
table_registry.register('fut_market_data', FutMarketData, FutMarketDataSerializer, '期货行情数据', 'futures')
table_registry.register('fut_market_stats', FutMarketStats, FutMarketStatsSerializer, '期货市场统计', 'futures')
table_registry.register('opt_risk_stats', OptRiskStats, OptRiskStatsSerializer, '期权风险指标', 'options')
table_registry.register('opt_market_data', OptMarketData, OptMarketDataSerializer, '期权行情数据', 'options')
