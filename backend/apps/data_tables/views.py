from django.db import models
from django.db.models import Q
from django.http import HttpResponse
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
    from .models import PerfProducts, PerfRiskIndicators, PerfNetValues, MomAccountRecord

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
        # 投顾概览（来自 mom_account_record）
        'account_name': acct.account_name if acct else None,
        'account_code': acct.account_id if acct else None,
        'is_stop': acct.is_stop if acct else None,
        'invest_logic': acct.invest_logic if acct else None,
        'invest_cate': acct.invest_cate if acct else None,
        'product_name_cn': acct.product_name if acct else None,
    }

    # 风险收益指标（优先取 1 年期，其次成立以来）
    def _val(risk_obj, field_1y, field_since):
        if not risk_obj:
            return None
        v = getattr(risk_obj, field_1y, None)
        if v is None:
            v = getattr(risk_obj, field_since, None)
        return v

    indicators = {}
    if risk:
        indicators = {
            'annual_yield': _val(risk, 'annual_yield_1y', 'annual_yield_since'),
            'annual_volatility': _val(risk, 'annual_volatility_1y', 'annual_volatility_since'),
            'max_drawdown': _val(risk, 'max_drawdown_1y', 'max_drawdown_since'),
            'sharpe_ratio': _val(risk, 'sharpe_ratio_1y', 'sharpe_ratio_since'),
            'kama_ratio': _val(risk, 'kama_ratio_1y', 'kama_ratio_since'),
            'info_ratio': _val(risk, 'info_ratio_1y', 'info_ratio_since'),
            'alpha': _val(risk, 'alpha_1y', 'alpha_since'),
            'beta': _val(risk, 'beta_1y', 'beta_since'),
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
