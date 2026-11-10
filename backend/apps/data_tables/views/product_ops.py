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


# ==================== 产品运维 · 投顾信息台账 ====================

def _advisor_info_dto(m):
    return {
        'id': m.id,
        'name': m.name,
        'account_code': m.account_code,
        'invest_amount': float(m.invest_amount) if m.invest_amount is not None else None,
        'max_margin_usage': float(m.max_margin_usage) if m.max_margin_usage is not None else None,
        'warning_line': float(m.warning_line) if m.warning_line is not None else None,
        'stop_loss_line': float(m.stop_loss_line) if m.stop_loss_line is not None else None,
        'margin_call_risk': float(m.margin_call_risk) if m.margin_call_risk is not None else None,
        'force_close_risk': float(m.force_close_risk) if m.force_close_risk is not None else None,
        'dividend_rate': float(m.dividend_rate) if m.dividend_rate is not None else None,
        'can_trade_option': bool(m.can_trade_option),
        'option_trade_type': m.option_trade_type,
        'product': m.product,
        'run_status': m.run_status,
        'suspend_date': m.suspend_date.isoformat() if m.suspend_date else None,
        'create_date': m.create_date.isoformat() if m.create_date else None,
        'liquidation_pnl': float(m.liquidation_pnl) if m.liquidation_pnl is not None else None,
        'invest_tag': m.invest_tag,
        'invest_logic': m.invest_logic,
        'remark': m.remark,
        'updated_at': m.updated_at.strftime('%Y-%m-%d %H:%M') if m.updated_at else None,
    }


def _advisor_info_apply(m, payload):
    """按白名单字段更新并保存；姓名必填。"""
    name = str(payload.get('name') or '').strip()
    if not name:
        raise ValueError('姓名不能为空')

    def _dec(key):
        v = payload.get(key)
        if v in (None, ''):
            return None
        return _decimal.Decimal(str(v))

    def _date(key):
        v = str(payload.get(key) or '').strip()
        if not v:
            return None
        d = parse_date(v)
        return d if d else v

    m.name = name
    m.account_code = str(payload.get('account_code') or '').strip() or None
    m.invest_amount = _dec('invest_amount')
    m.max_margin_usage = _dec('max_margin_usage')
    m.warning_line = _dec('warning_line')
    m.stop_loss_line = _dec('stop_loss_line')
    m.margin_call_risk = _dec('margin_call_risk')
    m.force_close_risk = _dec('force_close_risk')
    m.dividend_rate = _dec('dividend_rate')
    m.can_trade_option = bool(payload.get('can_trade_option'))
    m.option_trade_type = str(payload.get('option_trade_type') or '').strip()
    m.product = str(payload.get('product') or '').strip()
    m.run_status = str(payload.get('run_status') or '').strip() or '运行中'
    m.suspend_date = _date('suspend_date')
    m.create_date = _date('create_date')
    m.liquidation_pnl = _dec('liquidation_pnl')
    m.invest_tag = str(payload.get('invest_tag') or '').strip()
    m.invest_logic = str(payload.get('invest_logic') or '').strip()
    m.remark = str(payload.get('remark') or '').strip()
    # 派生口径：追保风险线 = 投资金额 × 预警线；强平风险线 = 投资金额 × 止损线
    if m.invest_amount is not None and m.warning_line is not None:
        m.margin_call_risk = (m.invest_amount * m.warning_line).quantize(_decimal.Decimal('0.01'))
    if m.invest_amount is not None and m.stop_loss_line is not None:
        m.force_close_risk = (m.invest_amount * m.stop_loss_line).quantize(_decimal.Decimal('0.01'))
    m.save()
    return m


def _sync_invest_tag_to_accounts(m):
    """投顾信息台账的「投资标签」同步到 mom_account_record.invest_cate（对应投顾）。

    优先按操作账户（account_code→account_id）精确匹配；
    操作账户为空或未命中时按同名（account_name）全部账号同步。
    台账先于账户建档时无匹配行，静默跳过（返回 0，不阻断保存）。
    """
    from ..models import MomAccountRecord

    qs = MomAccountRecord.objects.all()
    if m.account_code:
        matched = qs.filter(account_id=m.account_code)
        if not matched.exists():
            matched = qs.filter(account_name=m.name)
    else:
        matched = qs.filter(account_name=m.name)
    count = matched.update(invest_cate=(m.invest_tag or None))
    # 投顾列表接口按 invest_cate 筛选且有缓存，同步后清掉避免 10 分钟内显示旧标签
    if count:
        from django.core.cache import cache
        cache.delete_many(['advisor_perf_list_0', 'advisor_perf_list_1'])
    return count


