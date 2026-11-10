import re
import decimal as _decimal
from datetime import date as _date, timedelta

from django.db import connection, models
from django.db.models import F, Q
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .nav import (
    _account_series, _benchmark_series_for_dates, _group_equity_daily,
    _load_nhci_returns, _nav_window_metrics, _share_method_nav,
)


def _merged_nav_metrics(daily):
    """根据 [(date, equity, flow)] 日序列用份额法计算净值与风险指标。

    equity = Σ结算权益（rh_funds.settle_balance），flow = Σ出入金（deposit - withdraw）。
    份额法：share_t = share_{t-1} + flow_t / nav_{t-1}；nav_t = equity_t / share_t。
    返回 dict(total_return, annual_yield, annual_volatility, max_drawdown,
    sharpe_ratio, calmar_ratio)（百分数口径，与列表其他行一致）。
    """
    import math
    import statistics

    navs = []
    share = None
    prev_nav = 1.0
    for _, equity, flow in daily:
        equity = float(equity or 0)
        flow = float(flow or 0)
        if share is None:
            if equity <= 0:
                continue
            share = equity
            navs.append(1.0)
            continue
        share += flow / prev_nav
        nav = equity / share if share > 0 else prev_nav
        navs.append(nav)
        prev_nav = nav
    if len(navs) < 2:
        return None

    rets = [navs[i] / navs[i - 1] - 1 for i in range(1, len(navs))]
    total_return = navs[-1] - 1
    days = len(rets)
    annual_yield = (1 + total_return) ** (252 / days) - 1
    annual_vol = statistics.stdev(rets) * math.sqrt(252) if days >= 2 else None
    peak, max_dd = 1.0, 0.0
    for nav in navs:
        peak = max(peak, nav)
        max_dd = min(max_dd, nav / peak - 1)
    # 无风险利率取 1.5%
    risk_free = 0.015
    sharpe = ((annual_yield - risk_free) / annual_vol) if annual_vol else None
    calmar = (annual_yield / abs(max_dd)) if max_dd < 0 else None

    return {
        'total_return': round(total_return * 100, 4),
        'annual_yield': round(annual_yield * 100, 4),
        'annual_volatility': round(annual_vol * 100, 4) if annual_vol is not None else None,
        'max_drawdown': round(max_dd * 100, 4),
        'sharpe_ratio': round(sharpe, 4) if sharpe is not None else None,
        'calmar_ratio': round(calmar, 4) if calmar is not None else None,
    }


