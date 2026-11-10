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
    _account_pnl, _account_series, _benchmark_series_for_dates,
    _group_equity_daily, _share_method_nav,
)


@api_view(['GET'])
@permission_classes([AllowAny])
def strategy_portfolio(request):
    """自定义策略组合分析（参考火富牛基金组合模块）。

    ?pids=1,2,3            组合成分投顾 pid 列表（必填）
    ?model=equal           权重模型：equal 等权 / mv 均值方差 / rp 风险平价 / custom 自定义
    ?weights=30,30,40      custom 模型下的自定义权重（百分数或小数均可，自动归一化）
    ?equity=settle         权益口径：settle 期末结存（默认，结算单口径） / mv 市值权益（收盘价重估）

    成分净值数据源 rh_funds（所选口径权益 + 出入金），
    份额法还原净值：share_t = share_{t-1} + flow_t / nav_{t-1}，nav_t = equity_t / share_t；
    同名多账户投顾自动合并（经 MomAccountRecord 账号组）。
    成分日收益率 = nav_t / nav_{t-1} - 1。

    智能模型基于各成分投顾日收益率序列在接口内现算：
    - rp  风险平价：等风险贡献（ERC），协方差坐标下降迭代求解
    - mv  均值方差：最大夏普切点组合 w ∝ Σ⁻¹μ，负权截断归一
    组合日收益率 = Σ(成分日收益率 × 权重)，成分当日缺净值按 0 处理。
    """
    import math
    import statistics

    from .models import MomAccountRecord, PerfProducts

    pids_raw = request.query_params.get('pids', '').strip()
    weights_raw = request.query_params.get('weights', '').strip()
    model = (request.query_params.get('model') or 'equal').strip().lower()
    if model not in ('equal', 'mv', 'rp', 'custom', 'fund'):
        return Response({'detail': 'model 仅支持 equal / mv / rp / custom / fund'}, status=400)
    equity = (request.query_params.get('equity') or 'settle').strip().lower()
    if equity not in ('settle', 'mv'):
        return Response({'detail': 'equity 仅支持 settle / mv'}, status=400)
    equity_col = 'settle_balance' if equity == 'settle' else 'market_value_equity'
    if not pids_raw:
        return Response({'detail': '缺少 pids 参数'}, status=400)

    try:
        pids = [int(x) for x in re.split(r'[,\s]+', pids_raw) if x]
    except ValueError:
        return Response({'detail': 'pids 参数无效'}, status=400)
    pids = list(dict.fromkeys(pids))[:20]  # 去重，最多 20 个
    if not pids:
        return Response({'detail': 'pids 参数无效'}, status=400)

    # 各成分投顾净值序列 {pid: {date: nav}}
    # 数据源 rh_funds：市值权益 + 出入金份额法现算（同名多账户合并）
    pid_products = {p.pid: p.product_name for p in PerfProducts.objects.filter(pid__in=pids)}

    def _resolve_accounts(code):
        """pid 对应产品账号 → MomAccountRecord 同名账号组（多账户合并）。"""
        base = MomAccountRecord.objects.filter(account_id=code).first()
        if base and base.account_name:
            return list(
                MomAccountRecord.objects
                .filter(account_name=base.account_name)
                .values_list('account_id', flat=True)
            )
        return [code]

    pid_accounts = {}
    all_accounts = set()
    for pid in pids:
        code = pid_products.get(pid)
        if not code:
            continue
        accs = _resolve_accounts(code)
        pid_accounts[pid] = accs
        all_accounts.update(accs)

    acc_daily = {}  # account -> {date: (equity, flow)}（仅 rh_funds 覆盖账户；缺失账户由 helper 合成）
    group_daily = {}  # pid -> 组内每日聚合 {date: [equity, flow]}
    for pid, accs in pid_accounts.items():
        daily, _covered = _group_equity_daily(accs, equity_col)
        group_daily[pid] = daily

    nav_map = {pid: {} for pid in pids}
    latest_mv = {}  # pid -> 组内最新权益（最新市值，与权益口径一致）
    for pid in pids:
        daily = group_daily.get(pid) or {}
        if daily:
            latest_mv[pid] = daily[max(daily)][0]
        for d, nav in _share_method_nav(daily):
            nav_map[pid][d] = nav

    # 只保留有净值数据的成分
    valid_pids = [pid for pid in pids if nav_map[pid]]
    if not valid_pids:
        return Response({'detail': '所选投顾均无净值数据'}, status=404)
    n = len(valid_pids)

    # 成分日收益率：r_t = nv_t / nv_{t-1} - 1
    daily_ret = {}
    for pid in valid_pids:
        series = sorted(nav_map[pid].items())
        rets = {}
        prev = None
        for d, nv in series:
            if prev is not None:
                rets[d] = nv / prev - 1
            prev = nv
        daily_ret[pid] = rets

    # ---- 权重模型计算 ----
    def _mat_vec_mul(mat, vec):
        return [sum(mat[i][j] * vec[j] for j in range(len(vec))) for i in range(len(mat))]

    def _solve_linear(mat, vec):
        """高斯消元解 mat·x = vec（含主元选取）；奇异时加对角正则化重试。"""
        size = len(vec)
        for reg_attempts in range(4):
            m = [row[:] for row in mat]
            if reg_attempts:
                lam = 1e-8 * (10 ** reg_attempts)
                m = [[m[i][j] + (lam if i == j else 0.0) for j in range(size)] for i in range(size)]
            b = vec[:]
            try:
                for col in range(size):
                    pivot = max(range(col, size), key=lambda r: abs(m[r][col]))
                    if abs(m[pivot][col]) < 1e-14:
                        raise ZeroDivisionError
                    m[col], m[pivot] = m[pivot], m[col]
                    b[col], b[pivot] = b[pivot], b[col]
                    for r in range(col + 1, size):
                        factor = m[r][col] / m[col][col]
                        for c in range(col, size):
                            m[r][c] -= factor * m[col][c]
                        b[r] -= factor * b[col]
                x = [0.0] * size
                for i in range(size - 1, -1, -1):
                    x[i] = (b[i] - sum(m[i][j] * x[j] for j in range(i + 1, size))) / m[i][i]
                return x
            except ZeroDivisionError:
                continue
        return None

    def _compute_weights():
        """按权重模型返回归一化权重列表；失败回退等权。"""
        if model == 'custom':
            if not weights_raw:
                return [1.0 / n] * n, 'custom:未提供权重，回退等权'
            try:
                ws = [float(x) for x in re.split(r'[,\s]+', weights_raw) if x]
            except ValueError:
                return [1.0 / n] * n, 'custom:权重解析失败，回退等权'
            if len(ws) != n or any(w < 0 for w in ws) or sum(ws) <= 0:
                return [1.0 / n] * n, 'custom:权重数量/取值无效，回退等权'
            s = sum(ws)
            return [w / s for w in ws], None

        if model == 'equal':
            return [1.0 / n] * n, None

        # 智能模型：基于日收益率矩阵（缺失日按 0）
        all_d = sorted(set().union(*(set(daily_ret[pid].keys()) for pid in valid_pids)))
        if len(all_d) < max(20, n + 5):
            return [1.0 / n] * n, f'{model}:样本不足，回退等权'
        mat = [[daily_ret[pid].get(d, 0.0) for d in all_d] for pid in valid_pids]
        obs = len(all_d)
        mu = [sum(col) / obs for col in mat]
        cov = [[0.0] * n for _ in range(n)]
        for i in range(n):
            for j in range(i, n):
                c = sum((mat[i][t] - mu[i]) * (mat[j][t] - mu[j]) for t in range(obs)) / (obs - 1)
                cov[i][j] = cov[j][i] = c

        if model == 'rp':
            # 等风险贡献（ERC）坐标下降迭代：x_i ← [−(Σx)_i + x_i σ_ii + √((Σx−x_iσ_ii)² + 4σ_ii/n)] / (2σ_ii)
            x = [1.0 / max(math.sqrt(cov[i][i]), 1e-12) for i in range(n)]
            s = sum(x)
            x = [v / s for v in x]
            for _ in range(200):
                prev_x = x[:]
                for i in range(n):
                    sx = _mat_vec_mul(cov, x)
                    a = sx[i] - x[i] * cov[i][i]
                    x[i] = (-a + math.sqrt(a * a + 4 * cov[i][i] / n)) / (2 * cov[i][i])
                s = sum(x)
                x = [v / s for v in x]
                if max(abs(x[i] - prev_x[i]) for i in range(n)) < 1e-10:
                    break
            return x, None

        if model == 'mv':
            # 最大夏普切点组合：w ∝ Σ⁻¹μ；负权截断为 0 后归一
            w = _solve_linear(cov, mu)
            if w is None:
                return [1.0 / n] * n, 'mv:协方差矩阵奇异，回退等权'
            w = [max(v, 0.0) for v in w]
            s = sum(w)
            if s <= 0:
                return [1.0 / n] * n, 'mv:求解退化，回退等权'
            return [v / s for v in w], None

        return [1.0 / n] * n, None

    if model == 'fund':
        # 整体运作（fund）：组合视作单一投顾——各成员组每日权益与现金流直接合并，
        # 后上线投顾的初始投入按组合入金经份额法并入，无权重概念
        merged_daily = {}
        for pid in valid_pids:
            for d, (eq, fl) in (group_daily.get(pid) or {}).items():
                v = merged_daily.setdefault(d, [0.0, 0.0])
                v[0] += eq
                v[1] += fl
        port_nav_list = _share_method_nav(merged_daily)

        all_dates = [d for d, _ in port_nav_list]
        port_nav = port_nav_list[-1][1] if port_nav_list else 1.0
        nav_series = []
        port_rets = []
        peak = None
        prev_nav = None
        for d, nav in port_nav_list:
            if peak is None or nav > peak:
                peak = nav
            r = (nav / prev_nav - 1) if prev_nav else 0.0
            nav_series.append({
                'date': d.isoformat(),
                'nav': round(nav, 6),
                'cum_return': round((nav - 1) * 100, 4),
                'drawdown': round((nav / peak - 1) * 100, 4) if peak else 0.0,
            })
            port_rets.append(r)
            prev_nav = nav
        weights = [None] * len(valid_pids)
        weight_note = '整体运作：组合视作单一投顾，后上线成分的投入按组合入金处理，无权重概念'
    else:
        weights, weight_note = _compute_weights()

        # 交易日并集（各成分任一有净值/收益的日期）
        all_dates = sorted(set().union(*(set(nav_map[pid].keys()) for pid in valid_pids)))

        # 组合净值/累计收益/回撤
        port_nav = 1.0
        peak = 1.0
        nav_series = []
        port_rets = []
        for d in all_dates:
            r = sum(w * daily_ret[pid].get(d, 0.0) for pid, w in zip(valid_pids, weights))
            port_nav *= (1 + r)
            if port_nav > peak:
                peak = port_nav
            drawdown = port_nav / peak - 1
            nav_series.append({
                'date': d.isoformat(),
                'nav': round(port_nav, 6),
                'cum_return': round((port_nav - 1) * 100, 4),
                'drawdown': round(drawdown * 100, 4),
            })
            port_rets.append(r)

    # 风险收益指标（无风险利率取 1.5%）
    days = len(port_rets)
    total_return = port_nav - 1
    annual_yield = (1 + total_return) ** (252 / days) - 1 if days > 0 else None
    annual_vol = statistics.stdev(port_rets) * math.sqrt(252) if days >= 2 else None
    max_dd = min((p['drawdown'] for p in nav_series), default=0.0) / 100
    metrics = {
        'total_return': total_return,
        'annual_yield': annual_yield,
        'annual_volatility': annual_vol,
        'max_drawdown': max_dd,
        'sharpe_ratio': ((annual_yield - 0.015) / annual_vol) if annual_yield is not None and annual_vol else None,
        'calmar_ratio': (annual_yield / abs(max_dd)) if annual_yield is not None and max_dd < 0 else None,
        'daily_count': days,
        'start_date': all_dates[0].isoformat() if all_dates else None,
        'end_date': all_dates[-1].isoformat() if all_dates else None,
    }

    # 成分明细：名称/权重/累计收益/最新净值/规模
    products = {p.pid: p for p in PerfProducts.objects.filter(pid__in=valid_pids)}
    # 组内全部账号的账户记录（总投资金额按同名组合并，含已清盘账户）
    group_account_set = {acc for pid in valid_pids for acc in pid_accounts.get(pid, [])}
    accts = {m.account_id: m for m in MomAccountRecord.objects.filter(account_id__in=group_account_set)}
    # 账号代码 → pid（供前端点击代码跳转对应投顾业绩页）
    code_pid_map = {
        p.product_name: p.pid
        for p in PerfProducts.objects.filter(product_name__in=group_account_set)
    }
    # 账号级日序列（算每账号累计盈亏）
    acct_series, _rh_covered = _account_series(sorted(group_account_set), equity_col)

    advisors = []
    for pid, w in zip(valid_pids, weights):
        product = products.get(pid)
        acct = accts.get(product.product_name) if product else None
        navs = sorted(nav_map[pid].items())
        # 组合累计总投入：同名组全部账户 cum_investment 合计
        group_codes = pid_accounts.get(pid, [])
        group_invest_vals = [
            float(accts[c].cum_investment) for c in group_codes
            if accts.get(c) and accts[c].cum_investment is not None
        ]
        advisors.append({
            'pid': pid,
            # 代码显示组内全部账号（与净值/投入口径一致）
            'account_code': '、'.join(group_codes) if group_codes else (
                acct.account_id if acct else (product.product_name if product else str(pid))),
            'account_codes': group_codes,
            'account_pids': {c: code_pid_map[c] for c in group_codes if c in code_pid_map},
            # 账号级明细：每个账号的起止日期、累计投入与累计盈亏
            # 截至日期优先用人工维护的清盘日期（liquidation_date）
            'accounts': [
                {
                    'code': c,
                    'pid': code_pid_map.get(c),
                    'cum_investment': (
                        float(accts[c].cum_investment)
                        if accts.get(c) and accts[c].cum_investment is not None else None
                    ),
                    'pnl': _account_pnl(acct_series.get(c) or {}),
                    'start_date': min(acct_series[c]).isoformat() if acct_series.get(c) else None,
                    'end_date': (
                        accts[c].liquidation_date.isoformat()
                        if accts.get(c) and accts[c].liquidation_date
                        else (max(acct_series[c]).isoformat() if acct_series.get(c) else None)
                    ),
                }
                for c in group_codes
            ],
            'account_name': acct.account_name if acct else None,
            'invest_logic': acct.invest_logic if acct else None,
            'weight': round(w * 100, 2) if w is not None else None,
            'latest_nav': round(navs[-1][1], 4) if navs else None,
            # 累计收益与组合同口径：成分净值（rh_funds 权益+出入金份额法）末日/首日
            'total_return': (navs[-1][1] / navs[0][1] - 1) if navs else None,
            'cum_investment': round(sum(group_invest_vals), 2) if group_invest_vals else None,
            'latest_mv': latest_mv.get(pid),
        })

    # 组合规模合计
    def _sum(field):
        vals = [a[field] for a in advisors if a[field] is not None]
        return round(sum(vals), 2) if vals else None

    # 组合累计盈亏：Σ全部成分账号的账号级累计盈亏（含已清盘账号出金带走的盈利）
    total_pnl_vals = [
        p for p in (_account_pnl(s) for s in acct_series.values())
        if p is not None
    ]
    scale = {
        'advisor_count': len(advisors),
        'cum_investment': _sum('cum_investment'),
        'latest_mv': _sum('latest_mv'),
        'total_pnl': round(sum(total_pnl_vals), 2) if total_pnl_vals else None,
    }

    # 成分对比曲线（各投顾以自身首日净值归一的累计收益）
    member_series = []
    for pid in valid_pids:
        series = sorted(nav_map[pid].items())
        if not series:
            continue
        base = series[0][1]
        member_series.append({
            'pid': pid,
            'points': [
                {'date': d.isoformat(), 'cum_return': round((nv / base - 1) * 100, 4)}
                for d, nv in series
            ],
        })

    return Response({
        'model': model,
        'equity': equity,
        'weight_note': weight_note,
        'metrics': metrics,
        'nav_series': nav_series,
        'benchmark_series': _benchmark_series_for_dates(all_dates),
        'advisors': advisors,
        'scale': scale,
        'member_series': member_series,
    })


