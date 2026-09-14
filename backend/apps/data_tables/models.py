"""Models for existing MySQL tables in yl-webdata.

Generated from Aliyun RDS with `inspectdb`, then lightly cleaned:
- all tables remain managed=False
- tables without a physical id column use a stable natural primary key
"""
from django.db import models


class MomAccountRecord(models.Model):
    account_id = models.CharField(primary_key=True, max_length=50, db_comment='账户名称')
    account_category = models.CharField(max_length=50, blank=True, null=True, db_comment='账户类型')
    product_name = models.CharField(max_length=50, blank=True, null=True, db_comment='所属产品')
    account_name = models.CharField(max_length=50, blank=True, null=True, db_comment='开户人')
    account_certificate = models.CharField(max_length=50, blank=True, null=True, db_comment='证件号')
    manager = models.CharField(max_length=50, blank=True, null=True, db_comment='管理员')
    create_time = models.CharField(max_length=50, blank=True, null=True, db_comment='创建时间')
    status = models.CharField(max_length=10, blank=True, null=True, db_comment='状态')
    cum_investment = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='总投资金额')
    stop_loss_rate = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True, db_comment='止损线')
    max_pos_rate = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True, db_comment='保证金最大使用比例')
    mk_bf = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='初始市值（26年初or26年新投）')
    is_stop = models.IntegerField(blank=True, null=True, db_comment='是否停止（1为停止，0为持仓）')
    account_tag = models.IntegerField(blank=True, null=True, db_comment='投顾的类型（1：外部投顾；2：内部投顾；3：外部代持；4：内部持仓')
    perf_fee = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True, db_comment='业绩报酬比例')
    distribution_26 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='26年分红')
    distribution_bf = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='历史分红')
    redeem_mv = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='赎回市值')
    new_add = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='当日新增规模')
    tips = models.CharField(max_length=255, blank=True, null=True, db_comment='说明')
    invest_cate = models.CharField(max_length=255, blank=True, null=True, db_comment='投资品种')
    invest_logic = models.CharField(max_length=255, blank=True, null=True, db_comment='投资逻辑')

    class Meta:
        managed = False
        db_table = 'mom_account_record'


class MomProductInfo(models.Model):
    product_code = models.CharField(primary_key=True, max_length=50)
    product_name = models.CharField(max_length=50, blank=True, null=True)
    market_value_26bf = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='26年年初规模')
    new_add = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='新增规模，用来计算用，到账后一天清零')

    class Meta:
        managed = False
        db_table = 'mom_product_info'


class PerfProducts(models.Model):
    id = models.BigAutoField(primary_key=True)
    pid = models.BigIntegerField(blank=True, null=True, db_comment='产品ID')
    product_name = models.CharField(max_length=255, blank=True, null=True, db_comment='产品名称')
    is_support_type = models.FloatField(blank=True, null=True, db_comment='支持类型')
    last_edit_ts = models.BigIntegerField(blank=True, null=True, db_comment='最后更新时间戳(毫秒)')
    third_party_account = models.FloatField(blank=True, null=True, db_comment='第三方账户标记')
    product_type = models.FloatField(blank=True, null=True, db_comment='产品类型')
    raw_json = models.JSONField(db_comment='接口原始行JSON')
    created_at = models.DateTimeField(db_comment='入库时间')

    class Meta:
        managed = False
        db_table = 'perf_products'


class PerfRiskIndicators(models.Model):
    id = models.BigAutoField(primary_key=True)
    pid = models.BigIntegerField(blank=True, null=True, db_comment='产品ID')
    annual_yield_1y = models.FloatField(blank=True, null=True, db_comment='年化收益率(1年)')
    annual_volatility_1y = models.FloatField(blank=True, null=True, db_comment='年化波动率(1年)')
    max_drawdown_1y = models.FloatField(blank=True, null=True, db_comment='最大回撤(1年)')
    sharpe_ratio_1y = models.FloatField(blank=True, null=True, db_comment='夏普比率(1年)')
    kama_ratio_1y = models.FloatField(blank=True, null=True, db_comment='卡玛比率(1年)')
    info_ratio_1y = models.FloatField(blank=True, null=True, db_comment='信息比率(1年)')
    alpha_1y = models.FloatField(blank=True, null=True, db_comment='Alpha(1年)')
    beta_1y = models.FloatField(blank=True, null=True, db_comment='Beta(1年)')
    annual_yield_2y = models.FloatField(blank=True, null=True, db_comment='年化收益率(2年)')
    annual_volatility_2y = models.FloatField(blank=True, null=True, db_comment='年化波动率(2年)')
    max_drawdown_2y = models.FloatField(blank=True, null=True, db_comment='最大回撤(2年)')
    sharpe_ratio_2y = models.FloatField(blank=True, null=True, db_comment='夏普比率(2年)')
    kama_ratio_2y = models.FloatField(blank=True, null=True, db_comment='卡玛比率(2年)')
    info_ratio_2y = models.FloatField(blank=True, null=True, db_comment='信息比率(2年)')
    alpha_2y = models.FloatField(blank=True, null=True, db_comment='Alpha(2年)')
    beta_2y = models.FloatField(blank=True, null=True, db_comment='Beta(2年)')
    annual_yield_3y = models.FloatField(blank=True, null=True, db_comment='年化收益率(3年)')
    annual_volatility_3y = models.FloatField(blank=True, null=True, db_comment='年化波动率(3年)')
    max_drawdown_3y = models.FloatField(blank=True, null=True, db_comment='最大回撤(3年)')
    sharpe_ratio_3y = models.FloatField(blank=True, null=True, db_comment='夏普比率(3年)')
    kama_ratio_3y = models.FloatField(blank=True, null=True, db_comment='卡玛比率(3年)')
    info_ratio_3y = models.FloatField(blank=True, null=True, db_comment='信息比率(3年)')
    alpha_3y = models.FloatField(blank=True, null=True, db_comment='Alpha(3年)')
    beta_3y = models.FloatField(blank=True, null=True, db_comment='Beta(3年)')
    annual_yield_since = models.FloatField(blank=True, null=True, db_comment='年化收益率(成立以来)')
    annual_volatility_since = models.FloatField(blank=True, null=True, db_comment='年化波动率(成立以来)')
    max_drawdown_since = models.FloatField(blank=True, null=True, db_comment='最大回撤(成立以来)')
    sharpe_ratio_since = models.FloatField(blank=True, null=True, db_comment='夏普比率(成立以来)')
    kama_ratio_since = models.FloatField(blank=True, null=True, db_comment='卡玛比率(成立以来)')
    info_ratio_since = models.FloatField(blank=True, null=True, db_comment='信息比率(成立以来)')
    alpha_since = models.FloatField(blank=True, null=True, db_comment='Alpha(成立以来)')
    beta_since = models.FloatField(blank=True, null=True, db_comment='Beta(成立以来)')
    raw_json = models.JSONField(db_comment='接口原始行JSON')
    created_at = models.DateTimeField(db_comment='入库时间')

    class Meta:
        managed = False
        db_table = 'perf_risk_indicators'


