"""Neo4j property graph and atomic finance operations. No Oracle dependency."""
import json
import os
from datetime import date
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from neo4j import GraphDatabase

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / '.env', override=True)
META = json.loads((ROOT / 'data/metadata.json').read_text(encoding='utf-8'))
LABELS = dict(household='Household', company='Company', bank='Bank', category='Category',
              users='User', account='Account', shares='Share', subscription='Subscription',
              goal='Goal', transaction='Transaction')
# field, target collection, relationship type, direction relative to subject
LINKS = {
    'users': [('household_id','household','MEMBER_OF','out'),
              ('employer_company_id','company','WORKS_AT','out')],
    'account': [('user_id','users','OWNS','in'), ('company_id','company','OWNS','in'),
                ('bank_id','bank','HELD_AT','out')],
    'shares': [('company_id','company','ISSUES','in')],
    'subscription': [('account_id','account','HAS_SUBSCRIPTION','in')],
    'goal': [('account_id','account','HAS_GOAL','in'), ('category_id','category','IN_CATEGORY','out')],
    'transaction': [('account_id','account','HAS_TRANSACTION','in'),
                    ('category_id','category','IN_CATEGORY','out')],
}


@lru_cache(maxsize=1)
def driver():
    password = os.getenv('NEO4J_PASSWORD')
    if not password:
        raise RuntimeError('Neo4j is not configured. Run setup.py first.')
    return GraphDatabase.driver(os.getenv('NEO4J_URI', 'bolt://127.0.0.1:7687'),
        auth=(os.getenv('NEO4J_USER', 'neo4j'), password), connection_timeout=5,
        connection_acquisition_timeout=10, max_transaction_retry_time=15,
        notifications_min_severity='OFF')


def session():
    return driver().session(database=os.getenv('NEO4J_DATABASE', 'neo4j'))


def read(query, **params):
    with session() as s:
        return s.execute_read(lambda tx: [dict(r) for r in tx.run(query, **params)])


def lock(tx):
    # One lock serializes classroom writes, including reference checks and deletes.
    # Incrementing a property takes a write lock before any balances are read.
    tx.run("MERGE (s:DemoState {key:'finance-da3'}) ON CREATE SET s.revision=0 "
           "SET s.revision=s.revision+1 RETURN s.revision").consume()


def write(callback, *args):
    with session() as s:
        def work(tx):
            lock(tx)
            return callback(tx, *args)
        return s.execute_write(work)


def money_columns(kind):
    return {f[0] for f in META[kind]['fields'] if f[2] == 'money'}


def prop(kind, column):
    return column + '_paise' if column in money_columns(kind) else column


def key_of(kind, values):
    return ':'.join(str(values[k]) for k in META[kind]['keys'])


def validate(kind, raw, editing=False):
    if kind not in META:
        raise ValueError('Unknown collection')
    values = {}
    for col, label, typ, required, editable in META[kind]['fields']:
        if editing and not editable and col not in META[kind]['keys']:
            continue
        value = raw.get(col)
        if value is None or str(value).strip() == '':
            if required:
                raise ValueError(label + ' is required')
            values[col] = None
            continue
        try:
            if typ == 'int':
                number = Decimal(str(value))
                if not number.is_finite() or number != number.to_integral_value() or number <= 0:
                    raise ValueError(label + ' must be a positive integer')
                values[col] = int(number)
                if values[col] > 999999999:
                    raise ValueError(label + ' is too large')
            elif typ == 'money':
                number = Decimal(str(value))
                if not number.is_finite() or abs(number) > Decimal('999999999999.99'):
                    raise ValueError(label + ' must be a finite monetary amount within range')
                if number * 100 != (number * 100).to_integral_value():
                    raise ValueError(label + ' can have at most two decimal places')
                values[col] = int(number * 100)
            elif typ == 'date':
                values[col] = date.fromisoformat(str(value))
            else:
                values[col] = str(value).strip()
                if len(values[col]) > 100:
                    raise ValueError(label + ' must be at most 100 characters')
        except (InvalidOperation, OverflowError) as exc:
            raise ValueError('Invalid value for ' + label) from exc
    for col in ('acc_type', 'bill_cycle', 'trans_type'):
        if col in values:
            values[col] = values[col].upper()
    if kind == 'account':
        if values['acc_type'] not in ('SAVINGS', 'CURRENT'):
            raise ValueError('Account type must be SAVINGS or CURRENT')
        if (values.get('user_id') is None) == (values.get('company_id') is None):
            raise ValueError('Choose exactly one owner: a user or a company')
        if not editing and values['balance'] < 0:
            raise ValueError('Opening balance cannot be negative')
    if kind == 'transaction':
        if values['trans_type'] not in ('INCOME', 'EXPENSE') or values['amount'] <= 0:
            raise ValueError('Use INCOME or EXPENSE and an amount greater than zero')
    if kind == 'subscription':
        if values['bill_cycle'] not in ('WEEKLY','MONTHLY','YEARLY') or values['amount'] <= 0:
            raise ValueError('Choose a valid billing cycle and positive amount')
    if kind == 'shares' and values['market_price'] < 0:
        raise ValueError('Market price cannot be negative')
    if kind == 'goal' and (values['target_amt'] <= 0 or values['current_amt'] < 0):
        raise ValueError('Target must be positive; current savings cannot be negative')
    if kind == 'users' and values['dob'] > date.today():
        raise ValueError('Date of birth cannot be in the future')
    return values


