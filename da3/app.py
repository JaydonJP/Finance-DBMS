"""DA3 local finance UI. All live records come from Neo4j."""
import csv
import io
import os
import secrets
from decimal import Decimal

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for
from neo4j.exceptions import Neo4jError, ServiceUnavailable
import database as db
from reports import REPORTS, GRAPH_QUERIES

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY') or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_SAMESITE='Lax', MAX_CONTENT_LENGTH=256*1024)


@app.template_filter('rupees')
def rupees(value):
    return '\u20b9' + format(Decimal(value or 0)/100, ',.2f')


@app.template_filter('cell')
def cell(value):
    if value is None:
        return '\u2014'
    if isinstance(value, list):
        return ', '.join(str(x) for x in value)
    if isinstance(value,float):
        return format(value, ',.2f')
    return str(value)


@app.context_processor
def shared():
    if 'csrf' not in session:
        session['csrf'] = secrets.token_hex(24)
    return dict(meta=db.META, csrf=session['csrf'], reports=REPORTS)


@app.before_request
def protect():
    if request.method == 'POST' and not secrets.compare_digest(session.get('csrf','missing'),request.form.get('csrf','')):
        abort(400, 'The form expired. Refresh the page and try again.')


@app.get('/health')
def health():
    return jsonify(status='ok', component='flask', project='finance-da3')


@app.get('/db-check')
def db_check():
    try:
        counts = db.read('MATCH (n) WHERE NOT n:DemoState RETURN count(n) AS nodes')
        return jsonify(status='ok',component='neo4j',nodes=counts[0]['nodes'])
    except (Neo4jError, OSError, RuntimeError) as exc:
        return jsonify(status='error',component='neo4j',detail=str(exc)),503


@app.get('/')
def home():
    metrics = db.read('MATCH (a:Account) RETURN sum(a.balance_paise) AS balance,count(a) AS accounts')[0]
    metrics.update(db.read('MATCH (t:Transaction) RETURN count(t) AS transactions, '
        "sum(CASE t.trans_type WHEN 'EXPENSE' THEN t.amount_paise ELSE 0 END) AS expenses")[0])
    counts = {kind:len(db.records(kind)) for kind in db.META}
    expenses = db.read(REPORTS['Q04']['cypher'])
    return render_template('home.html', title='Financial overview', metrics=metrics, counts=counts,
                           expenses=expenses, accounts=db.read(REPORTS['Q02']['cypher']))


def collection(kind):
    if kind not in db.META:
        abort(404)
    return db.META[kind]


@app.get('/records/<kind>')
def records(kind):
    model = collection(kind)
    return render_template('records.html', title=model['title'],kind=kind,model=model,rows=db.records(kind))


def options_for(kind):
    options = {}
    targets = {col:target for col,target,*_ in db.LINKS.get(kind,[])}
    if kind == 'user_shares':
        targets = dict(user_id='users',share_id='shares')
    for col,target in targets.items():
        key = db.META[target]['keys'][0]
        options[col] = [(row[key], str(row[key])+' \u00b7 '+str(row.get('name',db.META[target]['title']))) for row in db.records(target)]
    for col,values in dict(acc_type=['SAVINGS','CURRENT'],trans_type=['INCOME','EXPENSE'],bill_cycle=['WEEKLY','MONTHLY','YEARLY']).items():
        options[col] = [(v,v) for v in values]
    return options


@app.route('/records/<kind>/new',methods=['GET','POST'])
@app.route('/records/<kind>/<key>/edit',methods=['GET','POST'])
def form(kind,key=None):
    model = collection(kind)
    row = {}
    if key is not None:
        with db.session() as s:
            try:
                row = s.execute_read(db.one,kind,key)
            except ValueError:
                abort(404)
        for col in db.money_columns(kind):
            if col in row:
                row[col] = format(Decimal(row[col])/100,'.2f')
    if request.method == 'POST':
        raw = request.form.to_dict()
        if key:
            # Primary keys come from the selected record, never editable POST fields.
            for col in model['keys']:
                raw[col] = row[col]
        try:
            db.save(kind,raw,editing=key is not None)
            flash('Changes saved.' if key else 'Record created.','success')
            return redirect(url_for('records',kind=kind))
        except (ValueError,Neo4jError) as exc:
            flash(str(exc) if isinstance(exc,ValueError) else 'The record conflicts with a database constraint.','error')
            row.update(raw)
    return render_template('form.html',title=('Edit ' if key else 'Add ')+model['title'],
        kind=kind,model=model,row=row,editing=key is not None,options=options_for(kind))


@app.post('/records/<kind>/<key>/delete')
def delete(kind,key):
    collection(kind)
    try:
        db.delete(kind,key)
        flash('Record deleted.','success')
    except (ValueError,Neo4jError) as exc:
        flash(str(exc) if isinstance(exc,ValueError) else 'The database could not delete this record.','error')
    return redirect(url_for('records',kind=kind))


@app.get('/reports')
def reports_page():
    selected = request.args.get('id','G01')
    if selected not in REPORTS:
        abort(404)
    report = REPORTS[selected]
    rows = db.read(report['cypher'])
    return render_template('reports.html',title='Reports and insights',selected=selected,
                           report=report,rows=rows,graph_query=GRAPH_QUERIES.get(selected))


@app.get('/reports/<id>/download')
def download(id):
    if id not in REPORTS:
        abort(404)
    rows = db.read(REPORTS[id]['cypher'])
    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return app.response_class(output.getvalue(),mimetype='text/csv',
        headers={'Content-Disposition':f'attachment; filename="{id}.csv"'})


@app.get('/graph')
def graph():
    return render_template('graph.html',title='Explore your financial connections',
        households=db.records('household'),graph_queries=GRAPH_QUERIES)


@app.get('/api/graph')
def api_graph():
    choice = request.args.get('insight')
    if choice in ('G01','G02','G03'):
        query = GRAPH_QUERIES[choice].replace('RETURN p','UNWIND relationships(p) AS r RETURN DISTINCT startNode(r) AS a,r,endNode(r) AS b')
        rows = db.read(query)
        nodes,edges = {},{}
        for row in rows:
            for n in (row['a'],row['b']):
                label = next(iter(n.labels))
                nodes[n.element_id]=dict(id=n.element_id,label=label,name=str(n.get('name',label+' '+n.get('key',''))),properties={k:str(v) for k,v in dict(n).items()})
            r=row['r']
            edges[r.element_id]=dict(id=r.element_id,source=row['a'].element_id,target=row['b'].element_id,type=r.type,properties={k:str(v) for k,v in dict(r).items()})
        return jsonify(nodes=list(nodes.values()),edges=list(edges.values()))
    try:
        return jsonify(db.graph_data(request.args.get('household')))
    except ValueError:
        abort(400,'Household must be a numeric ID')


@app.get('/about')
def about():
    return render_template('about.html',title='From relational tables to connected data')


@app.errorhandler(ServiceUnavailable)
@app.errorhandler(RuntimeError)
def unavailable(error):
    return render_template('error.html',title='Database unavailable',message='Start the DA3 demo launcher, then refresh this page.'),503


if __name__ == '__main__':
    from waitress import serve
    serve(app,host=os.getenv('APP_HOST','127.0.0.1'),port=int(os.getenv('PORT','5001')),threads=6)
