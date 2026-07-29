"""
已有 MySQL 数据表模型。

由 `python manage.py inspectdb` 反向生成。
所有表 managed = False，不由 Django 创建迁移。
"""
from django.db import models


class AccountRecord(models.Model):
    id = models.BigAutoField(primary_key=True)
    account_id = models.CharField(unique=True, max_length=50, blank=True, null=True, db_comment='投顾ID')
    account_category = models.CharField(max_length=50, blank=True, null=True, db_comment='账户类型')
    product_name = models.CharField(max_length=50, blank=True, null=True, db_comment='所属产品')
    account_name = models.CharField(max_length=50, blank=True, null=True, db_comment='投顾名称')
    account_certificate = models.CharField(max_length=50, blank=True, null=True, db_comment='证件号')
    manager = models.CharField(max_length=50, blank=True, null=True, db_comment='管理员')
    create_time = models.CharField(max_length=50, blank=True, null=True, db_comment='创建时间')
    status = models.CharField(max_length=10, blank=True, null=True, db_comment='状态')
    cum_investment = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='总投资金额')
    stop_loss_rate = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True, db_comment='止损线')
    max_pos_rate = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True, db_comment='最大保证金比例')
    mk_bf = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='初始市值')
    is_hold = models.IntegerField(blank=True, null=True, db_comment='是否还在持仓')
    account_tag = models.IntegerField(blank=True, null=True, db_comment='投顾的类型')
    perf_fee = models.DecimalField(max_digits=10, decimal_places=4, blank=True, null=True, db_comment='业绩报酬比例')
    distribution_26 = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='26年分红')
    distribution_bf = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='历史分红')
    redeem_mv = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='赎回市值')
    new_add = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='当日新增规模')
    tips = models.CharField(max_length=255, blank=True, null=True, db_comment='说明')
    invest_cate = models.CharField(max_length=255, blank=True, null=True, db_comment='投顾类型')

    class Meta:
        managed = False
        db_table = 'account_record'


class AdviserInfo(models.Model):
    id = models.BigAutoField(primary_key=True)
    account_id = models.IntegerField(unique=True, blank=True, null=True, db_comment='账户ID')
    group_name = models.CharField(max_length=100, blank=True, null=True, db_comment='产品/组名称')
    group_id = models.IntegerField(blank=True, null=True, db_comment='产品/组ID')
    department_id = models.IntegerField(blank=True, null=True, db_comment='部门ID')
    department_name = models.CharField(max_length=100, blank=True, null=True, db_comment='部门名称')
    customer_id = models.IntegerField(blank=True, null=True, db_comment='客户ID')
    customer_name = models.CharField(max_length=100, blank=True, null=True, db_comment='客户姓名(投顾)')
    id_card = models.CharField(max_length=50, blank=True, null=True, db_comment='身份证号')
    login_account = models.CharField(max_length=100, blank=True, null=True, db_comment='登录账号(操作账户)')
    total_positions = models.CharField(max_length=50, blank=True, null=True, db_comment='总持仓')
    total_pos_cost = models.CharField(max_length=50, blank=True, null=True, db_comment='总持仓成本')
    create_date = models.CharField(max_length=30, blank=True, null=True, db_comment='创建日期')
    midday_force_close_name = models.CharField(max_length=50, blank=True, null=True, db_comment='午盘强平设置')
    close_day_force_close_name = models.CharField(max_length=50, blank=True, null=True, db_comment='收盘强平设置')
    night_force_close_name = models.CharField(max_length=50, blank=True, null=True, db_comment='夜盘强平设置')
    master_name = models.CharField(max_length=100, blank=True, null=True, db_comment='主账户名称(投资顾问)')
    is_support_type = models.IntegerField(blank=True, null=True, db_comment='支持类型(1=期货)')
    is_support_type_name = models.CharField(max_length=20, blank=True, null=True, db_comment='支持类型名称')
    is_deleted = models.IntegerField(blank=True, null=True, db_comment='删除状态(0=启用,2=禁用,1=删除,3=注销)')
    is_deleted_name = models.CharField(max_length=20, blank=True, null=True, db_comment='状态名称')
    support_speculate = models.CharField(max_length=10, blank=True, null=True, db_comment='是否支持投机')
    auto_force_close_type = models.CharField(max_length=50, blank=True, null=True, db_comment='自动强平类型')
    auto_force_price_type = models.CharField(max_length=50, blank=True, null=True, db_comment='自动强平价格类型')
    force_add_tick = models.CharField(max_length=50, blank=True, null=True, db_comment='强制加跳')
    force_limit_tick = models.CharField(max_length=50, blank=True, null=True, db_comment='强制限跳')
    self_trade = models.CharField(max_length=50, blank=True, null=True, db_comment='自成交设置')
    op_cost = models.CharField(max_length=50, blank=True, null=True, db_comment='操作成本')
    margin_and_op = models.CharField(max_length=50, blank=True, null=True, db_comment='保证金及操作')
    offset_setting = models.CharField(max_length=50, blank=True, null=True, db_comment='平仓设置')
    raw_json = models.TextField(blank=True, null=True, db_comment='完整原始JSON')
    crawl_time = models.CharField(max_length=30, blank=True, null=True, db_comment='爬取时间')

    class Meta:
        managed = False
        db_table = 'adviser_info'
        db_table_comment = '投顾(操作账户)信息'


