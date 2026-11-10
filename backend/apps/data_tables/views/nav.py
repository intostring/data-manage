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


def _load_nhci_returns():
    """南华商品指数（NHCI.NH）日收益率 {date: r}，作为指标计算基准。"""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT trade_date, pct_chg FROM idx_nh_daily
            WHERE ts_code = 'NHCI.NH' AND pct_chg IS NOT NULL
            ORDER BY trade_date
        """)
        return {d: float(p) for d, p in cursor.fetchall()}


def _benchmark_series_for_dates(dates):
    """基准指数（NHCI.NH）在与给定日期序列对齐的累计收益曲线（首日为 0，百分数）。

    基准当日无数据按 0 收益处理，保证与组合 nav_series 逐日一一对应，
    前端可直接按下标计算超额收益（组合累计 − 基准累计）。
    """
    bench = _load_nhci_returns()
    nav_b = 1.0
    out = []
    for i, d in enumerate(dates):
        if i > 0:
            nav_b *= (1 + bench.get(d, 0.0))
        out.append({'date': d.isoformat(), 'cum_return': round((nav_b - 1) * 100, 4)})
    return out


def _account_series(accounts, equity_col='settle_balance', prefetched=None):
    """账号级日序列 {account: {date: [equity, flow]}} + rh_funds 覆盖账户集合。

    rh_funds 覆盖的账户：所选口径权益（默认结算权益）+ 出入金；
    rh_funds 无数据的账户（已清盘/数据未入库）：以 净值表净值 × 总投资规模
    合成权益曲线，首个净值日计一笔全额入金。
    prefetched：可选，复用已预取的 {account: series} 结果（批量场景避免逐组查库），
    其覆盖范围须包含 accounts。
    """
    from ..models import MomAccountRecord, PerfNetValues, PerfProducts

    if prefetched is not None:
        covered = {a for a in accounts if prefetched.get(a)}
        series = {a: prefetched.get(a, {}) for a in accounts}
        return series, covered

    series = {}  # account -> {date: [equity, flow]}
    rh_covered = set()
    if accounts:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT trade_date, account,
                       COALESCE({equity_col}, 0),
                       COALESCE(deposit_amount, 0) - COALESCE(withdraw_amount, 0)
                FROM rh_funds
                WHERE account IN %s AND trade_date IS NOT NULL
                """,
                [tuple(accounts)],
            )
            for d, acc, eq_val, flow in cursor.fetchall():
                rh_covered.add(acc)
                v = series.setdefault(acc, {}).setdefault(d, [0.0, 0.0])
                v[0] += float(eq_val)
                v[1] += float(flow)

    # 缺 rh_funds 的账户：净值表 × 投资规模 合成
    missing = [a for a in accounts if a not in rh_covered]
    if missing:
        pid_map = {p.product_name: p.pid for p in PerfProducts.objects.filter(product_name__in=missing)}
        acct_map = {m.account_id: m for m in MomAccountRecord.objects.filter(account_id__in=missing)}
        for code in missing:
            pid = pid_map.get(code)
            m = acct_map.get(code)
            scale = None
            if m is not None:
                if m.cum_investment:
                    scale = float(m.cum_investment)
                elif m.mk_bf:
                    scale = float(m.mk_bf)
            if pid is None or not scale or scale <= 0:
                continue
            nav_qs = (
                PerfNetValues.objects
                .filter(pid=pid, trade_date__isnull=False, net_value__isnull=False)
                .order_by('trade_date')
                .values_list('trade_date', 'net_value')
            )
            s = series.setdefault(code, {})
            first_day = True
            for d, nv in nav_qs:
                if not nv or nv <= 0:
                    continue
                s[d] = [float(nv) * scale, scale if first_day else 0.0]
                first_day = False
    return series, rh_covered


def _account_pnl(s):
    """单账号累计盈亏 = 数据末日权益 − 累计净入金（首日入金形成期初权益，口径自洽）。"""
    if not s:
        return None
    end_eq = s[max(s)][0]
    total_flow = sum(fl for _, (eq, fl) in s.items())
    return round(end_eq - total_flow, 2)


