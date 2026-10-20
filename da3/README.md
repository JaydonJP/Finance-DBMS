# Finance Graph DA3

Personal Finance and Investment Relationship Analysis using **Neo4j Community**.
This is a complete, standalone extension of the Oracle DA2 project. All live
DA3 records and relationships are stored in Neo4j. Oracle is not required to run DA3.

## Run on this PC

Double-click **Start DA3.cmd**, or the **Finance Graph DA3** desktop shortcut.

- Application: http://127.0.0.1:5001/
- Graph explorer: http://127.0.0.1:5001/graph
- Reports: http://127.0.0.1:5001/reports
- Native Neo4j Browser: http://127.0.0.1:7474/
- Application health: http://127.0.0.1:5001/health
- Database health: http://127.0.0.1:5001/db-check

Use **Stop DA3.cmd** when finished. Data remains in the WSL volume
`pf-da3-neo4j-data`. Subsequent starts work offline. The initial installation
needs Internet to download dependencies and the database image.

The original DA2 project and its launcher remain in the parent directory.
If the PC becomes short of memory, stop the Oracle demo while presenting DA3.

## Features

- Complete create/read/update/delete for all 11 original business collections.
- Native User-HOLDS-Share relationships with quantity properties.
- Exact amounts stored as integer paise; dates stored as native date properties.
- Atomic transaction insert/edit/delete with balance adjustments and permanent audit.
- ID, reference, ownership, amount and deletion validation; CSRF-protected forms.
- All 12 original reports rewritten in Cypher, plus 3 graph-specific insights.
- Interactive offline SVG explorer: node inspection, household/insight filters,
  pan, zoom, fit and relationship labels. No CDN or paid API dependencies.
- Inspectable Cypher and CSV exports for every report.

## Fresh Windows setup

Prerequisites: Python 3.10+, Ubuntu WSL2, and Internet for the first setup.
The launcher installs Python packages into `.venv`. `setup.py` installs Podman
inside Ubuntu if needed and creates the official Neo4j Community container.
It never installs or changes the original Oracle database.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe start.py
```

Container name: `pf-da3-neo4j`.
Pinned image: `docker.io/library/neo4j:2026.09.0`.
Host ports: HTTP 7474 and Bolt 7687, bound only to `127.0.0.1`.
Python web server: Waitress on port 5001.

`setup.py` generates local credentials in `.env` and `.container.env`. Both are
ignored by Git and excluded from the submission ZIP. To connect through Neo4j
Browser, select Bolt `bolt://127.0.0.1:7687`, user `neo4j`, and the existing
`NEO4J_PASSWORD` value from `.env`. Never include that file in your submission.

The default setup expects the Ubuntu WSL distribution to be named `Ubuntu`.
If your machine uses another name, change the `-d Ubuntu` launch arguments.

## Sample data and repeat import

`data/sample.json` contains the original fictional dataset, including **opening**
account balances. `import_data.py` creates nodes and relationships and applies the
12 sample ledger events exactly once, in a single atomic import.

Baseline: 57 business nodes, 72 relationships, 12 AuditEvent nodes, and 1 DemoState
node. There are 5 users, 7 accounts and 6 holdings. Category Other and company
Cedar Finance are initially isolated and still appear in the graph explorer.
Account 1001 finishes at INR 66800.00; all accounts total INR 435300.00.

```powershell
.\.venv\Scripts\python.exe import_data.py
.\.venv\Scripts\python.exe verify.py
```

Repeat import preserves existing records. It does not overwrite edits or reapply
balance effects. A partial/unrecognized store is rejected. Back up persistent
data before making manual changes; no automatic destructive reset is provided.

`verify.py` checks all collections, all 15 reports, graph APIs, rollback, balances,
audit persistence and competing writes. It removes its temporary records and
stores actual results in `submission/verification.json`. It expects the original
baseline dataset, so use it before making persistent demo edits.

## Design and limits

Business IDs map to unique `key` properties. Subscriptions use account ID and
subscription ID together; HOLDS relationships use user ID and share ID together.
Foreign-key links become typed graph relationships. Business values such as
balances and prices use `_paise` properties in the database.

Every application write increments a single DemoState revision to obtain a
database write lock before reading state. This serializes reference checks,
deletions and ledger writes, preventing conflicting classroom operations from
overdrawing an account. It is intentionally conservative for a small demo and
would need a more granular locking design for a high-throughput service.

Neo4j Community enforces uniqueness constraints. Application code enforces
mandatory fields, types, ownership, positive amounts, required relationships and
restricted deletion. Manual writes in Neo4j Browser can bypass those rules.
This is a localhost classroom admin interface with no user authentication or
authorization; keep it local. The graph API caps displayed results at 300 nodes/
relationships (200 relationships for household exploration), sufficient for the
sample dataset. Reports query the full dataset.

No benchmark establishes that Neo4j is faster than Oracle. The demonstrated
advantages are direct relationship modeling, Cypher patterns and graph exploration.

## Project files

- `app.py`, `templates/`, `static/`: browser application.
- `database.py`: graph model, validation, CRUD, atomic ledger and audit.
- `reports.py`, `queries.cypher`: 15 reports and native graph queries.
- `schema.cypher`: documented uniqueness constraints and date index.
- `data/`: portable metadata and fictional fixture.
- `setup.py`, `start.py`, launchers: installation, startup and shutdown.
- `verify.py`: real database integration checks.
- `DEMO_GUIDE.md`: presentation steps, expected results and viva notes.
- `submission/DA3_Report.pdf`: report with model, screenshots and actual results.
- `submission/DA3_Source.zip`: source package without credentials or virtual environments.

## References

- [Neo4j property graph concepts](https://neo4j.com/docs/getting-started/appendix/graphdb-concepts/)
- [Python managed transactions](https://neo4j.com/docs/python-manual/current/transactions/)
- [Cypher and Community Edition capabilities](https://neo4j.com/docs/cypher-manual/current/introduction/cypher-neo4j/)
- [Concurrent data access](https://neo4j.com/docs/operations-manual/current/database-internals/concurrent-data-access/)
- [Official container setup](https://neo4j.com/docs/operations-manual/current/docker/introduction/)