# 投顾信息列表：可排序字段白名单（前端列 key 与模型字段同名）
_ADVISOR_INFO_ORDER_FIELDS = {
    'name', 'account_code', 'create_date', 'product', 'invest_amount',
    'max_margin_usage', 'warning_line', 'stop_loss_line', 'margin_call_risk',
    'force_close_risk', 'dividend_rate', 'run_status', 'suspend_date',
    'liquidation_pnl', 'invest_tag', 'invest_logic',
}


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def advisor_info_records(request):
    """投顾信息台账：GET 列表（?search= 按姓名/账户/产品模糊），POST 新建（需登录）。

    排序：ordering=字段名（-前缀降序，白名单 _ADVISOR_INFO_ORDER_FIELDS 内）。
    """
    from ..models import AdvisorInfo

    if request.method == 'GET':
        qs = AdvisorInfo.objects.all()

        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(account_code__icontains=search)
                | Q(product__icontains=search)
            )

        ordering = request.query_params.get('ordering', '').strip()
        if ordering:
            desc = ordering.startswith('-')
            field = ordering.lstrip('-')
            if field in _ADVISOR_INFO_ORDER_FIELDS:
                expr = F(field).desc(nulls_last=True) if desc else F(field).asc(nulls_last=True)
                qs = qs.order_by(expr, '-id')
            else:
                qs = qs.order_by(F('create_date').desc(nulls_last=True), '-id')
        else:
            qs = qs.order_by(F('create_date').desc(nulls_last=True), '-id')
        # 分页：page 从 1 起，page_size 默认 20、上限 200
        try:
            page = max(int(request.query_params.get('page', 1)), 1)
            page_size = min(max(int(request.query_params.get('page_size', 20)), 1), 200)
        except (TypeError, ValueError):
            page, page_size = 1, 20
        total = qs.count()
        items = qs[(page - 1) * page_size: page * page_size]
        return Response({
            'rows': [_advisor_info_dto(m) for m in items],
            'total': total,
            'page': page,
            'page_size': page_size,
        })

    if not (request.user and request.user.is_authenticated):
        return Response({'detail': '登录后才能维护投顾信息'}, status=401)
    try:
        m = _advisor_info_apply(AdvisorInfo(), request.data or {})
    except ValueError as e:
        return Response({'detail': str(e)}, status=400)
    except Exception as e:
        if 'Duplicate' in str(e) or 'unique' in str(e).lower():
            return Response({'detail': '该操作账户已存在'}, status=400)
        raise
    synced = _sync_invest_tag_to_accounts(m)
    payload = _advisor_info_dto(m)
    payload['synced_accounts'] = synced
    return Response(payload, status=201)


@api_view(['PUT', 'DELETE'])
@permission_classes([AllowAny])
def advisor_info_record_detail(request, pk):
    """投顾信息台账：PUT 更新 / DELETE 删除（需登录）。"""
    from ..models import AdvisorInfo

    if not (request.user and request.user.is_authenticated):
        return Response({'detail': '登录后才能维护投顾信息'}, status=401)
    m = AdvisorInfo.objects.filter(pk=pk).first()
    if not m:
        return Response({'detail': '记录不存在'}, status=404)
    if request.method == 'DELETE':
        m.delete()
        return Response({'detail': '已删除'})
    try:
        m = _advisor_info_apply(m, request.data or {})
    except ValueError as e:
        return Response({'detail': str(e)}, status=400)
    except Exception as e:
        if 'Duplicate' in str(e) or 'unique' in str(e).lower():
            return Response({'detail': '该操作账户已存在'}, status=400)
        raise
    synced = _sync_invest_tag_to_accounts(m)
    payload = _advisor_info_dto(m)
    payload['synced_accounts'] = synced
    return Response(payload)


# ==================== 产品运维 · 分红信息台账 ====================

def _dividend_dto(m):
    return {
        'id': m.id,
        'dividend_date': m.dividend_date.isoformat() if m.dividend_date else None,
        'account_code': m.account_code,
        'advisor_name': m.advisor_name,
        'dividend_amount': float(m.dividend_amount) if m.dividend_amount is not None else None,
        'withdraw_amount': float(m.withdraw_amount) if m.withdraw_amount is not None else None,
        'product': m.product,
        'remark': m.remark,
        'updated_at': m.updated_at.strftime('%Y-%m-%d %H:%M') if m.updated_at else None,
    }


