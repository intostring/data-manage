from django.db import models
from django.http import HttpResponse
from django_filters import rest_framework as filters
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.filters import OrderingFilter
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .registry import table_registry


def _make_filterset(model):
    """为指定 model 动态生成 FilterSet。

    字符串/文本字段用 icontains 模糊匹配，其余字段精确匹配。
    """
    meta = model._meta
    attrs = {}
    for f in meta.fields:
        if isinstance(f, (models.CharField, models.TextField)):
            attrs[f.name] = filters.CharFilter(field_name=f.name, lookup_expr='icontains')
    FilterCls = type(
        f'{model.__name__}FilterSet',
        (filters.FilterSet,),
        {**attrs, 'Meta': type('Meta', (), {'model': model, 'fields': '__all__'})},
    )
    return FilterCls


class DynamicModelViewSet(viewsets.ModelViewSet):
    """通用 ViewSet，通过类属性 model / serializer_class 绑定具体表。

    子类（由 urls.py 动态生成）设置这两个属性即可获得完整 CRUD。
    支持排序（ordering 参数）与筛选（字段名=值）。
    """
    model = None
    serializer_class = None
    filterset_class = None
    filter_backends = [OrderingFilter, filters.DjangoFilterBackend]
    ordering_fields = '__all__'
    # 默认按 id 倒序，避免分页时 UnorderedObjectListWarning
    ordering = ['-id']

    def get_queryset(self):
        qs = self.model.objects.all()
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
        from django.db.models import Q
        q = Q()
        for f in entry.model._meta.fields:
            if isinstance(f, (models.CharField, models.TextField)):
                q |= Q(**{f'{f.name}__icontains': search})
        qs = qs.filter(q)

    # 字段精确/模糊筛选
    for f in entry.model._meta.fields:
        val = request.query_params.get(f.name)
        if not val:
            continue
        if isinstance(f, (models.CharField, models.TextField)):
            qs = qs.filter(**{f'{f.name}__icontains': val})
        else:
            qs = qs.filter(**{f.name: val})

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
    """从 Excel(.xlsx) 导入数据到已注册表。

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

    # 构造 Model 实例并批量创建
    field_types = {c['name']: c['type'] for c in cols}
    objs = []
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
        if kwargs:
            objs.append(entry.model(**kwargs))

    if not objs:
        return Response({'detail': '没有可导入的数据行', 'errors': errors}, status=400)

    try:
        created = entry.model.objects.bulk_create(objs)
    except Exception as e:
        return Response({'detail': f'导入失败: {e}', 'errors': errors}, status=400)

    return Response({
        'imported': len(created),
        'errors': errors,
    }, status=201)


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
