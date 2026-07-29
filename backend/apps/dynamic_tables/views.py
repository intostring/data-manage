from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.http import HttpResponse

from .models import TableMeta
from . import services


class TableMetaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TableMeta
        fields = ['id', 'key', 'label', 'table_name', 'columns', 'row_count', 'created_at', 'updated_at']
        read_only_fields = ['table_name', 'row_count', 'created_at', 'updated_at']


class DynamicTableView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """动态表列表"""
        metas = TableMeta.objects.all()
        return Response(TableMetaSerializer(metas, many=True).data)

    def post(self, request):
        """上传 CSV 建表。

        multipart/form-data:
            file: CSV 文件
            key: URL 标识
            label: 显示名
        """
        file = request.FILES.get('file')
        key = request.data.get('key', '').strip().lower()
        label = request.data.get('label', '').strip()

        if not file or not key:
            return Response({'detail': '缺少 file 或 key 参数'}, status=400)
        if not key.replace('_', '').isalnum():
            return Response({'detail': 'key 仅允许字母数字下划线'}, status=400)
        if TableMeta.objects.filter(key=key).exists():
            return Response({'detail': f'表 key={key} 已存在'}, status=400)

        columns, rows = services.parse_csv(file)
        if not columns:
            return Response({'detail': 'CSV 无有效列'}, status=400)

        meta = services.create_dynamic_table(key, label or key, columns)
        written = services.insert_rows(meta, rows)
        return Response({
            **TableMetaSerializer(meta).data,
            'imported_rows': written,
            'columns': columns,
        }, status=201)


class DynamicTableDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, key):
        """读取动态表数据，支持分页、搜索、排序与按字段筛选"""
        try:
            meta = TableMeta.objects.get(key=key)
        except TableMeta.DoesNotExist:
            return Response({'detail': '表不存在'}, status=404)

        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        search = request.query_params.get('search', '').strip()
        offset = (page - 1) * page_size

        # 排序：DRF 风格 ordering 字段，前缀 - 表示降序
        ordering = request.query_params.get('ordering', '').strip()
        order_by, order_dir = '', 'asc'
        if ordering:
            if ordering.startswith('-'):
                order_by, order_dir = ordering[1:], 'desc'
            else:
                order_by, order_dir = ordering, 'asc'

        # 按字段筛选：filter.<col>.<op>=value 形式（Navicat 风格多操作符）
        filters = {}
        for k, v in request.query_params.items():
            if not k.startswith('filter.') or not v:
                continue
            parts = k[len('filter.'):].split('.')
            if len(parts) == 2:
                col, op = parts
                filters.setdefault(col, {})[op] = v
            elif len(parts) == 1:
                # 旧格式兼容：filter.<col>=value
                filters[parts[0]] = v

        rows, total = services.fetch_rows(
            meta, limit=page_size, offset=offset, search=search,
            order_by=order_by, order_dir=order_dir, filters=filters,
        )
        return Response({
            'columns': meta.get_columns(),
            'results': rows,
            'count': total,
            'page': page,
            'page_size': page_size,
        })

    def delete(self, request, key):
        try:
            meta = TableMeta.objects.get(key=key)
        except TableMeta.DoesNotExist:
            return Response({'detail': '表不存在'}, status=404)
        services.drop_dynamic_table(meta)
        return Response({'detail': '已删除'}, status=204)


# ==================== Excel 导出 / 导入 ====================

def _parse_query_params(request):
    """解析分页/搜索/排序/筛选参数，供导出复用"""
    search = request.query_params.get('search', '').strip()
    ordering = request.query_params.get('ordering', '').strip()
    order_by, order_dir = '', 'asc'
    if ordering:
        if ordering.startswith('-'):
            order_by, order_dir = ordering[1:], 'desc'
        else:
            order_by, order_dir = ordering, 'asc'
    filters = {}
    for k, v in request.query_params.items():
        if not k.startswith('filter.') or not v:
            continue
        parts = k[len('filter.'):].split('.')
        if len(parts) == 2:
            col, op = parts
            filters.setdefault(col, {})[op] = v
        elif len(parts) == 1:
            filters[parts[0]] = v
    return search, order_by, order_dir, filters


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dynamic_table_export(request, key):
    """导出动态表为 Excel(.xlsx)，支持筛选参数"""
    try:
        meta = TableMeta.objects.get(key=key)
    except TableMeta.DoesNotExist:
        return Response({'detail': '表不存在'}, status=404)

    from openpyxl import Workbook
    from openpyxl.utils import get_column_letter
    from urllib.parse import quote
    import io
    import datetime

    search, order_by, order_dir, filters = _parse_query_params(request)
    # 导出全部匹配行（不分页）
    rows, _ = services.fetch_rows(
        meta, limit=10 ** 9, offset=0, search=search,
        order_by=order_by, order_dir=order_dir, filters=filters,
    )
    cols = meta.get_columns()

    wb = Workbook()
    ws = wb.active
    ws.title = (meta.label or key)[:31]
    # 表头：优先用列名（动态表 label == name）
    headers = [c.get('label') or c['name'] for c in cols]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = cell.font.copy(bold=True)

    # 数据行
    field_names = [c['name'] for c in cols]
    for r in rows:
        ws.append([_dyn_excel_cell(r.get(fn)) for fn in field_names])

    for i, c in enumerate(cols, start=1):
        ws.column_dimensions[get_column_letter(i)].width = min(max(len(str(c.get('label') or c['name'])) + 4, 10), 30)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f'{meta.label or key}_{datetime.datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    resp = HttpResponse(
        buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    resp['Content-Disposition'] = f"attachment; filename*=UTF-8''{quote(filename)}"
    return resp