class AdviserProduct(models.Model):
    id = models.BigAutoField(primary_key=True)
    pid = models.IntegerField(unique=True, db_comment='产品ID')
    group_name = models.CharField(max_length=100, blank=True, null=True, db_comment='产品名称')
    is_support_type = models.CharField(max_length=10, blank=True, null=True, db_comment='是否支持类型')
    last_edit_date = models.CharField(max_length=30, blank=True, null=True, db_comment='最后编辑日期')
    third_party_account = models.IntegerField(blank=True, null=True, db_comment='第三方账号')
    data_type = models.CharField(max_length=50, blank=True, null=True, db_comment='数据类型')
    file_name = models.CharField(max_length=200, blank=True, null=True, db_comment='文件名')
    product_type = models.IntegerField(blank=True, null=True, db_comment='产品类型')
    crawl_time = models.CharField(max_length=30, blank=True, null=True, db_comment='爬取时间')

    class Meta:
        managed = False
        db_table = 'adviser_product'
        db_table_comment = '投顾产品列表'


class AdviserProductApi(models.Model):
    id = models.BigAutoField(primary_key=True)
    pid = models.IntegerField(db_comment='产品ID')
    api_name = models.CharField(max_length=100, db_comment='API名称')
    response_json = models.TextField(blank=True, null=True, db_comment='API响应JSON')
    crawl_time = models.CharField(max_length=30, blank=True, null=True, db_comment='爬取时间')

    class Meta:
        managed = False
        db_table = 'adviser_product_api'
        unique_together = (('pid', 'api_name'),)
        db_table_comment = '投顾产品API原始响应数据'


