import re
from datetime import date as _date, timedelta

from django.db import connection, models
from django.db.models import Q
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .registry import table_registry


# 持仓明细表(perf_variety_position_detail)的品种命名与标准表
# (fut_symbol_info / fut_market_stats / yl_perf_variety_pnl_trend)不一致的别名
POSITION_VARIETY_ALIASES = {
    '中证1000': ['中证1000指数期货'],
    '铁矿石': ['铁矿'],
    '棕榈油': ['棕榈'],
    'PTA': ['精对苯二甲酸'],
    'LPG': ['液化石油气'],
    'PVC': ['聚氯乙烯'],
    '郑棉': ['棉花'],
    '集运指数(欧线)': ['EC'],
    '铝合金': ['AD'],
    '纯苯': ['BZ'],
    '原木': ['LG'],
    '多晶硅': ['PS'],
    '瓶片': ['PR'],
    '对二甲苯': ['PX'],
    '烧碱': ['SH'],
    '双胶纸': ['OP'],
    '丙烯': ['PL'],
    '铂': ['PT'],
    '钯': ['PD'],
}


def position_variety_names(standard_name):
    """返回标准品种名在持仓明细表中的全部可能命名（含自身），用于 IN 查询。"""
    return [standard_name, *POSITION_VARIETY_ALIASES.get(standard_name, [])]


def position_variety_in_sql(names):
    """生成 variety IN (...) 的占位片段，与参数列表配合使用。"""
    return 'variety IN (' + ','.join(['%s'] * len(names)) + ')'


# 筛选操作符 → Django ORM lookup 映射
FILTER_OPS = {
    'eq': '',            # 精确匹配
    'ne': '',            # 不等于（exclude）
    'contains': 'icontains',
    'not_contains': 'icontains',  # 不包含（exclude）
    'gt': 'gt',
    'lt': 'lt',
    'gte': 'gte',
    'lte': 'lte',
    'empty': 'isnull',   # 为空
    'not_empty': 'isnull',  # 不为空（exclude isnull）
}


def _apply_advanced_filters(qs, request, model):
    """解析 filter.<col>.<op>=value 查询参数并应用到 queryset

    支持的操作符：eq, ne, contains, not_contains, gt, lt, gte, lte, empty, not_empty
    """
    valid_fields = {f.name for f in model._meta.fields}
    for k, v in request.query_params.items():
        if not k.startswith('filter.'):
            continue
        parts = k[len('filter.'):].split('.')
        if len(parts) != 2:
            continue
        col, op = parts
        if col not in valid_fields or op not in FILTER_OPS:
            continue
        lookup = FILTER_OPS[op]
        if op in ('empty', 'not_empty'):
            # 为空/不为空：不需要值
            is_null = True
            if op == 'empty':
                qs = qs.filter(**{f'{col}__isnull': True}) | qs.filter(**{col: ''})
            else:
                qs = qs.filter(**{f'{col}__isnull': False}).exclude(**{col: ''})
        elif op in ('ne', 'not_contains'):
            # 排除型
            field_lookup = f'{col}__{lookup}' if lookup else col
            qs = qs.exclude(**{field_lookup: v})
        else:
            field_lookup = f'{col}__{lookup}' if lookup else col
            qs = qs.filter(**{field_lookup: v})
    return qs


class DynamicModelViewSet(viewsets.ModelViewSet):
    """通用 ViewSet，通过类属性 model / serializer_class 绑定具体表。

    子类（由 urls.py 动态生成）设置这两个属性即可获得完整 CRUD。
    支持排序（ordering 参数）与 Navicat 风格多操作符筛选。
    """
    model = None
    serializer_class = None
    filter_backends = [OrderingFilter]
    ordering_fields = '__all__'
    # 默认按 id 倒序，避免分页时 UnorderedObjectListWarning
    ordering = ['-id']

    def get_queryset(self):
        qs = self.model.objects.all()
        search = self.request.query_params.get('search', '').strip()
        if search:
            query = Q()
            for field in self.model._meta.fields:
                if isinstance(field, (models.CharField, models.TextField)):
                    query |= Q(**{f'{field.name}__icontains': search})
            if query:
                qs = qs.filter(query)
        qs = _apply_advanced_filters(qs, self.request, self.model)
        return qs


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_tables(request):
    """返回所有已注册的已有表清单，含行数与最新更新时间"""
    # 批量查 information_schema 获取每张表的行数和更新时间
    table_names = [e.model._meta.db_table for e in table_registry.all()]
    stats = {}
    if table_names:
        from django.db import connection
        placeholders = ','.join(['%s'] * len(table_names))
        with connection.cursor() as cur:
            cur.execute(
                f"SELECT TABLE_NAME, TABLE_ROWS, UPDATE_TIME "
                f"FROM information_schema.TABLES "
                f"WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME IN ({placeholders})",
                table_names,
            )
            for name, rows, upd in cur.fetchall():
                stats[name] = {'row_count': rows or 0, 'updated_at': upd}
    return Response([
        {
            'key': e.key,
            'label': e.label,
            'type': 'existing',
            'group': e.group,
            'row_count': stats.get(e.model._meta.db_table, {}).get('row_count', 0),
            'updated_at': stats.get(e.model._meta.db_table, {}).get('updated_at'),
        }
        for e in table_registry.all()
    ])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def table_columns(request, key):
    """返回指定表的字段元信息：[{name, label, type}]

    label 优先取数据库字段注释 db_comment（中文），用于前端表头中文化。
    """
    try:
        entry = table_registry.get(key)
    except KeyError:
        return Response({'detail': f'未注册的表: {key}'}, status=404)
    return Response({
        'key': entry.key,
        'label': entry.label,
        'columns': entry.get_columns(),
    })


# ==================== Excel 导出 / 导入 ====================

def _apply_filters(qs, request, entry):
    """对 queryset 应用 URL 查询参数中的筛选与搜索（与列表接口一致）"""
    # search：在所有 CharField / TextField 上 icontains
    search = request.query_params.get('search', '').strip()
    if search:
        q = Q()
        for f in entry.model._meta.fields:
            if isinstance(f, (models.CharField, models.TextField)):
                q |= Q(**{f'{f.name}__icontains': search})
        qs = qs.filter(q)

    # Navicat 风格多操作符筛选
    qs = _apply_advanced_filters(qs, request, entry.model)

    # 排序
    ordering = request.query_params.get('ordering', '').strip()
    if ordering:
        qs = qs.order_by(ordering)
    return qs


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def table_export(request, key):
    """导出已注册表为 Excel(.xlsx)。

    支持 search / 字段筛选 / ordering 参数，导出筛选后的结果。
    """
    try:
        entry = table_registry.get(key)
    except KeyError:
        return Response({'detail': f'未注册的表: {key}'}, status=404)

    from openpyxl import Workbook
    from openpyxl.utils import get_column_letter
    from urllib.parse import quote

    qs = _apply_filters(entry.model.objects.all(), request, entry)
    cols = entry.get_columns()

    wb = Workbook()
    ws = wb.active
    ws.title = entry.label[:31]  # Excel sheet 名最长 31
    # 表头：中文 label
    ws.append([c['label'] for c in cols])
    for cell in ws[1]:
        cell.font = cell.font.copy(bold=True)

    # 数据行
    field_names = [c['name'] for c in cols]
    for obj in qs.iterator():
        ws.append([_excel_cell(getattr(obj, fn, None)) for fn in field_names])

    # 列宽：按表头长度粗略设置
    for i, c in enumerate(cols, start=1):
        ws.column_dimensions[get_column_letter(i)].width = min(max(len(str(c['label'])) + 4, 10), 30)

    buf = __import__('io').BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f'{entry.label}_{__import__("datetime").datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    resp = HttpResponse(
        buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    resp['Content-Disposition'] = f"attachment; filename*=UTF-8''{quote(filename)}"
    return resp


def _excel_cell(val):
    """把 Django 字段值转为 Excel 可写的类型"""
    if val is None:
        return ''
    from datetime import date, datetime
    if isinstance(val, datetime):
        return val.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(val, date):
        return val.strftime('%Y-%m-%d')
    if isinstance(val, (models.DecimalField,)):
        return float(val) if val is not None else ''
    return val


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def table_import(request, key):
    """从 Excel(.xlsx) 导入数据到已注册表（存在则更新，不存在则新增，完全重复则跳过）。

    multipart/form-data:
        file: .xlsx 文件
    表头需与字段 name 或 label 匹配（中英文均可）。
    """
    try:
        entry = table_registry.get(key)
    except KeyError:
        return Response({'detail': f'未注册的表: {key}'}, status=404)

    file = request.FILES.get('file')
    if not file:
        return Response({'detail': '缺少 file 参数'}, status=400)

    from openpyxl import load_workbook
    cols = entry.get_columns()
    # 建立 表头 -> 字段名 映射（支持 label / name 双向匹配）
    header_to_name = {}
    for c in cols:
        header_to_name[c['label']] = c['name']
        header_to_name[c['name']] = c['name']

    try:
        wb = load_workbook(file, data_only=True)
    except Exception as e:
        return Response({'detail': f'Excel 解析失败: {e}'}, status=400)

    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    try:
        header = next(rows_iter)
    except StopIteration:
        return Response({'detail': 'Excel 文件为空'}, status=400)

    # 列索引 -> 字段名（跳过 id 列与未知列）
    col_map = {}
    for idx, h in enumerate(header):
        if h is None:
            continue
        h_str = str(h).strip()
        if h_str in header_to_name:
            fn = header_to_name[h_str]
            if fn != 'id':  # 不允许通过导入修改 id
                col_map[idx] = fn

    if not col_map:
        return Response({'detail': '未匹配到任何有效字段，请检查表头'}, status=400)

    # 获取模型的唯一约束字段组合（unique_together + 字段级 unique）
    field_types = {c['name']: c['type'] for c in cols}
    unique_fields = _get_unique_fields(entry.model)

    created_count = 0
    updated_count = 0
    skipped_count = 0
    errors = []
    for row_idx, row in enumerate(rows_iter, start=2):
        if row is None or all(v is None or v == '' for v in row):
            continue
        kwargs = {}
        for idx, fn in col_map.items():
            if idx >= len(row):
                continue
            val = row[idx]
            if val == '' or val is None:
                continue
            # 类型转换
            t = field_types.get(fn, 'str')
            try:
                if t == 'int':
                    val = int(float(val))
                elif t == 'float':
                    val = float(val)
                elif t == 'bool':
                    val = 1 if str(val).strip() in ('1', 'true', 'True', '是') else 0
            except (ValueError, TypeError):
                errors.append(f'第 {row_idx} 行字段 {fn} 值"{val}"类型转换失败')
                continue
            kwargs[fn] = val
        if not kwargs:
            continue

        # 按 unique 字段查找已有记录
        lookup = {}
        if unique_fields:
            for uf in unique_fields:
                if uf in kwargs:
                    lookup[uf] = kwargs[uf]
        if lookup:
            existing = entry.model.objects.filter(**lookup).first()
            if existing:
                # 检查是否有变化
                changed = False
                for k, v in kwargs.items():
                    if getattr(existing, k, None) != v:
                        setattr(existing, k, v)
                        changed = True
                if changed:
                    try:
                        existing.save()
                        updated_count += 1
                    except Exception as e:
                        errors.append(f'第 {row_idx} 行更新失败: {e}')
                else:
                    skipped_count += 1
                continue
        # 不存在则新增
        try:
            entry.model.objects.create(**kwargs)
            created_count += 1
        except Exception as e:
            errors.append(f'第 {row_idx} 行新增失败: {e}')

    return Response({
        'created': created_count,
        'updated': updated_count,
        'skipped': skipped_count,
        'errors': errors,
    }, status=201)


def _get_unique_fields(model):
    """获取模型的唯一约束字段列表。

    优先使用 unique_together 中的字段组合；
    如果没有 unique_together，则收集字段级 unique=True 的字段。
    """
    meta = model._meta
    # unique_together
    if meta.unique_together:
        return list(meta.unique_together[0])
    # Django 4.x constraints (UniqueConstraint)
    unique_constraint_fields = []
    for constraint in meta.constraints:
        if hasattr(constraint, 'fields') and constraint.fields:
            unique_constraint_fields = list(constraint.fields)
            break
    if unique_constraint_fields:
        return unique_constraint_fields
    # 字段级 unique=True
    unique_single = []
    for f in meta.fields:
        if f.unique and not f.primary_key:
            unique_single.append(f.name)
    return unique_single


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
    """
    from collections import defaultdict

    merge = request.query_params.get('merge') == '1'

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

    # ---- 拉取各组账号的 rh_funds 日序列，份额法现算指标与仓位 ----
    all_accounts = {r['account_code'] for r in rows}
    funds_by_account = defaultdict(list)  # account -> [(date, settle_balance, margin, flow)]
    if all_accounts:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT trade_date, account, settle_balance, margin,
                       COALESCE(deposit_amount, 0) - COALESCE(withdraw_amount, 0) AS flow
                FROM rh_funds
                WHERE account IN %s AND trade_date IS NOT NULL
                ORDER BY trade_date
            """, [tuple(all_accounts)])
            for d, acc, balance, margin, flow in cursor.fetchall():
                funds_by_account[acc].append((d, float(balance or 0), float(margin or 0), float(flow or 0)))

    result = []
    for key, g in groups.items():
        is_merged = merge and len(g) > 1
        # 组内各账号按日聚合
        daily = defaultdict(lambda: [0.0, 0.0, 0.0])  # date -> [equity, margin, flow]
        for row in g:
            for d, balance, margin, flow in funds_by_account.get(row['account_code'], []):
                v = daily[d]
                v[0] += balance
                v[1] += margin
                v[2] += flow
        series = [(d, v[0], v[2]) for d, v in sorted(daily.items())]
        metrics = _merged_nav_metrics(series) or {}
        # 平均仓位：成立以来 Σmargin/Σequity 日均
        ratios = [v[1] / v[0] * 100 for v in daily.values() if v[0] > 0]
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
    return Response(result)


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


