"""Integration checks against the real local Neo4j database; cleans test records."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone,timedelta
from decimal import Decimal
import json
import time

import database as db
from app import app
from reports import REPORTS


def verify():
    started=time.monotonic()
    checks=[]
    def passed(name,detail):
        checks.append(dict(name=name,status='PASS',detail=detail))
        print('PASS:',name,flush=True)
    def must_fail(call):
        try:
            call()
        except ValueError:
            return
        raise AssertionError('Invalid operation was accepted')
    def balance(id):
        return db.read('MATCH (a:Account {account_id:$id}) RETURN a.balance_paise AS amount',id=id)[0]['amount']
    baseline={k:len(db.records(k)) for k in db.META}
    assert baseline=={k:len(v) for k,v in json.loads((db.ROOT/'data/sample.json').read_text()).items()},baseline
    assert balance(1001)==6680000
    assert all(r['actual_paise']==r['expected_paise'] for r in db.reconciliation())
    before_graph=db.graph_data()
    assert len(before_graph['nodes'])==57 and len(before_graph['edges'])==72
    passed('Standalone sample import and reconciliation','57 business nodes, 72 relationships, 12 ledger records; account 1001 = INR 66800.00')
    assert db.initialize() is False
    assert {k:len(db.records(k)) for k in db.META}==baseline
    assert balance(1001)==6680000
    passed('Repeat import preserves data','No duplicate nodes/relationships or repeated balance effects')

    app.testing=True
    client=app.test_client()
    for path in ['/','/graph','/about','/health','/db-check']:
        assert client.get(path).status_code==200,path
    for kind in db.META:
        for path in [f'/records/{kind}',f'/records/{kind}/new']:
            assert client.get(path).status_code==200,path
    assert client.get('/records/not-real').status_code==404
    assert client.get('/reports?id=invalid').status_code==404
    assert client.post('/records/users/new',data={}).status_code==400
    with client.session_transaction() as s:
        csrf=s['csrf']
    passed('Web pages and CSRF protection','All 11 collection pages and forms return 200; unknown resources and missing CSRF are rejected')

    report_results={}
    for id,report in REPORTS.items():
        rows=db.read(report['cypher'])
        assert rows,id
        assert client.get('/reports?id='+id).status_code==200,id
        assert client.get('/reports/'+id+'/download').status_code==200,id
        report_results[id]=rows
    assert len(report_results['G01'])==4
    assert len(report_results['G02'])==4
    assert len(report_results['G03'])==2
    assert sum(r['spent_rupees'] for r in report_results['Q04'])==79700
    for insight in ['G01','G02','G03']:
        graph=client.get('/api/graph?insight='+insight).json
        assert graph['nodes'] and graph['edges'],insight
    assert client.get('/api/graph?household=1').json['nodes']
    assert client.get('/api/graph?household=invalid').status_code==400
    passed('All 15 Cypher reports and graph APIs','12 core reports, 3 graph insights; G01=4 rows, G02=4 rows, G03=2 rows; expense total INR 79700')

    # Use reserved temporary IDs and abort if the local store already uses them.
    for kind in db.META:
        assert all(not r['_key'].startswith('980') for r in db.records(kind)),'Reserved test ID is in use'
    txids=[980901,980902,980903,980904,980905]
    created=[]
    sample={
        'household':dict(household_id=980001,name='Temporary Verify Household'),
        'company':dict(company_id=980201,name='Temporary Verify Company',industry='Testing'),
        'bank':dict(bank_id=980001,name='Temporary Verify Bank',branch_code='TEST'),
        'category':dict(category_id=980001,name='Temporary Verify Category'),
        'users':dict(user_id=980101,name='Temporary Verify User',dob='2004-01-15',household_id=980001,employer_company_id=980201),
        'account':dict(account_id=980001,acc_type='SAVINGS',balance='1000',user_id=980101,company_id='',bank_id=980001),
        'shares':dict(share_id=980301,company_id=980201,market_price='25.50'),
        'user_shares':dict(user_id=980101,share_id=980301,quantity=2),
        'subscription':dict(account_id=980001,subscription_id=1,name='Temporary Verify Subscription',bill_cycle='MONTHLY',amount=10),
        'goal':dict(goal_id=980401,account_id=980001,category_id=980001,current_amt=10,target_amt=100),
        'transaction':dict(trans_id=980901,account_id=980001,category_id=980001,trans_date='2026-10-20',trans_type='EXPENSE',amount=20),
    }
    try:
        for kind,raw in sample.items():
            response=client.post(f'/records/{kind}/new',data={**raw,'csrf':csrf},follow_redirects=True)
            assert b'Record created.' in response.data,(kind,response.data[:150])
            key=db.key_of(kind,raw)
            created.append((kind,key))
            assert client.get(f'/records/{kind}/{key}/edit').status_code==200
            response=client.post(f'/records/{kind}/{key}/edit',data={**raw,'csrf':csrf},follow_redirects=True)
            assert b'Changes saved.' in response.data,kind
        passed('CRUD across all 11 collections','All create and edit forms persist against Neo4j, including HOLDS relationship properties')
        must_fail(lambda:db.save('users',sample['users']))
        must_fail(lambda:db.delete('users','980101'))
        for value in ['NaN','Infinity','1.001','-1','0']:
            must_fail(lambda value=value:db.save('transaction',{**sample['transaction'],'trans_id':980902,'amount':value}))
        must_fail(lambda:db.save('account',{**sample['account'],'account_id':980002,'company_id':980201}))
        passed('Validation and restricted deletion','Duplicate IDs, non-finite/negative/zero/overprecision amounts, dual owners and referenced-user deletion are rejected')
        initial=balance(1001)
        raw=dict(trans_id=980902,account_id=1001,category_id=2,trans_date='2026-10-20',trans_type='EXPENSE',amount=250)
        db.save('transaction',raw);created.append(('transaction','980902'))
        assert balance(1001)==initial-25000
        db.save('transaction',{**raw,'amount':300},True)
        assert balance(1001)==initial-30000
        db.save('transaction',{**raw,'amount':500,'trans_type':'INCOME'},True)
        assert balance(1001)==initial+50000
        other=balance(1002)
        db.save('transaction',{**raw,'account_id':1002,'amount':50},True)
        assert balance(1001)==initial and balance(1002)==other-5000
        db.delete('transaction','980902');created.remove(('transaction','980902'))
        assert balance(1002)==other
        audit=db.read('MATCH (e:AuditEvent {trans_id:980902}) RETURN e.action AS action')
        assert len(audit)==5 and sum(r['action']=='DELETE' for r in audit)==1
        passed('Ledger lifecycle and permanent audit','Expense 250 -> expense 300 -> income 500 -> move to another account -> delete; both balances restored and 5 audit snapshots retained')
        before=balance(1001)
        audit_before=db.read('MATCH (e:AuditEvent) RETURN count(e) AS count')[0]['count']
        must_fail(lambda:db.save('transaction',{**raw,'amount':'999999999','trans_id':980903}))
        must_fail(lambda:db.save('transaction',{**raw,'category_id':999999,'trans_id':980903}))
        assert balance(1001)==before
        assert db.read('MATCH (e:AuditEvent) RETURN count(e) AS count')[0]['count']==audit_before
        passed('Atomic rollback','Overspending and a missing category leave balances, transactions and audit counts unchanged')
        # Account 980001 has 980 rupees after the 20-rupee test expense.
        def spend(id):
            try:
                db.save('transaction',{**raw,'account_id':980001,'trans_id':id,'amount':700})
                return id
            except ValueError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(spend,[980904,980905]))
        winners=[id for id in results if id]
        for id in winners:
            created.append(('transaction',str(id)))
        assert len(winners)==1 and balance(980001)==28000
        passed('Concurrent overspending protection','Two simultaneous INR 700 expenses against INR 980: exactly one commits; final balance INR 280')
    finally:
        for kind,key in reversed(created):
            db.delete(kind,key)
        db.write(lambda tx:tx.run('MATCH (e:AuditEvent) WHERE e.trans_id IN $ids DELETE e',ids=txids).consume())
    assert {k:len(db.records(k)) for k in db.META}==baseline
    assert all(r['actual_paise']==r['expected_paise'] for r in db.reconciliation())
    passed('Cleanup and final reconciliation','Temporary records removed in dependency order; original sample dataset and balances retained')
    evidence=dict(status='PASS',tested_at=datetime.now(timezone(timedelta(hours=5,minutes=30))).isoformat(),
        duration_seconds=round(time.monotonic()-started,2),database='Neo4j Community 2026.09.0',
        checks=checks,counts=baseline,reports=report_results,reconciliation=db.reconciliation())
    out=db.ROOT/'submission/verification.json'
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(evidence,indent=2,default=str),encoding='utf-8')
    print('ALL CHECKS PASSED:',len(checks),'groups. Evidence:',out)


if __name__=='__main__':
    verify()