class PerfNetValues(models.Model):
    id = models.BigAutoField(primary_key=True)
    pid = models.BigIntegerField(blank=True, null=True, db_comment='产品ID')
    trade_date = models.DateField(blank=True, null=True, db_comment='交易日期')
    net_value = models.FloatField(blank=True, null=True, db_comment='单位净值')
    accumulated_net = models.FloatField(blank=True, null=True, db_comment='累计净值')
    daily_return_rate = models.FloatField(blank=True, null=True, db_comment='日收益率')
    bonus_net_value = models.FloatField(blank=True, null=True, db_comment='分红净值')
    sum_bonus_net_value = models.CharField(max_length=255, blank=True, null=True, db_comment='累计分红净值')
    net_value_type = models.FloatField(blank=True, null=True, db_comment='净值类型')
    raw_json = models.JSONField(db_comment='接口原始行JSON')
    created_at = models.DateTimeField(db_comment='入库时间')

    class Meta:
        managed = False
        db_table = 'perf_net_values'


class QuotesDynamic(models.Model):
    uid = models.CharField(primary_key=True, max_length=64)
    text = models.CharField(max_length=512, blank=True, null=True)
    author = models.CharField(max_length=128, blank=True, null=True)
    content_hash = models.CharField(max_length=64, blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    content_changed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'quotes_dynamic'


class QuotesStatic(models.Model):
    uid = models.CharField(primary_key=True, max_length=64)
    text = models.CharField(max_length=512, blank=True, null=True)
    author = models.CharField(max_length=128, blank=True, null=True)
    tags = models.CharField(max_length=512, blank=True, null=True)
    content_hash = models.CharField(max_length=64, blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)
    content_changed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'quotes_static'


class RhAdvisors(models.Model):
    id = models.BigAutoField(primary_key=True)
    account_id = models.BigIntegerField(blank=True, null=True, db_comment='账户ID')
    account = models.CharField(max_length=255, blank=True, null=True, db_comment='账户名称')
    issupporttype = models.CharField(max_length=255, blank=True, null=True, db_comment='账户类型代码')
    account_type = models.CharField(max_length=255, blank=True, null=True, db_comment='账户类型')
    product_name = models.CharField(max_length=255, blank=True, null=True, db_comment='所属产品')
    product_id = models.BigIntegerField(blank=True, null=True, db_comment='产品ID')
    count_num = models.BigIntegerField(blank=True, null=True, db_comment='子账户数量')
    department_id = models.BigIntegerField(blank=True, null=True, db_comment='部门ID')
    department_name = models.CharField(max_length=255, blank=True, null=True, db_comment='部门名称')
    customer_id = models.BigIntegerField(blank=True, null=True, db_comment='开户人ID')
    account_holder = models.CharField(max_length=255, blank=True, null=True, db_comment='开户人')
    id_card = models.CharField(max_length=255, blank=True, null=True, db_comment='证件号')
    total_positions = models.BigIntegerField(blank=True, null=True, db_comment='总持仓')
    total_position_cost = models.FloatField(blank=True, null=True, db_comment='总持仓成本')
    master_name = models.CharField(max_length=255, blank=True, null=True, db_comment='管理员')
    create_time = models.CharField(max_length=255, blank=True, null=True, db_comment='创建时间')
    isdeleted = models.BigIntegerField(blank=True, null=True, db_comment='状态代码')
    status = models.CharField(max_length=255, blank=True, null=True, db_comment='状态')
    support_speculate = models.CharField(max_length=255, blank=True, null=True, db_comment='支持投机')
    midday_force_close = models.CharField(max_length=255, blank=True, null=True, db_comment='午盘强平')
    close_day_force_close = models.CharField(max_length=255, blank=True, null=True, db_comment='收盘强平')
    night_force_close = models.CharField(max_length=255, blank=True, null=True, db_comment='夜盘强平')
    auto_force_close_type = models.CharField(max_length=255, blank=True, null=True, db_comment='自动强平类型')
    auto_force_price_type = models.CharField(max_length=255, blank=True, null=True, db_comment='强平价格类型')
    force_add_tick = models.FloatField(blank=True, null=True, db_comment='强平追加Tick')
    force_limit_tick = models.FloatField(blank=True, null=True, db_comment='强平限制Tick')
    self_trade = models.FloatField(blank=True, null=True, db_comment='自成交')
    op_cost = models.FloatField(blank=True, null=True, db_comment='期权成本')
    margin_and_op = models.FloatField(blank=True, null=True, db_comment='保证金与期权')
    offset_setting = models.FloatField(blank=True, null=True, db_comment='平仓设置')
    raw_json = models.JSONField(db_comment='接口原始行JSON')
    created_at = models.DateTimeField(db_comment='入库时间')

    class Meta:
        managed = False
        db_table = 'rh_advisors'


class RhFunds(models.Model):
    id = models.BigAutoField(primary_key=True)
    trade_date = models.DateField(blank=True, null=True, db_comment='交易日')
    account = models.CharField(max_length=255, blank=True, null=True, db_comment='账户')
    group_name = models.CharField(max_length=255, blank=True, null=True, db_comment='组合名称')
    presettle_balance = models.FloatField(blank=True, null=True, db_comment='期初结存')
    settle_balance = models.FloatField(blank=True, null=True, db_comment='期末结存')
    declaration_fee = models.FloatField(blank=True, null=True, db_comment='申报费')
    margin = models.FloatField(blank=True, null=True, db_comment='保证金')
    fee = models.FloatField(blank=True, null=True, db_comment='手续费')
    premium_income = models.FloatField(blank=True, null=True, db_comment='权利金收入')
    premium_expense = models.FloatField(blank=True, null=True, db_comment='权利金支出')
    daily_close_profit = models.FloatField(blank=True, null=True, db_comment='逐日平盈')
    daily_position_profit = models.FloatField(blank=True, null=True, db_comment='逐日持盈')
    close_profit = models.FloatField(blank=True, null=True, db_comment='逐笔平盈')
    floating_profit_loss = models.FloatField(blank=True, null=True, db_comment='逐笔浮动盈亏')
    deposit_amount = models.FloatField(blank=True, null=True, db_comment='入金金额')
    withdraw_amount = models.FloatField(blank=True, null=True, db_comment='出金金额')
    long_option_market_value = models.FloatField(blank=True, null=True, db_comment='多头期权市值')
    short_option_market_value = models.FloatField(blank=True, null=True, db_comment='空头期权市值')
    market_profit = models.FloatField(blank=True, null=True, db_comment='市值盈利')
    shares = models.FloatField(blank=True, null=True, db_comment='份额')
    market_value_equity = models.FloatField(blank=True, null=True, db_comment='市值权益')
    long_option_mv_close = models.FloatField(blank=True, null=True, db_comment='多头期权市值(收盘价)')
    short_option_mv_close = models.FloatField(blank=True, null=True, db_comment='空头期权市值(收盘价)')
    presettle_balance_by_trade = models.FloatField(blank=True, null=True, db_comment='逐笔期初结存')
    settle_balance_by_trade = models.FloatField(blank=True, null=True, db_comment='逐笔期末结存')
    raw_json = models.JSONField(db_comment='接口原始行JSON')
    created_at = models.DateTimeField(db_comment='入库时间')

    class Meta:
        managed = False
        db_table = 'rh_funds'


class RhOrders(models.Model):
    id = models.BigAutoField(primary_key=True)
    trade_date = models.DateField(blank=True, null=True, db_comment='交易日')
    tradingdayname = models.CharField(max_length=255, blank=True, null=True, db_comment='交易日名称')
    account = models.CharField(max_length=255, blank=True, null=True, db_comment='账户')
    group_name = models.CharField(max_length=255, blank=True, null=True, db_comment='组合名称')
    order_no = models.CharField(max_length=255, blank=True, null=True, db_comment='报单编号')
    uuid = models.CharField(max_length=255, blank=True, null=True, db_comment='UUID')
    contract = models.CharField(max_length=255, blank=True, null=True, db_comment='合约')
    exchange = models.CharField(max_length=255, blank=True, null=True, db_comment='交易所')
    direction = models.CharField(max_length=255, blank=True, null=True, db_comment='方向代码')
    side = models.CharField(max_length=255, blank=True, null=True, db_comment='方向')
    comboffsetflag = models.CharField(max_length=255, blank=True, null=True, db_comment='开平标志代码')
    open_close = models.CharField(max_length=255, blank=True, null=True, db_comment='开平')
    hedge_flag = models.CharField(max_length=255, blank=True, null=True, db_comment='投保')
    order_type = models.CharField(max_length=255, blank=True, null=True, db_comment='报单类型')
    order_price = models.FloatField(blank=True, null=True, db_comment='价格')
    order_qty = models.FloatField(blank=True, null=True, db_comment='委托数量')
    trade_qty = models.FloatField(blank=True, null=True, db_comment='成交数量')
    orderstatus = models.CharField(max_length=255, blank=True, null=True, db_comment='报单状态代码')
    order_status = models.CharField(max_length=255, blank=True, null=True, db_comment='报单状态')
    remark = models.CharField(max_length=512, blank=True, null=True, db_comment='备注')
    order_time = models.CharField(max_length=255, blank=True, null=True, db_comment='报单时间')
    cancel_time = models.CharField(max_length=255, blank=True, null=True, db_comment='撤单时间')
    order_source = models.CharField(max_length=255, blank=True, null=True, db_comment='报单来源')
    isswaporder = models.FloatField(blank=True, null=True, db_comment='是否互换单')
    user_product_info = models.CharField(max_length=255, blank=True, null=True, db_comment='用户端产品信息')
    trade_account = models.CharField(max_length=255, blank=True, null=True, db_comment='交易账户')
    ip_address = models.CharField(max_length=255, blank=True, null=True, db_comment='IP地址')
    local_ip = models.CharField(max_length=255, blank=True, null=True, db_comment='内网IP')
    mac = models.CharField(max_length=255, blank=True, null=True, db_comment='MAC')
    hdd_num = models.FloatField(blank=True, null=True, db_comment='HD')
    mangername = models.CharField(max_length=255, blank=True, null=True, db_comment='管理端名称')
    mangertime = models.CharField(max_length=255, blank=True, null=True, db_comment='管理端时间')
    mangerstatusname = models.CharField(max_length=255, blank=True, null=True, db_comment='管理端状态')
    mangerip = models.CharField(max_length=255, blank=True, null=True, db_comment='管理端IP')
    mangermac = models.CharField(max_length=255, blank=True, null=True, db_comment='管理端MAC')
    riskername = models.CharField(max_length=255, blank=True, null=True, db_comment='风控端名称')
    riskertime = models.CharField(max_length=255, blank=True, null=True, db_comment='风控端时间')
    riskerstatusname = models.CharField(max_length=255, blank=True, null=True, db_comment='风控端状态')
    riskerip = models.CharField(max_length=255, blank=True, null=True, db_comment='风控端IP')
    riskermac = models.CharField(max_length=255, blank=True, null=True, db_comment='风控端MAC')
    investorname = models.CharField(max_length=255, blank=True, null=True, db_comment='下单端名称')
    investortime = models.CharField(max_length=255, blank=True, null=True, db_comment='下单端时间')
    investorstatusname = models.CharField(max_length=255, blank=True, null=True, db_comment='下单端状态')
    investorip = models.CharField(max_length=255, blank=True, null=True, db_comment='下单端IP')
    investormac = models.CharField(max_length=255, blank=True, null=True, db_comment='下单端MAC')
    raw_json = models.JSONField(db_comment='接口原始行JSON')
    created_at = models.DateTimeField(db_comment='入库时间')

    class Meta:
        managed = False
        db_table = 'rh_orders'


class RhPositions(models.Model):
    id = models.BigAutoField(primary_key=True)
    trade_date = models.DateField(blank=True, null=True, db_comment='交易日')
    account = models.CharField(max_length=255, blank=True, null=True, db_comment='账户')
    group_name = models.CharField(max_length=255, blank=True, null=True, db_comment='组合名称')
    account_holder = models.CharField(max_length=255, blank=True, null=True, db_comment='开户人姓名')
    contract = models.CharField(max_length=255, blank=True, null=True, db_comment='合约')
    exchange_id = models.CharField(max_length=255, blank=True, null=True, db_comment='交易所代码')
    exchange = models.CharField(max_length=255, blank=True, null=True, db_comment='交易所')
    direction = models.CharField(max_length=255, blank=True, null=True, db_comment='方向代码')
    side = models.CharField(max_length=255, blank=True, null=True, db_comment='买/卖')
    hedge_flag = models.CharField(max_length=255, blank=True, null=True, db_comment='投/保')
    instrument_type = models.CharField(max_length=255, blank=True, null=True, db_comment='品种类型')
    position_qty = models.FloatField(blank=True, null=True, db_comment='持仓量')
    open_date = models.CharField(max_length=255, blank=True, null=True, db_comment='开仓日期')
    open_time = models.CharField(max_length=255, blank=True, null=True, db_comment='开仓时间')
    open_price = models.FloatField(blank=True, null=True, db_comment='开仓价')
    settlement_price = models.FloatField(blank=True, null=True, db_comment='结算价')
    margin = models.FloatField(blank=True, null=True, db_comment='保证金')
    market_value = models.FloatField(blank=True, null=True, db_comment='持仓市值')
    daily_position_profit = models.FloatField(blank=True, null=True, db_comment='逐日持盈')
    position_profit = models.FloatField(blank=True, null=True, db_comment='逐笔持盈')
    raw_json = models.JSONField(db_comment='接口原始行JSON')
    created_at = models.DateTimeField(db_comment='入库时间')

    class Meta:
        managed = False
        db_table = 'rh_positions'


class RhTrades(models.Model):
    id = models.BigAutoField(primary_key=True)
    trade_date = models.DateField(blank=True, null=True, db_comment='交易日')
    account = models.CharField(max_length=255, blank=True, null=True, db_comment='账户')
    group_name = models.CharField(max_length=255, blank=True, null=True, db_comment='组合名称')
    account_holder = models.CharField(max_length=255, blank=True, null=True, db_comment='开户人姓名')
    trade_no = models.CharField(max_length=255, blank=True, null=True, db_comment='成交编号')
    counter_trade_no = models.CharField(max_length=255, blank=True, null=True, db_comment='柜台成交编号')
    counter_order_no = models.CharField(max_length=255, blank=True, null=True, db_comment='柜台报单编号')
    counter_account = models.CharField(max_length=255, blank=True, null=True, db_comment='柜台账户')
    uuid = models.CharField(max_length=255, blank=True, null=True, db_comment='UUID')
    contract = models.CharField(max_length=255, blank=True, null=True, db_comment='合约')
    exchange = models.CharField(max_length=255, blank=True, null=True, db_comment='交易所')
    direction = models.CharField(max_length=255, blank=True, null=True, db_comment='方向代码')
    side = models.CharField(max_length=255, blank=True, null=True, db_comment='买/卖')
    offsetflag = models.CharField(max_length=255, blank=True, null=True, db_comment='开平标志代码')
    open_close = models.CharField(max_length=255, blank=True, null=True, db_comment='开/平')
    hedge_flag = models.CharField(max_length=255, blank=True, null=True, db_comment='投机/套保')
    trade_price = models.FloatField(blank=True, null=True, db_comment='成交价')
    trade_qty = models.FloatField(blank=True, null=True, db_comment='数量')
    trade_amount = models.FloatField(blank=True, null=True, db_comment='成交额')
    fee = models.FloatField(blank=True, null=True, db_comment='手续费')
    premium_income_expense = models.FloatField(blank=True, null=True, db_comment='权利金收支')
    daily_close_profit = models.FloatField(blank=True, null=True, db_comment='逐日平盈')
    close_profit = models.FloatField(blank=True, null=True, db_comment='逐笔平盈')
    trade_time = models.CharField(max_length=255, blank=True, null=True, db_comment='成交时间')
    trade_account = models.CharField(max_length=255, blank=True, null=True, db_comment='交易账户')
    ip_address = models.CharField(max_length=255, blank=True, null=True, db_comment='IP')
    local_ip = models.CharField(max_length=255, blank=True, null=True, db_comment='内网IP')
    mac = models.CharField(max_length=255, blank=True, null=True, db_comment='MAC')
    raw_json = models.JSONField(db_comment='接口原始行JSON')
    created_at = models.DateTimeField(db_comment='入库时间')

    class Meta:
        managed = False
        db_table = 'rh_trades'


class FutSymbolInfo(models.Model):
    code = models.CharField(primary_key=True, max_length=50, db_comment='代码')
    symbol_code = models.CharField(max_length=50, blank=True, null=True, db_comment='品种代码')
    symbol_name = models.CharField(max_length=50, blank=True, null=True, db_comment='品种简称')
    exchange_code = models.CharField(max_length=50, blank=True, null=True, db_comment='交易所代码')
    exchange_name = models.CharField(max_length=50, blank=True, null=True, db_comment='交易所名称')
    symbol_cate = models.CharField(max_length=50, blank=True, null=True, db_comment='品种类型简称')
    symbol_cate_code = models.CharField(max_length=50, blank=True, null=True, db_comment='品种类型代码')
    symbol_cate_l1 = models.CharField(max_length=50, blank=True, null=True, db_comment='品种大类简称')
    symbol_cate_l1_code = models.CharField(max_length=50, blank=True, null=True, db_comment='品种大类代码')

    class Meta:
        managed = False
        db_table = 'fut_symbol_info'


class FutSectorIndex(models.Model):
    id = models.BigAutoField(primary_key=True, db_comment='自增主键')
    sector_code = models.CharField(max_length=30, db_comment='板块代码, 如 BK_BuildMat')
    sector_name = models.CharField(max_length=30, db_comment='板块名称, 如 非金属建材')
    trade_date = models.DateField(db_comment='交易日期')
    index_value = models.DecimalField(max_digits=16, decimal_places=4, db_comment='板块指数值(基期1000)')
    daily_chg = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True, db_comment='日涨跌幅(%)')
    member_cnt = models.IntegerField(db_comment='当日参与计算的品种数')
    create_time = models.DateTimeField(db_comment='创建时间')
    update_time = models.DateTimeField(db_comment='更新时间')

    class Meta:
        managed = False
        db_table = 'fut_sector_index'
        unique_together = (('sector_code', 'trade_date'),)
        db_table_comment = '期货板块指数(基于连续合约等权计算)'


