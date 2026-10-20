# Run your finance DBMS demo

DA2 uses the original Oracle database and PL/SQL implementation. Flask runs in
Windows. In local mode, Oracle Database Free runs in a Podman container inside
Ubuntu WSL. In shared mode, Flask connects to the configured external Oracle
project schema. See `SHARED_ORACLE.md` for connecting two laptops.

## Start and stop

1. Double-click the **Finance DBMS Demo** desktop shortcut, or **Start Demo.cmd**
   in this folder.
2. Wait for Oracle to start (usually up to a minute after a restart).
3. The website opens at **http://127.0.0.1:5000/**.
4. Double-click **Stop Demo.cmd** when finished to release database memory.

The launcher works after a Windows restart. It preserves your records and does
not repeat the seed inserts. Local mode needs no Internet connection after setup.
Shared mode needs a working network connection to the host laptop and a running
Oracle container on that host. It never initializes or seeds the shared database.
Keep this folder and its `.venv`, `.env` and `.oracle.env` files together. Oracle
local data is stored separately in the WSL volume `pf-demo-oracle-data`.

To select a shared database, run **Connect Shared Oracle.cmd** and enter its
host, service, project username and password. The password stays in the local
ignored `.env` file. To return to the saved local database, run
**Use Local Oracle.cmd**. Selecting the shared database does not merge local
records into it. Both laptops must use the same database service and schema;
refresh a page after the other laptop commits a change.

## Suggested presentation (5 minutes)

1. **Dashboard:** show the 11 business tables and their record counts. Explain
   that an additional audit table records changes to transactions.
2. **Users:** add user `106`, name `Demo Student`, DOB `2004-01-15`, household
   `3`, employer blank. Edit the name, then delete the user. If ID 106 is already
   used, choose another unused ID.
3. **Accounts:** point out account `1001` and its original balance **66800**.
4. **Transactions:** add ID `50`, account `1001`, category `2`, date `2026-10-20`,
   type `EXPENSE`, amount `250`. The account balance becomes **66550**.
5. Edit transaction `50` to amount `300`: balance becomes **66500**. Delete
   transaction `50`: balance returns to **66800**. These figures assume the
   original sample data and no other changes to account 1001. Choose an unused
   transaction ID if 50 already exists.
6. **12 SQL Reports:** show Q02 (view/joins and balances), Q04 (GROUP BY and
   SUM), Q05 (subquery), Q06 (PL/SQL savings function), and Q12 (the trigger's
   INSERT/UPDATE/DELETE audit entries).
7. Explain the flow: browser form -> Flask -> Oracle SQL -> automatic PL/SQL
   trigger -> updated balance and audit record.

Use the actual schema and program definitions in `01_schema.sql` and
`03_plsql.sql` if asked to explain primary/foreign keys, CHECK constraints,
composite keys, sequences, functions, procedures, cursors or triggers.

## Database connection for an SQL IDE

- Host: `127.0.0.1`
- Port: `1521`
- Service name: `FREEPDB1` (select Service name, not SID)
- Username: `PF_DA2`
- Password: the `ORACLE_PASSWORD` value in your local `.env` file

The `.oracle.env` file contains separate container administrator credentials.
Both credential files are ignored by Git. Do not show them during the demo.
An SQL IDE is optional; all 12 reports work through the website.

To demonstrate the cursor in an SQL worksheet connected as `PF_DA2`:

```sql
SET SERVEROUTPUT ON;
EXEC PF_PRINT_ACCOUNT_HISTORY(1001);
SELECT PF_GOAL_PROGRESS(401) AS progress_percent FROM DUAL;
```

## Checks and troubleshooting

From PowerShell in this folder:

```powershell
.\.venv\Scripts\python.exe check_connection.py
.\.venv\Scripts\python.exe verify_demo.py
```

`verify_demo.py` checks the reports, web forms, stored programs, balance and
audit triggers, and overspending rejection. Test transactions roll back and the
temporary user is removed. Oracle sequence values can advance during checks.

- Website health: http://127.0.0.1:5000/health
- Database health: http://127.0.0.1:5000/db-check
- Website log: `.runtime/flask.log`
- Oracle status: `wsl -d Ubuntu -u root -- podman ps -a`
- Oracle log: `wsl -d Ubuntu -u root -- podman logs --tail 60 pf-demo-oracle`

If a launcher fails, its terminal stays open with an error. Keep Ubuntu WSL
installed; do not delete its container volume. **Do not rerun the original
CREATE TABLE or seed scripts on the populated database.**

The site listens only on this PC. Leave the PC awake during your presentation.