def _group_equity_daily(accounts, equity_col='settle_balance', prefetched=None):
    """同名账号组每日聚合权益与现金流 {date: [equity, flow]}。

    账号级序列见 _account_series；账户数据早于组合末日结束（清盘/赎回/停更）时，
    在其次一交易日计全额出金，避免权益凭空消失被份额法误判为亏损。
    prefetched：复用已预取的账号级序列（批量场景避免逐组查库）。
    返回 (daily, rh_covered账户集合)。
    """
    series, rh_covered = _account_series(accounts, equity_col, prefetched=prefetched)

    # 聚合 + 中断账户全额出金
    all_dates = sorted({d for s in series.values() for d in s})
    date_idx = {d: i for i, d in enumerate(all_dates)}
    daily = {}
    for s in series.values():
        if not s:
            continue
        for d, (eq, fl) in s.items():
            v = daily.setdefault(d, [0.0, 0.0])
            v[0] += eq
            v[1] += fl
        d_end = max(s)
        end_eq = s[d_end][0]
        idx = date_idx.get(d_end)
        if end_eq > 0 and idx is not None and idx + 1 < len(all_dates):
            daily.setdefault(all_dates[idx + 1], [0.0, 0.0])[1] -= end_eq
    return daily, rh_covered


def _share_method_nav(daily):
    """份额法由 {date: [equity, flow]} 还原净值序列 [(date, nav)]，首日净值 1.0。"""
    navs = []
    share = None
    prev_nav = 1.0
    for d in sorted(daily):
        equity, flow = daily[d]
        if share is None:
            if equity <= 0:
                continue
            share = equity
            navs.append((d, 1.0))
            continue
        share += flow / prev_nav
        nav = equity / share if share > 0 else prev_nav
        navs.append((d, nav))
        prev_nav = nav
    return navs


def _nav_window_metrics(navs, bench_rets=None):
    """由净值序列 [(date, nav)] 计算单窗口风险指标（小数口径，与 perf_risk_indicators 一致）。

    无风险利率 1.5%；
    bench_rets 为基准日收益 {date: r}（南华商品指数 NHCI.NH）时，
    另行计算 beta / Jensen 年化 alpha / 信息比率，否则置 None。
    """
    import math
    import statistics

    empty = {k: None for k in (
        'annual_yield', 'annual_volatility', 'max_drawdown',
        'sharpe_ratio', 'kama_ratio', 'info_ratio', 'alpha', 'beta')}
    if len(navs) < 2:
        return empty

    rets = [navs[i][1] / navs[i - 1][1] - 1 for i in range(1, len(navs))]
    total = navs[-1][1] / navs[0][1] - 1
    days = len(rets)
    annual_yield = (1 + total) ** (252 / days) - 1
    annual_vol = statistics.stdev(rets) * math.sqrt(252) if days >= 2 else None
    peak, max_dd = navs[0][1], 0.0
    for _, nav in navs:
        peak = max(peak, nav)
        max_dd = min(max_dd, nav / peak - 1)
    sharpe = ((annual_yield - 0.015) / annual_vol) if annual_vol else None
    kama = (annual_yield / abs(max_dd)) if max_dd < 0 else None

    info_ratio = alpha = beta = None
    if bench_rets:
        # 按日期对齐组合日收益与基准日收益
        pr, br = [], []
        for i in range(1, len(navs)):
            b = bench_rets.get(navs[i][0])
            if b is not None:
                pr.append(navs[i][1] / navs[i - 1][1] - 1)
                br.append(b)
        if len(pr) >= 3:
            mean_p, mean_b = statistics.mean(pr), statistics.mean(br)
            var_b = statistics.pvariance(br)
            cov_pb = sum((pr[i] - mean_p) * (br[i] - mean_b) for i in range(len(pr))) / len(pr)
            if var_b > 0:
                beta = cov_pb / var_b
                # Jensen 年化 alpha：组合年化 − rf − β×(基准年化 − rf)
                ann_p = (1 + mean_p) ** 252 - 1
                ann_b = (1 + mean_b) ** 252 - 1
                alpha = (ann_p - 0.015) - beta * (ann_b - 0.015)
            excess = [pr[i] - br[i] for i in range(len(pr))]
            if len(excess) >= 3:
                te_annual = statistics.stdev(excess) * math.sqrt(252)
                if te_annual > 0:
                    info_ratio = (statistics.mean(excess) * 252) / te_annual

    return {
        'annual_yield': annual_yield,
        'annual_volatility': annual_vol,
        'max_drawdown': max_dd,
        'sharpe_ratio': sharpe,
        'kama_ratio': kama,
        'info_ratio': info_ratio,
        'alpha': alpha,
        'beta': beta,
    }