class AdviserProductHeader(models.Model):
    id = models.BigAutoField(primary_key=True)
    pid = models.IntegerField(unique=True, db_comment='产品ID')
    p_name = models.CharField(max_length=100, blank=True, null=True, db_comment='产品名称')
    trading_day = models.CharField(max_length=30, blank=True, null=True, db_comment='交易日')
    net_value = models.CharField(max_length=50, blank=True, null=True, db_comment='单位净值')
    accumulated_net = models.CharField(max_length=50, blank=True, null=True, db_comment='累计净值')
    one_monthly_rise = models.CharField(max_length=50, blank=True, null=True, db_comment='近1月涨幅')
    three_monthly_rise = models.CharField(max_length=50, blank=True, null=True, db_comment='近3月涨幅')
    six_monthly_rise = models.CharField(max_length=50, blank=True, null=True, db_comment='近6月涨幅')
    year_rise = models.CharField(max_length=50, blank=True, null=True, db_comment='近1年涨幅')
    to_thisday_rise = models.CharField(max_length=50, blank=True, null=True, db_comment='成立以来涨幅')
    start_date = models.CharField(max_length=20, blank=True, null=True, db_comment='成立日期')
    sum_rights = models.CharField(max_length=50, blank=True, null=True, db_comment='总权益')
    adviser = models.CharField(max_length=100, blank=True, null=True, db_comment='投资顾问')
    company = models.CharField(max_length=100, blank=True, null=True, db_comment='公司')
    p_state = models.IntegerField(blank=True, null=True, db_comment='存续状态')
    data_level = models.CharField(max_length=20, blank=True, null=True, db_comment='数据等级')
    product_type = models.IntegerField(blank=True, null=True, db_comment='产品类型')
    is_support_type = models.IntegerField(blank=True, null=True, db_comment='是否支持类型')
    crawl_time = models.CharField(max_length=30, blank=True, null=True, db_comment='爬取时间')

    class Meta:
        managed = False
        db_table = 'adviser_product_header'
        db_table_comment = '投顾产品头部详情'


class AdviserTradingFund(models.Model):
    id = models.BigAutoField(primary_key=True)
    login_account = models.CharField(max_length=100, blank=True, null=True, db_comment='登录账户')
    trading_day = models.CharField(max_length=20, blank=True, null=True, db_comment='交易日期')
    real_capital_amount = models.CharField(max_length=50, blank=True, null=True, db_comment='真实资金')
    pre_settle_posit = models.CharField(max_length=50, blank=True, null=True, db_comment='昨日结算准备金')
    settle_posit = models.CharField(max_length=50, blank=True, null=True, db_comment='结算准备金')
    order_fee = models.CharField(max_length=50, blank=True, null=True, db_comment='报单费')
    commission = models.CharField(max_length=50, blank=True, null=True, db_comment='手续费')
    close_profit = models.CharField(max_length=50, blank=True, null=True, db_comment='平仓盈亏')
    position_profit = models.CharField(max_length=50, blank=True, null=True, db_comment='持仓盈亏')
    deposit = models.CharField(max_length=50, blank=True, null=True, db_comment='入金')
    withdraw = models.CharField(max_length=50, blank=True, null=True, db_comment='出金')
    margin = models.CharField(max_length=50, blank=True, null=True, db_comment='保证金')
    market_profit = models.CharField(max_length=50, blank=True, null=True, db_comment='盯市盈亏')
    cp_market_value_equity = models.CharField(max_length=50, blank=True, null=True, db_comment='持仓权益市值')
    raw_json = models.TextField(blank=True, null=True, db_comment='完整原始JSON')
    crawl_time = models.CharField(max_length=30, blank=True, null=True, db_comment='爬取时间')

    class Meta:
        managed = False
        db_table = 'adviser_trading_fund'
        unique_together = (('login_account', 'trading_day'),)
        db_table_comment = '投顾资金数据'


class AdviserTradingOrder(models.Model):
    id = models.BigAutoField(primary_key=True)
    login_account = models.CharField(max_length=100, blank=True, null=True, db_comment='登录账户')
    extend_account = models.CharField(max_length=100, blank=True, null=True, db_comment='扩展账户')
    trading_day = models.CharField(max_length=20, blank=True, null=True, db_comment='交易日期')
    insert_time = models.CharField(max_length=30, blank=True, null=True, db_comment='委托时间')
    order_sys_id = models.CharField(max_length=50, blank=True, null=True, db_comment='委托编号')
    exchange_name = models.CharField(max_length=50, blank=True, null=True, db_comment='交易所')
    instrument_id = models.CharField(max_length=50, blank=True, null=True, db_comment='合约代码')
    direction_name = models.CharField(max_length=20, blank=True, null=True, db_comment='买卖方向')
    combo_offset_flag_name = models.CharField(max_length=30, blank=True, null=True, db_comment='开平标志')
    limit_price = models.CharField(max_length=50, blank=True, null=True, db_comment='委托价格')
    volume_total_original = models.CharField(max_length=50, blank=True, null=True, db_comment='委托数量')
    volume_traded = models.CharField(max_length=50, blank=True, null=True, db_comment='成交数量')
    order_status_name = models.CharField(max_length=30, blank=True, null=True, db_comment='委托状态')
    order_price_type_name = models.CharField(max_length=30, blank=True, null=True, db_comment='报价类型')
    manger_name = models.CharField(max_length=100, blank=True, null=True, db_comment='投资顾问')
    user_product_info = models.CharField(max_length=100, blank=True, null=True, db_comment='产品信息')
    raw_json = models.TextField(blank=True, null=True, db_comment='完整原始JSON')
    crawl_time = models.CharField(max_length=30, blank=True, null=True, db_comment='爬取时间')

    class Meta:
        managed = False
        db_table = 'adviser_trading_order'
        unique_together = (('login_account', 'order_sys_id'),)
        db_table_comment = '投顾委托数据'