class FutMarketData(models.Model):
    id = models.BigAutoField(primary_key=True, db_comment='自增主键')
    ts_code = models.CharField(max_length=50, db_comment='tushare合约代码')
    trade_date = models.DateField(db_comment='交易日期')
    pre_close = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, db_comment='昨收盘价')
    pre_settle = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, db_comment='昨结算价')
    open = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, db_comment='开盘价')
    high = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, db_comment='最高价')
    low = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, db_comment='最低价')
    close = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, db_comment='收盘价')
    settle = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, db_comment='结算价')
    change1 = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, db_comment='涨跌额1(收盘-昨收盘)')
    change2 = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, db_comment='涨跌额2(结算-昨结算)')
    vol = models.DecimalField(max_digits=20, decimal_places=0, blank=True, null=True, db_comment='成交量(手)')
    amount = models.DecimalField(max_digits=22, decimal_places=2, blank=True, null=True, db_comment='成交额(万元)')
    oi = models.DecimalField(max_digits=20, decimal_places=0, blank=True, null=True, db_comment='持仓量')
    oi_chg = models.DecimalField(max_digits=20, decimal_places=0, blank=True, null=True, db_comment='持仓量变化')
    create_time = models.DateTimeField(db_comment='创建时间')
    update_time = models.DateTimeField(db_comment='更新时间')

    class Meta:
        managed = False
        db_table = 'fut_market_data'
        unique_together = (('ts_code', 'trade_date'),)
        db_table_comment = '期货日线行情数据(tushare fut_daily)'