@api_view(['GET'])
@permission_classes([AllowAny])
def advisor_performance_list(request):
    """投顾业绩列表（投顾业绩板块首页）。

    全部投顾的业绩指标统一现算：净值按 rh_funds 结算权益 + 出入金用份额法还原，
    总收益/年化/夏普（无风险利率 1.5%）/卡玛/波动/回撤均由该净值序列推导；
    平均仓位为成立以来 Σ保证金/Σ权益 的日均值。

    ?merge=1：同名投顾（mom_account_record.account_name 相同）多账号合并为一行；
    默认逐账号一行。

    结果按 merge 参数缓存 10 分钟（数据为日频更新，指标无需实时重算）。
    """
    from collections import defaultdict
    from django.core.cache import cache

    merge = request.query_params.get('merge') == '1'

    cache_key = f'advisor_perf_list_{int(merge)}'
    cached = cache.get(cache_key)
    if cached is not None:
        return Response(cached)

    sql = """
        SELECT p.pid,
               COALESCE(m.account_name, p.product_name)      AS account_name,
               m.account_name                                AS raw_name,
               p.product_name                                AS account_code,
               m.cum_investment,
               m.invest_logic,
               m.invest_cate,
               m.is_stop,
               nd.last_nav_date
        FROM perf_products p
        JOIN (
            SELECT DISTINCT pid FROM perf_net_values WHERE net_value IS NOT NULL
        ) nv ON nv.pid = p.pid
        LEFT JOIN mom_account_record m ON m.account_id = p.product_name
        LEFT JOIN (
            SELECT pid, MAX(trade_date) AS last_nav_date
            FROM perf_net_values
            WHERE net_value IS NOT NULL AND trade_date IS NOT NULL
            GROUP BY pid
        ) nd ON nd.pid = p.pid
        ORDER BY p.pid
    """
    with connection.cursor() as cursor:
        cursor.execute(sql)
        cols = [col[0] for col in cursor.description]
        rows = [dict(zip(cols, row)) for row in cursor.fetchall()]

    for row in rows:
        row['cum_investment'] = float(row['cum_investment']) if row['cum_investment'] is not None else None

    # 无账户记录（is_stop 为 NULL）的投顾用净值新鲜度推断停止状态：
    # 最新净值落后全库最新净值超过 30 天视为已终止
    global_last_nav = max((r['last_nav_date'] for r in rows if r.get('last_nav_date')), default=None)
    for row in rows:
        if row['is_stop'] is None:
            stale = (
                global_last_nav is not None
                and row.get('last_nav_date') is not None
                and (global_last_nav - row['last_nav_date']).days > 30
            )
            row['is_stop'] = 1 if stale else 0

    # ---- 分组：merge=1 按 raw_name 合并同名账号；否则每账号一组 ----
    groups = defaultdict(list)
    for row in rows:
        if merge and row['raw_name']:
            groups[row['raw_name']].append(row)
        else:
            groups[f"__single__{row['pid']}"].append(row)

    # ---- 拉取各组账号序列，份额法现算指标与仓位 ----
    # 净值：统一走 _group_equity_daily（rh_funds 为主，缺失账号用净值表×投资规模合成，
    # 中断账号在次一交易日全额出金）；保证金仅 rh_funds 覆盖账户有值
    all_accounts = {r['account_code'] for r in rows}
    margin_by_account = {}  # account -> {date: margin}（仅 rh_funds 覆盖账户）
    if all_accounts:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT trade_date, account, margin
                FROM rh_funds
                WHERE account IN %s AND trade_date IS NOT NULL
            """, [tuple(all_accounts)])
            for d, acc, margin in cursor.fetchall():
                margin_by_account.setdefault(acc, {})[d] = float(margin or 0)

    # 一次性预取全部账号级序列，分组循环内复用（否则每组一条 SQL，数百组即数秒）
    all_prefetched, _ = _account_series(sorted(all_accounts))

    result = []
    for key, g in groups.items():
        is_merged = merge and len(g) > 1
        accounts = [row['account_code'] for row in g]
        daily, _covered = _group_equity_daily(accounts, prefetched=all_prefetched)
        series = [(d, v[0], v[1]) for d, v in sorted(daily.items())]
        metrics = _merged_nav_metrics(series) or {}
        # 平均仓位：组内成立以来 Σmargin/Σequity 日均
        group_margin = defaultdict(float)
        for acc in accounts:
            for d, m in margin_by_account.get(acc, {}).items():
                group_margin[d] += m
        ratios = [
            group_margin[d] / eq * 100
            for d, (eq, _fl) in daily.items()
            if eq > 0
        ]
        avg_position = round(sum(ratios) / len(ratios), 2) if ratios else None

        def _pick(field):
            for row in g:
                if row.get(field):
                    return row[field]
            return None

        # 投资金额：合并组内已停止账号不纳入；全组停止回退为全部合计
        active = [r for r in g if r['is_stop'] != 1]
        invest_rows = active if (is_merged and active) else g

        first = g[0]
        result.append({
            'pid': first['pid'],
            'pids': [row['pid'] for row in g],
            'account_name': first['raw_name'] if is_merged else first['account_name'],
            'account_code': '、'.join(row['account_code'] for row in g),
            'account_codes': [row['account_code'] for row in g],
            'account_count': len(g),
            'merged': is_merged,
            'cum_investment': sum((r['cum_investment'] or 0) for r in invest_rows) or None,
            'invest_logic': _pick('invest_logic'),
            'invest_cate': _pick('invest_cate'),
            # 合并组内全部停止才算终止
            'is_stop': 1 if all(r['is_stop'] == 1 for r in g) else 0,
            'avg_position': avg_position,
            **{k: metrics.get(k) for k in (
                'total_return', 'annual_yield', 'sharpe_ratio',
                'calmar_ratio', 'annual_volatility', 'max_drawdown')},
        })

    result.sort(key=lambda r: -(r.get('total_return') if r.get('total_return') is not None else -9999))
    cache.set(cache_key, result, 60 * 10)
    return Response(result)


@api_view(['GET'])
@permission_classes([AllowAny])
def advisor_performance(request):
    """投顾业绩聚合接口。

    无参数：返回投顾产品列表 [{pid, product_name}]
    ?merge=1：列表按投顾名合并同名多账户，一组一条
    [{pid(组内代表), account_name, account_code, account_count, pids(组内全部)}]
    ?pid=xxx：返回单个投顾的基本信息 + 风险收益指标
    ?pid=xxx&merge=1：同名多账号合并详情
    净值统一由 rh_funds 每日结算权益+出入金份额法现算（缺数据账号用净值表×投资规模合成），
    指标（since/1y/2y/3y）由该净值序列切窗推导，单账号与合并模式同口径
    """
    from .models import MomAccountRecord, PerfNetValues, PerfProducts, PerfRiskIndicators

    pid = request.query_params.get('pid')
    search = request.query_params.get('search', '').strip()
    if not pid:
        # 返回投顾列表（有风险指标 + 有净值数据的，按 pid 排序）
        pids_with_risk = set(PerfRiskIndicators.objects.values_list('pid', flat=True))
        pids_with_nav = set(PerfNetValues.objects.filter(net_value__isnull=False).values_list('pid', flat=True))
        qs = PerfProducts.objects.filter(pid__in=pids_with_risk & pids_with_nav).order_by('pid')
        # 批量关联 MomAccountRecord 获取投顾名称和代码
        acct_map = {}
        for m in MomAccountRecord.objects.filter(account_id__in=[p.product_name for p in qs]):
            acct_map[m.account_id] = m
        result = []
        for p in qs:
            acct = acct_map.get(p.product_name)
            account_name = acct.account_name if acct else None
            account_code = acct.account_id if acct else p.product_name
            # 模糊搜索：匹配 account_name、account_code、product_name、pid
            if search:
                search_lower = search.lower()
                match_fields = [str(p.pid), p.product_name or '', account_name or '', account_code or '']
                if not any(search_lower in f.lower() for f in match_fields):
                    continue
            result.append({
                'pid': p.pid,
                'product_name': p.product_name,
                'account_name': account_name,
                'account_code': account_code,
            })
        # merge=1：同名多账户合并为一组，代表 pid 取组内最小
        if request.query_params.get('merge') == '1':
            groups = {}
            order = []
            for row in result:
                key = row['account_name'] or row['account_code']
                if key not in groups:
                    groups[key] = {
                        'pid': row['pid'],
                        'product_name': row['product_name'],
                        'account_name': row['account_name'],
                        'account_codes': [],
                        'account_count': 0,
                        'pids': [],
                    }
                    order.append(key)
                g = groups[key]
                g['account_codes'].append(row['account_code'])
                g['account_count'] += 1
                g['pids'].append(row['pid'])
            for g in groups.values():
                g['account_code'] = '、'.join(g['account_codes'])
            return Response(list(groups[k] for k in order))
        return Response(result)

    # 单个投顾详情
    try:
        pid_int = int(pid)
    except (TypeError, ValueError):
        return Response({'detail': 'pid 参数无效'}, status=400)

    product = PerfProducts.objects.filter(pid=pid_int).first()
    if not product:
        return Response({'detail': f'未找到 pid={pid} 的产品'}, status=404)

    # ---- 投顾详情：净值统一由 rh_funds 份额法现算（缺数据账号用净值表×投资规模合成） ----
    # 单账号与同名合并模式共用同一口径：每日结算权益 + 出入金份额法（费前毛收益）
    from datetime import timedelta

    is_merge = request.query_params.get('merge') == '1'
    base_acct = MomAccountRecord.objects.filter(account_id=product.product_name).first()
    group_products = [product]
    if is_merge and base_acct and base_acct.account_name:
        same_name = MomAccountRecord.objects.filter(account_name=base_acct.account_name)
        codes = [m.account_id for m in same_name]
        group_products = list(PerfProducts.objects.filter(product_name__in=codes))
        if product not in group_products:
            group_products.insert(0, product)
    accounts = [p.product_name for p in group_products]

    # 净值：rh_funds 份额法（缺数据账号由净值表×投资规模合成）
    eq_daily, _covered = _group_equity_daily(accounts)
    navs = _share_method_nav(eq_daily)

    nav_series = []
    peak = None
    base = navs[0][1] if navs else None
    for d, nav in navs:
        if peak is None or nav > peak:
            peak = nav
        nav_series.append({
            'date': d.isoformat(),
            'nav': round(nav, 6),
            'cum_return': round((nav / base - 1) * 100, 4) if base else 0.0,
            'drawdown': round((nav / peak - 1) * 100, 4) if peak else 0.0,
        })

    # 指标：since 全区间 + 1y/2y/3y 切窗（基准：南华商品指数 NHCI.NH）
    risk_periods = ['1y', '2y', '3y', 'since']
    risk_metrics = [
        'annual_yield', 'annual_volatility', 'max_drawdown',
        'sharpe_ratio', 'kama_ratio', 'info_ratio', 'alpha', 'beta',
    ]
    risk_table = None
    indicators = {}
    if len(navs) >= 2:
        bench_rets = _load_nhci_returns()
        first_date = navs[0][0]
        last_date = navs[-1][0]
        span_days = (last_date - first_date).days + 1
        windows = {'since': navs}
        # 数据不足对应窗口年限时，该窗口指标置 None（前端显示 —），不截短回退
        for label, days_back in (('1y', 365), ('2y', 730), ('3y', 1095)):
            if span_days >= days_back:
                cutoff = last_date - timedelta(days=days_back)
                windows[label] = [x for x in navs if x[0] >= cutoff] or navs[-1:]
            else:
                windows[label] = None
        window_metrics = {
            label: (_nav_window_metrics(seq, bench_rets) if seq else {k: None for k in risk_metrics})
            for label, seq in windows.items()
        }
        risk_table = {
            metric: {p: window_metrics[p][metric] for p in risk_periods}
            for metric in risk_metrics
        }
        since_m = window_metrics['since']
        indicators = {
            'total_return': navs[-1][1] / navs[0][1] - 1,
            **{k: since_m[k] for k in risk_metrics},
        }

    # 基本信息（单账号 / 合并模式字段兼容）
    accts = {m.account_id: m for m in MomAccountRecord.objects.filter(account_id__in=accounts)}
    def _pick(field):
        for code in accounts:
            a = accts.get(code)
            if a and getattr(a, field):
                return getattr(a, field)
        return None
    active_codes = [c for c in accounts if accts.get(c) and accts[c].is_stop != 1]
    invest_codes = active_codes if active_codes else accounts
    # 该投顾是否属于同名多账号组（用于前端提供「查看合并业绩」入口）
    mergeable = False
    if base_acct and base_acct.account_name:
        mergeable = MomAccountRecord.objects.filter(
            account_name=base_acct.account_name
        ).count() > 1
    rj = product.raw_json or {}
    if is_merge:
        display_name = _pick('account_name') or product.product_name
    else:
        display_name = product.product_name
    info = {
        'pid': product.pid,
        'product_name': display_name,
        'group_name': rj.get('groupName'),
        'product_type': product.product_type,
        'last_edit_ts': product.last_edit_ts,
        'data_update_date': navs[-1][0].isoformat() if navs else None,
        # 投顾概览（来自 mom_account_record）
        'account_name': _pick('account_name'),
        'account_code': '、'.join(accounts),
        'account_codes': accounts,
        'account_pids': {p.product_name: p.pid for p in group_products},
        'account_count': len(accounts),
        'merged': is_merge,
        'mergeable': mergeable,
        'is_stop': 1 if accounts and all(
            accts.get(c) and accts[c].is_stop == 1 for c in accounts) else 0,
        'invest_logic': _pick('invest_logic'),
        'invest_cate': _pick('invest_cate'),
        'product_name_cn': base_acct.product_name if base_acct else None,
        'cum_investment': sum(
            float(accts[c].cum_investment or 0) for c in invest_codes
            if accts.get(c)) or None,
    }

    return Response({
        'info': info,
        'indicators': indicators,
        'risk_table': risk_table,
        'nav_series': nav_series,
        'benchmark_series': _benchmark_series_for_dates([d for d, _ in navs]) if navs else [],
    })
