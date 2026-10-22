"""data_tables 应用配置：启动期权盈亏汇总的每日调度线程。"""

import datetime as dt
import logging
import os
import threading
import time

from django.apps import AppConfig

logger = logging.getLogger(__name__)

# 调度时刻：每个交易日（周一至周五）19:00；节假日触发幂等重写无害
SCHEDULE_HOUR = 19
SCHEDULE_MINUTE = 0


def _next_run_time(now):
    """计算下一次调度时刻（周一~周五 19:00）。"""
    target = (now + dt.timedelta(minutes=1)).replace(
        hour=SCHEDULE_HOUR, minute=SCHEDULE_MINUTE, second=0, microsecond=0
    )
    while target <= now or target.weekday() >= 5:
        target += dt.timedelta(days=1)
        target = target.replace(
            hour=SCHEDULE_HOUR, minute=SCHEDULE_MINUTE, second=0, microsecond=0
        )
    return target


def _scheduler_loop():
    from django.core.management import call_command

    while True:
        try:
            now = dt.datetime.now()
            nxt = _next_run_time(now)
            time.sleep(max(1.0, (nxt - now).total_seconds()))
            call_command('refresh_option_pnl_summary')
            logger.info('[option-pnl-scheduler] refreshed yl_option_pnl_summary')
        except Exception:
            logger.exception('[option-pnl-scheduler] refresh failed')
            time.sleep(60)


class DataTablesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.data_tables'

    def ready(self):
        # 仅在 runserver 的实际服务进程启动（StatReloader 父进程/管理命令不启动）
        if os.environ.get('RUN_MAIN') != 'true':
            return
        threading.Thread(
            target=_scheduler_loop,
            daemon=True,
            name='option-pnl-scheduler',
        ).start()
        print(f'[option-pnl-scheduler] started, fires at {SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d} on weekdays')
