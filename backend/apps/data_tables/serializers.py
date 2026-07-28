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


# 注册全部已有表：URL 标识 / Model / Serializer / 显示名
table_registry.register('account_record', AccountRecord, AccountRecordSerializer, '账户记录')
table_registry.register('adviser_info', AdviserInfo, AdviserInfoSerializer, '投顾信息')
table_registry.register('adviser_product', AdviserProduct, AdviserProductSerializer, '投顾产品')
table_registry.register('adviser_product_api', AdviserProductApi, AdviserProductApiSerializer, '产品API')
table_registry.register('adviser_product_header', AdviserProductHeader, AdviserProductHeaderSerializer, '产品详情')
table_registry.register('adviser_trading_fund', AdviserTradingFund, AdviserTradingFundSerializer, '资金数据')
table_registry.register('adviser_trading_order', AdviserTradingOrder, AdviserTradingOrderSerializer, '委托数据')
table_registry.register('adviser_trading_position', AdviserTradingPosition, AdviserTradingPositionSerializer, '持仓数据')
table_registry.register('adviser_trading_trade', AdviserTradingTrade, AdviserTradingTradeSerializer, '成交数据')
