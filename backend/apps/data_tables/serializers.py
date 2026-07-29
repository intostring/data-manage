from rest_framework import serializers

from .models import (
    AccountRecord,
    AdviserInfo,
    AdviserProduct,
    AdviserProductApi,
    AdviserProductHeader,
    AdviserTradingFund,
    AdviserTradingOrder,
    AdviserTradingPosition,
    AdviserTradingTrade,
    FundCodesLh,
    FundNetValue,
    FundNetValueHypo,
    FundShareChg,
    ProductFundInfo,
    ProductHoldingDaily,
    ProductHoldingDailyGs,
    ProductHoldingDailyMix,
    ProductNav,
    ProductNav2,
)
from .registry import table_registry


class AccountRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccountRecord
        fields = '__all__'


class AdviserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdviserInfo
        fields = '__all__'


class AdviserProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdviserProduct
        fields = '__all__'


class AdviserProductApiSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdviserProductApi
        fields = '__all__'


class AdviserProductHeaderSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdviserProductHeader
        fields = '__all__'


class AdviserTradingFundSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdviserTradingFund
        fields = '__all__'


class AdviserTradingOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdviserTradingOrder
        fields = '__all__'


class AdviserTradingPositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdviserTradingPosition
        fields = '__all__'


class AdviserTradingTradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdviserTradingTrade
        fields = '__all__'


# ---- FOF 数据表 Serializer ----

class FundCodesLhSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundCodesLh
        fields = '__all__'


class FundNetValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundNetValue
        fields = '__all__'


class FundNetValueHypoSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundNetValueHypo
        fields = '__all__'


class FundShareChgSerializer(serializers.ModelSerializer):
    class Meta:
        model = FundShareChg
        fields = '__all__'


class ProductFundInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductFundInfo
        fields = '__all__'


class ProductHoldingDailyGsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductHoldingDailyGs
        fields = '__all__'


class ProductHoldingDailyMixSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductHoldingDailyMix
        fields = '__all__'


class ProductHoldingDailySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductHoldingDaily
        fields = '__all__'


class ProductNavSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductNav
        fields = '__all__'


class ProductNav2Serializer(serializers.ModelSerializer):
    class Meta:
        model = ProductNav2
        fields = '__all__'


# 注册全部已有表：URL 标识 / Model / Serializer / 显示名 / 分组
# MOM 数据
table_registry.register('account_record', AccountRecord, AccountRecordSerializer, '账户记录', 'mom')
table_registry.register('adviser_info', AdviserInfo, AdviserInfoSerializer, '投顾信息', 'mom')
table_registry.register('adviser_product', AdviserProduct, AdviserProductSerializer, '投顾产品', 'mom')
table_registry.register('adviser_product_api', AdviserProductApi, AdviserProductApiSerializer, '产品API', 'mom')
table_registry.register('adviser_product_header', AdviserProductHeader, AdviserProductHeaderSerializer, '产品详情', 'mom')
table_registry.register('adviser_trading_fund', AdviserTradingFund, AdviserTradingFundSerializer, '资金数据', 'mom')
table_registry.register('adviser_trading_order', AdviserTradingOrder, AdviserTradingOrderSerializer, '委托数据', 'mom')
table_registry.register('adviser_trading_position', AdviserTradingPosition, AdviserTradingPositionSerializer, '持仓数据', 'mom')
table_registry.register('adviser_trading_trade', AdviserTradingTrade, AdviserTradingTradeSerializer, '成交数据', 'mom')
# FOF 数据
table_registry.register('fund_codes_lh', FundCodesLh, FundCodesLhSerializer, '基金代码', 'fof')
table_registry.register('fund_net_value', FundNetValue, FundNetValueSerializer, '基金净值', 'fof')
table_registry.register('fund_net_value_hypo', FundNetValueHypo, FundNetValueHypoSerializer, '虚拟净值', 'fof')
table_registry.register('fund_share_chg', FundShareChg, FundShareChgSerializer, '基金申赎', 'fof')
table_registry.register('product_fund_info', ProductFundInfo, ProductFundInfoSerializer, '持仓基金', 'fof')
table_registry.register('product_holding_daily_gs', ProductHoldingDailyGs, ProductHoldingDailyGsSerializer, '每日持仓(固收)', 'fof')
table_registry.register('product_holding_daily_mix', ProductHoldingDailyMix, ProductHoldingDailyMixSerializer, '每日持仓(混合)', 'fof')
table_registry.register('product_holding_daily', ProductHoldingDaily, ProductHoldingDailySerializer, '每日持仓', 'fof')
table_registry.register('product_nav', ProductNav, ProductNavSerializer, 'FOF净值1', 'fof')
table_registry.register('product_nav2', ProductNav2, ProductNav2Serializer, 'FOF净值2', 'fof')
