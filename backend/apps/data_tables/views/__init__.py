"""data_tables 视图包：按模块拆分（tables/advisor/sector/option/strategy/product_ops）。

原单文件 views.py 拆分而来；urls.py 仍以 views.<name> 引用。
"""
from .tables import (
    DynamicModelViewSet, list_tables, table_columns, table_export,
    table_import, table_template,
)
from .advisor import advisor_performance, advisor_performance_list
from .sector import (
    sector_varieties, sector_contract_kline, sector_advisor_variety,
    sector_pnl, sector_pnl_ranking, advisor_trade_overview,
    sector_bk_latest, sector_bk_margin, sector_bk_net_risk,
    sector_bk_detail_tree, sector_position_overview, sector_board,
    variety_top_margin, variety_top_net_risk, variety_advisor_long_short,
)
from .option import option_pnl, option_pnl_underlying, option_trades
from .strategy import (
    strategy_portfolio, portfolio_records, portfolio_record_detail,
)
from .product_ops import (
    advisor_info_records, advisor_info_lookup, advisor_info_sync,
    advisor_info_record_detail, advisor_dividend_records,
    advisor_dividend_record_detail, counter_account,
)