class AdviserTradingPosition(models.Model):
    id = models.BigAutoField(primary_key=True)
    login_account = models.CharField(max_length=100, blank=True, null=True, db_comment='登录账户')
    trading_day = models.CharField(max_length=20, blank=True, null=True, db_comment='交易日期')
    exchange_name = models.CharField(max_length=50, blank=True, null=True, db_comment='交易所')
    instrument_id = models.CharField(max_length=50, blank=True, null=True, db_comment='合约代码')
    direction_name = models.CharField(max_length=20, blank=True, null=True, db_comment='买卖方向')
    direction = models.CharField(max_length=10, blank=True, null=True, db_comment='买卖方向代码')
    volume = models.CharField(max_length=50, blank=True, null=True, db_comment='持仓量')
    open_price = models.CharField(max_length=50, blank=True, null=True, db_comment='开仓价')
    settlement_price = models.CharField(max_length=50, blank=True, null=True, db_comment='结算价')
    margin = models.CharField(max_length=50, blank=True, null=True, db_comment='保证金')
    position_profit = models.CharField(max_length=50, blank=True, null=True, db_comment='持仓盈亏')
    position_profit_by_trade = models.CharField(max_length=50, blank=True, null=True, db_comment='持仓盈亏(成交)')
    open_date = models.CharField(max_length=20, blank=True, null=True, db_comment='开仓日期')
    open_time = models.CharField(max_length=20, blank=True, null=True, db_comment='开仓时间')
    hedge_flag_name = models.CharField(max_length=30, blank=True, null=True, db_comment='投机套保')
    product_class = models.CharField(max_length=20, blank=True, null=True, db_comment='产品类型')
    raw_json = models.TextField(blank=True, null=True, db_comment='完整原始JSON')
    crawl_time = models.CharField(max_length=30, blank=True, null=True, db_comment='爬取时间')

    class Meta:
        managed = False
        db_table = 'adviser_trading_position'
        unique_together = (('login_account', 'trading_day', 'instrument_id', 'direction'),)
        db_table_comment = '投顾持仓数据'


# ==================== FOF 数据表 ====================


class FundCodesLh(models.Model):
    """FOF - 基金代码表"""
    id = models.BigAutoField(primary_key=True)
    fund_code = models.CharField(unique=True, max_length=50, blank=True, null=True, db_comment='基金代码')
    fund_name = models.CharField(max_length=50, blank=True, null=True, db_comment='基金简称')
    cate_code_1 = models.CharField(max_length=50, blank=True, null=True, db_comment='一级分类代码')
    cate_name_1 = models.CharField(max_length=50, blank=True, null=True, db_comment='一级分类简称')
    cate_code_2 = models.CharField(max_length=50, blank=True, null=True, db_comment='二级分类代码')
    cate_name_2 = models.CharField(max_length=50, blank=True, null=True, db_comment='二级分类简称')
    cate_code_3 = models.CharField(max_length=50, blank=True, null=True, db_comment='三级分类代码')
    cate_name_3 = models.CharField(max_length=50, blank=True, null=True, db_comment='三级分类简称')
    tips = models.CharField(max_length=255, blank=True, null=True, db_comment='说明')
    bm_code_def = models.CharField(max_length=50, blank=True, null=True, db_comment='默认基准代码')
    bm_name_def = models.CharField(max_length=50, blank=True, null=True, db_comment='默认基准简称')

    class Meta:
        managed = False
        db_table = 'fund_codes_lh'
        db_table_comment = '基金代码表'