class FutMarketStats(models.Model):
    id = models.BigAutoField(primary_key=True, db_comment='自增主键')
    trade_date = models.DateField(db_comment='交易日期')
    variety_code = models.CharField(max_length=20, db_comment='品种代码, 如 CU')
    variety_name = models.CharField(max_length=30, db_comment='品种名称')
    sector_code = models.CharField(max_length=30, db_comment='板块代码')
    sector_name = models.CharField(max_length=30, db_comment='板块名称')
    close = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True)
    total_volume = models.DecimalField(max_digits=22, decimal_places=0, blank=True, null=True, db_comment='全市场总成交量(手)')
    total_oi = models.DecimalField(max_digits=22, decimal_places=0, blank=True, null=True, db_comment='全市场总持仓量(手)')
    vol_10d = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    vol_20d = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    vol_60d = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    create_time = models.DateTimeField(db_comment='创建时间')
    update_time = models.DateTimeField(db_comment='更新时间')

    class Meta:
        managed = False
        db_table = 'fut_market_stats'
        unique_together = (('trade_date', 'variety_code'),)
        db_table_comment = '全品种市场统计:波动率/持仓量/成交量'


class OptRiskStats(models.Model):
    ts_code = models.CharField(primary_key=True, max_length=40)
    trade_date = models.CharField(max_length=10)
    variety = models.CharField(max_length=10, blank=True, null=True)
    option_type = models.CharField(max_length=2, blank=True, null=True)
    strike = models.FloatField(blank=True, null=True)
    settle = models.FloatField(blank=True, null=True)
    underlying_price = models.FloatField(blank=True, null=True)
    days_to_expiry = models.IntegerField(blank=True, null=True)
    t = models.FloatField(db_column='T', blank=True, null=True)
    iv = models.FloatField(blank=True, null=True)
    delta_val = models.FloatField(blank=True, null=True)
    gamma = models.FloatField(blank=True, null=True)
    theta = models.FloatField(blank=True, null=True)
    vega = models.FloatField(blank=True, null=True)
    intrinsic_value = models.FloatField(blank=True, null=True)
    time_value = models.FloatField(blank=True, null=True)
    underlying_vol_10d = models.FloatField(blank=True, null=True)
    underlying_vol_20d = models.FloatField(blank=True, null=True)
    underlying_vol_60d = models.FloatField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'opt_risk_stats'
        unique_together = (('ts_code', 'trade_date'),)


