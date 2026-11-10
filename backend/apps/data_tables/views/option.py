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
def option_pnl_underlying(request):
    """单个标的品种的期权盈亏详情：品种汇总 + 各投顾在该品种期权上的盈亏拆分。

    ?underlying=MO：合约前导字母匹配（与期权盈亏列表口径一致）；
    投顾行附投顾名（mom_account_record）与 pid（perf_products），
    前端可直接链接到投顾业绩页；按权利金净收支倒序。

    性能：LIKE 前缀粗筛 + REGEXP 精筛（collation 大小写不敏感），
    两步聚合避免 GROUP BY account 走 account 索引回表；结果缓存 10 分钟。
    """
    from django.core.cache import cache

    underlying = (request.query_params.get('underlying') or '').strip().upper()
    if not underlying or not underlying.isalpha():
        return Response({'detail': 'underlying 参数无效'}, status=400)

    cache_key = f'option_pnl_underlying_{underlying}'
    cached = cache.get(cache_key)
    if cached is not None:
        return Response(cached)

    # 前导字母 + 期权合约形态（如 MO2609-C-2550 / SR309C5700）
    # collation 为 0900_ai_ci（大小写不敏感），LIKE/REGEXP 无需字符类
    where = f"contract LIKE %s AND contract REGEXP '^{underlying}[0-9]{{3,4}}-?[CP]-?'"

    with connection.cursor() as cursor:
        # 投顾行：先按 (account, contract) 细分再按 account 聚合，
        # 避免 GROUP BY account 直接过滤全表 COUNT(DISTINCT) 的开销
        cursor.execute(
            f"""
            SELECT t.account,
                   COUNT(*)                    AS contracts,
                   SUM(t.trades)               AS trades,
                   SUM(t.premium)              AS premium,
                   SUM(t.fee)                  AS fee,
                   MIN(t.first_date)           AS first_date,
                   MAX(t.last_date)            AS last_date
            FROM (
                SELECT account, contract,
                       COUNT(*)                                   AS trades,
                       SUM(COALESCE(premium_income_expense, 0))  AS premium,
                       SUM(COALESCE(fee, 0))                     AS fee,
                       MIN(trade_date)                           AS first_date,
                       MAX(trade_date)                           AS last_date
                FROM rh_trades
                WHERE {where}
                GROUP BY account, contract
            ) t
            GROUP BY t.account
            ORDER BY premium DESC
            """,
            [f'{underlying}%'],
        )
        advisor_rows = cursor.fetchall()
        if not advisor_rows:
            payload = {'detail': '该品种无期权成交记录'}
            return Response(payload, status=404)

        # 品种级合约数（跨投顾去重）与数据截止日
        cursor.execute(
            f"""
            SELECT COUNT(DISTINCT contract), MAX(trade_date)
            FROM rh_trades
            WHERE {where}
            """,
            [f'{underlying}%'],
        )
        total_contracts, last_date = cursor.fetchone()

        # 投顾名 / 停止状态 / 业绩页 pid
        accounts = [r[0] for r in advisor_rows]
        name_map, stop_map, pid_map = {}, {}, {}
        if accounts:
            cursor.execute(
                """
                SELECT m.account_id, m.account_name, m.is_stop, p.pid
                FROM mom_account_record m
                LEFT JOIN perf_products p ON p.product_name = m.account_id
                WHERE m.account_id IN %s
                """,
                [tuple(accounts)],
            )
            for acc, nm, stop, pid in cursor.fetchall():
                name_map[acc] = nm
                stop_map[acc] = stop
                pid_map[acc] = pid

        cursor.execute(
            'SELECT symbol_name FROM fut_symbol_info WHERE UPPER(symbol_code) = %s',
            [underlying],
        )
        row0 = cursor.fetchone()
        name = row0[0] if row0 and row0[0] else underlying

    advisors = [
        {
            'account': r[0],
            'account_name': name_map.get(r[0]) or r[0],
            'pid': pid_map.get(r[0]),
            'is_stop': 1 if stop_map.get(r[0]) == 1 else 0,
            'contracts': int(r[1]),
            'trades': int(r[2]),
            'premium': float(r[3] or 0),
            'fee': float(r[4] or 0),
            'first_date': r[5].isoformat() if r[5] else None,
            'last_date': r[6].isoformat() if r[6] else None,
        }
        for r in advisor_rows
    ]
    payload = {
        'trade_date': last_date.isoformat() if last_date else None,
        'underlying': underlying,
        'name': name,
        'summary': {
            'premium': sum(a['premium'] for a in advisors),
            'fee': sum(a['fee'] for a in advisors),
            'contracts': int(total_contracts or 0),
            'trades': sum(a['trades'] for a in advisors),
            'advisors': len(advisors),
        },
        'advisors': advisors,
    }
    cache.set(cache_key, payload, 60 * 10)
    return Response(payload)


