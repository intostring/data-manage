from rest_framework import serializers

from .models import (
    FutMarketData,
    FutMarketStats,
    FutCodesZl,
    FutContractStats,
    FutSectorIndex,
    FutSymbolInfo,
    FofEmailHypo,
    FofEmailNav,
    FofFundInfo,
    FofFundShareChg,
    FofHoldingDaily,
    FofHoldingDailyMix,
    FofNavHypo,
    FofProductNav,
    FofProductNav2,
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
    TradeDays,
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


class FofEmailHypoSerializer(serializers.ModelSerializer):
    class Meta:
        model = FofEmailHypo
        fields = '__all__'


class FofEmailNavSerializer(serializers.ModelSerializer):
    class Meta:
        model = FofEmailNav
        fields = '__all__'


class FofFundInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = FofFundInfo
        fields = '__all__'


class FofFundShareChgSerializer(serializers.ModelSerializer):
    class Meta:
        model = FofFundShareChg
        fields = '__all__'


class FofHoldingDailySerializer(serializers.ModelSerializer):
    class Meta:
        model = FofHoldingDaily
        fields = '__all__'


class FofHoldingDailyMixSerializer(serializers.ModelSerializer):
    class Meta:
        model = FofHoldingDailyMix
        fields = '__all__'


class FofNavHypoSerializer(serializers.ModelSerializer):
    class Meta:
        model = FofNavHypo
        fields = '__all__'


class FofProductNavSerializer(serializers.ModelSerializer):
    class Meta:
        model = FofProductNav
        fields = '__all__'


class FofProductNav2Serializer(serializers.ModelSerializer):
    class Meta:
        model = FofProductNav2
        fields = '__all__'


class FutCodesZlSerializer(serializers.ModelSerializer):
    class Meta:
        model = FutCodesZl
        fields = '__all__'


class FutContractStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FutContractStats
        fields = '__all__'


class TradeDaysSerializer(serializers.ModelSerializer):
    class Meta:
        model = TradeDays
        fields = '__all__'


table_registry.register('mom_account_record', MomAccountRecord, MomAccountRecordSerializer, 'MOM账户记录', 'mom')
table_registry.register('mom_product_info', MomProductInfo, MomProductInfoSerializer, 'MOM产品信息', 'mom')
table_registry.register('perf_products', PerfProducts, PerfProductsSerializer, '绩效产品', 'performance')
table_registry.register('perf_risk_indicators', PerfRiskIndicators, PerfRiskIndicatorsSerializer, '风险指标', 'performance')
table_registry.register('rh_advisors', RhAdvisors, RhAdvisorsSerializer, '投顾账户', 'rh')
table_registry.register('rh_funds', RhFunds, RhFundsSerializer, '权益信息', 'rh')
table_registry.register('rh_orders', RhOrders, RhOrdersSerializer, '委托信息', 'rh')
table_registry.register('rh_positions', RhPositions, RhPositionsSerializer, '持仓信息', 'rh')
table_registry.register('rh_trades', RhTrades, RhTradesSerializer, '成交信息', 'rh')
table_registry.register('fut_symbol_info', FutSymbolInfo, FutSymbolInfoSerializer, '期货品种信息', 'futures')
table_registry.register('fut_sector_index', FutSectorIndex, FutSectorIndexSerializer, '期货板块指数', 'futures')
table_registry.register('fut_market_data', FutMarketData, FutMarketDataSerializer, '期货行情数据', 'futures')
table_registry.register('fut_market_stats', FutMarketStats, FutMarketStatsSerializer, '期货市场统计', 'futures')
table_registry.register('fut_codes_zl', FutCodesZl, FutCodesZlSerializer, '期货主连代码', 'futures')
table_registry.register('fut_contract_stats', FutContractStats, FutContractStatsSerializer, '期货合约统计', 'futures')
table_registry.register('opt_risk_stats', OptRiskStats, OptRiskStatsSerializer, '期权风险指标', 'options')
table_registry.register('opt_market_data', OptMarketData, OptMarketDataSerializer, '期权行情数据', 'options')
table_registry.register('fof_email_hypo', FofEmailHypo, FofEmailHypoSerializer, '邮件虚拟净值', 'fof')
table_registry.register('fof_email_nav', FofEmailNav, FofEmailNavSerializer, '邮件基金净值', 'fof')
table_registry.register('fof_fund_info', FofFundInfo, FofFundInfoSerializer, 'FOF持仓基金', 'fof')
table_registry.register('fof_fund_share_chg', FofFundShareChg, FofFundShareChgSerializer, 'FOF份额变动', 'fof')
table_registry.register('fof_holding_daily', FofHoldingDaily, FofHoldingDailySerializer, 'FOF每日持仓', 'fof')
table_registry.register('fof_holding_daily_mix', FofHoldingDailyMix, FofHoldingDailyMixSerializer, 'FOF持仓混合', 'fof')
table_registry.register('fof_nav_hypo', FofNavHypo, FofNavHypoSerializer, 'FOF虚拟净值', 'fof')
table_registry.register('fof_product_nav', FofProductNav, FofProductNavSerializer, '渊流产品净值', 'fof')
table_registry.register('fof_product_nav2', FofProductNav2, FofProductNav2Serializer, '臻选贰号净值', 'fof')
table_registry.register('trade_days', TradeDays, TradeDaysSerializer, '交易日历', 'fof')