class FundNetValue(models.Model):
    """FOF - 基金净值表"""
    id = models.BigAutoField(primary_key=True, db_column='id')
    fund_code = models.CharField(max_length=20, db_comment='基金代码')
    fund_name = models.CharField(max_length=50, blank=True, null=True, db_comment='基金简称')
    trade_date = models.DateField(db_comment='交易日期')
    unit_nav = models.DecimalField(max_digits=18, decimal_places=6, blank=True, null=True, db_comment='单位净值')
    accum_nav = models.DecimalField(max_digits=18, decimal_places=6, blank=True, null=True, db_comment='累计净值')
    adjust_nav = models.DecimalField(max_digits=18, decimal_places=6, blank=True, null=True, db_comment='复权净值')
    create_time = models.DateTimeField(db_comment='创建时间')
    update_time = models.DateTimeField(db_comment='更新时间')

    class Meta:
        managed = False
        db_table = 'fund_net_value'
        unique_together = (('fund_code', 'trade_date'),)
        db_table_comment = '基金净值表'


class FundShareChg(models.Model):
    """FOF - 基金份额变动表"""
    id = models.BigAutoField(primary_key=True, db_column='id')
    product_id = models.CharField(max_length=50, db_comment='产品代码')
    product_name = models.CharField(max_length=50, blank=True, null=True, db_comment='产品简称')
    trade_date = models.DateField(db_comment='份额变动日期')
    confirm_date = models.DateField(blank=True, null=True, db_comment='确认日期')
    fund_code = models.CharField(max_length=50, db_comment='基金代码')
    fund_name = models.CharField(max_length=50, blank=True, null=True, db_comment='基金简称')
    share_chg = models.DecimalField(max_digits=18, decimal_places=6, blank=True, null=True, db_comment='份额变动')
    price = models.DecimalField(max_digits=18, decimal_places=8, blank=True, null=True, db_comment='变动价格')
    market_value = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True, db_comment='市值')
    cost = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True, db_comment='费用')
    tips = models.CharField(max_length=100, blank=True, null=True, db_comment='操作说明')
    is_clear = models.IntegerField(blank=True, null=True, db_comment='全部赎回为1；否则为0')
    chg_type = models.IntegerField(db_comment='份额变动类型')
    chg_name = models.CharField(max_length=50, blank=True, null=True, db_comment='份额变动名称')

    class Meta:
        managed = False
        db_table = 'fund_share_chg'
        unique_together = (('product_id', 'trade_date', 'fund_code', 'chg_type'),)
        db_table_comment = '基金份额变动表'


class ProductFundInfo(models.Model):
    """FOF - 产品持仓基金信息"""
    id = models.BigAutoField(primary_key=True, db_column='id')
    product_id = models.CharField(max_length=50, db_comment='产品代码')
    product_name = models.CharField(max_length=50, blank=True, null=True, db_comment='产品简称')
    fund_code = models.CharField(max_length=50, db_comment='基金代码')
    fund_name = models.CharField(max_length=50, blank=True, null=True, db_comment='基金简称')
    full_name = models.CharField(max_length=255, blank=True, null=True, db_comment='基金全称')
    pr_order = models.IntegerField(db_comment='申赎序号')
    purchase_date = models.DateField(db_comment='申购日期')
    redeem_date = models.DateField(blank=True, null=True, db_comment='赎回日期')
    hd_state = models.IntegerField(blank=True, null=True, db_comment='持有状态')
    cate_code_l1 = models.CharField(max_length=255, blank=True, null=True, db_comment='一级分类代码')
    cate_name_l1 = models.CharField(max_length=255, blank=True, null=True, db_comment='一级分类简称')
    cate_code_l2 = models.CharField(max_length=255, blank=True, null=True, db_comment='二级分类代码')
    cate_name_l2 = models.CharField(max_length=255, blank=True, null=True, db_comment='二级分类简称')
    cate_code_l3 = models.CharField(max_length=255, blank=True, null=True, db_comment='三级分类代码')
    cate_name_l3 = models.CharField(max_length=255, blank=True, null=True, db_comment='三级分类简称')

    class Meta:
        managed = False
        db_table = 'product_fund_info'
        unique_together = (('product_id', 'fund_code', 'purchase_date', 'pr_order'),)
        db_table_comment = '产品持仓基金信息'


