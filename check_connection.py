"""Oracle-only smoke check; run after populating the schema, before Flask."""
import os
from pathlib import Path

import oracledb
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / '.env')
username = os.getenv('ORACLE_USER')
password = os.getenv('ORACLE_PASSWORD')
dsn = os.getenv('ORACLE_DSN')
if not all((username, password, dsn)):
    raise SystemExit('Missing ORACLE_USER / ORACLE_PASSWORD / ORACLE_DSN in .env')

print('Attempting Oracle connection to:', dsn)
try:
    with oracledb.connect(user=username, password=password, dsn=dsn) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT SYS_CONTEXT('USERENV','CURRENT_SCHEMA') FROM DUAL")
            print('Connected schema:', cur.fetchone()[0])
            cur.execute('SELECT COUNT(*) FROM PF_USERS')
            print('PF_USERS rows:', cur.fetchone()[0])
            cur.execute('SELECT COUNT(*) FROM PF_TRANSACTION')
            print('PF_TRANSACTION rows:', cur.fetchone()[0])
            cur.execute('SELECT balance FROM PF_ACCOUNT WHERE account_id=1001')
            print('Account 1001 balance:', cur.fetchone()[0])
    print('SUCCESS: Oracle connectivity and seeded project tables verified.')
except oracledb.Error as exc:
    raise SystemExit(f'FAILED Oracle connection or setup: {exc}')
