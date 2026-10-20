"""Check the real Oracle-backed demo. Temporary test records are cleaned up."""
from datetime import date
from decimal import Decimal

import oracledb

from app import app, get_connection, QUERIES, TABLES


def verify():
    app.testing = True
    client = app.test_client()
    for path in ('/', '/health', '/db-check'):
        response = client.get(path)
        assert response.status_code == 200, (path, response.status_code)
    for table in TABLES:
        for suffix in ('', '/add'):
            response = client.get('/table/' + table + suffix)
            assert response.status_code == 200, table
            assert b'ORA-' not in response.data, table
    for query in QUERIES:
        response = client.get('/queries?id=' + query)
        assert response.status_code == 200, query
        assert b'ORA-' not in response.data, query
    print('PASS: dashboard, database health, 11 table pages/forms and all 12 SQL reports')

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT object_name FROM user_objects WHERE object_name LIKE 'PF_%' AND status <> 'VALID'")
            assert not cur.fetchall(), 'Invalid Oracle objects'
            cur.execute('SELECT PF_GOAL_PROGRESS(401) FROM DUAL')
            assert cur.fetchone()[0] == 20
            cur.execute('SELECT balance FROM PF_ACCOUNT WHERE account_id=1001')
            opening = Decimal(str(cur.fetchone()[0]))
            cur.execute('SELECT NVL(MAX(trans_id),0)+1 FROM PF_TRANSACTION')
            tx = int(cur.fetchone()[0])
            try:
                cur.execute('INSERT INTO PF_TRANSACTION VALUES (:id,1001,2,:dt,\'EXPENSE\',250)',
                            dict(id=tx, dt=date(2026, 10, 20)))
                cur.execute('SELECT balance FROM PF_ACCOUNT WHERE account_id=1001')
                assert Decimal(str(cur.fetchone()[0])) == opening - 250
                cur.execute('UPDATE PF_TRANSACTION SET amount=300 WHERE trans_id=:id', dict(id=tx))
                cur.execute('SELECT balance FROM PF_ACCOUNT WHERE account_id=1001')
                assert Decimal(str(cur.fetchone()[0])) == opening - 300
                cur.execute('DELETE FROM PF_TRANSACTION WHERE trans_id=:id', dict(id=tx))
                cur.execute('SELECT balance FROM PF_ACCOUNT WHERE account_id=1001')
                assert Decimal(str(cur.fetchone()[0])) == opening
                cur.execute('SELECT action_name FROM PF_TRANS_AUDIT WHERE trans_id=:id ORDER BY audit_id', dict(id=tx))
                assert [r[0] for r in cur.fetchall()] == ['INSERT', 'UPDATE', 'DELETE']
                try:
                    cur.execute('INSERT INTO PF_TRANSACTION VALUES (:id,1001,2,:dt,\'EXPENSE\',:amount)',
                                dict(id=tx, dt=date(2026, 10, 20), amount=opening+1))
                except oracledb.IntegrityError:
                    pass
                else:
                    raise AssertionError('Overspending was allowed')
                result = cur.var(oracledb.NUMBER)
                cur.callproc('PF_ADD_TRANSACTION', [1001, 2, 'EXPENSE', 10, result])
                assert result.getvalue() is not None
                cur.callproc('DBMS_OUTPUT.ENABLE')
                cur.callproc('PF_PRINT_ACCOUNT_HISTORY', [1001])
                line, status = cur.var(str, size=32767), cur.var(int)
                cur.callproc('DBMS_OUTPUT.GET_LINE', [line, status])
                assert status.getvalue() == 0 and line.getvalue().startswith('TX ')
            finally:
                conn.rollback()
    print('PASS: valid PL/SQL objects, goal function, transaction procedure and history cursor')
    print('PASS: transaction insert/update/delete balances, audit trigger, overspending rejection (rolled back)')

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT NVL(MAX(user_id),0)+1 FROM PF_USERS')
            user_id = int(cur.fetchone()[0])
    payload = dict(user_id=str(user_id), name='Temporary Demo Check', dob='2004-01-15',
                   household_id='3', employer_company_id='')
    try:
        response = client.post('/table/PF_USERS/add', data=payload, follow_redirects=True)
        assert b'Record inserted successfully.' in response.data
        payload['name'] = 'Temporary Demo Check Updated'
        response = client.post('/table/PF_USERS/edit', data=payload, follow_redirects=True)
        assert b'Record updated successfully.' in response.data
        response = client.post('/table/PF_USERS/delete', data=dict(user_id=user_id), follow_redirects=True)
        assert b'Record deleted successfully.' in response.data
    finally:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM PF_USERS WHERE user_id=:id AND name LIKE \'Temporary Demo Check%\'', dict(id=user_id))
            conn.commit()
    print('PASS: web form insert, edit and delete; temporary user removed')
    print('ALL DEMO CHECKS PASSED')


if __name__ == '__main__':
    verify()