class OptMarketData(models.Model):
    id = models.BigAutoField(primary_key=True, db_comment='自增主键')
    ts_code = models.CharField(max_length=50, db_comment='tushare期权代码')
    trade_date = models.DateField(db_comment='交易日期')
    exchange = models.CharField(max_length=10, db_comment='交易所')
    pre_settle = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, db_comment='昨结算价')
    pre_close = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, db_comment='昨收盘价')
    open = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, db_comment='开盘价')
    high = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, db_comment='最高价')
    low = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, db_comment='最低价')
    close = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, db_comment='收盘价')
    settle = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True, db_comment='结算价')
    vol = models.DecimalField(max_digits=20, decimal_places=0, blank=True, null=True, db_comment='成交量(手)')
    amount = models.DecimalField(max_digits=22, decimal_places=2, blank=True, null=True, db_comment='成交额(万元)')
    oi = models.DecimalField(max_digits=20, decimal_places=0, blank=True, null=True, db_comment='持仓量(手)')
    create_time = models.DateTimeField(db_comment='创建时间')
    update_time = models.DateTimeField(db_comment='更新时间')

    class Meta:
        managed = False
        db_table = 'opt_market_data'
        unique_together = (('ts_code', 'trade_date'),)
        db_table_comment = '期权日线行情数据(tushare opt_daily)'


