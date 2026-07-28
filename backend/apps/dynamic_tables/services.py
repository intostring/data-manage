"""动态表服务：原生 SQL 建表、写入、查询。

用 connection.cursor() 绕过 ORM 的动态模型限制，
直接操作 dynamic_<key> 物理表。
"""
from django.db import connection

from .models import TableMeta

# Python 类型 → MySQL 类型映射
TYPE_MAP = {
    'int': 'BIGINT',
    'float': 'DOUBLE',
    'text': 'TEXT',
    'str': 'VARCHAR(255)',
    'datetime': 'DATETIME',
    'date': 'DATE',
    'bool': 'TINYINT(1)',
}


def table_name_for(key: str) -> str:
    return f'dynamic_{key}'


def quote_ident(name: str) -> str:
    """转义标识符，防止 SQL 注入（仅允许字母数字下划线）"""
    if not name.replace('_', '').isalnum():
        raise ValueError(f'非法列名: {name}')
    return f'`{name}`'


def create_dynamic_table(key: str, label: str, columns: list) -> TableMeta:
    """根据列定义创建物理表 + 写入元信息。

    columns: [{'name': 'col1', 'type': 'str'}, ...]
    """
    physical = table_name_for(key)
    col_defs = ['`id` BIGINT AUTO_INCREMENT PRIMARY KEY']
    for col in columns:
        mysql_type = TYPE_MAP.get(col['type'], 'TEXT')
        col_defs.append(f'{quote_ident(col["name"])} {mysql_type}')
    ddl = f'CREATE TABLE `{physical}` ({", ".join(col_defs)}) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4'

    with connection.cursor() as cur:
        cur.execute(f'DROP TABLE IF EXISTS `{physical}`')
        cur.execute(ddl)

    meta = TableMeta.objects.create(
        key=key,
        label=label,
        table_name=physical,
        columns='[]',
    )
    meta.set_columns(columns)
    meta.save()
    return meta


def insert_rows(meta: TableMeta, rows: list) -> int:
    """批量写入数据行，返回写入条数"""
    if not rows:
        return 0
    cols = meta.get_columns()
    col_names = [quote_ident(c['name']) for c in cols]
    placeholders = ', '.join(['%s'] * len(col_names))
    sql = f'INSERT INTO `{meta.table_name}` ({", ".join(col_names)}) VALUES ({placeholders})'
    data = [tuple(row.get(c['name']) for c in cols) for row in rows]
    with connection.cursor() as cur:
        cur.executemany(sql, data)
    meta.row_count = meta.row_count + len(data)
    meta.save(update_fields=['row_count', 'updated_at'])
    return len(data)


def fetch_rows(meta: TableMeta, limit: int = 20, offset: int = 0,
               search: str = '', order_by: str = '', order_dir: str = 'asc',
               filters: dict = None) -> tuple:
    """查询动态表数据，返回 (rows, total)

    - search: 全局模糊搜索（在所有文本列上 LIKE）
    - order_by: 排序字段名（必须是已注册列名或 'id'）
    - order_dir: 'asc' 或 'desc'
    - filters: 按字段筛选 {col_name: value}，文本列 LIKE，数值列精确匹配
    """
    cols = meta.get_columns()
    col_names = [quote_ident(c['name']) for c in cols]
    select = f'SELECT `id`, {", ".join(col_names)} FROM `{meta.table_name}`'

    # 校验排序字段，防 SQL 注入
    valid_names = {'id', *(c['name'] for c in cols)}
    order_clause = 'ORDER BY `id` DESC'
    if order_by and order_by in valid_names and order_dir in ('asc', 'desc'):
        order_clause = f'ORDER BY {quote_ident(order_by)} {order_dir.upper()}, `id` DESC'

    where_parts = []
    params = []

    # 全局搜索
    if search:
        like_clauses = []
        for c in cols:
            if c['type'] in ('str', 'text'):
                like_clauses.append(f'{quote_ident(c["name"])} LIKE %s')
                params.append(f'%{search}%')
        if like_clauses:
            where_parts.append('(' + ' OR '.join(like_clauses) + ')')

    # 按字段筛选
    if filters:
        col_map = {c['name']: c for c in cols}
        for fname, fval in filters.items():
            if fname not in col_map or fval in (None, ''):
                continue
            c = col_map[fname]
            if c['type'] in ('str', 'text'):
                where_parts.append(f'{quote_ident(fname)} LIKE %s')
                params.append(f'%{fval}%')
            else:
                where_parts.append(f'{quote_ident(fname)} = %s')
                params.append(fval)

    where = (' WHERE ' + ' AND '.join(where_parts)) if where_parts else ''

    with connection.cursor() as cur:
        cur.execute(f'SELECT COUNT(*) FROM `{meta.table_name}`{where}', params)
        total = cur.fetchone()[0]

        cur.execute(
            f'{select}{where} {order_clause} LIMIT %s OFFSET %s',
            params + [limit, offset],
        )
        result = cur.fetchall()

    keys = ['id'] + [c['name'] for c in cols]
    rows = [dict(zip(keys, row)) for row in result]
    return rows, total


def drop_dynamic_table(meta: TableMeta) -> None:
    with connection.cursor() as cur:
        cur.execute(f'DROP TABLE IF EXISTS `{meta.table_name}`')
    meta.delete()


def parse_csv(file_obj) -> tuple:
    """解析上传的 CSV 文件，返回 (columns, rows)"""
    import csv
    import io

    stream = io.TextIOWrapper(file_obj, encoding='utf-8-sig')
    reader = csv.reader(stream)
    header = next(reader)
    rows = list(reader)

    # 推断列类型
    columns = []
    for i, name in enumerate(header):
        col_type = 'str'
        if rows:
            sample = [r[i] for r in rows[:20] if i < len(r) and r[i]]
            if sample and all(_is_int(v) for v in sample):
                col_type = 'int'
            elif sample and all(_is_float(v) for v in sample):
                col_type = 'float'
        columns.append({'name': name.strip(), 'type': col_type})

    return columns, rows


def _is_int(v):
    try:
        int(v)
        return True
    except (ValueError, TypeError):
        return False


def _is_float(v):
    try:
        float(v)
        return True
    except (ValueError, TypeError):
        return False
