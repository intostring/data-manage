from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone


class Command(BaseCommand):
    help = 'Refresh precomputed option PnL summary used by the display option PnL endpoint.'

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            self._ensure_table(cursor)
            rows, trade_date, total_advisors = self._calculate_rows(cursor)
            if not trade_date:
                self.stdout.write(self.style.WARNING('No rh_trades data found.'))
                return

            cursor.execute(
                'DELETE FROM yl_option_pnl_summary WHERE trade_date = %s',
                [trade_date],
            )
            if rows:
                refreshed_at = timezone.now()
                cursor.executemany(
                    """
                    INSERT INTO yl_option_pnl_summary (
                        trade_date,
                        underlying,
                        underlying_name,
                        contracts,
                        trades,
                        advisors,
                        total_advisors,
                        premium,
                        fee,
                        refreshed_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            trade_date,
                            row['underlying'],
                            row['name'],
                            row['contracts'],
                            row['trades'],
                            row['advisors'],
                            total_advisors,
                            row['premium'],
                            row['fee'],
                            refreshed_at,
                        )
                        for row in rows
                    ],
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'Refreshed yl_option_pnl_summary for {trade_date}: {len(rows)} underlyings.'
            )
        )

    def _ensure_table(self, cursor):
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS yl_option_pnl_summary (
                id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                trade_date DATE NOT NULL,
                underlying VARCHAR(20) NOT NULL,
                underlying_name VARCHAR(50) NULL,
                contracts INT NOT NULL DEFAULT 0,
                trades INT NOT NULL DEFAULT 0,
                advisors INT NOT NULL DEFAULT 0,
                total_advisors INT NOT NULL DEFAULT 0,
                premium DECIMAL(22, 4) NOT NULL DEFAULT 0,
                fee DECIMAL(22, 4) NOT NULL DEFAULT 0,
                refreshed_at DATETIME NOT NULL,
                UNIQUE KEY uq_option_pnl_trade_underlying (trade_date, underlying),
                KEY idx_option_pnl_trade_date (trade_date)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """
        )

    def _calculate_rows(self, cursor):
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
        total_advisors = int(cursor.fetchone()[0] or 0)

        cursor.execute('SELECT UPPER(symbol_code), symbol_name FROM fut_symbol_info')
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
        return rows, trade_date, total_advisors