class ProductHoldingDailyGs(models.Model):
    """FOF - 产品每日持仓(估值)"""
    id = models.BigAutoField(primary_key=True, db_column='id')
    product_id = models.CharField(max_length=50, db_comment='FOF母基金ID')
    product_name = models.CharField(max_length=50, blank=True, null=True, db_comment='FOF母基金简称')
    trade_date = models.DateField(db_comment='交易日')
    fund_code = models.CharField(max_length=50, db_comment='基金代码')
    fund_name = models.CharField(max_length=50, blank=True, null=True, db_comment='基金简称')
    net_value = models.FloatField(blank=True, null=True, db_comment='基金净值')
    share_chg = models.FloatField(blank=True, null=True, db_comment='申赎')
    hh_amt = models.FloatField(blank=True, null=True, db_comment='互换金额')
    hh_chg = models.FloatField(blank=True, null=True, db_comment='互换金额变动')
    jiexi = models.FloatField(blank=True, null=True, db_comment='结息')
    cash_back = models.FloatField(blank=True, null=True, db_comment='本金返还')
    tips = models.CharField(max_length=255, blank=True, null=True, db_comment='备注')

    class Meta:
        managed = False
        db_table = 'product_holding_daily_gs'
        unique_together = (('product_id', 'trade_date', 'fund_code'),)
        db_table_comment = '产品每日持仓(估值)'


class ProductHoldingDailyMix(models.Model):
    """FOF - 产品每日持仓(混合)"""
    id = models.BigAutoField(primary_key=True, db_column='id')
    product_id = models.CharField(max_length=50, db_comment='FOF母基金ID')
    product_name = models.CharField(max_length=50, blank=True, null=True, db_comment='FOF母基金简称')
    trade_date = models.DateField(db_comment='交易日')
    fund_code = models.CharField(max_length=50, db_comment='基金代码')
    fund_name = models.CharField(max_length=50, blank=True, null=True, db_comment='基金简称')
    market_value = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='基金市值')
    adj_item = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='调节项')

    class Meta:
        managed = False
        db_table = 'product_holding_daily_mix'
        unique_together = (('product_id', 'trade_date', 'fund_code'),)
        db_table_comment = '产品每日持仓(混合)'


class AdviserTradingTrade(models.Model):
    id = models.BigAutoField(primary_key=True)
    login_account = models.CharField(max_length=100, blank=True, null=True, db_comment='登录账户')
    extend_account = models.CharField(max_length=100, blank=True, null=True, db_comment='扩展账户')
    trading_day = models.CharField(max_length=20, blank=True, null=True, db_comment='交易日期')
    trade_time = models.CharField(max_length=30, blank=True, null=True, db_comment='成交时间')
    trade_id = models.CharField(max_length=50, blank=True, null=True, db_comment='成交编号')
    exchange_name = models.CharField(max_length=50, blank=True, null=True, db_comment='交易所')
    instrument_id = models.CharField(max_length=50, blank=True, null=True, db_comment='合约代码')
    direction_name = models.CharField(max_length=20, blank=True, null=True, db_comment='买卖方向')
    offset_flag = models.CharField(max_length=30, blank=True, null=True, db_comment='开平标志')
    hedge_flag_name = models.CharField(max_length=30, blank=True, null=True, db_comment='投机套保')
    trade_price = models.CharField(max_length=50, blank=True, null=True, db_comment='成交价格')
    volume = models.CharField(max_length=50, blank=True, null=True, db_comment='成交数量')
    commission = models.CharField(max_length=50, blank=True, null=True, db_comment='手续费')
    close_profit = models.CharField(max_length=50, blank=True, null=True, db_comment='平仓盈亏')
    total_cost = models.CharField(max_length=50, blank=True, null=True, db_comment='总成本')
    premium = models.CharField(max_length=50, blank=True, null=True, db_comment='期权权利金')
    raw_json = models.TextField(blank=True, null=True, db_comment='完整原始JSON')
    crawl_time = models.CharField(max_length=30, blank=True, null=True, db_comment='爬取时间')

    class Meta:
        managed = False
        db_table = 'adviser_trading_trade'
        unique_together = (('login_account', 'trade_id'),)
        db_table_comment = '投顾成交数据'