@api_view(['GET'])
@permission_classes([AllowAny])
def advisor_performance(request):
    """投顾业绩聚合接口。

    无参数：返回投顾产品列表 [{pid, product_name}]
    ?pid=xxx：返回单个投顾的基本信息 + 风险收益指标
    ?pid=xxx&merge=1：同名多账号合并详情——净值由 rh_funds 市值+出入金份额法现算，
    指标（since/1y/2y/3y）由该净值序列切窗推导
    """
    from .models import PerfHeaderStats, PerfProducts, PerfRiskIndicators, PerfNetValues, MomAccountRecord

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
        return Response(result)

    # 单个投顾详情
    try:
        pid_int = int(pid)
    except (TypeError, ValueError):
        return Response({'detail': 'pid 参数无效'}, status=400)

    product = PerfProducts.objects.filter(pid=pid_int).first()
    if not product:
        return Response({'detail': f'未找到 pid={pid} 的产品'}, status=404)

    # ---- 合并模式：同名多账号合并详情 ----
    if request.query_params.get('merge') == '1':
        from collections import defaultdict
        from datetime import timedelta

        base_acct = MomAccountRecord.objects.filter(account_id=product.product_name).first()
        group_products = [product]
        if base_acct and base_acct.account_name:
            same_name = MomAccountRecord.objects.filter(account_name=base_acct.account_name)
            codes = [m.account_id for m in same_name]
            group_products = list(PerfProducts.objects.filter(product_name__in=codes))
            if product not in group_products:
                group_products.insert(0, product)
        accounts = [p.product_name for p in group_products]

        # 合并净值：rh_funds 份额法
        daily = defaultdict(lambda: [0.0, 0.0, 0.0])  # date -> [equity, margin, flow]
        if accounts:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT trade_date, account, settle_balance, margin,
                           COALESCE(deposit_amount, 0) - COALESCE(withdraw_amount, 0) AS flow
                    FROM rh_funds
                    WHERE account IN %s AND trade_date IS NOT NULL
                    ORDER BY trade_date
                """, [tuple(accounts)])
                for d, acc, balance, margin, flow in cursor.fetchall():
                    v = daily[d]
                    v[0] += float(balance or 0)
                    v[1] += float(margin or 0)
                    v[2] += float(flow or 0)

        navs = []  # [(date, nav)]
        share = None
        prev_nav = 1.0
        for d, (equity, _margin, flow) in sorted(daily.items()):
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
            last_date = navs[-1][0]
            windows = {'since': navs}
            for label, days_back in (('1y', 365), ('2y', 730), ('3y', 1095)):
                cutoff = last_date - timedelta(days=days_back)
                windows[label] = [x for x in navs if x[0] >= cutoff] or navs[-1:]
            window_metrics = {label: _nav_window_metrics(seq, bench_rets) for label, seq in windows.items()}
            risk_table = {
                metric: {p: window_metrics[p][metric] for p in risk_periods}
                for metric in risk_metrics
            }
            since_m = window_metrics['since']
            indicators = {
                'total_return': navs[-1][1] / navs[0][1] - 1,
                **{k: since_m[k] for k in risk_metrics},
            }

        # 合并 info
        accts = {m.account_id: m for m in MomAccountRecord.objects.filter(account_id__in=accounts)}
        def _pick(field):
            for code in accounts:
                a = accts.get(code)
                if a and getattr(a, field):
                    return getattr(a, field)
            return None
        active_codes = [c for c in accounts if accts.get(c) and accts[c].is_stop != 1]
        invest_codes = active_codes if active_codes else accounts
        info = {
            'pid': product.pid,
            'product_name': _pick('account_name') or product.product_name,
            'group_name': None,
            'product_type': product.product_type,
            'last_edit_ts': product.last_edit_ts,
            'data_update_date': navs[-1][0].isoformat() if navs else None,
            'account_name': _pick('account_name'),
            'account_code': '、'.join(accounts),
            'account_codes': accounts,
            'account_count': len(accounts),
            'merged': True,
            'is_stop': 1 if accounts and all(
                accts.get(c) and accts[c].is_stop == 1 for c in accounts) else 0,
            'invest_logic': _pick('invest_logic'),
            'invest_cate': _pick('invest_cate'),
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

    risk = PerfRiskIndicators.objects.filter(pid=pid_int).first()
    header = PerfHeaderStats.objects.filter(pid=pid_int, trade_date__isnull=False).order_by('-trade_date').first()

    # 从 MomAccountRecord 取投顾概览（account_id = product_name）
    acct = MomAccountRecord.objects.filter(account_id=product.product_name).first()

    # 基本信息
    rj = product.raw_json or {}
    # 该投顾是否属于同名多账号组（用于前端提供「查看合并业绩」入口）
    mergeable = False
    if acct and acct.account_name:
        mergeable = MomAccountRecord.objects.filter(
            account_name=acct.account_name
        ).count() > 1
    info = {
        'pid': product.pid,
        'product_name': product.product_name,
        'group_name': rj.get('groupName'),
        'product_type': product.product_type,
        'last_edit_ts': product.last_edit_ts,
        'data_update_date': header.trade_date.isoformat() if header and header.trade_date else None,
        # 投顾概览（来自 mom_account_record）
        'account_name': acct.account_name if acct else None,
        'account_code': acct.account_id if acct else None,
        'is_stop': acct.is_stop if acct else None,
        'invest_logic': acct.invest_logic if acct else None,
        'invest_cate': acct.invest_cate if acct else None,
        'product_name_cn': acct.product_name if acct else None,
        'mergeable': mergeable,
    }

    # 风险收益指标：投顾业绩顶部基本数据取成立以来口径
    indicators = {}
    risk_periods = ['1y', '2y', '3y', 'since']
    risk_metrics = [
        'annual_yield', 'annual_volatility', 'max_drawdown',
        'sharpe_ratio', 'kama_ratio', 'info_ratio', 'alpha', 'beta',
    ]
    risk_table = None
    if risk:
        indicators = {
            'total_return': header.since_inception_rise if header else None,
            'annual_yield': risk.annual_yield_since,
            'annual_volatility': risk.annual_volatility_since,
            'max_drawdown': risk.max_drawdown_since,
            'sharpe_ratio': risk.sharpe_ratio_since,
            'kama_ratio': risk.kama_ratio_since,
            'info_ratio': risk.info_ratio_since,
            'alpha': risk.alpha_since,
            'beta': risk.beta_since,
        }
        risk_table = {
            metric: {p: getattr(risk, f'{metric}_{p}') for p in risk_periods}
            for metric in risk_metrics
        }

    # 净值序列：从 perf_net_values 查询，按日期升序
    nav_qs = PerfNetValues.objects.filter(pid=pid_int, trade_date__isnull=False).order_by('trade_date')
    nav_series = []
    prev_nv = None
    peak = None  # 用于计算回撤
    for n in nav_qs:
        nv = n.net_value
        if nv is None:
            continue
        # 累计收益率（基于首日净值）
        if prev_nv is None:
            cum_ret = 0.0
            base_nv = nv
        else:
            cum_ret = (nv / base_nv - 1) if base_nv else 0.0
        # 回撤
        if peak is None or nv > peak:
            peak = nv
        drawdown = (nv / peak - 1) if peak else 0.0
        nav_series.append({
            'date': n.trade_date.isoformat() if n.trade_date else None,
            'nav': nv,
            'cum_return': round(cum_ret * 100, 4),
            'drawdown': round(drawdown * 100, 4),
        })
        prev_nv = nv

    return Response({
        'info': info,
        'indicators': indicators,
        'risk_table': risk_table,
        'nav_series': nav_series,
        'benchmark_series': (
            _benchmark_series_for_dates([
                _date.fromisoformat(p['date'])
                for p in nav_series if p['date']
            ]) if nav_series else []
        ),
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def sector_varieties(request):
    """品种搜索列表，支持按品种代码或简称模糊查询。"""
    q = request.query_params.get('q', '').strip()
    limit = min(max(int(request.query_params.get('limit', 20) or 20), 1), 50)

    with connection.cursor() as cursor:
        params = []
        where_sql = ''
        if q:
            where_sql = 'WHERE variety_code LIKE %s OR variety_name LIKE %s'
            like = f'%{q}%'
            params.extend([like, like])

        cursor.execute(
            f"""
            SELECT variety_code, variety_name
            FROM (
                SELECT
                    variety_code,
                    variety_name,
                    MAX(trade_date) AS latest_date
                FROM yl_perf_variety_pnl_trend
                {where_sql}
                GROUP BY variety_code, variety_name
            ) v
            ORDER BY latest_date DESC, variety_code
            LIMIT %s
            """,
            [*params, limit],
        )
        rows = [
            {'code': row[0], 'name': row[1]}
            for row in cursor.fetchall()
        ]

    return Response({'results': rows})


@api_view(['GET'])
@permission_classes([AllowAny])
def sector_contract_kline(request):
    """合约日K线数据。"""
    contract = request.query_params.get('contract', '').strip()
    account = request.query_params.get('account', '250528_HG').strip() or '250528_HG'
    window = request.query_params.get('window', '6m')
    if not contract:
        return Response({'detail': 'contract 不能为空'}, status=400)
    allowed_windows = {'1m', '3m', '6m', '1y', 'all', 'custom'}
    if window not in allowed_windows:
        return Response({'detail': 'window 参数无效'}, status=400)
    start_date = parse_date(request.query_params.get('start_date', '')) if window == 'custom' else None
    end_date = parse_date(request.query_params.get('end_date', '')) if window == 'custom' else None
    if window == 'custom' and (not start_date or not end_date or start_date > end_date):
        return Response({'detail': '自定义日期范围无效'}, status=400)

    code = contract.upper()
    code_base = re.sub(r'\.[A-Z]+$', '', code)
    code_key = code_base.replace('-', '')
    option_match = re.match(r'^([A-Z]+)(\d{3,4})-?([CP])-?(\d+)$', code_base)
    is_option_contract = bool(option_match)
    market_codes = {code_base, code_key}
    if option_match:
        opt_symbol, opt_month, opt_type, opt_strike = option_match.groups()
        market_codes.add(f'{opt_symbol}{opt_month}-{opt_type}-{opt_strike}')
        market_codes.add(f'{opt_symbol}{opt_month}{opt_type}{opt_strike}')
    market_codes = [item for item in market_codes if item]
    exchange_suffixes = ['', '.DCE', '.SHF', '.SHFE', '.CZCE', '.CZC', '.INE', '.GFEX', '.CFFEX', '.CFX']
    market_ts_codes = []
    for item in market_codes:
        market_ts_codes.extend(f'{item}{suffix}' for suffix in exchange_suffixes)
    market_ts_codes = list(dict.fromkeys(market_ts_codes))
    contract_candidates = set(market_codes)
    contract_candidates.add(contract.strip())
    contract_candidates.update(item.lower() for item in list(contract_candidates))
    contract_candidates = [item for item in contract_candidates if item]
    trade_page = max(int(request.query_params.get('trade_page', 1) or 1), 1)
    trade_page_size = min(max(int(request.query_params.get('trade_page_size', 20) or 20), 1), 100)
    offset = (trade_page - 1) * trade_page_size
    with connection.cursor() as cursor:
        ts_placeholders = ','.join(['%s'] * len(market_ts_codes))
        market_sql = f"""
            SELECT
                ts_code,
                trade_date,
                open,
                high,
                low,
                close,
                vol,
                amount,
                oi
            FROM {{table}}
            WHERE ts_code IN ({ts_placeholders})
            ORDER BY trade_date
        """

        def fetch_market_rows(table):
            cursor.execute(market_sql.format(table=table), market_ts_codes)
            fetched = [
                {
                    'ts_code': row[0],
                    'date': row[1].isoformat() if row[1] else None,
                    'open': row[2],
                    'high': row[3],
                    'low': row[4],
                    'close': row[5],
                    'vol': row[6],
                    'amount': row[7],
                    'oi': row[8],
                }
                for row in cursor.fetchall()
            ]
            if fetched:
                return fetched
            cursor.execute(
                f"""
                SELECT
                    ts_code,
                    trade_date,
                    open,
                    high,
                    low,
                    close,
                    vol,
                    amount,
                    oi
                FROM {table}
                WHERE ts_code LIKE %s
                ORDER BY trade_date
                """,
                [f'{code_base}.%'],
            )
            return [
                {
                    'ts_code': row[0],
                    'date': row[1].isoformat() if row[1] else None,
                    'open': row[2],
                    'high': row[3],
                    'low': row[4],
                    'close': row[5],
                    'vol': row[6],
                    'amount': row[7],
                    'oi': row[8],
                }
                for row in cursor.fetchall()
            ]

        market_tables = ['opt_market_data', 'fut_market_data'] if is_option_contract else ['fut_market_data', 'opt_market_data']
        rows = []
        for table in market_tables:
            rows = fetch_market_rows(table)
            if rows:
                break
        if rows:
            latest_trade_date = parse_date(rows[-1]['date'])
            if window == 'custom':
                filter_start = start_date
                filter_end = end_date
            elif window == 'all':
                filter_start = None
                filter_end = None
            else:
                days_map = {'1m': 31, '3m': 93, '6m': 186, '1y': 366}
                filter_start = latest_trade_date - timedelta(days=days_map[window])
                filter_end = latest_trade_date

            if filter_start or filter_end:
                rows = [
                    row for row in rows
                    if (not filter_start or parse_date(row['date']) >= filter_start)
                    and (not filter_end or parse_date(row['date']) <= filter_end)
                ]
        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM rh_trades
            WHERE contract IN ({','.join(['%s'] * len(contract_candidates))})
              AND account = %s
            """,
            [*contract_candidates, account],
        )
        trade_count = cursor.fetchone()[0]

        cursor.execute(
            f"""
            SELECT
                r.trade_date,
                r.trade_time,
                r.account,
                COALESCE(m.account_name, r.account) AS advisor_name,
                r.contract,
                r.side,
                r.open_close,
                r.trade_price,
                r.trade_qty,
                r.trade_amount,
                r.fee,
                r.close_profit,
                r.daily_close_profit
            FROM rh_trades r
            LEFT JOIN mom_account_record m ON m.account_id = r.account
            WHERE r.contract IN ({','.join(['%s'] * len(contract_candidates))})
              AND r.account = %s
            ORDER BY r.trade_date DESC, r.trade_time DESC, r.id DESC
            LIMIT %s OFFSET %s
            """,
            [*contract_candidates, account, trade_page_size, offset],
        )
        trade_rows = [
            {
                'trade_date': row[0].isoformat() if row[0] else None,
                'trade_time': row[1],
                'account': row[2],
                'advisor_name': row[3],
                'contract': row[4],
                'side': row[5],
                'open_close': row[6],
                'trade_price': row[7],
                'trade_qty': row[8],
                'trade_amount': row[9],
                'fee': row[10],
                'close_profit': row[11],
                'daily_close_profit': row[12],
            }
            for row in cursor.fetchall()
        ]
        cursor.execute(
            f"""
            SELECT
                trade_date,
                COALESCE(side, '') AS side,
                COALESCE(open_close, '') AS open_close,
                COUNT(*) AS trade_count,
                SUM(COALESCE(trade_qty, 0)) AS trade_qty,
                SUM(COALESCE(trade_amount, 0)) AS trade_amount,
                CASE
                    WHEN SUM(COALESCE(trade_qty, 0)) = 0 THEN AVG(trade_price)
                    ELSE SUM(COALESCE(trade_price, 0) * COALESCE(trade_qty, 0)) / SUM(COALESCE(trade_qty, 0))
                END AS avg_price
            FROM rh_trades
            WHERE contract IN ({','.join(['%s'] * len(contract_candidates))})
            {'AND account = %s' if account else ''}
            GROUP BY trade_date, COALESCE(side, ''), COALESCE(open_close, '')
            ORDER BY trade_date, side, open_close
            """,
            [*contract_candidates, account] if account else contract_candidates,
        )
        marker_rows = [
            {
                'date': row[0].isoformat() if row[0] else None,
                'side': row[1],
                'open_close': row[2],
                'trade_count': row[3],
                'trade_qty': row[4],
                'trade_amount': row[5],
                'avg_price': row[6],
            }
            for row in cursor.fetchall()
        ]

    return Response({
        'contract': contract,
        'account': account,
        'window': window,
        'start_date': start_date.isoformat() if start_date else (rows[0]['date'] if rows else None),
        'end_date': end_date.isoformat() if end_date else (rows[-1]['date'] if rows else None),
        'ts_code': rows[0]['ts_code'] if rows else contract.upper(),
        'latest_date': rows[-1]['date'] if rows else None,
        'rows': rows,
        'marker_rows': marker_rows,
        'trade_rows': trade_rows,
        'trade_count': trade_count,
        'trade_page': trade_page,
        'trade_page_size': trade_page_size,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def sector_advisor_variety(request):
    """单个投顾在单个品种上的累计盈亏与成交记录。

    account 支持投顾代码/名称模糊匹配，variety 支持品种代码/简称模糊匹配。
    """
    account = request.query_params.get('account', '250528_HG').strip()
    variety = request.query_params.get('variety', 'LH').strip()
    trade_page = max(int(request.query_params.get('trade_page', 1) or 1), 1)
    trade_page_size = min(max(int(request.query_params.get('trade_page_size', 20) or 20), 1), 100)
    offset = (trade_page - 1) * trade_page_size

    if not account or not variety:
        return Response({'detail': 'account 和 variety 不能为空'}, status=400)

    with connection.cursor() as cursor:
        # 投顾：代码精确命中或代码/名称模糊匹配
        like_account = f'%{account}%'
        cursor.execute(
            """
            SELECT m.account_id, COALESCE(m.account_name, m.account_id)
            FROM mom_account_record m
            WHERE m.account_id = %s OR m.account_id LIKE %s OR m.account_name LIKE %s
            ORDER BY (m.account_id = %s) DESC, m.account_id
            LIMIT 1
            """,
            [account, like_account, like_account, account],
        )
        advisor_row = cursor.fetchone()
        if advisor_row:
            account, advisor_name = advisor_row[0], advisor_row[1]
        else:
            advisor_name = account

        # 品种：代码精确命中或代码/简称模糊匹配（用 fut_symbol_info 小表，避免扫大表）
        like_variety = f'%{variety}%'
        cursor.execute(
            """
            SELECT symbol_code, symbol_name
            FROM fut_symbol_info
            WHERE symbol_code = %s OR symbol_name = %s OR symbol_code LIKE %s OR symbol_name LIKE %s
            ORDER BY (symbol_code = %s) DESC, symbol_code
            LIMIT 1
            """,
            [variety.upper(), variety, like_variety, like_variety, variety.upper()],
        )
        variety_row = cursor.fetchone()
        if variety_row:
            variety_code = variety_row[0].upper()
            variety_name = variety_row[1]
        else:
            variety_code = variety.upper()
            variety_name = variety

        cursor.execute(
            """
            SELECT
                t.trade_date,
                MAX(t.variety_code) AS variety_code,
                MAX(t.variety_name) AS variety_name,
                SUM(COALESCE(t.accum_pl_value, 0)) AS cumulative_pnl,
                SUM(COALESCE(t.profit_loss_value, 0)) AS daily_pnl
            FROM yl_perf_variety_pnl_trend t
            WHERE t.calc_window = 'std'
              AND t.account = %s
              AND t.variety_code = %s
            GROUP BY t.trade_date
            ORDER BY t.trade_date
            """,
            [account, variety_code],
        )
        chart_rows = [
            {
                'date': row[0].isoformat() if row[0] else None,
                'symbol_code': row[1],
                'symbol_name': row[2],
                'cumulative_pnl': row[3],
                'daily_pnl': row[4],
            }
            for row in cursor.fetchall()
        ]
        selected_variety_code = chart_rows[-1]['symbol_code'] if chart_rows else variety_code
        selected_variety_name = chart_rows[-1]['symbol_name'] if chart_rows else variety_name

        # 该投顾在该品种的每日持仓金额（多空合计）与单边敞口（轧差）
        # 先取出该账户在该品种的 pid，再用 pid 查持仓（避免 IN 子查询扫大表）
        cursor.execute(
            """
            SELECT DISTINCT pid
            FROM yl_perf_variety_pnl_trend
            WHERE calc_window = 'std'
              AND account = %s
              AND variety_code = %s
            """,
            [account, variety_code],
        )
        pids = [row[0] for row in cursor.fetchall()]

        position_by_date = {}
        if pids:
            placeholders = ','.join(['%s'] * len(pids))
            pos_names = position_variety_names(selected_variety_name)
            cursor.execute(
                f"""
                SELECT
                    p.trade_date,
                    SUM(COALESCE(p.more_market_value, 0) + COALESCE(p.empty_market_value, 0)) AS position_value,
                    SUM(COALESCE(p.more_market_value, 0) - COALESCE(p.empty_market_value, 0)) AS net_value
                FROM perf_variety_position_detail p
                WHERE {position_variety_in_sql(pos_names).replace('variety', 'p.variety')}
                  AND p.pid IN ({placeholders})
                GROUP BY p.trade_date
                ORDER BY p.trade_date
                """,
                [*pos_names, *pids],
            )
            position_by_date = {
                (row[0].isoformat() if row[0] else None): (float(row[1] or 0), float(row[2] or 0))
                for row in cursor.fetchall()
            }
        for item in chart_rows:
            value, net_value = position_by_date.get(item['date'], (None, None))
            item['position_value'] = value if value is not None and value > 0 else None
            item['net_position_value'] = net_value if net_value is not None and net_value != 0 else None

        contract_like = f'{selected_variety_code}%'
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM rh_trades
            WHERE account = %s AND contract LIKE %s
            """,
            [account, contract_like],
        )
        trade_count = cursor.fetchone()[0]

        cursor.execute(
            """
            SELECT
                trade_date,
                trade_time,
                account,
                contract,
                side,
                open_close,
                trade_price,
                trade_qty,
                trade_amount,
                fee,
                close_profit,
                daily_close_profit
            FROM rh_trades
            WHERE account = %s AND contract LIKE %s
            ORDER BY trade_date DESC, trade_time DESC, id DESC
            LIMIT %s OFFSET %s
            """,
            [account, contract_like, trade_page_size, offset],
        )
        trade_rows = [
            {
                'trade_date': row[0].isoformat() if row[0] else None,
                'trade_time': row[1],
                'account': row[2],
                'contract': row[3],
                'side': row[4],
                'open_close': row[5],
                'trade_price': row[6],
                'trade_qty': row[7],
                'trade_amount': row[8],
                'fee': row[9],
                'close_profit': row[10],
                'daily_close_profit': row[11],
            }
            for row in cursor.fetchall()
        ]

    return Response({
        'account': account,
        'advisor_name': advisor_name,
        'variety': selected_variety_code,
        'variety_name': selected_variety_name,
        'latest_date': chart_rows[-1]['date'] if chart_rows else None,
        'chart_rows': chart_rows,
        'trade_rows': trade_rows,
        'trade_count': trade_count,
        'trade_page': trade_page,
        'trade_page_size': trade_page_size,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def sector_pnl(request):
    """品种盈亏页面数据。

    默认使用 calc_window=std（成立以来）。
    """
    window = request.query_params.get('window', 'std')
    variety = request.query_params.get('variety', 'LH').strip()
    allowed_windows = {'1m', '3m', '6m', '1y', 'ytd', 'std', 'custom'}
    if window not in allowed_windows:
        return Response({'detail': 'window 参数无效'}, status=400)
    is_custom = window == 'custom'
    start_date = parse_date(request.query_params.get('start_date', '')) if is_custom else None
    end_date = parse_date(request.query_params.get('end_date', '')) if is_custom else None
    if is_custom and (not start_date or not end_date or start_date > end_date):
        return Response({'detail': '自定义日期范围无效'}, status=400)
    stat_window = 'std' if is_custom else window

    with connection.cursor() as cursor:
        # 统一品种代码（兼容传入名称）
        cursor.execute(
            'SELECT symbol_code FROM fut_symbol_info WHERE symbol_code = %s OR symbol_name = %s LIMIT 1',
            [variety.upper(), variety],
        )
        code_row = cursor.fetchone()
        variety_code = code_row[0].upper() if code_row else variety.upper()

        trend_filters = ['t.calc_window = %s', 't.variety_code = %s']
        trend_params = [stat_window, variety_code]
        if is_custom:
            trend_filters.append('t.trade_date BETWEEN %s AND %s')
            trend_params.extend([start_date, end_date])
        trend_where_sql = ' AND '.join(trend_filters)

        cursor.execute(
            f"""
            SELECT
                t.trade_date,
                MAX(t.variety_code) AS variety_code,
                MAX(t.variety_name) AS variety_name,
                SUM(COALESCE(t.accum_pl_value, 0)) AS cumulative_pnl,
                SUM(COALESCE(t.profit_loss_value, 0)) AS daily_pnl,
                COUNT(DISTINCT t.account) AS advisor_count
            FROM yl_perf_variety_pnl_trend t
            WHERE {trend_where_sql}
            GROUP BY t.trade_date
            ORDER BY t.trade_date
            """,
            trend_params,
        )
        chart_rows = [
            {
                'date': row[0].isoformat() if row[0] else None,
                'symbol_code': row[1],
                'symbol_name': row[2],
                'cumulative_pnl': row[3],
                'daily_pnl': row[4],
                'advisor_count': row[5],
            }
            for row in cursor.fetchall()
        ]
        selected_variety_code = chart_rows[-1]['symbol_code'] if chart_rows else variety_code
        selected_variety_name = chart_rows[-1]['symbol_name'] if chart_rows else variety

        # 品种每日持仓金额（多空市值合计）与单边敞口（轧差市值 = 多头 - 空头）
        pos_names = position_variety_names(selected_variety_name)
        pos_filters = [position_variety_in_sql(pos_names)]
        pos_params = [*pos_names]
        if is_custom:
            pos_filters.append('trade_date BETWEEN %s AND %s')
            pos_params.extend([start_date, end_date])
        cursor.execute(
            f"""
            SELECT
                trade_date,
                SUM(COALESCE(more_market_value, 0) + COALESCE(empty_market_value, 0)) AS position_value,
                SUM(COALESCE(more_market_value, 0) - COALESCE(empty_market_value, 0)) AS net_value
            FROM perf_variety_position_detail
            WHERE {' AND '.join(pos_filters)}
            GROUP BY trade_date
            ORDER BY trade_date
            """,
            pos_params,
        )
        position_by_date = {
            (row[0].isoformat() if row[0] else None): (float(row[1] or 0), float(row[2] or 0))
            for row in cursor.fetchall()
        }
        for item in chart_rows:
            value, net_value = position_by_date.get(item['date'], (None, None))
            item['position_value'] = value if value is not None and value > 0 else None
            item['net_position_value'] = net_value if net_value is not None and net_value != 0 else None

        # 最新一期日期（一次性取出，避免相关子查询反复扫描大表）
        latest_filters = ['calc_window = %s']
        latest_params = [stat_window]
        if is_custom:
            latest_filters.append('trade_date BETWEEN %s AND %s')
            latest_params.extend([start_date, end_date])
        cursor.execute(
            f"SELECT MAX(trade_date) FROM yl_perf_variety_pnl_trend WHERE {' AND '.join(latest_filters)}",
            latest_params,
        )
        pnl_latest = cursor.fetchone()[0]

        # 账户总盈利 + 该品种盈利：合并为一次扫描
        pnl_by_account = {}
        if pnl_latest:
            cursor.execute(
                """
                SELECT account,
                       SUM(COALESCE(accum_pl_value, 0)) AS total_pnl,
                       SUM(CASE WHEN variety_code = %s THEN COALESCE(accum_pl_value, 0) ELSE 0 END) AS variety_pnl
                FROM yl_perf_variety_pnl_trend
                WHERE calc_window = %s AND trade_date = %s
                GROUP BY account
                """,
                [variety_code, stat_window, pnl_latest],
            )
            pnl_by_account = {
                r[0]: (float(r[1] or 0), float(r[2] or 0))
                for r in cursor.fetchall()
            }

        # 当前持仓改用 rh_positions 原始持仓表判断（数据更新及时，按持仓数量而非保证金）
        contract_like = f'{variety_code}%'

        filters = ['s.calc_window = %s', 's.variety_code = %s']
        params = [stat_window, variety_code]
        where_sql = ' AND '.join(filters)

        cursor.execute(
            f"""
            SELECT
                COALESCE(m.account_name, s.account) AS advisor_name,
                s.account AS advisor_code,
                CASE WHEN p.account IS NULL THEN 0 ELSE 1 END AS has_position,
                s.variety_code,
                s.variety_name,
                s.trade_amount,
                s.trade_qty_avg,
                s.trade_amount_avg,
                s.intraday_trade_ratio,
                s.turnover_rate,
                s.win_ratio,
                s.profit_loss_ratio,
                s.profit_max,
                s.loss_max,
                s.margin_rate,
                CASE WHEN COALESCE(tt.total_trade_amount, 0) > 0
                     THEN s.trade_amount / tt.total_trade_amount ELSE NULL END AS trade_amount_ratio
            FROM yl_perf_trade_variety_stat s
            LEFT JOIN mom_account_record m ON m.account_id = s.account
            LEFT JOIN (
                SELECT account, SUM(COALESCE(trade_amount, 0)) AS total_trade_amount
                FROM yl_perf_trade_variety_stat
                WHERE calc_window = %s
                GROUP BY account
            ) tt ON tt.account = s.account
            LEFT JOIN (
                SELECT DISTINCT account
                FROM rh_positions
                WHERE trade_date = (SELECT MAX(trade_date) FROM rh_positions)
                  AND contract LIKE %s
                  AND COALESCE(position_qty, 0) <> 0
            ) p ON p.account = s.account
            WHERE {where_sql}
            ORDER BY COALESCE(s.trade_amount, 0) DESC
            LIMIT 500
            """,
            [stat_window, contract_like, *params],
        )
        detail_rows = []
        for row in cursor.fetchall():
            account = row[1]
            total_pnl, variety_pnl = pnl_by_account.get(account, (None, None))
            detail_rows.append({
                'advisor_name': row[0],
                'advisor_code': account,
                'has_position': bool(row[2]),
                'symbol_code': row[3],
                'symbol_name': row[4],
                'profit_loss': variety_pnl,
                'trade_amount': row[5],
                'avg_daily_volume': row[6],
                'avg_daily_amount': row[7],
                'intraday_trade_ratio': row[8],
                'turnover_rate': row[9],
                'win_rate': row[10],
                'profit_loss_ratio': row[11],
                'max_profit': row[12],
                'max_loss': row[13],
                'margin_return_rate': row[14],
                'total_ratio': float(row[15]) if row[15] is not None else None,
                'profit_ratio': (
                    variety_pnl / total_pnl
                    if variety_pnl is not None and total_pnl not in (None, 0)
                    else None
                ),
            })

        latest_date = chart_rows[-1]['date'] if chart_rows else None

    return Response({
        'window': window,
        'start_date': start_date.isoformat() if start_date else None,
        'end_date': end_date.isoformat() if end_date else None,
        'variety': selected_variety_code,
        'variety_name': selected_variety_name,
        'latest_date': latest_date,
        'chart_rows': chart_rows,
        'detail_rows': detail_rows,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def advisor_trade_overview(request):
    """主观投顾交易品种统计：投顾 × 品种矩阵（成交额/保证金及占比）。

    参考 calc_rh_trade.py 逻辑：
    - 投顾筛选：当前运行（status='启用', is_stop=0），account_tag IN(1,2), invest_logic='主观'，同名去重取 create_time 最早
    - 成交额：rh_trades 按 (account, contract) 聚合 trade_amount
    - 保证金率：rh_positions 各合约最新 margin/market_value
    - 保证金 = 成交额 × 保证金率
    - 品种代码：合约首字母大写前缀，期权合约过滤
    - 板块结构：fut_symbol_info 的 symbol_cate_l1(大类)/symbol_cate(子类)
    """
    mode = request.query_params.get('mode', 'margin_share')
    window = request.query_params.get('window', 'std')
    allowed_modes = {'turnover', 'turnover_share', 'margin', 'margin_share'}
    allowed_windows = {'day', '1m', '3m', '1y', 'std'}
    if mode not in allowed_modes:
        return Response({'detail': 'mode 参数无效'}, status=400)
    if window not in allowed_windows:
        return Response({'detail': 'window 参数无效'}, status=400)

    l1_name_map = {'金属': '有色金属'}
    sector_order = [
        ('金融期货', ['股指期货', '国债期货']),
        ('有色金属', ['贵金属', '传统有色', '新能源']),
        ('农林产品', ['油脂油料', '农副产品', '软商品', '谷物', '林产品']),
        ('黑色', ['煤炭', '黑色金属']),
        ('能源化工', ['能源', '芳烃', '烯烃', '醇类及其他', '轻工制造']),
        ('航运', ['集运']),
    ]

    with connection.cursor() as cursor:
        # 品种 -> (名称, 子类, 大类)
        cursor.execute('SELECT symbol_code, symbol_name, symbol_cate, symbol_cate_l1 FROM fut_symbol_info')
        variety_meta = {}
        for code, name, cate, l1 in cursor.fetchall():
            if code:
                variety_meta[code.upper()] = (name or code, cate, l1_name_map.get(l1, l1))

        # 投顾筛选 + 同名去重（create_time 最早）
        cursor.execute(
            """
            SELECT account_id, account_name, create_time
            FROM mom_account_record
            WHERE is_stop = 0 AND account_tag IN (1, 2) AND invest_logic = '主观' AND status = '启用'
            ORDER BY create_time
            """
        )
        advisors = []
        seen_names = set()
        for account_id, name, create_time in cursor.fetchall():
            if name in seen_names:
                continue
            seen_names.add(name)
            advisors.append({'account_id': account_id, 'name': name or account_id, 'create_time': create_time})
        if not advisors:
            return Response({'detail': '暂无主观投顾'}, status=404)

        account_ids = [a['account_id'] for a in advisors]
        ph = ','.join(['%s'] * len(account_ids))

        # 时间区间
        cursor.execute('SELECT MAX(trade_date) FROM rh_trades')
        latest = cursor.fetchone()[0]
        if not latest:
            return Response({'detail': '暂无成交数据'}, status=404)
        if window == 'day':
            start = end = latest
        elif window == '1m':
            start, end = latest - timedelta(days=30), latest
        elif window == '3m':
            start, end = latest - timedelta(days=90), latest
        elif window == '1y':
            start, end = latest - timedelta(days=365), latest
        else:
            start = end = None

        # 成交额（account × variety）
        # 1m/3m/1y/std 直接读预聚合表 yl_perf_trade_variety_stat（毫秒级）；
        # 仅 day 窗口回退到 rh_trades 原始聚合
        trade_rows = []
        if window != 'day':
            cursor.execute(
                f"""
                SELECT account, variety_code, SUM(COALESCE(trade_amount, 0))
                FROM yl_perf_trade_variety_stat
                WHERE account IN ({ph}) AND calc_window = %s
                  AND trade_date = (
                      SELECT MAX(trade_date) FROM yl_perf_trade_variety_stat WHERE calc_window = %s
                  )
                GROUP BY account, variety_code
                """,
                [*account_ids, window, window],
            )
            trade_rows = cursor.fetchall()
        else:
            cursor.execute(
                f"""
                SELECT account, contract, SUM(COALESCE(trade_amount, 0))
                FROM rh_trades
                WHERE account IN ({ph}) AND trade_date BETWEEN %s AND %s
                GROUP BY account, contract
                """,
                [*account_ids, start, end],
            )
            trade_rows = cursor.fetchall()

        # 保证金率原始数据（各合约最新交易日 margin/market_value），后按品种聚合
        cursor.execute('SELECT MAX(trade_date) FROM rh_positions')
        pos_latest = cursor.fetchone()[0]
        cursor.execute(
            """
            SELECT contract, margin, market_value
            FROM rh_positions
            WHERE trade_date = %s
            """,
            [pos_latest],
        )
        margin_rows = cursor.fetchall()

    def extract_variety(contract):
        text = str(contract or '').strip()
        if not re.fullmatch(r'[A-Za-z]+\d+', text):
            return None
        return re.match(r'[A-Za-z]+', text).group(0).upper()

    # 保证金率按品种聚合（margin / market_value 求和），已到期合约也能按品种取到保证金率
    margin_sum = {}
    mv_sum = {}
    for contract, mg, mv in margin_rows:
        vc = extract_variety(contract)
        if vc is None:
            continue
        mg_f = float(mg or 0)
        mv_f = float(mv or 0)
        if mg_f <= 0 or mv_f <= 0:
            continue
        margin_sum[vc] = margin_sum.get(vc, 0.0) + mg_f
        mv_sum[vc] = mv_sum.get(vc, 0.0) + mv_f
    margin_rate = {vc: margin_sum[vc] / mv_sum[vc] for vc in margin_sum if mv_sum.get(vc, 0) > 0}

    # 回退：最新日保证金缺失的品种（如数据源当日 margin=0），取该品种近30天内最近一个有值日期的率
    missing = [c for c in variety_meta if c not in margin_rate]
    if missing and pos_latest:
        missing_set = set(missing)
        likes = ' OR '.join(['(contract LIKE %s OR contract LIKE %s)'] * len(missing))
        like_params = []
        for c in missing:
            like_params.extend([c + '%', c.lower() + '%'])
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT trade_date, contract, margin, market_value
                FROM rh_positions
                WHERE trade_date >= %s - INTERVAL 30 DAY
                  AND margin > 0 AND market_value > 0
                  AND ({likes})
                """,
                [pos_latest, *like_params],
            )
            by_date = {}
            for d, contract, mg, mv in cursor.fetchall():
                vc = extract_variety(contract)
                if vc is None or vc not in missing_set:
                    continue
                acc = by_date.setdefault((vc, d), [0.0, 0.0])
                acc[0] += float(mg or 0)
                acc[1] += float(mv or 0)
        best = {}
        for (vc, d), (mg, mv) in by_date.items():
            if mv > 0 and (vc not in best or d > best[vc][0]):
                best[vc] = (d, mg / mv)
        for vc, (_d, rate) in best.items():
            margin_rate[vc] = rate

    # 聚合：投顾 × 品种 的成交额与保证金
    turnover = {}
    margin = {}
    for row in trade_rows:
        account, second_col, amount = row
        if window != 'day':
            variety_code = str(second_col or '').upper() or None
        else:
            variety_code = extract_variety(second_col)
        if variety_code is None:
            continue
        key = (account, variety_code)
        amt = float(amount or 0)
        turnover[key] = turnover.get(key, 0.0) + amt
        margin[key] = margin.get(key, 0.0) + amt * margin_rate.get(variety_code, 0.0)

    # 构建列（板块结构 + 合计列）
    columns = []
    for l1, sub_cates in sector_order:
        l1_members = []
        for sub in sub_cates:
            sub_members = sorted(
                [code for code, (name, cate, l1v) in variety_meta.items() if cate == sub and l1v == l1]
            )
            l1_members.extend(sub_members)
            if len(sub_members) > 1:
                columns.append({
                    'key': f'L2:{sub}', 'l1': l1, 'l2': sub, 'code': '', 'name': f'{sub}合计',
                    'agg': 'l2', 'members': sub_members,
                })
            for code in sub_members:
                name = variety_meta[code][0]
                columns.append({
                    'key': code, 'l1': l1, 'l2': sub, 'code': code, 'name': name,
                    'agg': '', 'members': [code],
                })
        if len(l1_members) > 1:
            columns.append({
                'key': f'L1:{l1}', 'l1': l1, 'l2': '', 'code': '', 'name': f'{l1}合计',
                'agg': 'l1', 'members': l1_members,
            })

    # 金额/占比矩阵
    rows = []
    for advisor in advisors:
        account = advisor['account_id']
        amounts = {}
        total = 0.0
        for code in variety_meta:
            amt = turnover.get((account, code), 0.0) if mode in ('turnover', 'turnover_share') else margin.get((account, code), 0.0)
            amounts[code] = amt
            total += amt
        values = {}
        variety_count = 0
        for col in columns:
            if col['agg']:
                val = sum(amounts.get(m, 0.0) for m in col['members'])
            else:
                val = amounts.get(col['code'], 0.0)
            if mode in ('turnover_share', 'margin_share'):
                val = val / total if total else 0.0
            values[col['key']] = val
        for code in variety_meta:
            if amounts.get(code, 0.0) > 1.0:
                variety_count += 1
        sector_count = 0
        for l1, _sub in sector_order:
            l1_total = sum(amounts.get(m, 0.0) for m in variety_meta if variety_meta.get(m, (None, None, None))[2] == l1)
            if l1_total > 1.0:
                sector_count += 1
        rows.append({
            'advisor_name': advisor['name'],
            'account_id': account,
            'start_time': str(advisor['create_time'])[:10] if advisor['create_time'] else None,
            'sector_count': sector_count,
            'variety_count': variety_count,
            'values': values,
        })

    # 按品种数量降序排列投顾
    rows.sort(key=lambda r: (-r['variety_count'], r['advisor_name']))

    return Response({
        'mode': mode,
        'window': window,
        'trade_date': latest.isoformat() if latest else None,
        'columns': columns,
        'rows': rows,
        'advisor_count': len(rows),
        'variety_count': len(variety_meta),
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def sector_pnl_ranking(request):
    """盈亏分析：盈利/亏损品种列表。

    yl_perf_variety_pnl_trend 最新一期按品种聚合全体投顾的累计盈亏
    （accum_pl_value 求和），盈利品种（value>0）与亏损品种（value<0）全量返回。
    """
    window = request.query_params.get('window', 'std')
    allowed_windows = {'1m', '3m', '6m', '1y', 'ytd', 'std'}
    if window not in allowed_windows:
        return Response({'detail': 'window 参数无效'}, status=400)

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT variety_code, MAX(variety_name),
                   SUM(COALESCE(accum_pl_value, 0)), COUNT(DISTINCT account)
            FROM yl_perf_variety_pnl_trend
            WHERE calc_window = %s
              AND trade_date = (
                  SELECT MAX(trade_date) FROM yl_perf_variety_pnl_trend WHERE calc_window = %s
              )
            GROUP BY variety_code
            """,
            [window, window],
        )
        rows = [
            {
                'code': r[0],
                'name': r[1] or r[0],
                'value': float(r[2] or 0),
                'advisor_count': int(r[3] or 0),
            }
            for r in cursor.fetchall()
        ]
        cursor.execute(
            'SELECT MAX(trade_date) FROM yl_perf_variety_pnl_trend WHERE calc_window = %s',
            [window],
        )
        trade_date = cursor.fetchone()[0]

    def with_rank(items):
        return [{**item, 'rank': i + 1} for i, item in enumerate(items)]

    profit_list = with_rank(sorted(
        (r for r in rows if r['value'] > 0), key=lambda r: r['value'], reverse=True
    ))
    loss_list = with_rank(sorted(
        (r for r in rows if r['value'] < 0), key=lambda r: r['value']
    ))

    return Response({
        'trade_date': trade_date.isoformat() if trade_date else None,
        'window': window,
        'variety_count': len(rows),
        'profit_list': profit_list,
        'loss_list': loss_list,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def option_pnl(request):
    """期权盈亏：全体投顾所有期权合约的权利金净收支，按标的品种聚合。

    期权合约无平仓盈亏（close_profit 为空），口径取 rh_trades.premium_income_expense
    （权利金收支，正=净收入）。标的代码取合约前导字母，中文名经 fut_symbol_info 映射。
    """
    with connection.cursor() as cursor:
        try:
            cursor.execute('SELECT MAX(trade_date) FROM yl_option_pnl_summary')
            summary_trade_date = cursor.fetchone()[0]
        except Exception:
            summary_trade_date = None

        if summary_trade_date:
            cursor.execute(
                """
                SELECT
                    underlying,
                    underlying_name,
                    contracts,
                    trades,
                    advisors,
                    total_advisors,
                    premium,
                    fee
                FROM yl_option_pnl_summary
                WHERE trade_date = %s
                ORDER BY premium DESC
                """,
                [summary_trade_date],
            )
            summary_rows = cursor.fetchall()
            rows = [
                {
                    'underlying': r[0],
                    'name': r[1] or r[0],
                    'contracts': int(r[2] or 0),
                    'trades': int(r[3] or 0),
                    'advisors': int(r[4] or 0),
                    'premium': float(r[6] or 0),
                    'fee': float(r[7] or 0),
                }
                for r in summary_rows
            ]
            total = {
                'underlying_count': len(rows),
                'contracts': sum(r['contracts'] for r in rows),
                'trades': sum(r['trades'] for r in rows),
                'advisors': int(summary_rows[0][5] or 0) if summary_rows else 0,
                'premium': sum(r['premium'] for r in rows),
                'fee': sum(r['fee'] for r in rows),
            }
            return Response({
                'trade_date': summary_trade_date.isoformat() if summary_trade_date else None,
                'rows': rows,
                'total': total,
                'source': 'summary',
            })

        cursor.execute(
            """
            SELECT UPPER(REGEXP_SUBSTR(contract, '^[A-Za-z]+')) AS underlying,
                   COUNT(DISTINCT contract),
                   COUNT(*) AS trades,
                   COUNT(DISTINCT account) AS advisors,
                   SUM(COALESCE(premium_income_expense, 0)) AS premium,
                   SUM(COALESCE(fee, 0)) AS fee
            FROM rh_trades
            WHERE contract REGEXP '^[A-Za-z]+[0-9]{3,4}-?[CP]-?'
            GROUP BY underlying
            ORDER BY premium DESC
            """
        )
        agg = cursor.fetchall()
        cursor.execute('SELECT MAX(trade_date) FROM rh_trades')
        trade_date = cursor.fetchone()[0]
        cursor.execute(
            """
            SELECT COUNT(DISTINCT account)
            FROM rh_trades
            WHERE contract REGEXP '^[A-Za-z]+[0-9]{3,4}-?[CP]-?'
            """
        )
        total_advisors = cursor.fetchone()[0]
        cursor.execute(
            'SELECT UPPER(symbol_code), symbol_name FROM fut_symbol_info'
        )
        name_map = {code: name for code, name in cursor.fetchall()}

    rows = [
        {
            'underlying': r[0],
            'name': name_map.get(r[0], r[0]),
            'contracts': int(r[1]),
            'trades': int(r[2]),
            'advisors': int(r[3]),
            'premium': float(r[4] or 0),
            'fee': float(r[5] or 0),
        }
        for r in agg
    ]
    total = {
        'underlying_count': len(rows),
        'contracts': sum(r['contracts'] for r in rows),
        'trades': sum(r['trades'] for r in rows),
        'advisors': int(total_advisors or 0),
        'premium': sum(r['premium'] for r in rows),
        'fee': sum(r['fee'] for r in rows),
    }
    return Response({
        'trade_date': trade_date.isoformat() if trade_date else None,
        'rows': rows,
        'total': total,
        'source': 'realtime',
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def sector_bk_latest(request):
    """板块分析首模块：yl_perf_bk 最新一期的资产/保证金/风险度快照。"""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT trade_date, asset_total, margin, pos_rate,
                   variety_margin, variety_risk_degree, bk_margin, bk_risk_degree
            FROM yl_perf_bk
            WHERE trade_date = (SELECT MAX(trade_date) FROM yl_perf_bk)
            LIMIT 1
            """
        )
        row = cursor.fetchone()
    if not row:
        return Response({'detail': '暂无板块风险数据'}, status=404)
    return Response({
        'trade_date': row[0].isoformat() if row[0] else None,
        'asset_total': float(row[1]),
        'margin': float(row[2]),
        'pos_rate': float(row[3]),
        'variety_margin': float(row[4]),
        'variety_risk_degree': float(row[5]),
        'bk_margin': float(row[6]),
        'bk_risk_degree': float(row[7]),
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def sector_bk_margin(request):
    """板块总保证金分布：总资产 = 闲置资金 + 保证金占用 + 各板块保证金。

    rows 按金额降序：闲置资金(asset-margin)、yl_perf_bk_detail 中 level=1 的各板块 net_margin。
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT trade_date, asset_total, margin, bk_margin
            FROM yl_perf_bk
            WHERE trade_date = (SELECT MAX(trade_date) FROM yl_perf_bk)
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if not row:
            return Response({'detail': '暂无板块保证金数据'}, status=404)
        trade_date, asset_total, margin, bk_margin = row[0], float(row[1]), float(row[2]), float(row[3])
        cursor.execute(
            """
            SELECT code, buy_margin, sell_margin, risk_degree_10d, risk_degree_20d
            FROM yl_perf_bk_detail
            WHERE trade_date = (SELECT MAX(trade_date) FROM yl_perf_bk_detail)
              AND level = 1
            ORDER BY (COALESCE(buy_margin, 0) + COALESCE(sell_margin, 0)) DESC
            """
        )
        sectors = [
            {
                'name': r[0],
                'value': float(r[1] or 0) + float(r[2] or 0),
                'risk_10d': float(r[3]) if r[3] is not None else None,
                'risk_20d': float(r[4]) if r[4] is not None else None,
            }
            for r in cursor.fetchall()
        ]
    rows = []
    idle = asset_total - margin
    if idle > 0:
        rows.append({'name': '闲置资金', 'value': idle, 'kind': 'idle'})
    rows.extend({**item, 'kind': 'sector'} for item in sectors)
    return Response({
        'trade_date': trade_date.isoformat() if trade_date else None,
        'asset_total': asset_total,
        'margin': margin,
        'bk_margin': bk_margin,
        'rows': rows,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def sector_bk_net_risk(request):
    """板块净持仓市值与10天风险度占比。"""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT trade_date
            FROM yl_perf_bk_detail
            WHERE trade_date = (SELECT MAX(trade_date) FROM yl_perf_bk_detail)
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if not row:
            return Response({'detail': '暂无板块净持仓市值与风险度数据'}, status=404)
        trade_date = row[0]

        cursor.execute(
            """
            SELECT code, net_market_value, risk_degree_10d
            FROM yl_perf_bk_detail
            WHERE trade_date = %s
              AND level = 1
            ORDER BY ABS(COALESCE(net_market_value, 0)) DESC
            """,
            [trade_date],
        )
        rows = [
            {
                'name': r[0],
                'net_market_value': float(r[1] or 0),
                'risk_degree_10d': float(r[2] or 0),
            }
            for r in cursor.fetchall()
        ]

    risk_total = sum(max(row['risk_degree_10d'], 0) for row in rows)
    for row in rows:
        row['risk_share'] = row['risk_degree_10d'] / risk_total if risk_total else None

    return Response({
        'trade_date': trade_date.isoformat() if trade_date else None,
        'risk_total': risk_total,
        'rows': rows,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def variety_top_margin(request):
    """品种保证金前30：yl_perf_bk_detail 中 level=2 的各品种，保证金按多空合计(buy+sell)降序取前30。

    名称取自 fut_symbol_info（symbol_code 关联），未匹配到的回退显示代码。
    rows 按金额降序返回，供条形图/饼图/转置表格使用。
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT trade_date, asset_total, margin
            FROM yl_perf_bk
            WHERE trade_date = (SELECT MAX(trade_date) FROM yl_perf_bk)
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if not row:
            return Response({'detail': '暂无品种保证金数据'}, status=404)
        trade_date, asset_total, margin = row[0], float(row[1]), float(row[2])
        cursor.execute(
            """
            SELECT d.code, d.buy_margin, d.sell_margin, COALESCE(s.symbol_name, d.code)
            FROM yl_perf_bk_detail d
            LEFT JOIN fut_symbol_info s ON s.symbol_code = d.code
            WHERE d.trade_date = (SELECT MAX(trade_date) FROM yl_perf_bk_detail)
              AND d.level = 2
            ORDER BY (COALESCE(d.buy_margin, 0) + COALESCE(d.sell_margin, 0)) DESC
            LIMIT 30
            """
        )
        varieties = [
            {'name': r[3], 'value': float(r[1] or 0) + float(r[2] or 0), 'kind': 'variety'}
            for r in cursor.fetchall()
        ]
    return Response({
        'trade_date': trade_date.isoformat() if trade_date else None,
        'asset_total': asset_total,
        'margin': margin,
        'rows': varieties,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def variety_top_net_risk(request):
    """品种净持仓市值与10天风险度占比前30。"""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT trade_date
            FROM yl_perf_bk_detail
            WHERE trade_date = (SELECT MAX(trade_date) FROM yl_perf_bk_detail)
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if not row:
            return Response({'detail': '暂无品种净持仓市值与风险度数据'}, status=404)
        trade_date = row[0]

        cursor.execute(
            """
            SELECT
                d.code,
                COALESCE(s.symbol_name, d.code) AS name,
                d.net_market_value,
                d.risk_degree_10d
            FROM yl_perf_bk_detail d
            LEFT JOIN fut_symbol_info s ON s.symbol_code = d.code
            WHERE d.trade_date = %s
              AND d.level = 2
            ORDER BY ABS(COALESCE(d.net_market_value, 0)) DESC
            LIMIT 30
            """,
            [trade_date],
        )
        rows = [
            {
                'code': r[0],
                'name': r[1],
                'net_market_value': float(r[2] or 0),
                'risk_degree_10d': float(r[3] or 0),
            }
            for r in cursor.fetchall()
        ]

    risk_total = sum(max(row['risk_degree_10d'], 0) for row in rows)
    for row in rows:
        row['risk_share'] = row['risk_degree_10d'] / risk_total if risk_total else None

    return Response({
        'trade_date': trade_date.isoformat() if trade_date else None,
        'risk_total': risk_total,
        'rows': rows,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def sector_bk_detail_tree(request):
    """板块-品种-合约三级持仓明细树（yl_perf_bk_detail 最新一期）。

    层级关系：
    - level=1 板块（code 即板块名称）
    - level=2 品种（code 为品种代码，经 fut_symbol_info.symbol_cate 归入板块）
    - level=3 合约（code 前导字母大写后匹配品种代码）
    各级按保证金占用（多+空）降序，父节点未出现在 level 数据中时按子节点即时归并生成。
    """
    db_num_fields = (
        'buy_num', 'sell_num', 'net_num',
        'buy_margin', 'sell_margin', 'net_margin', 'margin_ratio',
        'buy_market_value', 'sell_market_value', 'net_market_value',
        'net_mv_chg_1d', 'net_mv_chr_1d', 'net_mv_chg_1w', 'net_mv_chr_1w',
        'hv_10d', 'hv_20d', 'hv_60d',
        'risk_degree_10d', 'risk_degree_20d',
    )
    node_fields = db_num_fields + ('total_margin',)

    def make_node(code, name, level):
        return {'code': code, 'name': name, 'level': level, **{f: 0.0 for f in node_fields}, 'children': []}

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT trade_date
            FROM yl_perf_bk_detail
            WHERE trade_date = (SELECT MAX(trade_date) FROM yl_perf_bk_detail)
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if not row:
            return Response({'detail': '暂无板块持仓明细数据'}, status=404)
        trade_date = row[0]

        cursor.execute(
            """
            SELECT code, buy_num, sell_num, net_num,
                   buy_margin, sell_margin, net_margin, margin_ratio,
                   buy_market_value, sell_market_value, net_market_value,
                   net_mv_chg_1d, net_mv_chr_1d, net_mv_chg_1w, net_mv_chr_1w,
                   hv_10d, hv_20d, hv_60d,
                   risk_degree_10d, risk_degree_20d, level
            FROM yl_perf_bk_detail
            WHERE trade_date = %s
            """,
            [trade_date],
        )
        detail_rows = cursor.fetchall()

        # 品种代码 -> (品种名称, 板块名称)
        cursor.execute('SELECT symbol_code, symbol_name, symbol_cate FROM fut_symbol_info')
        variety_info = {r[0]: (r[1], r[2]) for r in cursor.fetchall()}

    sectors = {}   # 板块名 -> node
    varieties = {}  # 品种代码 -> node

    def get_sector(name):
        node = sectors.get(name)
        if not node:
            node = make_node(name, name, 1)
            sectors[name] = node
        return node

    def get_variety(code):
        node = varieties.get(code)
        if not node:
            name, sector_name = variety_info.get(code, (code, None))
            sector = get_sector(sector_name or '未分类')
            node = make_node(code, name or code, 2)
            sector['children'].append(node)
            varieties[code] = node
        return node

    for r in detail_rows:
        code, values, level = r[0], [float(v or 0) for v in r[1:20]], r[20]
        if level == 1:
            node = get_sector(code)
        elif level == 2:
            node = get_variety(code.upper())
        elif level == 3:
            # 仅取前导字母（如 a2611-P-4500 -> a，AP701P6700 -> AP），避免误读期权代码中的 P/C
            prefix = code[:len(code) - len(code.lstrip('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'))].upper()
            node = make_node(code, code, 3)
            get_variety(prefix)['children'].append(node)
        else:
            continue
        for field, value in zip(db_num_fields, values):
            node[field] = value
        node['total_margin'] = node['buy_margin'] + node['sell_margin']

    def sort_nodes(nodes):
        nodes.sort(key=lambda n: n['total_margin'], reverse=True)
        for child in nodes:
            sort_nodes(child['children'])

    tree = list(sectors.values())
    sort_nodes(tree)

    return Response({
        'trade_date': trade_date.isoformat() if trade_date else None,
        'rows': tree,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def sector_position_overview(request):
    """板块持仓概览：板块-品种-合约三级树。

    每级字段：
    - 净持仓市值、净持仓市值变化(1天/1周) 来自 yl_perf_bk_detail(三级)
    - 波动率、全市场持仓量/成交量 来自 fut_market_stats(品种) / fut_contract_stats(期货合约)
    - 波动率/持仓量/成交量分位数 = 当前值在近约250个交易日历史中的百分位(0~1)
    - 持仓量/成交量占比 = 该节点 / 全市场合计；板块级为子品种聚合
    期权合约无法映射到期货合约表，其全市场字段留空。
    """
    lookback_days = 400  # 日历日，约覆盖 250 个交易日

    def percentile_rank(series, current):
        if current is None or len(series) < 2:
            return None
        less = sum(1 for v in series if v < current)
        return less / (len(series) - 1)

    with connection.cursor() as cursor:
        cursor.execute('SELECT MAX(trade_date) FROM yl_perf_bk_detail')
        bk_latest = cursor.fetchone()[0]
        cursor.execute('SELECT MAX(trade_date) FROM fut_market_stats')
        mkt_latest = cursor.fetchone()[0]
        cursor.execute('SELECT MAX(trade_date) FROM fut_contract_stats')
        ct_latest = cursor.fetchone()[0]
        if not bk_latest or not mkt_latest:
            return Response({'detail': '暂无数据'}, status=404)

        # yl_perf_bk_detail 三级：净持仓市值及变化
        cursor.execute(
            """
            SELECT code, level, net_market_value, net_mv_chg_1d, net_mv_chg_1w
            FROM yl_perf_bk_detail
            WHERE trade_date = %s
            """,
            [bk_latest],
        )
        bk_detail = list(cursor.fetchall())

        # 品种代码 -> (品种名称, 板块名称)
        cursor.execute('SELECT symbol_code, symbol_name, symbol_cate FROM fut_symbol_info')
        variety_info = {r[0]: (r[1], r[2]) for r in cursor.fetchall()}

        # 品种级全市场数据（最新 + 历史）
        cursor.execute(
            """
            SELECT variety_code, total_volume, total_oi, vol_10d
            FROM fut_market_stats
            WHERE trade_date = %s
            """,
            [mkt_latest],
        )
        mkt_latest_rows = {}
        oi_mkt_total = 0.0
        volume_mkt_total = 0.0
        for code, volume, oi, vol in cursor.fetchall():
            mkt_latest_rows[code] = (float(volume or 0), float(oi or 0), float(vol) if vol is not None else None)
            oi_mkt_total += float(oi or 0)
            volume_mkt_total += float(volume or 0)

        cursor.execute(
            """
            SELECT variety_code, vol_10d, total_oi, total_volume
            FROM fut_market_stats
            WHERE trade_date >= %s
            """,
            [mkt_latest - timedelta(days=lookback_days)],
        )
        mkt_hist = {}
        for code, vol, oi, volume in cursor.fetchall():
            b = mkt_hist.setdefault(code, {'vol': [], 'oi': [], 'volume': []})
            if vol is not None:
                b['vol'].append(float(vol))
            if oi is not None:
                b['oi'].append(float(oi))
            if volume is not None:
                b['volume'].append(float(volume))

        # 合约级全市场数据（最新 + 历史）：ts_code 去掉交易所后缀后大写作为 key
        cursor.execute(
            """
            SELECT ts_code, volume, oi, vol_10d
            FROM fut_contract_stats
            WHERE trade_date = %s
            """,
            [ct_latest],
        )
        ct_latest_rows = {}
        oi_ct_total = 0.0
        volume_ct_total = 0.0
        for ts_code, volume, oi, vol in cursor.fetchall():
            key = ts_code.split('.')[0].upper()
            ct_latest_rows[key] = (float(volume or 0), float(oi or 0), float(vol) if vol is not None else None)
            oi_ct_total += float(oi or 0)
            volume_ct_total += float(volume or 0)

        cursor.execute(
            """
            SELECT ts_code, vol_10d, oi, volume
            FROM fut_contract_stats
            WHERE trade_date >= %s
            """,
            [ct_latest - timedelta(days=lookback_days)],
        )
        ct_hist = {}
        for ts_code, vol, oi, volume in cursor.fetchall():
            key = ts_code.split('.')[0].upper()
            b = ct_hist.setdefault(key, {'vol': [], 'oi': [], 'volume': []})
            if vol is not None:
                b['vol'].append(float(vol))
            if oi is not None:
                b['oi'].append(float(oi))
            if volume is not None:
                b['volume'].append(float(volume))

    def make_node(code, name, level):
        return {
            'code': code, 'name': name, 'level': level, 'children': [],
            'net_market_value': None, 'net_mv_chg_1d': None, 'net_mv_chg_1w': None,
            'volatility': None, 'vol_pctl': None,
            'total_oi': None, 'oi_share': None, 'oi_pctl': None,
            'total_volume': None, 'volume_share': None, 'volume_pctl': None,
        }

    sectors = {}
    varieties = {}

    def get_sector(name):
        node = sectors.get(name)
        if not node:
            node = make_node(name, name, 1)
            sectors[name] = node
        return node

    def get_variety(code):
        node = varieties.get(code)
        if not node:
            name, sector_name = variety_info.get(code, (code, None))
            sector = get_sector(sector_name or '未分类')
            node = make_node(code, name or code, 2)
            sector['children'].append(node)
            varieties[code] = node
        return node

    # 1) 组装三级树 + 填净持仓市值及变化
    for code, level, net_mv, chg_1d, chg_1w in bk_detail:
        if level == 1:
            node = get_sector(code)
        elif level == 2:
            node = get_variety(code.upper())
        elif level == 3:
            prefix = code[:len(code) - len(code.lstrip('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'))].upper()
            node = make_node(code, code, 3)
            get_variety(prefix)['children'].append(node)
        else:
            continue
        node['net_market_value'] = float(net_mv) if net_mv is not None else None
        node['net_mv_chg_1d'] = float(chg_1d) if chg_1d is not None else None
        node['net_mv_chg_1w'] = float(chg_1w) if chg_1w is not None else None

    # 2) 品种级全市场字段
    for code, node in varieties.items():
        mkt = mkt_latest_rows.get(code)
        if mkt is None:
            continue
        volume, oi, vol = mkt
        hist = mkt_hist.get(code, {})
        node['volatility'] = vol
        node['vol_pctl'] = percentile_rank(hist.get('vol', []), vol)
        node['total_oi'] = oi
        node['oi_share'] = oi / oi_mkt_total if oi_mkt_total else None
        node['oi_pctl'] = percentile_rank(hist.get('oi', []), oi)
        node['total_volume'] = volume
        node['volume_share'] = volume / volume_mkt_total if volume_mkt_total else None
        node['volume_pctl'] = percentile_rank(hist.get('volume', []), volume)

    # 3) 合约级全市场字段（仅期货合约可映射）
    def contract_key(code):
        m = re.match(r'^([A-Za-z]+)(\d+)$', code)
        return (m.group(1) + m.group(2)).upper() if m else None

    for variety_node in varieties.values():
        for node in variety_node['children']:
            key = contract_key(node['code'])
            if not key:
                continue
            ct = ct_latest_rows.get(key)
            if ct is None:
                continue
            volume, oi, vol = ct
            hist = ct_hist.get(key, {})
            node['volatility'] = vol
            node['vol_pctl'] = percentile_rank(hist.get('vol', []), vol)
            node['total_oi'] = oi
            node['oi_share'] = oi / oi_ct_total if oi_ct_total else None
            node['oi_pctl'] = percentile_rank(hist.get('oi', []), oi)
            node['total_volume'] = volume
            node['volume_share'] = volume / volume_ct_total if volume_ct_total else None
            node['volume_pctl'] = percentile_rank(hist.get('volume', []), volume)

    # 4) 板块级：聚合子品种
    for sector_node in sectors.values():
        oi_sum = sum(v['total_oi'] or 0 for v in sector_node['children'])
        vol_sum = sum(v['total_volume'] or 0 for v in sector_node['children'])
        sector_node['total_oi'] = oi_sum or None
        sector_node['total_volume'] = vol_sum or None
        sector_node['oi_share'] = oi_sum / oi_mkt_total if oi_mkt_total else None
        sector_node['volume_share'] = vol_sum / volume_mkt_total if volume_mkt_total else None
        # 波动率按持仓量加权平均
        weighted = [(v['volatility'], v['total_oi'] or 0) for v in sector_node['children'] if v['volatility'] is not None]
        w_sum = sum(w for _, w in weighted)
        sector_node['volatility'] = sum(vol * w for vol, w in weighted) / w_sum if w_sum else None

    def sort_nodes(nodes):
        nodes.sort(key=lambda n: -(n['total_oi'] or 0))
        for child in nodes:
            sort_nodes(child['children'])

    tree = list(sectors.values())
    sort_nodes(tree)

    return Response({
        'trade_date': bk_latest.isoformat() if bk_latest else None,
        'market_date': mkt_latest.isoformat() if mkt_latest else None,
        'rows': tree,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def sector_board(request):
    """板块分析：板块指数走势与 MOM 板块配置概览。

    index_series: 各板块窗口内指数序列（降采样至500点内）。
    sector_rows: 板块表现（最新指数/日涨跌/区间涨跌幅）+ MOM配置（盈亏/持仓/敞口/投顾数/品种数）。
    """
    window = request.query_params.get('window', '1y')
    allowed_windows = {'1m', '3m', '6m', '1y', 'ytd', 'all', 'custom'}
    if window not in allowed_windows:
        return Response({'detail': 'window 参数无效'}, status=400)
    is_custom = window == 'custom'
    start_date = parse_date(request.query_params.get('start_date', '')) if is_custom else None
    end_date = parse_date(request.query_params.get('end_date', '')) if is_custom else None
    if is_custom and (not start_date or not end_date or start_date > end_date):
        return Response({'detail': '自定义日期范围无效'}, status=400)

    with connection.cursor() as cursor:
        cursor.execute('SELECT MAX(trade_date) FROM fut_sector_index')
        latest_index_date = cursor.fetchone()[0]
        if not latest_index_date:
            return Response({'detail': '暂无板块指数数据'}, status=404)
        win_end = min(end_date, latest_index_date) if is_custom else latest_index_date
        if window == 'ytd':
            win_start = win_end.replace(month=1, day=1)
        elif window in {'1m', '3m', '6m', '1y'}:
            days_map = {'1m': 31, '3m': 93, '6m': 186, '1y': 366}
            win_start = win_end - timedelta(days=days_map[window])
        elif is_custom:
            win_start = start_date
        else:
            win_start = None

        # 窗口内指数序列（按板块分组）
        index_where = 'trade_date <= %s' + (' AND trade_date >= %s' if win_start else '')
        index_params = [win_end] + ([win_start] if win_start else [])
        cursor.execute(
            f"""
            SELECT sector_code, sector_name, trade_date, index_value
            FROM fut_sector_index
            WHERE {index_where}
            ORDER BY sector_code, trade_date
            """,
            index_params,
        )
        series_by_code = {}
        name_by_code = {}
        for code, name, trade_date, value in cursor.fetchall():
            series_by_code.setdefault(code, []).append((trade_date.isoformat(), float(value)))
            name_by_code[code] = name

        def downsample(points):
            if len(points) <= 500:
                return points
            step = (len(points) - 1) / 499.0
            keep = sorted({round(i * step) for i in range(500)} | {len(points) - 1})
            return [points[i] for i in keep]

        index_series = {
            code: [{'date': d, 'value': v} for d, v in downsample(points)]
            for code, points in series_by_code.items()
        }

        # 最新交易日的日涨跌幅
        cursor.execute(
            """
            SELECT sector_code, index_value, daily_chg
            FROM fut_sector_index
            WHERE trade_date = %s
            """,
            [win_end],
        )
        latest_by_code = {row[0]: (float(row[1]), float(row[2]) if row[2] is not None else None) for row in cursor.fetchall()}

        # 品种 -> 板块 映射（取 fut_market_stats 最新日期）
        cursor.execute(
            """
            SELECT variety_code, variety_name, sector_code, sector_name
            FROM fut_market_stats
            WHERE trade_date = (SELECT MAX(trade_date) FROM fut_market_stats)
            """
        )
        sector_by_code = {}
        sector_by_name = {}
        for variety_code, variety_name, sector_code, sector_name in cursor.fetchall():
            sector_by_code[variety_code] = sector_code
            sector_by_name[variety_name] = sector_code
        # 持仓明细表使用别名命名的品种（如 中证1000指数期货/铁矿/棕榈）也映射到同一板块
        for std_name, aliases in POSITION_VARIETY_ALIASES.items():
            code = sector_by_name.get(std_name)
            if code:
                for alias in aliases:
                    sector_by_name[alias] = code

        # MOM 持仓/敞口/投顾数（持仓明细最新日期，按品种）
        cursor.execute(
            """
            SELECT
                p.variety,
                SUM(COALESCE(p.more_market_value, 0) + COALESCE(p.empty_market_value, 0)),
                SUM(COALESCE(p.more_market_value, 0) - COALESCE(p.empty_market_value, 0)),
                COUNT(DISTINCT p.pid)
            FROM perf_variety_position_detail p
            WHERE p.trade_date = (SELECT MAX(trade_date) FROM perf_variety_position_detail)
            GROUP BY p.variety
            """
        )
        position_by_sector = {}
        for variety_name, position_value, net_value, advisor_count in cursor.fetchall():
            code = sector_by_name.get(variety_name)
            if not code:
                continue
            agg = position_by_sector.setdefault(code, {'position_value': 0.0, 'net_value': 0.0, 'advisor_count': 0, 'variety_count': 0})
            agg['position_value'] += float(position_value or 0)
            agg['net_value'] += float(net_value or 0)
            agg['advisor_count'] = max(agg['advisor_count'], int(advisor_count or 0))
            agg['variety_count'] += 1

        # MOM 区间累计盈亏（窗口末日 - 窗口内首个交易日，按品种）
        pnl_by_sector = {}
        cursor.execute(
            """
            SELECT MIN(trade_date), MAX(trade_date)
            FROM yl_perf_variety_pnl_trend
            WHERE calc_window = %s AND trade_date <= %s
            """,
            ['std', win_end],
        )
        trend_first, trend_last = cursor.fetchone()
        if trend_first and trend_last:
            trend_where = 'calc_window = %s AND trade_date <= %s'
            trend_params = ['std', win_end]
            if win_start:
                trend_where += ' AND trade_date >= %s'
                trend_params.append(win_start)
            cursor.execute(
                f'SELECT MIN(trade_date) FROM yl_perf_variety_pnl_trend WHERE {trend_where}',
                trend_params,
            )
            win_first = cursor.fetchone()[0] or trend_first
            cursor.execute(
                """
                SELECT variety_code, variety_name, trade_date, SUM(COALESCE(accum_pl_value, 0))
                FROM yl_perf_variety_pnl_trend
                WHERE calc_window = %s AND trade_date IN (%s, %s)
                GROUP BY variety_code, variety_name, trade_date
                """,
                ['std', win_first, trend_last],
            )
            accum = {}
            for variety_code, variety_name, trade_date, total in cursor.fetchall():
                key = sector_by_code.get(variety_code) or sector_by_name.get(variety_name)
                if not key:
                    continue
                accum.setdefault(key, {})[trade_date] = float(total or 0)
            for code, by_date in accum.items():
                if trend_last in by_date and win_first in by_date:
                    pnl_by_sector[code] = by_date[trend_last] - by_date[win_first]

        sector_rows = []
        for code in sorted(name_by_code):
            points = series_by_code.get(code) or []
            latest_value, daily_chg = latest_by_code.get(code, (None, None))
            period_chg = None
            if len(points) >= 2 and points[0][1]:
                period_chg = (points[-1][1] / points[0][1] - 1) * 100
            mom = position_by_sector.get(code) or {}
            sector_rows.append({
                'sector_code': code,
                'sector_name': name_by_code[code],
                'latest_index': latest_value,
                'daily_chg': daily_chg,
                'period_chg': period_chg,
                'mom_pnl': pnl_by_sector.get(code),
                'mom_position_value': mom.get('position_value') or 0,
                'mom_net_value': mom.get('net_value') or 0,
                'mom_advisor_count': mom.get('advisor_count') or 0,
                'mom_variety_count': mom.get('variety_count') or 0,
            })

    return Response({
        'window': window,
        'start_date': win_start.isoformat() if win_start else None,
        'end_date': win_end.isoformat() if win_end else None,
        'index_series': index_series,
        'sector_rows': sector_rows,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def variety_advisor_long_short(request):
    """品种维度的投顾多空数量热力表。"""
    metric_keys = [
        'net_long',
        'net_short',
        'add_long',
        'reduce_long',
        'long_to_short',
        'add_short',
        'reduce_short',
        'short_to_long',
    ]

    def empty_metrics():
        return {key: {'advisors_by_name': {}} for key in metric_keys}

    def add_metric(metrics, key, advisor):
        name = advisor.get('name') or advisor.get('account_code') or str(advisor.get('pid'))
        bucket = metrics[key]['advisors_by_name']
        current = bucket.get(name)
        account_code = advisor.get('account_code')
        pid = advisor.get('pid')
        if current:
            if account_code and account_code not in current['account_codes']:
                current['account_codes'].append(account_code)
            if pid is not None and pid not in current['pids']:
                current['pids'].append(pid)
            current['is_quant'] = current['is_quant'] or advisor.get('is_quant', False)
            if current['is_quant']:
                current['invest_logic'] = '量化'
            current['account_code'] = '、'.join(current['account_codes'])
            return

        bucket[name] = {
            'pid': pid,
            'pids': [pid] if pid is not None else [],
            'account_code': account_code,
            'account_codes': [account_code] if account_code else [],
            'name': name,
            'invest_logic': advisor.get('invest_logic'),
            'is_quant': advisor.get('is_quant', False),
        }

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT DISTINCT trade_date
            FROM rh_positions
            WHERE trade_date IS NOT NULL
            ORDER BY trade_date DESC
            LIMIT 2
            """
        )
        dates = [row[0] for row in cursor.fetchall()]
        if not dates:
            return Response({'detail': '暂无品种投顾多空数据'}, status=404)
        latest_date = dates[0]
        previous_date = dates[1] if len(dates) > 1 else None

        cursor.execute('SELECT symbol_code, symbol_name FROM fut_symbol_info')
        variety_name_by_code = {
            str(code).upper(): name
            for code, name in cursor.fetchall()
            if code
        }

        option_pattern = re.compile(r'^([A-Za-z]+)(\d{3,4})-?([CP])-?(\d+)$')

        def parse_contract(contract):
            text = str(contract or '').strip()
            option_match = option_pattern.match(text)
            if option_match:
                code, month, option_type, strike = option_match.groups()
                code = code.upper()
                return {
                    'is_option': True,
                    'variety_code': code,
                    'variety': variety_name_by_code.get(code) or code,
                    'option_type': option_type.upper(),
                    'risk_keys': [
                        f'{code}{month}{option_type.upper()}{strike}'.upper(),
                        f'{code}2{month}{option_type.upper()}{strike}'.upper() if len(month) == 3 else None,
                    ],
                }
            match = re.match(r'^[A-Za-z]+', text)
            if not match:
                return {
                    'is_option': False,
                    'variety_code': text,
                    'variety': text,
                    'option_type': None,
                    'risk_keys': [],
                }
            code = match.group(0).upper()
            return {
                'is_option': False,
                'variety_code': code,
                'variety': variety_name_by_code.get(code) or code,
                'option_type': None,
                'risk_keys': [],
            }

        def fetch_delta_map(trade_date):
            cursor.execute(
                """
                SELECT ts_code, delta_val
                FROM opt_risk_stats
                WHERE trade_date = %s
                  AND ts_code IS NOT NULL
                """,
                [trade_date],
            )
            delta_map = {}
            for ts_code, delta in cursor.fetchall():
                key = re.sub(r'\.[A-Za-z]+$', '', str(ts_code or '').strip())
                key = key.replace('-', '').upper()
                if key:
                    delta_map[key] = abs(float(delta or 0))
            return delta_map

        def fetch_positions(trade_date):
            delta_map = fetch_delta_map(trade_date)
            cursor.execute(
                """
                SELECT
                    account,
                    contract,
                    direction,
                    side,
                    SUM(COALESCE(position_qty, 0)) AS position_qty
                FROM rh_positions
                WHERE trade_date = %s
                  AND account IS NOT NULL
                  AND contract IS NOT NULL
                GROUP BY account, contract, direction, side
                """,
                [trade_date],
            )
            positions = {}
            for account, contract, direction, side, qty in cursor.fetchall():
                quantity = float(qty or 0)
                side_text = str(side or '').strip()
                direction_text = str(direction or '').strip()
                is_buy = side_text == '买' or direction_text == '0'
                is_sell = side_text == '卖' or direction_text == '1'
                if not is_buy and not is_sell:
                    continue

                contract_info = parse_contract(contract)
                signed_qty = quantity if is_buy else -quantity
                if contract_info['is_option']:
                    delta = next(
                        (delta_map[key] for key in contract_info['risk_keys'] if key and key in delta_map),
                        None,
                    )
                    if delta is None or delta <= 0:
                        continue
                    equivalent_qty = quantity * delta
                    is_call = contract_info['option_type'] == 'C'
                    is_put = contract_info['option_type'] == 'P'
                    if (is_buy and is_call) or (is_sell and is_put):
                        signed_qty = equivalent_qty
                    elif (is_sell and is_call) or (is_buy and is_put):
                        signed_qty = -equivalent_qty
                    else:
                        continue

                key = (account, contract_info['variety'])
                positions[key] = positions.get(key, 0.0) + signed_qty
            return positions

        latest_positions = fetch_positions(latest_date)
        previous_positions = fetch_positions(previous_date) if previous_date else {}

        cursor.execute(
            """
            SELECT
                account_id,
                COALESCE(account_name, account_id) AS account_name,
                invest_logic
            FROM mom_account_record
            WHERE account_id IS NOT NULL
            """
        )
        advisor_by_account = {
            row[0]: {
                'pid': row[0],
                'account_code': row[0],
                'name': row[1],
                'invest_logic': row[2],
                'is_quant': row[2] == '量化',
            }
            for row in cursor.fetchall()
            if row[0]
        }

    by_variety = {}
    all_keys = set(latest_positions.keys()) | set(previous_positions.keys())
    for account, variety in all_keys:
        current = latest_positions.get((account, variety), 0.0)
        previous = previous_positions.get((account, variety), 0.0)
        metrics = by_variety.setdefault(variety, empty_metrics())
        advisor = advisor_by_account.get(account) or {
            'pid': account,
            'account_code': account,
            'name': str(account),
            'invest_logic': None,
            'is_quant': False,
        }

        if current > 0:
            add_metric(metrics, 'net_long', advisor)
        elif current < 0:
            add_metric(metrics, 'net_short', advisor)

        if previous > 0 and current < 0:
            add_metric(metrics, 'long_to_short', advisor)
        elif previous < 0 and current > 0:
            add_metric(metrics, 'short_to_long', advisor)
        elif current > 0 and previous >= 0 and current > previous:
            add_metric(metrics, 'add_long', advisor)
        elif previous > 0 and current >= 0 and current < previous:
            add_metric(metrics, 'reduce_long', advisor)
        elif current < 0 and previous <= 0 and current < previous:
            add_metric(metrics, 'add_short', advisor)
        elif previous < 0 and current <= 0 and current > previous:
            add_metric(metrics, 'reduce_short', advisor)

    for metrics in by_variety.values():
        for key in metric_keys:
            advisors = list(metrics[key].pop('advisors_by_name').values())
            advisors.sort(key=lambda item: (not item.get('is_quant', False), item.get('name') or ''))
            metrics[key]['advisors'] = advisors
            metrics[key]['count'] = len(advisors)
            metrics[key]['quant_count'] = sum(1 for item in advisors if item.get('is_quant'))

    rows = [
        {
            'variety': variety,
            'metrics': metrics,
        }
        for variety, metrics in by_variety.items()
    ]
    rows.sort(
        key=lambda row: (
            -row['metrics']['net_long']['count'],
            -row['metrics']['net_short']['count'],
            row['variety'],
        )
    )

    return Response({
        'trade_date': latest_date.isoformat() if latest_date else None,
        'previous_trade_date': previous_date.isoformat() if previous_date else None,
        'rows': rows,
        'columns': metric_keys,
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def strategy_portfolio(request):
    """自定义策略组合分析（参考火富牛基金组合模块）。

    ?pids=1,2,3            组合成分投顾 pid 列表（必填）
    ?model=equal           权重模型：equal 等权 / mv 均值方差 / rp 风险平价 / custom 自定义
    ?weights=30,30,40      custom 模型下的自定义权重（百分数或小数均可，自动归一化）

    智能模型基于各成分投顾日收益率序列在接口内现算：
    - rp  风险平价：等风险贡献（ERC），协方差坐标下降迭代求解
    - mv  均值方差：最大夏普切点组合 w ∝ Σ⁻¹μ，负权截断归一
    组合日收益率 = Σ(成分日收益率 × 权重)，成分当日缺净值按 0 处理。
    """
    import math
    import statistics

    from .models import MomAccountRecord, PerfHeaderStats, PerfNetValues, PerfProducts

    pids_raw = request.query_params.get('pids', '').strip()
    weights_raw = request.query_params.get('weights', '').strip()
    model = (request.query_params.get('model') or 'equal').strip().lower()
    if model not in ('equal', 'mv', 'rp', 'custom'):
        return Response({'detail': 'model 仅支持 equal / mv / rp / custom'}, status=400)
    if not pids_raw:
        return Response({'detail': '缺少 pids 参数'}, status=400)

    try:
        pids = [int(x) for x in re.split(r'[,\s]+', pids_raw) if x]
    except ValueError:
        return Response({'detail': 'pids 参数无效'}, status=400)
    pids = list(dict.fromkeys(pids))[:20]  # 去重，最多 20 个
    if not pids:
        return Response({'detail': 'pids 参数无效'}, status=400)

    # 各成分投顾净值序列 {pid: {date: nv}}
    nav_qs = (
        PerfNetValues.objects
        .filter(pid__in=pids, trade_date__isnull=False, net_value__isnull=False)
        .order_by('trade_date')
        .values_list('pid', 'trade_date', 'net_value')
    )
    nav_map = {pid: {} for pid in pids}
    for pid, d, nv in nav_qs:
        if nv and nv > 0:
            nav_map[pid][d] = nv

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

    # 成分明细：名称/权重/自身以来累计收益/最新净值/规模
    products = {p.pid: p for p in PerfProducts.objects.filter(pid__in=valid_pids)}
    accts = {m.account_id: m for m in MomAccountRecord.objects.filter(
        account_id__in=[p.product_name for p in products.values()])}
    headers = {}
    seen = set()
    for h in PerfHeaderStats.objects.filter(pid__in=valid_pids, trade_date__isnull=False).order_by('-trade_date'):
        if h.pid not in seen:
            seen.add(h.pid)
            headers[h.pid] = h

    advisors = []
    for pid, w in zip(valid_pids, weights):
        product = products.get(pid)
        acct = accts.get(product.product_name) if product else None
        header = headers.get(pid)
        advisors.append({
            'pid': pid,
            'account_code': acct.account_id if acct else (product.product_name if product else str(pid)),
            'account_name': acct.account_name if acct else None,
            'invest_logic': acct.invest_logic if acct else None,
            'weight': round(w * 100, 2),
            'latest_nav': round(next(reversed(list(nav_map[pid].values()))), 4) if nav_map[pid] else None,
            'total_return': (round((header.since_inception_rise or 0) * 100, 4)
                             if header and header.since_inception_rise is not None else None),
            'cum_investment': float(acct.cum_investment) if acct and acct.cum_investment is not None else None,
            'mk_bf': float(acct.mk_bf) if acct and acct.mk_bf is not None else None,
            'new_add': float(acct.new_add) if acct and acct.new_add is not None else None,
        })

    # 组合规模合计
    def _sum(field):
        vals = [a[field] for a in advisors if a[field] is not None]
        return round(sum(vals), 2) if vals else None

    scale = {
        'advisor_count': len(advisors),
        'cum_investment': _sum('cum_investment'),
        'mk_bf': _sum('mk_bf'),
        'new_add': _sum('new_add'),
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
        'weight_note': weight_note,
        'metrics': metrics,
        'nav_series': nav_series,
        'advisors': advisors,
        'scale': scale,
        'member_series': member_series,
    })


MODEL_LABELS = {
    'equal': '等权',
    'mv': '均值方差',
    'rp': '风险平价',
    'custom': '自定义',
}


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def portfolio_records(request):
    """我的组合列表 / 新建保存组合。"""
    from .models import StrategyPortfolioRecord

    if request.method == 'GET':
        qs = StrategyPortfolioRecord.objects.order_by('-updated_at')
        return Response([{
            'id': r.id,
            'name': r.name,
            'note': r.note,
            'pids': r.pids,
            'weights': r.weights,
            'weight_model': r.weight_model,
            'weight_model_label': MODEL_LABELS.get(r.weight_model, r.weight_model),
            'created_at': r.created_at,
            'updated_at': r.updated_at,
        } for r in qs])

    # POST：保存组合
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
        record.name, record.note = name, note
        record.pids, record.weights, record.weight_model = pids, weights, model
        record.save()
    else:
        record = StrategyPortfolioRecord.objects.create(
            name=name[:100], note=note, pids=pids, weights=weights, weight_model=model)
    return Response({
        'id': record.id,
        'name': record.name,
        'note': record.note,
        'pids': record.pids,
        'weights': record.weights,
        'weight_model': record.weight_model,
        'weight_model_label': MODEL_LABELS.get(record.weight_model, record.weight_model),
        'created_at': record.created_at,
        'updated_at': record.updated_at,
    }, status=201 if not record_id else 200)


@api_view(['GET', 'DELETE'])
@permission_classes([AllowAny])
def portfolio_record_detail(request, pk):
    """查询单个组合 / 删除指定组合。"""
    from .models import StrategyPortfolioRecord

    try:
        record = StrategyPortfolioRecord.objects.get(pk=pk)
    except StrategyPortfolioRecord.DoesNotExist:
        return Response({'detail': '组合不存在'}, status=404)

    if request.method == 'GET':
        return Response({
            'id': record.id,
            'name': record.name,
            'note': record.note,
            'pids': record.pids,
            'weights': record.weights,
            'weight_model': record.weight_model,
            'weight_model_label': MODEL_LABELS.get(record.weight_model, record.weight_model),
            'created_at': record.created_at,
            'updated_at': record.updated_at,
        })

    record.delete()
    return Response({'detail': '已删除'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def table_template(request, key):
    """下载指定表的导入模板(.xlsx)。

    模板包含表头（中文 label）+ 一行示例数据，用户填好后通过 /import/ 上传。
    """
    try:
        entry = table_registry.get(key)
    except KeyError:
        return Response({'detail': f'未注册的表: {key}'}, status=404)

    from openpyxl import Workbook
    from openpyxl.utils import get_column_letter
    from urllib.parse import quote
    import io
    import datetime

    cols = entry.get_columns()
    wb = Workbook()
    ws = wb.active
    ws.title = entry.label[:31]

    # 第 1 行：中文 label（导入时会被匹配）
    headers = [c['label'] for c in cols]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = cell.font.copy(bold=True)

    # 第 2 行：字段名注释行（供参考，使用灰色斜体）
    ws.append([f'字段: {c["name"]}  类型: {c["type"]}' for c in cols])
    for cell in ws[2]:
        cell.font = cell.font.copy(italic=True, color='888888')

    # 第 3 行：示例数据行（按字段类型给出占位值，便于用户理解格式）
    sample = []
    for c in cols:
        if c['name'] == 'id':
            sample.append('')
        elif c['type'] == 'int':
            sample.append(0)
        elif c['type'] == 'float':
            sample.append(0.0)
        elif c['type'] == 'bool':
            sample.append(0)
        elif c['type'] in ('date', 'datetime'):
            sample.append('2026-01-01')
        elif c['type'] == 'text':
            sample.append('示例文本')
        else:
            sample.append('示例')
    ws.append(sample)

    # 设置列宽
    for i, c in enumerate(cols, start=1):
        ws.column_dimensions[get_column_letter(i)].width = min(max(len(str(c['label'])) + 4, 12), 30)

    # 冻结表头
    ws.freeze_panes = 'A2'

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f'{entry.label}_导入模板_{datetime.datetime.now().strftime("%Y%m%d")}.xlsx'
    resp = HttpResponse(
        buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    resp['Content-Disposition'] = f"attachment; filename*=UTF-8''{quote(filename)}"
    return resp