def _dyn_excel_cell(val):
    """动态表值转 Excel 单元格可写类型"""
    if val is None:
        return ''
    from datetime import date, datetime
    if isinstance(val, datetime):
        return val.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(val, date):
        return val.strftime('%Y-%m-%d')
    return val


def _norm_val(v):
    """规范化值用于比较：None 与空串视为相同"""
    if v is None or v == '':
        return None
    return v


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def dynamic_table_import(request, key):
    """向已存在的动态表导入 Excel(.xlsx) 数据。

    存在则更新，不存在则新增，完全重复则跳过。
    匹配依据：动态表的唯一索引列；若无唯一索引，则按所有非 id 列匹配。
    表头需与建表时的列名匹配。
    """
    try:
        meta = TableMeta.objects.get(key=key)
    except TableMeta.DoesNotExist:
        return Response({'detail': '表不存在'}, status=404)

    file = request.FILES.get('file')
    if not file:
        return Response({'detail': '缺少 file 参数'}, status=400)

    from openpyxl import load_workbook

    cols = meta.get_columns()
    col_names = {c['name'] for c in cols}

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

    # 列索引 -> 字段名
    col_map = {}
    for idx, h in enumerate(header):
        if h is None:
            continue
        h_str = str(h).strip()
        if h_str in col_names:
            col_map[idx] = h_str

    if not col_map:
        return Response({'detail': '未匹配到任何有效字段，请检查表头'}, status=400)

    field_types = {c['name']: c['type'] for c in cols}
    # 唯一标识列：优先唯一索引；无则用所有非 id 列
    unique_fields = services.get_unique_index_columns(meta)
    if not unique_fields:
        unique_fields = [c['name'] for c in cols if c['name'] != 'id']
    all_col_names = [c['name'] for c in cols if c['name'] != 'id']

    created_count = 0
    updated_count = 0
    skipped_count = 0
    errors = []
    has_data = False
    for row_idx, row in enumerate(rows_iter, start=2):
        if row is None or all(v is None or v == '' for v in row):
            continue
        has_data = True
        record = {}
        for idx, fn in col_map.items():
            if idx >= len(row):
                continue
            val = row[idx]
            if val == '' or val is None:
                continue
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
            record[fn] = val
        if not record:
            continue

        # 构建匹配 lookup（基于唯一标识列）
        lookup = {}
        for uf in unique_fields:
            if uf in record:
                lookup[uf] = record[uf]
            elif uf in all_col_names:
                lookup[uf] = None

        existing_id = services.find_row_id_by_lookup(meta, lookup) if lookup else None

        if existing_id is not None:
            existing = services.get_row_values_by_id(meta, existing_id, all_col_names)
            update_fields = {}
            changed = False
            for k, v in record.items():
                if _norm_val(existing.get(k)) != _norm_val(v):
                    update_fields[k] = v
                    changed = True
            if changed:
                try:
                    services.update_row_by_id(meta, existing_id, update_fields)
                    updated_count += 1
                except Exception as e:
                    errors.append(f'第 {row_idx} 行更新失败: {e}')
            else:
                skipped_count += 1
        else:
            try:
                services.insert_single_row(meta, record)
                created_count += 1
            except Exception as e:
                errors.append(f'第 {row_idx} 行新增失败: {e}')

    if not has_data:
        return Response({'detail': '没有可导入的数据行', 'errors': errors}, status=400)

    services.recount_rows(meta)
    return Response({
        'created': created_count,
        'updated': updated_count,
        'skipped': skipped_count,
        'errors': errors,
    }, status=201)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dynamic_table_template(request, key):
    """下载指定动态表的导入模板(.xlsx)。"""
    try:
        meta = TableMeta.objects.get(key=key)
    except TableMeta.DoesNotExist:
        return Response({'detail': '表不存在'}, status=404)

    from openpyxl import Workbook
    from openpyxl.utils import get_column_letter
    from urllib.parse import quote
    import io
    import datetime

    cols = meta.get_columns()
    wb = Workbook()
    ws = wb.active
    ws.title = (meta.label or key)[:31]

    # 第 1 行：表头（动态表 label == name）
    headers = [c.get('label') or c['name'] for c in cols]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = cell.font.copy(bold=True)

    # 第 2 行：字段名注释
    ws.append([f'字段: {c["name"]}  类型: {c["type"]}' for c in cols])
    for cell in ws[2]:
        cell.font = cell.font.copy(italic=True, color='888888')

    # 第 3 行：示例数据
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

    for i, c in enumerate(cols, start=1):
        ws.column_dimensions[get_column_letter(i)].width = min(max(len(str(c.get('label') or c['name'])) + 4, 12), 30)

    ws.freeze_panes = 'A2'

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f'{meta.label or key}_导入模板_{datetime.datetime.now().strftime("%Y%m%d")}.xlsx'
    resp = HttpResponse(
        buf.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    resp['Content-Disposition'] = f"attachment; filename*=UTF-8''{quote(filename)}"
    return resp
