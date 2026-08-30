import os

import pymysql
from django.core.management.base import BaseCommand, CommandError

from apps.data_tables.registry import table_registry
from apps.data_tables import serializers  # noqa: F401 - populate table_registry


SYSTEM_DATABASES = {'information_schema', 'mysql', 'performance_schema', 'sys'}


class Command(BaseCommand):
    help = 'Inspect the configured Aliyun RDS MySQL instance and compare tables with the local registry.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--database',
            default=os.getenv('DB_NAME') or '',
            help='Database/schema name. Defaults to DB_NAME from backend/.env.',
        )
        parser.add_argument(
            '--show-databases',
            action='store_true',
            help='List available non-system databases on the MySQL instance.',
        )

    def handle(self, *args, **options):
        host = os.getenv('DB_HOST')
        port = int(os.getenv('DB_PORT', '3306'))
        user = os.getenv('DB_USER')
        password = os.getenv('DB_PASSWORD')
        charset = os.getenv('DB_CHARSET', 'utf8mb4')
        database = options['database'].strip()

        missing = [name for name, value in {
            'DB_HOST': host,
            'DB_USER': user,
            'DB_PASSWORD': password,
        }.items() if not value]
        if missing:
            raise CommandError(f'Missing required env values: {", ".join(missing)}')

        try:
            conn = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database or None,
                charset=charset,
                connect_timeout=10,
                read_timeout=20,
                write_timeout=20,
            )
        except pymysql.MySQLError as exc:
            raise CommandError(f'Unable to connect to MySQL: {exc}') from exc

        with conn:
            if options['show_databases'] or not database:
                self._show_databases(conn)
                if not database:
                    self.stdout.write(self.style.WARNING('Set DB_NAME in backend/.env or rerun with --database to inspect tables.'))
                    return

            self._show_tables(conn, database)

    def _show_databases(self, conn):
        with conn.cursor() as cur:
            cur.execute('SHOW DATABASES')
            databases = [row[0] for row in cur.fetchall() if row[0] not in SYSTEM_DATABASES]

        self.stdout.write(self.style.SUCCESS('Databases:'))
        if not databases:
            self.stdout.write('  (none visible for this user)')
            return
        for name in databases:
            self.stdout.write(f'  - {name}')

    def _show_tables(self, conn, database):
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT TABLE_NAME, TABLE_ROWS, UPDATE_TIME
                FROM information_schema.TABLES
                WHERE TABLE_SCHEMA = %s
                ORDER BY TABLE_NAME
                """,
                [database],
            )
            rows = cur.fetchall()

        rds_tables = {name: {'rows': count or 0, 'updated_at': updated_at} for name, count, updated_at in rows}
        registered_tables = {entry.model._meta.db_table: entry for entry in table_registry.all()}

        self.stdout.write(self.style.SUCCESS(f'Tables in {database}: {len(rds_tables)}'))
        for name, meta in rds_tables.items():
            status = 'registered' if name in registered_tables else 'not registered'
            self.stdout.write(f'  - {name} ({status}, rows~{meta["rows"]}, updated_at={meta["updated_at"] or "-"})')

        missing_in_db = sorted(set(registered_tables) - set(rds_tables))
        unregistered = sorted(set(rds_tables) - set(registered_tables))

        if missing_in_db:
            self.stdout.write(self.style.WARNING('\nRegistered locally but missing in database:'))
            for name in missing_in_db:
                self.stdout.write(f'  - {name}')

        if unregistered:
            self.stdout.write(self.style.WARNING('\nPresent in database but not registered locally:'))
            for name in unregistered:
                self.stdout.write(f'  - {name}')