def _dividend_apply(m, payload):
    """按白名单字段更新并保存。"""
    m.dividend_date = _parse_date_str(payload.get('dividend_date'))
    m.account_code = str(payload.get('account_code') or '').strip()
    m.advisor_name = str(payload.get('advisor_name') or '').strip()

    def _dec(key):
        v = payload.get(key)
        if v in (None, ''):
            return None
        return _decimal.Decimal(str(v))

    m.dividend_amount = _dec('dividend_amount')
    m.withdraw_amount = _dec('withdraw_amount')
    m.product = str(payload.get('product') or '').strip()
    m.remark = str(payload.get('remark') or '').strip()
    m.save()
    return m


def _parse_date_str(v):
    v = str(v or '').strip()
    if not v:
        return None
    d = parse_date(v)
    return d if d else v


@api_view(['GET'])
@permission_classes([AllowAny])
def advisor_info_lookup(request):
    """按操作账户查投顾名称与所属产品（分红信息自动填充用）。

    优先 mom_account_record（account_id 精确匹配），回退投顾信息台账 mom_advisor_info。
    """
    from ..models import AdvisorInfo, MomAccountRecord

    code = (request.query_params.get('account_code') or '').strip()
    if not code:
        return Response({'found': False})

    m = MomAccountRecord.objects.filter(account_id=code).first()
    if m:
        return Response({
            'found': True,
            'source': 'mom_account_record',
            'advisor_name': m.account_name or '',
            'product': m.product_name or '',
        })

    a = AdvisorInfo.objects.filter(account_code=code).first()
    if a:
        return Response({
            'found': True,
            'source': 'mom_advisor_info',
            'advisor_name': a.name or '',
            'product': a.product or '',
        })
    return Response({'found': False})


def _mom_fill_fields(m):
    """mom_account_record → 台账可回填字段映射（空值返回 None，由调用方判断是否覆盖）。"""
    return {
        'invest_amount': float(m.cum_investment) if m.cum_investment is not None else None,
        'max_margin_usage': float(m.max_pos_rate) if m.max_pos_rate is not None else None,
        'stop_loss_line': float(m.stop_loss_rate) if m.stop_loss_rate is not None else None,
        'dividend_rate': float(m.perf_fee) if m.perf_fee is not None else None,
        'product': (m.product_name or '').strip() or None,
        'invest_tag': (m.invest_cate or '').strip() or None,
        'invest_logic': (m.invest_logic or '').strip() or None,
        'create_date': parse_date(str(m.create_time).strip()[:10]) if m.create_time else None,
    }