@api_view(['GET'])
@permission_classes([AllowAny])
def option_trades(request):
    """单个投顾在单个品种期权上的成交记录明细（分页）。

    ?account=250206_HC&underlying=MO&page=1&page_size=20：
    account 走索引过滤 + 品种前导字母 LIKE/REGEXP 精筛期权合约；
    返回该投顾该品种的汇总（权利金净收支/手续费/合约数/笔数/区间）与逐笔明细。
    """
    account = (request.query_params.get('account') or '').strip()
    underlying = (request.query_params.get('underlying') or '').strip().upper()
    if not account or not underlying or not underlying.isalpha():
        return Response({'detail': 'account / underlying 参数无效'}, status=400)

    try:
        page = max(int(request.query_params.get('page', 1) or 1), 1)
        page_size = min(max(int(request.query_params.get('page_size', 20) or 20), 1), 100)
    except ValueError:
        return Response({'detail': '分页参数无效'}, status=400)
    offset = (page - 1) * page_size

    # collation 大小写不敏感；account 索引先过滤再正则精筛
    where = (
        "account = %s AND contract LIKE %s "
        f"AND contract REGEXP '^{underlying}[0-9]{{3,4}}-?[CP]-?'"
    )
    params_prefix = [account, f'{underlying}%']

    with connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT COUNT(DISTINCT contract), COUNT(*),
                   SUM(COALESCE(premium_income_expense, 0)),
                   SUM(COALESCE(fee, 0)),
                   MIN(trade_date), MAX(trade_date)
            FROM rh_trades
            WHERE {where}
            """,
            params_prefix,
        )
        s = cursor.fetchone()
        if not s or not s[1]:
            return Response({'detail': '该投顾在此品种无期权成交'}, status=404)

        cursor.execute(
            f"""
            SELECT r.trade_date, r.trade_time, r.contract, r.side, r.open_close,
                   r.trade_price, r.trade_qty, r.trade_amount,
                   r.premium_income_expense, r.fee
            FROM rh_trades r
            WHERE {where}
            ORDER BY r.trade_date DESC, r.trade_time DESC, r.id DESC
            LIMIT %s OFFSET %s
            """,
            [*params_prefix, page_size, offset],
        )
        trade_rows = [
            {
                'trade_date': row[0].isoformat() if row[0] else None,
                'trade_time': row[1],
                'contract': row[2],
                'side': row[3],
                'open_close': row[4],
                'trade_price': row[5],
                'trade_qty': row[6],
                'trade_amount': row[7],
                'premium_income_expense': float(row[8]) if row[8] is not None else None,
                'fee': float(row[9]) if row[9] is not None else None,
            }
            for row in cursor.fetchall()
        ]

        cursor.execute(
            'SELECT account_name FROM mom_account_record WHERE account_id = %s',
            [account],
        )
        row0 = cursor.fetchone()
        advisor_name = row0[0] if row0 and row0[0] else account

        cursor.execute(
            'SELECT symbol_name FROM fut_symbol_info WHERE UPPER(symbol_code) = %s',
            [underlying],
        )
        row1 = cursor.fetchone()
        underlying_name = row1[0] if row1 and row1[0] else underlying

    return Response({
        'account': account,
        'advisor_name': advisor_name,
        'underlying': underlying,
        'underlying_name': underlying_name,
        'summary': {
            'contracts': int(s[0]),
            'trades': int(s[1]),
            'premium': float(s[2] or 0),
            'fee': float(s[3] or 0),
            'first_date': s[4].isoformat() if s[4] else None,
            'last_date': s[5].isoformat() if s[5] else None,
        },
        'page': page,
        'page_size': page_size,
        'total': int(s[1]),
        'rows': trade_rows,
    })