class FofEmailHypo(models.Model):
    product_id = models.CharField(primary_key=True, max_length=50)
    product_name = models.CharField(max_length=50, blank=True, null=True)
    fund_code = models.CharField(max_length=50)
    fund_name = models.CharField(max_length=50, blank=True, null=True)
    trade_date = models.DateField()
    share = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True)
    nav_hypo = models.DecimalField(max_digits=18, decimal_places=8, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'fof_email_hypo'
        unique_together = (('product_id', 'fund_code', 'trade_date'),)
        db_table_comment = '从邮件中读取虚拟净值数据'


class FofEmailNav(models.Model):
    fund_code = models.CharField(primary_key=True, max_length=50)
    fund_name = models.CharField(max_length=50, blank=True, null=True)
    trade_date = models.DateField()
    unit_nav = models.DecimalField(max_digits=18, decimal_places=8, blank=True, null=True)
    accum_nav = models.DecimalField(max_digits=18, decimal_places=8, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'fof_email_nav'
        unique_together = (('fund_code', 'trade_date'),)
        db_table_comment = '从邮件中读取单位净值和累计净值数据'


class FofFundInfo(models.Model):
    product_id = models.CharField(primary_key=True, max_length=50, db_comment='产品代码')
    product_name = models.CharField(max_length=50, blank=True, null=True, db_comment='产品简称')
    fund_code = models.CharField(max_length=50, db_comment='基金代码')
    fund_name = models.CharField(max_length=50, blank=True, null=True, db_comment='基金简称')
    full_name = models.CharField(max_length=255, blank=True, null=True, db_comment='基金全称')
    pr_order = models.IntegerField(db_comment='申赎序号（完整的申赎为一次）')
    purchase_date = models.DateField(db_comment='申购日期')
    redeem_date = models.DateField(blank=True, null=True, db_comment='赎回日期')
    hd_state = models.IntegerField(blank=True, null=True, db_comment='持有状态(1为持有；0为赎回）')
    cate_code_l1 = models.CharField(max_length=255, blank=True, null=True, db_comment='一级分类代码')
    cate_name_l1 = models.CharField(max_length=255, blank=True, null=True, db_comment='一级分类简称')
    cate_code_l2 = models.CharField(max_length=255, blank=True, null=True, db_comment='二级代码')
    cate_name_l2 = models.CharField(max_length=255, blank=True, null=True, db_comment='二级简称')
    cate_code_l3 = models.CharField(max_length=255, blank=True, null=True, db_comment='三级代码')
    cate_name_l3 = models.CharField(max_length=255, blank=True, null=True, db_comment='三级简称')

    class Meta:
        managed = False
        db_table = 'fof_fund_info'
        unique_together = (('product_id', 'fund_code', 'purchase_date', 'pr_order'),)
        db_table_comment = '产品持仓基金的基本信息'


class FofFundShareChg(models.Model):
    product_id = models.CharField(primary_key=True, max_length=50, db_comment='产品代码')
    product_name = models.CharField(max_length=50, blank=True, null=True, db_comment='产品简称')
    trade_date = models.DateField(db_comment='份额变动日期')
    confirm_date = models.DateField(blank=True, null=True, db_comment='确认日期')
    fund_code = models.CharField(max_length=50, db_comment='证券代码')
    fund_name = models.CharField(max_length=50, blank=True, null=True, db_comment='证券简称')
    share_chg = models.DecimalField(max_digits=18, decimal_places=6, blank=True, null=True, db_comment='份额变动；如果为负，则为卖出')
    price = models.DecimalField(max_digits=18, decimal_places=8, blank=True, null=True, db_comment='变动价格')
    market_value = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True, db_comment='市值')
    cost = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True, db_comment='费用（申赎费，业绩报酬等）')
    tips = models.CharField(max_length=100, blank=True, null=True, db_comment='操作说明')
    is_clear = models.IntegerField(blank=True, null=True, db_comment='是否清仓')
    chg_type = models.IntegerField(db_comment='份额变动类型')
    chg_name = models.CharField(max_length=50, blank=True, null=True, db_comment='份额变动名称')

    class Meta:
        managed = False
        db_table = 'fof_fund_share_chg'
        unique_together = (('product_id', 'trade_date', 'fund_code', 'chg_type'),)
        db_table_comment = '份额变动表'