def select_query(kind, one=False):
    if kind == 'user_shares':
        return ("MATCH (u:User)-[h:HOLDS]->(s:Share) " +
                ("WHERE h.key=$key " if one else '') +
                "RETURN h.key AS _key, u.user_id AS user_id, s.share_id AS share_id, "
                "h.quantity AS quantity ORDER BY user_id, share_id")
    label = LABELS[kind]
    query = f'MATCH (n:{label}) ' + ('WHERE n.key=$key ' if one else '')
    references = {}
    for i, (col, target, rel, direction) in enumerate(LINKS.get(kind, [])):
        pattern = f'(n)-[:{rel}]->(r{i}:{LABELS[target]})' if direction == 'out' else f'(n)<-[:{rel}]-(r{i}:{LABELS[target]})'
        query += 'OPTIONAL MATCH ' + pattern + ' '
        references[col] = f'r{i}.{META[target]["keys"][0]}'
    projections = ['n.key AS _key']
    for col, *_ in META[kind]['fields']:
        projections.append(references.get(col, 'n.' + prop(kind, col)) + ' AS ' + col)
    return query + 'RETURN ' + ', '.join(projections) + ' ORDER BY ' + ', '.join(META[kind]['keys'])


def records(kind):
    return read(select_query(kind))


def one(tx, kind, key):
    result = tx.run(select_query(kind, True), key=key).single()
    if result is None:
        raise ValueError('Record not found')
    return dict(result)


def attach(tx, kind, key, values):
    label = LABELS[kind]
    for col, target, rel, direction in LINKS.get(kind, []):
        value = values.get(col)
        if value is None:
            continue
        if not tx.run(f'MATCH (t:{LABELS[target]} {{key:$key}}) RETURN t.key', key=str(value)).single():
            raise ValueError(f'{META[target]["title"]}: ID {value} does not exist')
        pattern = f'(n)-[:{rel}]->(t)' if direction == 'out' else f'(t)-[:{rel}]->(n)'
        tx.run(f'MATCH (n:{label} {{key:$key}}), (t:{LABELS[target]} {{key:$target}}) CREATE {pattern}',
               key=key, target=str(value)).consume()


def mutate_balance(tx, old, new):
    changes = {}
    for row, sign in ((old, -1), (new, 1)):
        if row:
            aid = row['account_id']
            delta = row['amount'] * (1 if row['trans_type'] == 'INCOME' else -1)
            changes[aid] = changes.get(aid, 0) + sign * delta
    for aid, delta in sorted(changes.items()):
        record = tx.run('MATCH (a:Account {account_id:$id}) RETURN a.balance_paise AS balance', id=aid).single()
        if record is None:
            raise ValueError(f'Account {aid} does not exist')
        if record['balance'] + delta < 0:
            raise ValueError('Insufficient balance: the change would overdraw account ' + str(aid))
        tx.run('MATCH (a:Account {account_id:$id}) SET a.balance_paise=a.balance_paise+$delta', id=aid, delta=delta).consume()


