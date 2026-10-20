"""Local demo UI for Personal Finance DBMS DA2 (Oracle + Flask).

Start: pip install -r requirements.txt && python app.py
Never host this classroom admin interface on the public internet (no login/CSRF).
"""
import os
import json
import hashlib
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import oracledb
from dotenv import load_dotenv
from flask import Flask, flash, jsonify, redirect, render_template_string, request, url_for

ROOT = Path(__file__).parent
load_dotenv(ROOT / '.env')
app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'local-classroom-demo-only-change-me')

# The 11 DA1-to-relational-design tables. The audit table is read via Query Q12.
# (column, label, datatype, is_required, is_editable_after_creation)
TABLES = {
    'PF_HOUSEHOLD': ('Households', ('household_id',), [
        ('household_id', 'Household ID', 'int', True, False), ('name', 'Name', 'text', True, True)]),
    'PF_COMPANY': ('Companies', ('company_id',), [
        ('company_id', 'Company ID', 'int', True, False), ('name', 'Name', 'text', True, True),
        ('industry', 'Industry', 'text', True, True)]),
    'PF_BANK': ('Banks', ('bank_id',), [
        ('bank_id', 'Bank ID', 'int', True, False), ('name', 'Name', 'text', True, True),
        ('branch_code', 'Branch Code', 'text', True, True)]),
    'PF_CATEGORY': ('Categories', ('category_id',), [
        ('category_id', 'Category ID', 'int', True, False), ('name', 'Name', 'text', True, True)]),
    'PF_USERS': ('Users', ('user_id',), [
        ('user_id', 'User ID', 'int', True, False), ('name', 'Name', 'text', True, True),
        ('dob', 'Date of Birth', 'date', True, True),
        ('household_id', 'Household ID (FK)', 'int', True, True),
        ('employer_company_id', 'Employer Company ID (optional)', 'int', False, True)]),
    'PF_ACCOUNT': ('Accounts', ('account_id',), [
        ('account_id', 'Account ID', 'int', True, False),
        ('acc_type', 'Type: SAVINGS or CURRENT', 'text', True, True),
        ('balance', 'Opening Balance (set only at creation)', 'money', True, False),
        ('user_id', 'User ID (personal, or blank)', 'int', False, True),
        ('company_id', 'Company ID (corporate, or blank)', 'int', False, True),
        ('bank_id', 'Bank ID', 'int', True, True)]),
    'PF_SHARES': ('Shares', ('share_id',), [
        ('share_id', 'Share ID', 'int', True, False),
        ('company_id', 'Listed Company ID', 'int', True, True),
        ('market_price', 'Market Price', 'money', True, True)]),
    'PF_USER_SHARES': ('Share Ownership', ('user_id', 'share_id'), [
        ('user_id', 'User ID', 'int', True, False),
        ('share_id', 'Share ID', 'int', True, False),
        ('quantity', 'Quantity', 'int', True, True)]),
    'PF_SUBSCRIPTION': ('Subscriptions', ('account_id', 'subscription_id'), [
        ('account_id', 'Account ID', 'int', True, False),
        ('subscription_id', 'Subscription ID within account', 'int', True, False),
        ('name', 'Subscription Name', 'text', True, True),
        ('bill_cycle', 'Cycle: WEEKLY / MONTHLY / YEARLY', 'text', True, True),
        ('amount', 'Bill Amount', 'money', True, True)]),
    'PF_GOAL': ('Goals', ('goal_id',), [
        ('goal_id', 'Goal ID', 'int', True, False),
        ('account_id', 'Account ID', 'int', True, True),
        ('category_id', 'Category ID', 'int', True, True),
        ('current_amt', 'Current Goal Savings', 'money', True, True),
        ('target_amt', 'Target Savings', 'money', True, True)]),
    'PF_TRANSACTION': ('Transactions', ('trans_id',), [
        ('trans_id', 'Transaction ID', 'int', True, False),
        ('account_id', 'Account ID', 'int', True, True),
        ('category_id', 'Category ID', 'int', True, True),
        ('trans_date', 'Transaction Date', 'date', True, True),
        ('trans_type', 'Type: INCOME or EXPENSE', 'text', True, True),
        ('amount', 'Amount', 'money', True, True)]),
}

QUERIES = {x['id']: x for x in json.loads((ROOT / 'queries.json').read_text())}


def get_connection():
    user = os.environ.get('ORACLE_USER')
    password = os.environ.get('ORACLE_PASSWORD')
    dsn = os.environ.get('ORACLE_DSN')
    if not all([user, password, dsn]):
        raise RuntimeError('Configure ORACLE_USER, ORACLE_PASSWORD, and ORACLE_DSN in .env first')
    return oracledb.connect(user=user, password=password, dsn=dsn, tcp_connect_timeout=8)


