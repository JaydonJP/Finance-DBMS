"""Switch DA2 to a verified shared Oracle project schema or restore local mode.

Password input stays on this PC. The shared database is inspected with SELECTs;
no schema initialization, import or migration is performed by this utility.
"""
import argparse
import getpass
from pathlib import Path
import shutil
import sys

from dotenv import dotenv_values, set_key, load_dotenv
import oracledb

ROOT = Path(__file__).resolve().parent
ENV = ROOT / '.env'
BACKUP = ROOT / '.runtime' / 'oracle-local.env'


def verify_schema(conn):
    # Reuse only the original server-owned schema metadata, not form identifiers.
    from app import TABLES
    with conn.cursor() as cur:
        cur.execute("SELECT table_name,column_name FROM user_tab_columns WHERE table_name LIKE 'PF_%'")
        columns = {}
        for table, column in cur:
            columns.setdefault(table, set()).add(column.lower())
        missing = []
        for table, (_, _, fields) in TABLES.items():
            for field in fields:
                if field[0] not in columns.get(table, set()):
                    missing.append(table + '.' + field[0])
        audit_columns = {'audit_id', 'trans_id', 'action_name', 'old_amount', 'new_amount', 'changed_at'}
        missing.extend('PF_TRANS_AUDIT.' + c for c in sorted(audit_columns-columns.get('PF_TRANS_AUDIT',set())))
        if missing:
            raise RuntimeError('The shared schema is missing required columns: ' + ', '.join(missing) +
                               '. No shared records were changed.')
        required = {'PF_GOAL_PROGRESS', 'PF_ACCOUNT_OVERVIEW', 'PF_TRANSACTION_BALANCE_TRG'}
        cur.execute("SELECT object_name,status FROM user_objects WHERE object_name IN "
                    "('PF_GOAL_PROGRESS','PF_ACCOUNT_OVERVIEW','PF_TRANSACTION_BALANCE_TRG')")
        valid = {name for name, status in cur if status == 'VALID'}
        if required - valid:
            raise RuntimeError('Missing or invalid project objects: ' + ', '.join(sorted(required-valid)))
        cur.execute("SELECT status FROM user_triggers WHERE trigger_name='PF_TRANSACTION_BALANCE_TRG'")
        row = cur.fetchone()
        if not row or row[0] != 'ENABLED':
            raise RuntimeError('The transaction balance trigger must be enabled on the shared schema.')
        cur.execute('SELECT COUNT(*) FROM PF_USERS')
        users = cur.fetchone()[0]
        cur.execute('SELECT COUNT(*) FROM PF_TRANSACTION')
        transactions = cur.fetchone()[0]
    return users, transactions


def configure(args):
    current = dotenv_values(ENV)
    if args.local:
        if not BACKUP.exists():
            raise RuntimeError('No saved local configuration exists. The current connection was not changed.')
        shutil.copy2(BACKUP, ENV)
        set_key(str(ENV), 'ORACLE_MODE', 'local')
        load_dotenv(ENV, override=True)
        print('Restored the local Oracle configuration.')
        return
    host = args.host or input('Friend\'s reachable IP address or hostname: ').strip()
    if not host or any(c.isspace() for c in host) or any(c in host for c in '/?@'):
        raise ValueError('Enter just the database host/IP, without a URL, path or password.')
    if not 1 <= args.port <= 65535:
        raise ValueError('The port must be between 1 and 65535.')
    service = args.service or input('Oracle service name [FREEPDB1]: ').strip() or 'FREEPDB1'
    user = args.user or input('Shared project schema username [PF_DA2]: ').strip() or 'PF_DA2'
    if user.upper() in ('SYS', 'SYSTEM'):
        raise ValueError('Use the project schema account containing PF_ tables rather than an administrator login.')
    password = getpass.getpass('Shared project password (hidden): ')
    if not password:
        raise ValueError('A database password is required.')
    params = oracledb.ConnectParams(host=host, port=args.port, service_name=service, tcp_connect_timeout=8)
    print('Checking the shared project schema; no database records will be changed...', flush=True)
    with oracledb.connect(user=user, password=password, params=params) as conn:
        conn.call_timeout = 10000
        users, transactions = verify_schema(conn)
    print(f'Project schema verified: {users} users, {transactions} transactions.')
    BACKUP.parent.mkdir(exist_ok=True)
    if current.get('ORACLE_MODE', 'local') != 'remote' and not BACKUP.exists():
        shutil.copy2(ENV, BACKUP)
    # ConnectParams produces a supported descriptor including connection timeout.
    pending = BACKUP.parent / 'oracle-pending.env'
    shutil.copy2(ENV, pending)
    for name, value in dict(ORACLE_USER=user, ORACLE_PASSWORD=password,
                            ORACLE_DSN=params.get_connect_string(), ORACLE_MODE='remote').items():
        set_key(str(pending), name, value)
    pending.replace(ENV)
    load_dotenv(ENV, override=True)
    print('Shared Oracle selected. The original local database and its records are preserved.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host')
    parser.add_argument('--port', type=int, default=1521)
    parser.add_argument('--service')
    parser.add_argument('--user')
    parser.add_argument('--local', action='store_true')
    parser.add_argument('--no-start', action='store_true')
    options = parser.parse_args()
    try:
        configure(options)
        # A previously running Flask process must reload its saved configuration.
        from start_demo import stop_owned_server, start
        stop_owned_server()
        if not options.no_start:
            start()
    except (ValueError, RuntimeError, OSError, oracledb.Error) as exc:
        print('Connection setup failed:', exc)
        sys.exit(1)