def audit(tx, old, new, action):
    row = new or old
    tx.run('CREATE (e:AuditEvent {key:$key, trans_id:$id, action:$action, '
           'old_amount_paise:$old, new_amount_paise:$new, old_account_id:$oa, '
           'new_account_id:$na, old_type:$ot, new_type:$nt, changed_at:datetime()})',
           key=str(uuid4()), id=row['trans_id'], action=action,
           old=old['amount'] if old else None, new=new['amount'] if new else None,
           oa=old['account_id'] if old else None, na=new['account_id'] if new else None,
           ot=old['trans_type'] if old else None, nt=new['trans_type'] if new else None).consume()


def save_tx(tx, kind, values, editing=False):
    key = key_of(kind, values)
    if kind == 'user_shares':
        existing = tx.run('MATCH ()-[h:HOLDS {key:$key}]->() RETURN h.key', key=key).single()
        if editing != bool(existing):
            raise ValueError('Record not found' if editing else 'This holding already exists')
        for col, target in [('user_id','User'), ('share_id','Share')]:
            if not tx.run(f'MATCH (n:{target} {{key:$key}}) RETURN n.key', key=str(values[col])).single():
                raise ValueError(col + ' does not exist')
        tx.run('MATCH (u:User {user_id:$user_id}), (s:Share {share_id:$share_id}) '
               'MERGE (u)-[h:HOLDS {key:$key}]->(s) SET h.quantity=$quantity', key=key, **values).consume()
        return key
    label = LABELS[kind]
    exists = tx.run(f'MATCH (n:{label} {{key:$key}}) RETURN n.key', key=key).single()
    if editing != bool(exists):
        raise ValueError('Record not found' if editing else 'That ID already exists')
    old = one(tx, kind, key) if editing else None
    if kind == 'category':
        if tx.run('MATCH (c:Category {name:$name}) WHERE c.key<>$key RETURN c.key', name=values['name'], key=key).single():
            raise ValueError('Category name must be unique')
    if kind == 'transaction':
        mutate_balance(tx, old, values)
    if editing:
        # Remove only the subject's model-owned foreign-key relationships.
        for col, target, rel, direction in LINKS.get(kind, []):
            pattern = f'(n)-[r:{rel}]->(:{LABELS[target]})' if direction == 'out' else f'(n)<-[r:{rel}]-(:{LABELS[target]})'
            tx.run(f'MATCH (n:{label} {{key:$key}}) MATCH {pattern} DELETE r', key=key).consume()
    links = {r[0] for r in LINKS.get(kind, [])}
    properties = {prop(kind, k): v for k, v in values.items() if k not in links}
    properties['key'] = key
    if kind == 'account' and not editing:
        properties['opening_balance_paise'] = values['balance']
    command = 'MATCH' if editing else 'CREATE'
    if editing:
        tx.run(f'MATCH (n:{label} {{key:$key}}) SET n += $props', key=key, props=properties).consume()
    else:
        tx.run(f'CREATE (n:{label}) SET n = $props', props=properties).consume()
    attach(tx, kind, key, values)
    if kind == 'transaction':
        audit(tx, old, values, 'UPDATE' if editing else 'INSERT')
    return key


def save(kind, raw, editing=False):
    values = validate(kind, raw, editing)
    return write(save_tx, kind, values, editing)


def delete_tx(tx, kind, key):
    old = one(tx, kind, key)
    if kind == 'user_shares':
        tx.run('MATCH ()-[h:HOLDS {key:$key}]->() DELETE h', key=key).consume()
        return
    # Restrict deletion if another record references this subject.
    for source, links in LINKS.items():
        for col, target, rel, direction in links:
            if target != kind:
                continue
            pattern = f'(n)<-[:{rel}]-(:{LABELS[source]})' if direction == 'out' else f'(n)-[:{rel}]->(:{LABELS[source]})'
            if tx.run(f'MATCH (n:{LABELS[kind]} {{key:$key}}) MATCH {pattern} RETURN n.key LIMIT 1', key=key).single():
                raise ValueError('Delete dependent ' + META[source]['title'].lower() + ' first')
    if kind in ('users','shares'):
        if tx.run(f'MATCH (n:{LABELS[kind]} {{key:$key}})-[:HOLDS]-() RETURN n.key LIMIT 1', key=key).single():
            raise ValueError('Delete this record\'s share holdings first')
    if kind == 'transaction':
        mutate_balance(tx, old, None)
        audit(tx, old, None, 'DELETE')
    tx.run(f'MATCH (n:{LABELS[kind]} {{key:$key}}) DETACH DELETE n', key=key).consume()