def connection_id():
    """Identify the selected database without exposing its host or credentials."""
    return hashlib.sha256((os.getenv('ORACLE_DSN', '') + '\0' +
                           os.getenv('ORACLE_USER', '')).encode()).hexdigest()[:16]


def rows_to_dicts(cur):
    names = [d[0].lower() for d in cur.description]
    data = []
    for row in cur:
        data.append({k: (v.strftime('%Y-%m-%d') if isinstance(v, (date, datetime)) else v)
                     for k, v in zip(names, row)})
    return data


def convert(raw, kind, required):
    if raw is None or raw.strip() == '':
        if required:
            raise ValueError('A required field is empty')
        return None
    raw = raw.strip()
    if kind == 'int':
        return int(raw)
    if kind == 'money':
        try:
            value = Decimal(raw)
        except InvalidOperation as exc:
            raise ValueError('Enter a valid monetary amount') from exc
        if not value.is_finite():
            raise ValueError('Amount must be finite')
        return value
    if kind == 'date':
        return datetime.strptime(raw, '%Y-%m-%d')
    return raw


def table_meta(table):
    if table not in TABLES:
        raise ValueError('Table is not permitted')
    return TABLES[table]


def fetch_table(table):
    _, keys, fields = table_meta(table)
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Columns and table identifier are exclusively server-owned whitelist metadata.
            cur.execute('SELECT ' + ', '.join(f[0] for f in fields) + ' FROM ' + table +
                        ' ORDER BY ' + ', '.join(keys))
            return rows_to_dicts(cur)


PAGE = '''<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{{ title }} · Finance DA2</title>
<style>
:root{font-family:system-ui,-apple-system,Segoe UI,sans-serif;color:#183149;background:#f5f7fb}
body{margin:0}.bar{background:#10283d;color:#fff;padding:16px 4.2%;display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap}
.bar strong{font-size:19px}.bar a{color:#e9f4ff;text-decoration:none;margin-right:17px}
main{max-width:1280px;margin:28px auto;padding:0 20px}h1{font-size:27px;margin:0 0 10px}h2{font-size:19px}
.muted{color:#657789}.card{background:#fff;border:1px solid #e1e8f1;border-radius:13px;padding:22px;margin:16px 0;box-shadow:0 3px 13px #112c4510}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(215px,1fr));gap:14px}
.card a{color:#10548c;text-decoration:none}.cta,.btn{background:#146b99;color:white!important;display:inline-block;border:0;border-radius:8px;padding:10px 14px;cursor:pointer;text-decoration:none;font:inherit}
.btn-quiet{background:#e9f0f6;color:#19425b!important}.btn-del{background:#fff1f1;color:#a32929!important}
.tbl-wrap{width:100%;overflow:auto}table{width:100%;border-collapse:collapse;font-size:14px}th,td{padding:10px 12px;border-bottom:1px solid #e9eef5;text-align:left;white-space:nowrap}th{background:#f3f7fa;color:#3d5367}
form.inline{display:inline}fieldset{border:0;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}
label{display:block;font-size:14px;font-weight:600}input,select{width:100%;box-sizing:border-box;border:1px solid #cfd9e4;border-radius:7px;padding:10px;margin-top:6px;font:inherit}pre{white-space:pre-wrap;background:#172d3c;color:#e6f2fa;padding:18px;border-radius:9px;overflow:auto;font-size:13px}
.notice{border-left:4px solid #4b98c8;padding:12px 16px;background:#ebf4fc;margin:14px 0;border-radius:6px}.error{border-left-color:#b52433;background:#fdecee}
small{color:#6c7d8b}.actions{display:flex;gap:7px;align-items:center}.navlist a{margin:4px 7px 4px 0}
</style></head><body><div class="bar"><strong>◉ Personal Finance · DA2</strong><nav><a href="{{ url_for('home') }}">Dashboard</a><a href="{{ url_for('queries') }}">12 SQL Reports</a></nav></div>
<main><h1>{{ title }}</h1><p class="muted">Oracle Database • Flask frontend • Insert, update, delete, reports and PL/SQL trigger</p>
{% with messages=get_flashed_messages(with_categories=true) %}{% for category,message in messages %}<div class="notice {% if category=='error' %}error{% endif %}">{{ message }}</div>{% endfor %}{% endwith %}
{% if error %}<div class="notice error">{{ error }}</div>{% endif %}
{{ body|safe }}
<footer style="padding:22px 0;color:#728394;font-size:12px">Local classroom demonstration • Not a publicly deployed banking application</footer></main></body></html>'''


def display(title, body, **kwargs):
    return render_template_string(PAGE, title=title, body=body, error=kwargs.get('error'))


