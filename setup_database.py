"""Initialize only a fresh project schema; never reset existing demo data."""
import re

from app import ROOT, get_connection


def statements(text):
    buffer = []
    plsql = False
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith('--'):
            continue
        if not buffer:
            plsql = bool(re.match(
                r'CREATE OR REPLACE (TRIGGER|FUNCTION|PROCEDURE)\b', line, re.I))
        if plsql and line.strip() == '/':
            yield '\n'.join(buffer)
            buffer = []
        elif not plsql and line.rstrip().endswith(';'):
            buffer.append(line.rstrip()[:-1])
            yield '\n'.join(buffer)
            buffer = []
        else:
            buffer.append(line)
    if buffer:
        raise RuntimeError('Unterminated SQL statement')


def initialize():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM user_tables WHERE table_name LIKE 'PF_%'")
            count = cur.fetchone()[0]
            if count:
                if count != 12:
                    raise RuntimeError('Partial schema found. Inspect it before continuing; no data was reset.')
                print('Existing project database preserved.')
                return
            for filename in ('01_schema.sql', '03_plsql.sql', '02_seed.sql'):
                print('Loading', filename, flush=True)
                for sql in statements((ROOT / filename).read_text(encoding='utf-8')):
                    cur.execute(sql)
            cur.execute("SELECT name, line, text FROM user_errors WHERE name LIKE 'PF_%'")
            errors = cur.fetchall()
            if errors:
                raise RuntimeError(f'Oracle compilation errors: {errors}')
        conn.commit()
    print('Project schema, PL/SQL programs and sample records are ready.')


if __name__ == '__main__':
    initialize()