def delete(kind, key):
    if kind not in META:
        raise ValueError('Unknown collection')
    return write(delete_tx, kind, key)


def initialize():
    with session() as s:
        for label in [*LABELS.values(), 'AuditEvent', 'DemoState']:
            s.run(f'CREATE CONSTRAINT {label.lower()}_key IF NOT EXISTS FOR (n:{label}) REQUIRE n.key IS UNIQUE').consume()
        s.run('CREATE CONSTRAINT category_name IF NOT EXISTS FOR (n:Category) REQUIRE n.name IS UNIQUE').consume()
        s.run('CREATE CONSTRAINT holding_key IF NOT EXISTS FOR ()-[h:HOLDS]-() REQUIRE h.key IS UNIQUE').consume()
        s.run('CREATE INDEX transaction_date IF NOT EXISTS FOR (t:Transaction) ON (t.trans_date)').consume()
    fixture = json.loads((ROOT / 'data/sample.json').read_text(encoding='utf-8'))
    def seed(tx):
        state = tx.run("MATCH (s:DemoState {key:'finance-da3'}) RETURN s.seeded AS seeded").single()
        if state and state['seeded']:
            return False
        count = tx.run('MATCH (n) WHERE NOT n:DemoState RETURN count(n) AS count').single()['count']
        if count:
            raise ValueError('Uninitialized database contains records; refusing to overwrite them')
        for kind, rows in fixture.items():
            for raw in rows:
                save_tx(tx, kind, validate(kind, raw))
        tx.run("MATCH (s:DemoState {key:'finance-da3'}) SET s.seeded=true, s.seed_version=1").consume()
        return True
    return write(seed)


def graph_data(household=None):
    # The graph contains domain entities, not password/configuration state.
    if household:
        query = ('MATCH (h:Household {household_id:$id})<-[:MEMBER_OF]-(u:User) '
                 'MATCH p=(u)-[*0..3]-(n) WHERE NONE(x IN nodes(p) WHERE x:DemoState OR x:AuditEvent) '
                 'UNWIND relationships(p) AS r RETURN DISTINCT startNode(r) AS a, r, endNode(r) AS b LIMIT 200')
        rows = read(query, id=int(household))
    else:
        rows = read('MATCH (a)-[r]->(b) WHERE NOT a:DemoState AND NOT b:DemoState '
                    'RETURN a,r,b LIMIT 300')
    nodes, edges = {}, {}
    for row in rows:
        for node in (row['a'], row['b']):
            label = next(iter(node.labels))
            nodes[node.element_id] = dict(id=node.element_id, label=label,
                name=str(node.get('name', label + ' ' + str(node.get('key', '')))),
                properties={k:str(v) for k,v in dict(node).items()})
        rel = row['r']
        edges[rel.element_id] = dict(id=rel.element_id, source=row['a'].element_id,
            target=row['b'].element_id, type=rel.type,
            properties={k:str(v) for k,v in dict(rel).items()})
    if not household:
        for row in read('MATCH (n) WHERE NOT n:DemoState AND NOT n:AuditEvent RETURN n LIMIT 300'):
            node=row['n']
            label=next(iter(node.labels))
            nodes[node.element_id]=dict(id=node.element_id,label=label,
                name=str(node.get('name',label+' '+str(node.get('key','')))),
                properties={k:str(v) for k,v in dict(node).items()})
    return dict(nodes=list(nodes.values()), edges=list(edges.values()))


def reconciliation():
    return read('MATCH (a:Account) OPTIONAL MATCH (a)-[:HAS_TRANSACTION]->(t:Transaction) '
        'WITH a, coalesce(sum(CASE t.trans_type WHEN \'INCOME\' THEN t.amount_paise ELSE -t.amount_paise END),0) AS delta '
        'RETURN a.account_id AS account_id, a.balance_paise AS actual_paise, '
        'a.opening_balance_paise+delta AS expected_paise ORDER BY account_id')