HOME = '''<div class="notice">Run the SQL setup first. Select any table to manage rows, then use <b>12 SQL Reports</b> to present your Oracle queries.</div>
<div class="grid">{% for t,label,n in counts %}<div class="card"><h2><a href="{{ url_for('table_page',table=t) }}">{{ label }}</a></h2><p><b>{{ n }}</b> records</p></div>{% endfor %}</div>'''


@app.get('/health')
def health():
    """Check that Flask is responding, even if Oracle is not configured yet."""
    return jsonify(status='ok', component='flask', message='Flask web server is running')


@app.get('/db-check')
def db_check():
    """Check Oracle connectivity separately from the web server."""
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA') FROM DUAL")
                schema = cur.fetchone()[0]
                cur.execute('SELECT COUNT(*) FROM PF_USERS')
                count = cur.fetchone()[0]
        return jsonify(status='ok', component='oracle', schema=schema, users=count,
                       connection_id=connection_id())
    except (oracledb.Error, RuntimeError) as exc:
        return jsonify(status='error', component='oracle', detail=str(exc)), 503


@app.get('/')
def home():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                counts = []
                for table, meta in TABLES.items():
                    cur.execute('SELECT COUNT(*) FROM ' + table)
                    counts.append((table, meta[0], cur.fetchone()[0]))
        return display('Project Dashboard', render_template_string(HOME, counts=counts))
    except (oracledb.Error, RuntimeError) as exc:
        return display('Project Dashboard', render_template_string(
            '<div class="notice">Set up Oracle and the .env file; then refresh the page.</div>') , error=str(exc))


TABLE_PAGE = '''<p><a class="cta" href="{{ url_for('add_record',table=table) }}">+ Add Record</a>
<a class="btn btn-quiet" href="{{ url_for('home') }}">← All Tables</a></p>
<div class="card"><div class="tbl-wrap"><table><thead><tr>{% for col in columns %}<th>{{ col }}</th>{% endfor %}<th>Actions</th></tr></thead>
<tbody>{% for r in records %}<tr>{% for col in columns %}<td>{{ r[col] if r[col] is not none else '—' }}</td>{% endfor %}
<td><div class="actions"><a class="btn btn-quiet" href="{{ url_for('edit_record',table=table, **keydata(r)) }}">Edit</a>
<form class="inline" method="post" action="{{ url_for('delete_record',table=table) }}" onsubmit="return confirm('Delete this record? Foreign-key rules may block deletion.');">
{% for key in keys %}<input type="hidden" name="{{ key }}" value="{{ r[key] }}">{% endfor %}<button class="btn btn-del" type="submit">Delete</button></form></div></td></tr>
{% endfor %}</tbody></table></div>{% if not records %}<p class="muted">No records yet.</p>{% endif %}</div>
<p class="muted">Foreign keys protect related records. For example, delete a transaction before deleting its account.</p>'''


@app.get('/table/<table>')
def table_page(table):
    try:
        label, keys, fields = table_meta(table)
        records = fetch_table(table)
        def keydata(r):
            return {k: r[k] for k in keys}
        body = render_template_string(TABLE_PAGE, table=table,
                                      keys=keys, records=records,
                                      columns=[f[0] for f in fields], keydata=keydata)
        return display(label + ' • View and Manage', body)
    except (ValueError, oracledb.Error, RuntimeError) as exc:
        return display('Table', '', error=str(exc)), 400


FORM = '''<div class="card"><form method="post"><fieldset>
{% for col,label,kind,required,canedit in fields %}
{% if not editing or canedit %}
<label>{{ label }}{% if required %} *{% endif %}
<input name="{{ col }}" type="{{ 'date' if kind=='date' else 'number' if kind in ['int','money'] else 'text' }}"
{% if kind=='money' %}step="0.01"{% elif kind=='int' %}step="1"{% endif %}
value="{{ record.get(col,'') if record.get(col) is not none else '' }}" {% if required %}required{% endif %}></label>
{% endif %}{% endfor %}</fieldset>
{% if editing %}{% for k in keys %}<input type="hidden" name="{{ k }}" value="{{ record[k] }}">{% endfor %}{% endif %}
<p><button type="submit" class="btn">{{ 'Save Changes' if editing else 'Insert Record' }}</button>
<a class="btn btn-quiet" href="{{ url_for('table_page',table=table) }}">Cancel</a></p></form></div>
{% if table=='PF_ACCOUNT' %}<div class="notice">Account balance is an opening balance when creating an account. For ordinary income and expenses, insert or edit a transaction; the PL/SQL trigger then changes the balance automatically.</div>{% endif %}'''


def form_values(table, editing):
    _, keys, fields = table_meta(table)
    return {col: convert(request.form.get(col), kind, required)
            for col, _label, kind, required, canedit in fields
            if (not editing or canedit)}