MODEL_LABELS = {
    'equal': '等权',
    'mv': '均值方差',
    'rp': '风险平价',
    'custom': '自定义',
    'fund': '整体运作',
}


def _portfolio_record_dto(record):
    return {
        'id': record.id,
        'name': record.name,
        'note': record.note,
        'pids': record.pids,
        'weights': record.weights,
        'weight_model': record.weight_model,
        'weight_model_label': MODEL_LABELS.get(record.weight_model, record.weight_model),
        'owner_id': record.owner_id,
        'owner_name': record.owner.username if record.owner else None,
        'created_at': record.created_at,
        'updated_at': record.updated_at,
    }


def _can_manage(record, user):
    """本人或超管可编辑/删除；公共组合（owner=NULL）仅超管可管理。"""
    if not (user and user.is_authenticated):
        return False
    if user.is_superuser:
        return True
    return record.owner_id == user.id


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def portfolio_records(request):
    """我的组合列表 / 新建保存组合。

    组合归属登录用户：GET 返回 自己的 + 公共（owner=NULL）组合，未登录仅返回公共组合；
    POST 需登录（组合归属当前用户）；编辑仅限本人（超管可管理全部）。
    """
    from .models import StrategyPortfolioRecord

    if request.method == 'GET':
        qs = StrategyPortfolioRecord.objects.select_related('owner').order_by('-updated_at')
        if not (request.user and request.user.is_authenticated):
            qs = qs.filter(owner__isnull=True)
        elif not request.user.is_superuser:
            qs = qs.filter(Q(owner=request.user) | Q(owner__isnull=True))
        return Response([
            {**_portfolio_record_dto(r),
             'is_mine': request.user.is_authenticated and r.owner_id == request.user.id}
            for r in qs
        ])

    # POST：保存组合（需登录）
    if not (request.user and request.user.is_authenticated):
        return Response({'detail': '登录后才能保存组合'}, status=401)
    payload = request.data or {}
    name = str(payload.get('name') or '').strip()
    pids = payload.get('pids')
    if not name:
        return Response({'detail': '组合名称不能为空'}, status=400)
    if not isinstance(pids, list) or not pids or len(pids) > 20:
        return Response({'detail': 'pids 须为非空列表（最多 20 个）'}, status=400)
    try:
        pids = [int(p) for p in pids]
    except (TypeError, ValueError):
        return Response({'detail': 'pids 元素须为整数'}, status=400)

    model = str(payload.get('weight_model') or 'equal').strip().lower()
    if model not in MODEL_LABELS:
        return Response({'detail': 'weight_model 仅支持 equal / mv / rp / custom'}, status=400)

    weights = payload.get('weights')
    if weights:  # 非空才校验；空列表 = 按模型自动计算，不存自定义权重
        if not isinstance(weights, list) or len(weights) != len(pids):
            return Response({'detail': 'weights 须为与 pids 等长的列表'}, status=400)
        try:
            weights = [round(float(w), 4) for w in weights]
        except (TypeError, ValueError):
            return Response({'detail': 'weights 元素须为数值'}, status=400)
    else:
        weights = []

    note = str(payload.get('note') or '').strip()[:255]

    record_id = payload.get('id')
    if record_id:
        try:
            record = StrategyPortfolioRecord.objects.get(pk=record_id)
        except StrategyPortfolioRecord.DoesNotExist:
            return Response({'detail': '组合不存在'}, status=404)
        if not _can_manage(record, request.user):
            return Response({'detail': '只能编辑自己的组合'}, status=403)
        record.name, record.note = name, note
        record.pids, record.weights, record.weight_model = pids, weights, model
        record.save()
    else:
        record = StrategyPortfolioRecord.objects.create(
            name=name[:100], note=note, pids=pids, weights=weights,
            weight_model=model, owner=request.user if request.user.is_authenticated else None)
    return Response(_portfolio_record_dto(record), status=201 if not record_id else 200)


@api_view(['GET', 'DELETE'])
@permission_classes([AllowAny])
def portfolio_record_detail(request, pk):
    """查询单个组合 / 删除指定组合（删除限本人或超管）。"""
    from .models import StrategyPortfolioRecord

    try:
        record = StrategyPortfolioRecord.objects.select_related('owner').get(pk=pk)
    except StrategyPortfolioRecord.DoesNotExist:
        return Response({'detail': '组合不存在'}, status=404)

    if request.method == 'GET':
        return Response(_portfolio_record_dto(record))

    if not _can_manage(record, request.user):
        return Response({'detail': '只能删除自己的组合'}, status=403)
    record.delete()
    return Response({'detail': '已删除'})