class FofHoldingDaily(models.Model):
    product_id = models.CharField(primary_key=True, max_length=50, db_comment='FOF母基金ID')
    product_name = models.CharField(max_length=50, blank=True, null=True, db_comment='FOF母基金简称')
    trade_date = models.DateField(db_comment='交易日')
    fund_code = models.CharField(max_length=50, db_comment='基金代码')
    fund_name = models.CharField(max_length=50, blank=True, null=True, db_comment='基金简称')
    share = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='基金份额')
    nav = models.DecimalField(max_digits=18, decimal_places=8, blank=True, null=True, db_comment='基金虚拟净值')
    market_value = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='基金市值')

    class Meta:
        managed = False
        db_table = 'fof_holding_daily'
        unique_together = (('product_id', 'trade_date', 'fund_code'),)
        db_table_comment = '产品每日持仓'


class FofHoldingDailyMix(models.Model):
    product_id = models.CharField(primary_key=True, max_length=50, db_comment='FOF母基金ID')
    product_name = models.CharField(max_length=50, blank=True, null=True, db_comment='FOF母基金简称')
    trade_date = models.DateField(db_comment='交易日')
    fund_code = models.CharField(max_length=50, db_comment='基金代码')
    fund_name = models.CharField(max_length=50, blank=True, null=True, db_comment='基金简称')
    market_value = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='基金市值')
    adj_item = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='调节项')

    class Meta:
        managed = False
        db_table = 'fof_holding_daily_mix'
        unique_together = (('product_id', 'trade_date', 'fund_code'),)
        db_table_comment = '产品每日持仓'


class FofNavHypo(models.Model):
    product_id = models.CharField(max_length=50)
    product_name = models.CharField(max_length=50, blank=True, null=True)
    fund_code = models.CharField(primary_key=True, max_length=50)
    fund_name = models.CharField(max_length=50, blank=True, null=True)
    trade_date = models.DateField()
    unit_nav = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True)
    hypo_nav = models.DecimalField(max_digits=18, decimal_places=8, blank=True, null=True)
    create_time = models.DateTimeField()
    update_time = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'fof_nav_hypo'
        unique_together = (('fund_code', 'trade_date', 'product_id'),)
        db_table_comment = '虚拟净值表'


