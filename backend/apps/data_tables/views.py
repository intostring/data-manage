from datetime import timedelta

from django.db import connection, models
from django.db.models import Q
from django.http import HttpResponse
from django.utils.dateparse import parse_date
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .registry import table_registry


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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def advisor_performance(request):
    """投顾业绩聚合接口。

    无参数：返回投顾产品列表 [{pid, product_name}]
    ?pid=xxx：返回单个投顾的基本信息 + 风险收益指标
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

    risk = PerfRiskIndicators.objects.filter(pid=pid_int).first()
    header = PerfHeaderStats.objects.filter(pid=pid_int, trade_date__isnull=False).order_by('-trade_date').first()

    # 从 MomAccountRecord 取投顾概览（account_id = product_name）
    acct = MomAccountRecord.objects.filter(account_id=product.product_name).first()

    # 基本信息
    rj = product.raw_json or {}
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
    }

    # 风险收益指标：投顾业绩顶部基本数据取成立以来口径
    indicators = {}
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
        'nav_series': nav_series,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
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
@permission_classes([IsAuthenticated])
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
    trade_page = max(int(request.query_params.get('trade_page', 1) or 1), 1)
    trade_page_size = min(max(int(request.query_params.get('trade_page_size', 20) or 20), 1), 100)
    offset = (trade_page - 1) * trade_page_size
    with connection.cursor() as cursor:
        cursor.execute(
            """
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
            FROM fut_market_data
            WHERE UPPER(ts_code) = %s
               OR UPPER(ts_code) LIKE %s
            ORDER BY trade_date
            """,
            [code, f'{code}.%'],
        )
        rows = [
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
            """
            SELECT COUNT(*)
            FROM rh_trades
            WHERE UPPER(contract) = %s
              AND account = %s
            """,
            [code, account],
        )
        trade_count = cursor.fetchone()[0]

        cursor.execute(
            """
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
            WHERE UPPER(r.contract) = %s
              AND r.account = %s
            ORDER BY r.trade_date DESC, r.trade_time DESC, r.id DESC
            LIMIT %s OFFSET %s
            """,
            [code, account, trade_page_size, offset],
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
            WHERE UPPER(contract) = %s
            {'AND account = %s' if account else ''}
            GROUP BY trade_date, COALESCE(side, ''), COALESCE(open_close, '')
            ORDER BY trade_date, side, open_close
            """,
            [code, account] if account else [code],
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
@permission_classes([IsAuthenticated])
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

        # 品种：代码精确命中或代码/简称模糊匹配
        like_variety = f'%{variety}%'
        cursor.execute(
            """
            SELECT variety_code, variety_name
            FROM (
                SELECT variety_code, variety_name
                FROM yl_perf_variety_pnl_trend
                WHERE calc_window = 'std'
                  AND (variety_code = %s OR variety_name = %s OR variety_code LIKE %s OR variety_name LIKE %s)
                GROUP BY variety_code, variety_name
                ORDER BY (variety_code = %s) DESC, variety_code
                LIMIT 1
            ) v
            """,
            [variety, variety, like_variety, like_variety, variety],
        )
        variety_row = cursor.fetchone()
        if variety_row:
            variety = variety_row[0]

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
              AND (t.variety_code = %s OR t.variety_name = %s)
            GROUP BY t.trade_date
            ORDER BY t.trade_date
            """,
            [account, variety, variety],
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
        selected_variety_code = chart_rows[-1]['symbol_code'] if chart_rows else variety
        selected_variety_name = chart_rows[-1]['symbol_name'] if chart_rows else variety

        # 该投顾在该品种的每日持仓金额（多空合计）与单边敞口（轧差）
        cursor.execute(
            """
            SELECT
                p.trade_date,
                SUM(COALESCE(p.more_market_value, 0) + COALESCE(p.empty_market_value, 0)) AS position_value,
                SUM(COALESCE(p.more_market_value, 0) - COALESCE(p.empty_market_value, 0)) AS net_value
            FROM perf_variety_position_detail p
            WHERE p.variety = %s
              AND p.pid IN (
                  SELECT DISTINCT pid
                  FROM yl_perf_variety_pnl_trend
                  WHERE calc_window = 'std'
                    AND account = %s
                    AND (variety_code = %s OR variety_name = %s)
              )
            GROUP BY p.trade_date
            ORDER BY p.trade_date
            """,
            [selected_variety_name, account, variety, variety],
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
@permission_classes([IsAuthenticated])
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
        filters = ['s.calc_window = %s']
        params = [stat_window]
        if variety:
            filters.append('(s.variety_code = %s OR s.variety_name = %s)')
            params.extend([variety, variety])
        where_sql = ' AND '.join(filters)

        trend_filters = ['t.calc_window = %s']
        trend_params = [stat_window]
        if variety:
            trend_filters.append('(t.variety_code = %s OR t.variety_name = %s)')
            trend_params.extend([variety, variety])
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
        selected_variety_code = chart_rows[-1]['symbol_code'] if chart_rows else variety
        selected_variety_name = chart_rows[-1]['symbol_name'] if chart_rows else variety

        # 品种每日持仓金额（多空市值合计）与单边敞口（轧差市值 = 多头 - 空头）
        pos_filters = ['variety = %s']
        pos_params = [selected_variety_name]
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

        pnl_date_filters = ''
        pnl_date_params = []
        if is_custom:
            pnl_date_filters = ' AND trade_date BETWEEN %s AND %s'
            pnl_date_params = [start_date, end_date]

        cursor.execute(
            f"""
            SELECT
                COALESCE(m.account_name, s.account) AS advisor_name,
                s.account AS advisor_code,
                CASE WHEN p.pid IS NULL THEN 0 ELSE 1 END AS has_position,
                s.variety_code,
                s.variety_name,
                pnl.cumulative_profit_loss,
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
                     THEN s.trade_amount / tt.total_trade_amount ELSE NULL END AS trade_amount_ratio,
                CASE WHEN tp.total_profit_loss IS NOT NULL AND tp.total_profit_loss <> 0
                     THEN pnl.cumulative_profit_loss / tp.total_profit_loss ELSE NULL END AS profit_ratio
            FROM yl_perf_trade_variety_stat s
            LEFT JOIN mom_account_record m ON m.account_id = s.account
            LEFT JOIN (
                SELECT account, SUM(COALESCE(trade_amount, 0)) AS total_trade_amount
                FROM yl_perf_trade_variety_stat
                WHERE calc_window = %s
                GROUP BY account
            ) tt ON tt.account = s.account
            LEFT JOIN (
                SELECT account, SUM(COALESCE(accum_pl_value, 0)) AS total_profit_loss
                FROM yl_perf_variety_pnl_trend
                WHERE calc_window = %s
                  {pnl_date_filters}
                  AND trade_date = (
                      SELECT MAX(trade_date)
                      FROM yl_perf_variety_pnl_trend
                      WHERE calc_window = %s
                        {pnl_date_filters}
                  )
                GROUP BY account
            ) tp ON tp.account = s.account
            LEFT JOIN (
                SELECT account, SUM(COALESCE(accum_pl_value, 0)) AS cumulative_profit_loss
                FROM yl_perf_variety_pnl_trend
                WHERE calc_window = %s
                  AND (variety_code = %s OR variety_name = %s)
                  {pnl_date_filters}
                  AND trade_date = (
                      SELECT MAX(trade_date)
                      FROM yl_perf_variety_pnl_trend
                      WHERE calc_window = %s
                        AND (variety_code = %s OR variety_name = %s)
                        {pnl_date_filters}
                  )
                GROUP BY account
            ) pnl ON pnl.account = s.account
            LEFT JOIN (
                SELECT pid
                FROM perf_variety_position_detail
                WHERE variety = %s
                  AND trade_date = (
                      SELECT MAX(trade_date)
                      FROM perf_variety_position_detail
                      WHERE variety = %s
                  )
                  AND (COALESCE(more_market_value, 0) <> 0 OR COALESCE(empty_market_value, 0) <> 0)
                GROUP BY pid
            ) p ON p.pid = s.pid
            WHERE {where_sql}
            ORDER BY COALESCE(s.trade_amount, 0) DESC
            LIMIT 500
            """,
            [
                stat_window,
                stat_window,
                *pnl_date_params,
                stat_window,
                *pnl_date_params,
                stat_window,
                variety,
                variety,
                *pnl_date_params,
                stat_window,
                variety,
                variety,
                *pnl_date_params,
                selected_variety_name,
                selected_variety_name,
                *params,
            ],
        )
        detail_rows = [
            {
                'advisor_name': row[0],
                'advisor_code': row[1],
                'has_position': bool(row[2]),
                'symbol_code': row[3],
                'symbol_name': row[4],
                'profit_loss': row[5],
                'trade_amount': row[6],
                'avg_daily_volume': row[7],
                'avg_daily_amount': row[8],
                'intraday_trade_ratio': row[9],
                'turnover_rate': row[10],
                'win_rate': row[11],
                'profit_loss_ratio': row[12],
                'max_profit': row[13],
                'max_loss': row[14],
                'margin_return_rate': row[15],
                'total_ratio': float(row[16]) if row[16] is not None else None,
                'profit_ratio': float(row[17]) if row[17] is not None else None,
            }
            for row in cursor.fetchall()
        ]

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
@permission_classes([IsAuthenticated])
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
@permission_classes([IsAuthenticated])
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
@permission_classes([IsAuthenticated])
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
@permission_classes([IsAuthenticated])
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
