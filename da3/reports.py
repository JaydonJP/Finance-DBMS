"""Parameterized, inspectable Cypher reports used by the application and demo."""
REPORTS = [
('Q01','Household members and ages','Core',"""MATCH (u:User)-[:MEMBER_OF]->(h:Household)
RETURN h.name AS household, u.name AS member,
duration.between(u.dob,date()).years AS age ORDER BY household, member"""),
('Q02','Account owners and bank balances','Core',"""MATCH (o)-[:OWNS]->(a:Account)-[:HELD_AT]->(b:Bank)
RETURN a.account_id AS account_id, o.name AS owner, labels(o)[0] AS owner_type,
b.name AS bank, a.acc_type AS type, a.balance_paise/100.0 AS balance_rupees ORDER BY account_id"""),
('Q03','Investment portfolio value','Core',"""MATCH (u:User)-[h:HOLDS]->(s:Share)<-[:ISSUES]-(c:Company)
RETURN u.name AS investor, c.name AS company, s.share_id AS share_id,
h.quantity AS quantity, s.market_price_paise/100.0 AS price_rupees,
h.quantity*s.market_price_paise/100.0 AS value_rupees ORDER BY investor, company"""),
('Q04','Spending by category','Core',"""MATCH (t:Transaction)-[:IN_CATEGORY]->(c:Category)
WHERE t.trans_type='EXPENSE'
RETURN c.name AS category, count(t) AS transactions,
sum(t.amount_paise)/100.0 AS spent_rupees ORDER BY spent_rupees DESC"""),
('Q05','Accounts above average balance','Core',"""MATCH (a:Account) WITH avg(a.balance_paise) AS average
MATCH (a:Account) WHERE a.balance_paise>average
RETURN a.account_id AS account_id, a.balance_paise/100.0 AS balance_rupees ORDER BY balance_rupees DESC"""),
('Q06','Savings goal progress','Core',"""MATCH (a:Account)-[:HAS_GOAL]->(g:Goal)-[:IN_CATEGORY]->(c:Category)
RETURN g.goal_id AS goal_id, c.name AS goal, g.current_amt_paise/100.0 AS saved_rupees,
g.target_amt_paise/100.0 AS target_rupees,
round(100.0*g.current_amt_paise/g.target_amt_paise,2) AS progress_percent ORDER BY progress_percent DESC"""),
('Q07','Monthly subscription costs','Core',"""MATCH (a:Account)-[:HAS_SUBSCRIPTION]->(s:Subscription)
RETURN a.account_id AS account_id, count(s) AS subscriptions,
round(sum(CASE s.bill_cycle WHEN 'WEEKLY' THEN s.amount_paise*52.0/12
WHEN 'YEARLY' THEN s.amount_paise/12.0 ELSE s.amount_paise END)/100.0,2) AS monthly_rupees
ORDER BY monthly_rupees DESC"""),
('Q08','Company employee counts','Core',"""MATCH (c:Company) OPTIONAL MATCH (u:User)-[:WORKS_AT]->(c)
RETURN c.name AS company, count(u) AS employees ORDER BY employees DESC, company"""),
('Q09','Largest expense per account','Core',"""MATCH (a:Account)-[:HAS_TRANSACTION]->(t:Transaction)
WHERE t.trans_type='EXPENSE' WITH a,max(t.amount_paise) AS largest
MATCH (a)-[:HAS_TRANSACTION]->(t:Transaction)-[:IN_CATEGORY]->(c:Category)
WHERE t.trans_type='EXPENSE' AND t.amount_paise=largest
RETURN a.account_id AS account_id,t.trans_id AS trans_id,c.name AS category,
t.amount_paise/100.0 AS amount_rupees ORDER BY account_id,trans_id"""),
('Q10','Monthly income and expenses','Core',"""MATCH (u:User)-[:OWNS]->(:Account)-[:HAS_TRANSACTION]->(t:Transaction)
RETURN u.name AS member, substring(toString(t.trans_date),0,7) AS month,
sum(CASE t.trans_type WHEN 'INCOME' THEN t.amount_paise ELSE 0 END)/100.0 AS income_rupees,
sum(CASE t.trans_type WHEN 'EXPENSE' THEN t.amount_paise ELSE 0 END)/100.0 AS expenses_rupees
ORDER BY member,month"""),
('Q11','Total balances by bank','Core',"""MATCH (b:Bank) OPTIONAL MATCH (a:Account)-[:HELD_AT]->(b)
RETURN b.name AS bank,count(a) AS accounts,coalesce(sum(a.balance_paise),0)/100.0 AS total_rupees
ORDER BY total_rupees DESC"""),
('Q12','Transaction audit history','Core',"""MATCH (e:AuditEvent)
RETURN e.trans_id AS transaction_id,e.action AS action,
e.old_amount_paise/100.0 AS old_rupees,e.new_amount_paise/100.0 AS new_rupees,
e.old_account_id AS old_account,e.new_account_id AS new_account,
toString(e.changed_at) AS changed_at ORDER BY changed_at DESC"""),
('G01','Employer and investment overlap','Graph',"""MATCH (u:User)-[:WORKS_AT]->(c:Company)-[:ISSUES]->(s:Share)<-[h:HOLDS]-(u)
RETURN u.name AS member,c.name AS employer,s.share_id AS share_id,
h.quantity*s.market_price_paise/100.0 AS investment_rupees ORDER BY member"""),
('G02','Household exposure to companies','Graph',"""MATCH (h:Household)<-[:MEMBER_OF]-(u:User)-[holding:HOLDS]->(s:Share)<-[:ISSUES]-(c:Company)
RETURN h.name AS household,c.name AS company,collect(DISTINCT u.name) AS investors,
sum(holding.quantity*s.market_price_paise)/100.0 AS exposure_rupees
ORDER BY household,exposure_rupees DESC"""),
('G03','Shared investment connections','Graph',"""MATCH (u:User)-[:HOLDS]->(s:Share)<-[:HOLDS]-(v:User)
WHERE u.user_id<v.user_id
RETURN u.name AS member_one,v.name AS member_two,collect(s.share_id) AS shared_shares,
count(s) AS shared_count ORDER BY shared_count DESC,member_one,member_two"""),
]
REPORTS = {id:dict(id=id,title=title,group=group,cypher=cypher) for id,title,group,cypher in REPORTS}

GRAPH_QUERIES = {
    'all': 'MATCH p=(a)-[r]->(b) RETURN p LIMIT 100',
    'G01': 'MATCH p=(u:User)-[:WORKS_AT]->(c:Company)-[:ISSUES]->(s:Share)<-[:HOLDS]-(u) RETURN p',
    'G02': 'MATCH p=(:Household)<-[:MEMBER_OF]-(:User)-[:HOLDS]->(:Share)<-[:ISSUES]-(:Company) RETURN p',
    'G03': 'MATCH p=(u:User)-[:HOLDS]->(:Share)<-[:HOLDS]-(v:User) WHERE u.user_id<v.user_id RETURN p',
}