class FundNetValueHypo(models.Model):
    """FOF - 虚拟净值表（复合主键，无 id 列）"""
    product_id = models.CharField(max_length=50, primary_key=True, db_column='product_id', db_comment='产品代码')
    product_name = models.CharField(max_length=50, blank=True, null=True, db_comment='产品简称')
    fund_code = models.CharField(max_length=50, db_comment='基金代码')
    fund_name = models.CharField(max_length=50, blank=True, null=True, db_comment='基金简称')
    trade_date = models.DateField(db_comment='交易日期')
    unit_nav = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='单位净值')
    hypo_nav = models.DecimalField(max_digits=18, decimal_places=8, blank=True, null=True, db_comment='虚拟净值')
    create_time = models.DateTimeField(db_comment='创建时间')
    update_time = models.DateTimeField(db_comment='更新时间')

    class Meta:
        managed = False
        db_table = 'fund_net_value_hypo'
        unique_together = (('product_id', 'fund_code', 'trade_date'),)
        ordering = ['-create_time']
        db_table_comment = '虚拟净值表'


class ProductHoldingDaily(models.Model):
    """FOF - 产品每日持仓（复合主键，无 id 列）"""
    product_id = models.CharField(max_length=50, primary_key=True, db_column='product_id', db_comment='母基金ID')
    product_name = models.CharField(max_length=50, blank=True, null=True, db_comment='母基金简称')
    trade_date = models.DateField(db_comment='交易日')
    fund_code = models.CharField(max_length=50, db_comment='基金代码')
    fund_name = models.CharField(max_length=50, blank=True, null=True, db_comment='基金简称')
    share = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='基金份额')
    nav = models.DecimalField(max_digits=18, decimal_places=8, blank=True, null=True, db_comment='基金虚拟净值')
    market_value = models.DecimalField(max_digits=18, decimal_places=4, blank=True, null=True, db_comment='基金市值')

    class Meta:
        managed = False
        db_table = 'product_holding_daily'
        unique_together = (('product_id', 'trade_date', 'fund_code'),)
        ordering = ['-trade_date']
        db_table_comment = '产品每日持仓'


class ProductNav(models.Model):
    """FOF - 渊流产品每日净值（复合主键，无 id 列）"""
    product_id = models.CharField(max_length=20, primary_key=True, db_column='product_id', db_comment='产品代码')
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
        db_table = 'product_nav'
        unique_together = (('product_id', 'trade_date'),)
        ordering = ['-trade_date']
        db_table_comment = '渊流产品每日净值'


class ProductNav2(models.Model):
    """FOF - 臻选贰号每日净值（复合主键，无 id 列）"""
    product_id = models.CharField(max_length=20, primary_key=True, db_column='product_id', db_comment='产品代码')
    product_name = models.CharField(max_length=50, blank=True, null=True, db_comment='产品简称')
    trade_date = models.DateField(db_comment='日期')
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
        db_table = 'product_nav2'
        unique_together = (('product_id', 'trade_date'),)
        ordering = ['-trade_date']
        db_table_comment = '臻选贰号每日净值'