@app.route('/table/<table>/add', methods=['GET', 'POST'])
def add_record(table):
    try:
        label, _keys, fields = table_meta(table)
        if request.method == 'POST':
            values = form_values(table, editing=False)
            cols = list(values.keys())
            sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join(':'+c for c in cols)})"
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, values)
                conn.commit()
            flash('Record inserted successfully.', 'success')
            return redirect(url_for('table_page', table=table))
        body = render_template_string(FORM, table=table, fields=fields, keys=(),
                                      editing=False, record={})
        return display('Add • ' + label, body)
    except (ValueError, oracledb.Error, RuntimeError) as exc:
        flash(str(exc), 'error')
        return redirect(url_for('table_page', table=table))


def get_pk(table, source):
    _, keys, fields = table_meta(table)
    typemap = {f[0]: f[2] for f in fields}
    return {k: convert(source.get(k), typemap[k], True) for k in keys}


def pk_where(keys):
    return ' AND '.join(f'{k} = :pk_{k}' for k in keys)


@app.route('/table/<table>/edit', methods=['GET', 'POST'])
def edit_record(table):
    try:
        label, keys, fields = table_meta(table)
        pk = get_pk(table, request.form if request.method == 'POST' else request.args)
        binds = {'pk_' + k: v for k, v in pk.items()}
        if request.method == 'POST':
            values = form_values(table, editing=True)
            if not values:
                raise ValueError('This row contains no editable columns')
            update_sql = ('UPDATE ' + table + ' SET ' +
                          ', '.join(f'{k} = :{k}' for k in values) +
                          ' WHERE ' + pk_where(keys))
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(update_sql, {**values, **binds})
                    if cur.rowcount != 1:
                        raise ValueError('Record not found')
                conn.commit()
            flash('Record updated successfully.', 'success')
            return redirect(url_for('table_page', table=table))
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('SELECT ' + ', '.join(f[0] for f in fields) +
                            ' FROM ' + table + ' WHERE ' + pk_where(keys), binds)
                result = rows_to_dicts(cur)
        if not result:
            raise ValueError('Record not found')
        body = render_template_string(FORM, fields=fields, table=table, keys=keys,
                                      editing=True, record=result[0])
        return display('Edit • ' + label, body)
    except (ValueError, oracledb.Error, RuntimeError) as exc:
        flash(str(exc), 'error')
        return redirect(url_for('table_page', table=table))


@app.post('/table/<table>/delete')
def delete_record(table):
    try:
        _, keys, _fields = table_meta(table)
        pk = get_pk(table, request.form)
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('DELETE FROM ' + table + ' WHERE ' + pk_where(keys),
                            {'pk_' + k: v for k, v in pk.items()})
                if cur.rowcount != 1:
                    raise ValueError('Record not found')
            conn.commit()
        flash('Record deleted successfully.', 'success')
    except (ValueError, oracledb.Error, RuntimeError) as exc:
        flash(str(exc), 'error')
    return redirect(url_for('table_page', table=table))


REPORTS = '''<div class="card"><h2>Choose a SQL report</h2><div class="navlist">
{% for id,q in queries.items() %}<a class="btn {% if id!=selected %}btn-quiet{% endif %}" href="{{ url_for('queries',id=id) }}">{{ id }} · {{ q['title'] }}</a>{% endfor %}</div></div>
{% if chosen %}<div class="card"><h2>{{ chosen['id'] }} · {{ chosen['title'] }}</h2><pre>{{ chosen['sql'] }}</pre>
<div class="tbl-wrap"><table><thead><tr>{% for c in cols %}<th>{{ c }}</th>{% endfor %}</tr></thead>
<tbody>{% for r in results %}<tr>{% for c in cols %}<td>{{ r[c] if r[c] is not none else '—' }}</td>{% endfor %}</tr>{% endfor %}</tbody></table></div>
<p class="muted">{{ results|length }} row(s) returned by Oracle.</p></div>{% endif %}'''


@app.get('/queries')
def queries():
    choice = request.args.get('id', 'Q01')
    if choice not in QUERIES:
        return display('Queries', '', error='Unknown query ID'), 404
    chosen = QUERIES[choice]
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(chosen['sql'])
                result = rows_to_dicts(cur)
                cols = [d[0].lower() for d in cur.description]
        body = render_template_string(REPORTS, queries=QUERIES,
                                      chosen=chosen, results=result, cols=cols, selected=choice)
        return display('12 SQL Reports', body)
    except (oracledb.Error, RuntimeError) as exc:
        return display('12 SQL Reports', '', error=str(exc)), 500


if __name__ == '__main__':
    # Development server intended only for local classroom demonstration.
    app.run(host=os.environ.get('APP_HOST', '127.0.0.1'),
            port=int(os.environ.get('PORT', '5000')), debug=False)