@api_view(['POST'])
@permission_classes([AllowAny])
def advisor_info_sync(request):
    """从 rh_advisors / mom_account_record 同步投顾信息台账（需登录）。

    1) rh_advisors 新账户 → 新增台账行（姓名/产品来自 rh_advisors，其余字段带出 mom_account_record）；
    2) 台账已有投顾命中 mom_account_record → 仅回填空白字段（投资金额/最大保证金使用/止损线/
       分红率/所属产品/投资标签/投资逻辑/创建日期），不覆盖人工维护数据。
    """
    from ..models import AdvisorInfo, MomAccountRecord

    if not (request.user and request.user.is_authenticated):
        return Response({'detail': '登录后才能同步'}, status=401)

    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT r.account, MAX(r.account_holder), MAX(r.product_name)
            FROM rh_advisors r
            WHERE r.account IS NOT NULL AND r.account <> ''
            GROUP BY r.account
            """
        )
        rh_rows = cursor.fetchall()

    existing = {a.account_code: a for a in AdvisorInfo.objects.all()}
    mom_map = {m.account_id: m for m in MomAccountRecord.objects.all()}

    # 1) 新增 rh_advisors 新账户
    added = []
    for code, holder, product in rh_rows:
        code = str(code or '').strip()
        if not code or code in existing:
            continue
        m = mom_map.get(code)
        name = str(holder or '').strip() or (m.account_name if m else '') or code
        fills = _mom_fill_fields(m) if m else {}
        prod = str(product or '').strip() or fills.get('product') or ''
        try:
            obj = AdvisorInfo.objects.create(
                name=name,
                account_code=code,
                product=prod,
                invest_amount=fills.get('invest_amount'),
                max_margin_usage=fills.get('max_margin_usage'),
                stop_loss_line=fills.get('stop_loss_line'),
                dividend_rate=fills.get('dividend_rate'),
                invest_tag=fills.get('invest_tag') or '',
                invest_logic=fills.get('invest_logic') or '',
                create_date=fills.get('create_date'),
                run_status='运行中',
            )
            added.append({'account_code': code, 'name': name})
            existing[code] = obj
        except Exception:
            continue

    # 2) 已有投顾按 mom_account_record 补空白字段
    FIELD_LABELS = {
        'invest_amount': '投资金额', 'max_margin_usage': '最大保证金使用',
        'stop_loss_line': '止损线', 'dividend_rate': '分红率',
        'product': '所属产品', 'invest_tag': '投资标签',
        'invest_logic': '投资逻辑', 'create_date': '创建日期',
    }
    updated = []
    for code, info in existing.items():
        m = mom_map.get(code)
        if not m:
            continue
        fills = _mom_fill_fields(m)
        changed_fields = []
        for field, val in fills.items():
            if val is None:
                continue
            cur = getattr(info, field, None)
            if cur is None or cur == '':
                setattr(info, field, val)
                changed_fields.append(FIELD_LABELS[field])
        if changed_fields:
            try:
                info.save()
                updated.append({
                    'account_code': code,
                    'name': info.name,
                    'fields': changed_fields,
                })
            except Exception:
                continue

    return Response({
        'added': added,
        'added_count': len(added),
        'updated': updated,
        'updated_count': len(updated),
    })


# ==================== 产品运维 · 柜台账户（mom_fund_status 只读） ====================

def _customer_short_name(name):
    """客户名称简称：去掉管理人前缀（首个「公司」前，含其后的连字符）与「私募证券投资基金」等后缀。

    与前端 CounterAccount.vue 的 shortName 规则保持一致，
    用于 ?customer= 按基金（客户简称）过滤时两侧口径统一。
    """
    if not name:
        return ''
    s = name
    idx = s.find('公司')
    if idx >= 0:
        s = s[idx + 2:]
    s = s.lstrip('-—－')
    s = re.sub(r'(私募证券投资基金|私募基金|证券投资基金)$', '', s)
    return s or name


@api_view(['GET'])
@permission_classes([AllowAny])
def counter_account(request):
    """柜台账户快照（mom_fund_status，只读）。

    ?date=YYYY-MM-DD 默认最新交易日；?account=保证金账户 过滤；
    ?customer=基金（客户名称全称或简称，按简称等值匹配该基金全部账户）；
    ?search= 客户/公司/账户模糊。
    """
    with connection.cursor() as cursor:
        cursor.execute('SELECT MAX(trade_date), MIN(trade_date) FROM mom_fund_status')
        latest_date, min_date = cursor.fetchone()
        if not latest_date:
            return Response({'trade_date': None, 'rows': [], 'accounts': [], 'latest_date': None})

        date_param = request.query_params.get('date', '').strip()
        d = parse_date(date_param) if date_param else latest_date
        if not d:
            return Response({'detail': 'date 参数无效'}, status=400)

        account = request.query_params.get('account', '').strip()
        customer = request.query_params.get('customer', '').strip()
        search = request.query_params.get('search', '').strip()

        sql = """
            SELECT trade_date, margin_account, futures_account, customer_name, broker_name,
                   prev_balance, customer_equity, deposit_withdraw, currency_funds, day_pl,
                   non_monetary_pledge, total_premium, monetary_pledge, fee, frozen,
                   balance, margin_occupied, floating_pl, available, risk_degree, margin_call
            FROM mom_fund_status
            WHERE trade_date = %s
        """
        params = [d]
        if account:
            sql += ' AND margin_account = %s'
            params.append(account)
        if search:
            sql += ' AND (customer_name LIKE %s OR broker_name LIKE %s OR margin_account LIKE %s OR futures_account LIKE %s)'
            kw = f'%{search}%'
            params.extend([kw, kw, kw, kw])
        sql += ' ORDER BY customer_equity DESC'

        cursor.execute(sql, params)
        rows = [
            {
                'trade_date': r[0].isoformat() if r[0] else None,
                'margin_account': r[1],
                'futures_account': r[2],
                'customer_name': r[3],
                'broker_name': r[4],
                'prev_balance': float(r[5]) if r[5] is not None else None,
                'customer_equity': float(r[6]) if r[6] is not None else None,
                'deposit_withdraw': float(r[7]) if r[7] is not None else None,
                'currency_funds': float(r[8]) if r[8] is not None else None,
                'day_pl': float(r[9]) if r[9] is not None else None,
                'non_monetary_pledge': float(r[10]) if r[10] is not None else None,
                'total_premium': float(r[11]) if r[11] is not None else None,
                'monetary_pledge': float(r[12]) if r[12] is not None else None,
                'fee': float(r[13]) if r[13] is not None else None,
                'frozen': float(r[14]) if r[14] is not None else None,
                'balance': float(r[15]) if r[15] is not None else None,
                'margin_occupied': float(r[16]) if r[16] is not None else None,
                'floating_pl': float(r[17]) if r[17] is not None else None,
                'available': float(r[18]) if r[18] is not None else None,
                'risk_degree': float(r[19]) if r[19] is not None else None,
                'margin_call': float(r[20]) if r[20] is not None else None,
            }
            for r in cursor.fetchall()
        ]

        # 按基金（客户简称）过滤：展示该基金在各期货公司的全部账户
        if customer:
            want = _customer_short_name(customer)
            rows = [r for r in rows if _customer_short_name(r['customer_name'] or '') == want]

        # 账户清单（供筛选下拉）
        cursor.execute(
            """
            SELECT margin_account, futures_account, broker_name, customer_name, MAX(trade_date)
            FROM mom_fund_status
            GROUP BY 1, 2, 3, 4
            ORDER BY broker_name
            """
        )
        accounts = [
            {
                'margin_account': a[0],
                'futures_account': a[1],
                'broker_name': a[2],
                'customer_name': a[3],
            }
            for a in cursor.fetchall()
        ]

        return Response({
            'trade_date': d.isoformat(),
            'latest_date': latest_date.isoformat(),
            'min_date': min_date.isoformat() if min_date else None,
            'rows': rows,
            'accounts': accounts,
        })


@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
def advisor_dividend_records(request):
    """分红信息台账：GET 分页列表（?search= 按账户/投顾/产品模糊，按分红日期倒序），POST 新建（需登录）。"""
    from ..models import AdvisorDividend

    if request.method == 'GET':
        qs = AdvisorDividend.objects.all().order_by(
            F('dividend_date').desc(nulls_last=True), '-id'
        )
        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(account_code__icontains=search)
                | Q(advisor_name__icontains=search)
                | Q(product__icontains=search)
            )
        try:
            page = max(int(request.query_params.get('page', 1)), 1)
            page_size = min(max(int(request.query_params.get('page_size', 20)), 1), 200)
        except (TypeError, ValueError):
            page, page_size = 1, 20
        total = qs.count()
        items = qs[(page - 1) * page_size: page * page_size]
        return Response({
            'rows': [_dividend_dto(m) for m in items],
            'total': total,
            'page': page,
            'page_size': page_size,
        })

    if not (request.user and request.user.is_authenticated):
        return Response({'detail': '登录后才能维护分红信息'}, status=401)
    try:
        m = _dividend_apply(AdvisorDividend(), request.data or {})
    except Exception as e:
        if 'Duplicate' in str(e) or 'unique' in str(e).lower():
            return Response({'detail': '该「分红日期+操作账户」已存在'}, status=400)
        return Response({'detail': f'保存失败: {e}'}, status=400)
    return Response(_dividend_dto(m), status=201)


@api_view(['PUT', 'DELETE'])
@permission_classes([AllowAny])
def advisor_dividend_record_detail(request, pk):
    """分红信息台账：PUT 更新 / DELETE 删除（需登录）。"""
    from ..models import AdvisorDividend

    if not (request.user and request.user.is_authenticated):
        return Response({'detail': '登录后才能维护分红信息'}, status=401)
    m = AdvisorDividend.objects.filter(pk=pk).first()
    if not m:
        return Response({'detail': '记录不存在'}, status=404)
    if request.method == 'DELETE':
        m.delete()
        return Response({'detail': '已删除'})
    try:
        m = _dividend_apply(m, request.data or {})
    except Exception as e:
        if 'Duplicate' in str(e) or 'unique' in str(e).lower():
            return Response({'detail': '该「分红日期+操作账户」已存在'}, status=400)
        return Response({'detail': f'保存失败: {e}'}, status=400)
    return Response(_dividend_dto(m))