class FofProductNav(models.Model):
    product_id = models.CharField(primary_key=True, max_length=20, db_comment='产品代码')
    product_name = models.CharField(max_length=50, blank=True, null=True, db_comment='产品简称')
    trade_date = models.DateField(db_comment='日期')
    f_1002 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='银行存款')
    f_1021 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='结算备付金')
    f_1031 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='存出保证金')
    f_1105 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='交易类基金投资')
    f_1108 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='理财投资')
    f_1109 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='其他投资')
    f_1202 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='买入返售金融资产')
    f_1203 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='应收股利')
    f_1204 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='应收利息')
    f_1207 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='应收申购款')
    f_1221 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='其他应收款')
    f_2211 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='应付基金运营服务费')
    f_2206 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='应付管理人报酬')
    f_2207 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='应付托管费')
    f_2331 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='应付税费')
    f_3003 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='证券清算款')
    f_3102 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='衍生工具')
    capital = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='实收资本')
    asset_total = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='资产合计')
    debt_total = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='负债合计')
    asset_net = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='资产净值')
    unit_nav_begin = models.DecimalField(max_digits=8, decimal_places=4, blank=True, null=True, db_comment='期初单位净值')
    unit_nav = models.DecimalField(max_digits=8, decimal_places=4, blank=True, null=True, db_comment='单位净值')
    accum_nav = models.DecimalField(max_digits=8, decimal_places=4, blank=True, null=True, db_comment='累计单位净值')

    class Meta:
        managed = False
        db_table = 'fof_product_nav'
        unique_together = (('product_id', 'trade_date'),)
        db_table_comment = '渊流产品每日净值'


class FofProductNav2(models.Model):
    product_id = models.CharField(primary_key=True, max_length=20, db_comment='产品代码')
    product_name = models.CharField(max_length=50, blank=True, null=True, db_comment='产品简称')
    trade_date = models.DateField()
    f_1002 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='银行存款')
    f_1021 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='结算备付金')
    f_1031 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='存出保证金')
    f_1103 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='交易性债券投资')
    f_1105 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='交易类基金投资')
    f_1108 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='理财投资')
    f_1109 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='其他投资')
    f_1204 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='应收利息')
    f_2205 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='应付运营管理费')
    f_2206 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='应付管理人报酬')
    f_2207 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='应付托管费')
    f_3003 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='证券清算款')
    f_3102 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='衍生工具')
    capital = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='实收资本')
    asset_total = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='资产合计')
    debt_total = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='负债合计')
    asset_net = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='资产净值')
    unit_nav_begin = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='期初单位净值')
    unit_nav = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='今日单位净值')
    accum_nav = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='累计单位净值')

    class Meta:
        managed = False
        db_table = 'fof_product_nav2'
        unique_together = (('product_id', 'trade_date'),)
        db_table_comment = '臻选贰号每日净值'


class FutCodesZl(models.Model):
    id = models.IntegerField(primary_key=True)
    code = models.CharField(max_length=50, blank=True, null=True)
    symbol_code = models.CharField(max_length=50, blank=True, null=True)
    symbol_name = models.CharField(max_length=50, blank=True, null=True)
    ts_dom_code = models.CharField(max_length=50, blank=True, null=True)
    ts_dom_name = models.CharField(max_length=50, blank=True, null=True)
    ts_cont_code = models.CharField(max_length=50, blank=True, null=True)
    ts_cont_name = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'fut_codes_zl'


class FutContractStats(models.Model):
    id = models.BigAutoField(primary_key=True)
    trade_date = models.DateField()
    ts_code = models.CharField(max_length=50)
    variety_code = models.CharField(max_length=20)
    variety_name = models.CharField(max_length=30)
    sector_code = models.CharField(max_length=30)
    sector_name = models.CharField(max_length=30)
    open = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True)
    high = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True)
    low = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True)
    close = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True)
    settle = models.DecimalField(max_digits=16, decimal_places=2, blank=True, null=True)
    volume = models.DecimalField(max_digits=20, decimal_places=0, blank=True, null=True)
    amount = models.DecimalField(max_digits=22, decimal_places=2, blank=True, null=True)
    oi = models.DecimalField(max_digits=20, decimal_places=0, blank=True, null=True)
    vol_10d = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    vol_20d = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    vol_60d = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True)
    create_time = models.DateTimeField()
    update_time = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'fut_contract_stats'
        unique_together = (('ts_code', 'trade_date'),)


class TradeDays(models.Model):
    calendar_date = models.DateField(primary_key=True, db_comment='日历日')
    is_open = models.IntegerField(blank=True, null=True, db_comment='是否是交易日')
    pre_trade_date = models.DateField(blank=True, null=True, db_comment='前一交易日')
    is_week_end = models.IntegerField(blank=True, null=True, db_comment='是否是周的最后一个交易日')
    is_month_end = models.IntegerField(blank=True, null=True, db_comment='是否是月的最后一交易日')
    is_quarter_end = models.IntegerField(blank=True, null=True, db_comment='是否是季的最后一个交易日')
    is_year_end = models.IntegerField(blank=True, null=True, db_comment='是否是年的最后一个交易日')
    exchange_cd = models.CharField(max_length=10, db_comment='属于哪个交易所')

    class Meta:
        managed = False
        db_table = 'trade_days'
        unique_together = (('calendar_date', 'exchange_cd'),)
        db_table_comment = '交易日期表'
