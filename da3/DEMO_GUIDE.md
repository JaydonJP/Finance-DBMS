# DA3 presentation guide

Start **Finance Graph DA3** from the desktop. Open http://127.0.0.1:5001/.
The application works independently of Oracle after Neo4j has started.

## Five to seven minute presentation

1. **Overview:** explain that DA2 used Oracle; DA3 models the same domain in
   Neo4j Community, a graph database. Show 7 accounts, 12 transactions, 5 users,
   total balance INR 435300 and expenses INR 79700.
2. **Graph explorer:** select Employer and investment overlap. Select Meera Singh
   or Arun Kumar to inspect a User node. Enable relationship names and follow
   WORKS_AT, ISSUES and HOLDS. Explain that quantity belongs to HOLDS.
3. **Users:** Add user 106, Demo Student, DOB 2004-01-15, household 3, employer
   blank. Edit the name. Delete that temporary user. Choose another unused ID if
   you have already used 106. Confirm deletion only for the row you created.
4. **Transactions:** note account 1001 balance INR 66800. Add ID 50, account
   1001, category 2, date 2026-10-20, type EXPENSE, amount 250. Balance becomes
   INR 66550. Edit amount to 300: INR 66500. Delete it: INR 66800 again.
   Pick an unused transaction ID if 50 is already present.
5. **Audit:** show Q12. The INSERT, UPDATE and DELETE snapshots remain after
   deleting the transaction. Explain atomic commit/rollback in Python-managed
   Neo4j transactions; do not call this an Oracle PL/SQL trigger.
6. **Reports:** show G01 and its Cypher. It returns four employer/investment
   overlaps. Show G02: Kumar Household has INR 5850 in BlueSky Retail and INR
   3600 in Nexa; Rao has INR 5400 in Nexa; Singh has INR 6400 in GreenWave.
   G03 shows two shared-share connections: Arun/Priya and Arun/Rahul.
7. **Comparison:** open Database design & comparison. Explain relationships and
   path matching, then acknowledge Oracle's strong declarative constraints and
   ledger/reporting fit. There is no measured performance claim.

The baseline figures assume no other saved edits. The sample includes a company
expense classified as Salary, so Q04 includes Salary among expense categories.
Income/expense direction is stored separately from category; this follows DA2.

## Native Neo4j Browser demonstration

Open http://127.0.0.1:7474 and connect to `bolt://127.0.0.1:7687` using username
`neo4j` and the password from `.env`. Do not display the credential file on the
projector. Connect beforehand and keep the Browser tab ready.

```cypher
MATCH p=(u:User)-[:WORKS_AT]->(c:Company)-[:ISSUES]->(s:Share)<-[:HOLDS]-(u)
RETURN p;
```

```cypher
MATCH p=(h:Household)<-[:MEMBER_OF]-(:User)-[:HOLDS]->(:Share)<-[:ISSUES]-(:Company)
RETURN p;
```

```cypher
SHOW CONSTRAINTS;
```

The full `queries.cypher` contains all reports and graph-returning variants.

## Likely viva questions

**Why Neo4j?** Households, people, employers, banks and investments form an
interconnected domain. Relationships are explicit data, and Cypher describes
connected patterns directly.

**Is Oracle unsuitable?** No. Oracle is appropriate for the original ledger.
Neo4j is selected for this extension's relationship exploration and graph queries.

**Where did the junction table go?** PF_USER_SHARES becomes User-HOLDS-Share.
Quantity is stored on HOLDS; its key identifies the user/share pair.

**How are amounts stored?** Integer paise, not binary floating-point balances.
The UI accepts rupees and converts exactly. Reports divide paise by 100 for display.

**What replaces triggers?** A managed write transaction obtains the application
lock, validates references and balances, applies the ledger and balance changes,
and creates an AuditEvent. Any failure rolls back the whole operation.

**What happens with two concurrent expenses?** The database state lock serializes
application writes. The actual integration test lets one of two competing INR
700 expenses commit against INR 980; the other fails, leaving INR 280.

**What rules are in the database?** Unique keys, unique category names, unique
holding keys and a transaction-date index. Other business rules are checked by
the Python application; direct Browser writes can bypass those checks.

**Do we need graph plugins?** No. All features use Community Edition, standard
Cypher and the official Python driver. Visualization uses local SVG/JavaScript.

**What are limitations?** Small fictional data; serialized writes; a local admin
UI; no production user access controls; graph display capped at 300 elements.

## Before submission

- Fill student name and registration number on the report cover.
- Submit the PDF and `DA3_Source.zip`, following faculty instructions.
- Keep `.env`, `.container.env`, `.venv` and `.runtime` private and out of the ZIP.
- Launch the app before your slot, keep the PC awake, and stop DA3 afterwards.
