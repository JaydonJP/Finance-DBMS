> **UPDATED SETUP:** Start with [`SETUP_GUIDE_WINDOWS_UBUNTU.md`](SETUP_GUIDE_WINDOWS_UBUNTU.md) for Oracle 26ai Free installation, Windows Home (Docker), Ubuntu, and local-IP website troubleshooting. A new `/health` route checks Flask independently, `/db-check` checks Oracle, and `check_connection.py` verifies seed data.

# Personal Finance & Investment Management System — DBMS DA2

**Deadline:** 11 October 2026  
**Backend:** Oracle Database SQL + PL/SQL  
**Frontend:** Python Flask (local browser)  
**Source:** Uploaded DA1 hand-drawn ER diagram, and Experiments 5–9.

## Files and order

1. `01_schema.sql` — Creates **11 business tables plus 1 audit table**, FKs, checks, and two sequences.
2. `03_plsql.sql` — Creates transaction balance/audit trigger, goal function, transaction procedure, explicit-cursor procedure, and an account view.
3. `02_seed.sql` — Populates all 11 business tables, including 12 transactions. **Run only once.**
4. `04_queries.sql` — 12 project-specific queries; also exposed as buttons in Flask app.
5. `app.py`, `queries.json`, `.env.example`, `requirements.txt` — Browser UI and connection configuration.
6. `DA2_Report.docx` — Editable report (insert actual output screenshots and fill identity fields).
7. `DA2_Report.md` — Markdown report text to copy into Word if preferred.

**Execute in this exact sequence:** `01_schema.sql` → `03_plsql.sql` → `02_seed.sql` → `04_queries.sql`.

## Step 1 — Oracle SQL Developer or SQL*Plus

- Sign in with the Oracle user you will use for the web app.
- Open `01_schema.sql`; run as a *script* (F5 in SQL Developer). The `CREATE TABLE` statements must succeed.
- Open `03_plsql.sql`; run as a script. The `/` lines are SQL*Plus script terminators and are needed to compile PL/SQL objects correctly.
- Open `02_seed.sql`; run as a script **one time**. Verify that account `1001` has balance `66800` and the transaction count is `12`.
- Open `04_queries.sql`; run as a script. It has 12 labelled SELECT queries.
- If `ORA-00955` occurs, the project object already exists. **Do not blindly rerun** the seed, or drop other lab tables. Use a fresh dedicated Oracle user/schema if necessary.
- Make sure each PL/SQL object status in `USER_OBJECTS` is `VALID`. To diagnose a failed object: `SELECT name, type, line, text FROM USER_ERRORS WHERE name LIKE 'PF_%' ORDER BY name, sequence;`.

## Step 2 — Launch frontend on Windows

Install Python 3.10+ if missing, open terminal inside this folder, and run:

```bat
py -m venv .venv
.venv\Scripts\activate
py -m pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` with **the same Oracle username/password and DSN used in SQL Developer**. Do not write your password in the submission report or commit the `.env` file. Use the correct PDB service name for your installation; examples are `localhost:1521/XEPDB1` for XE and `localhost:1521/FREEPDB1` for Oracle Free. If your college's Oracle environment is remote, ask for a permitted DSN and network connection. The app uses python-oracledb Thin mode, which normally does not need Oracle Instant Client for supported recent Oracle versions.

Start the app:

```bat
py app.py
```

Open `http://127.0.0.1:5000` in Chrome.

**Troubleshooting:** `ORA-12514` usually indicates a wrong Oracle service name; `ORA-01017` incorrect login; connection-refused errors mean the database/listener isn't reachable. A local SQL*Plus connection does not automatically guarantee Python can reach the PDB using TCP; check the configured listener and service.

## Step 3 — Live teacher demonstration

1. Dashboard: show counts for 11 business tables.
2. `Users`: insert `user_id=106`, name `Demo User`, DOB `2004-01-15`, household ID `3`, employer blank.
3. `Users`: edit the name to `Demo Student` and show the row changed.
4. `Users`: delete user `106` and show the row disappears. This user has no dependent records, so FK constraints permit the deletion.
5. `Transactions`: note account `1001`'s balance first, then insert `trans_id=50`, account `1001`, category `2`, date `2026-10-08`, type `EXPENSE`, amount `250`. The account balance decreases automatically by 250.
6. Edit transaction `50` to amount `300`: balance decreases by another 50.
7. Delete transaction `50`: balance returns to its previous value; Q12 shows INSERT, UPDATE and DELETE audit rows.
8. Open `12 SQL Reports` and click Q01–Q12. Explain JOIN, GROUP BY, subquery, PL/SQL function, left join, view and trigger.
9. In SQL Developer demonstrate cursor and stored procedure (examples below). Roll back optional test work so your display stays consistent.

### PL/SQL function test

```sql
SELECT goal_id, PF_GOAL_PROGRESS(goal_id) AS progress_pct FROM PF_GOAL;
```

### Cursor test (does not change data)

```sql
SET SERVEROUTPUT ON;
BEGIN
    PF_PRINT_ACCOUNT_HISTORY(1001);
END;
/
```

### Procedure test (changes data; use ROLLBACK to undo)

```sql
SET SERVEROUTPUT ON;
DECLARE
    v_new_id NUMBER;
BEGIN
    PF_ADD_TRANSACTION(1001, 2, 'EXPENSE', 100, v_new_id);
    DBMS_OUTPUT.PUT_LINE('Inserted transaction ID: ' || v_new_id);
END;
/
SELECT balance FROM PF_ACCOUNT WHERE account_id = 1001;
ROLLBACK;
```

## ER model and implementation notes

Entities shown on DA1: Household, Users, Account, Bank, Company, Shares, Subscription, Goal, Category, Transaction. `USER_SHARES` resolves the M:N share ownership relationship. Supporting `PF_TRANS_AUDIT` is **not** a DA1 entity, but is added for the trigger demonstration. `AGE` is derived using `TRUNC(MONTHS_BETWEEN(SYSDATE, dob)/12)` and not physically stored.

A personal account belongs to exactly one user and a corporate account to exactly one company. The source diagram draws both account-user and account-company relationships without clearly specifying whether both may own one account, so this XOR ownership is a declared implementation assumption. The employment relationship is implemented with `PF_USERS.employer_company_id` (company 1:N user). Subscription uses `(account_id, subscription_id)` because the diagram uses weak entity / identifying relationship notation.

The trigger applies expense and income ledger deltas to balances, including EDIT and DELETE. A CHECK prevents negative balances. Goal savings (`current_amt`) are separately maintained, not automatically computed from account balance.

**Review caution:** the web UI has no authentication or CSRF protection; it is intended only for local classroom demonstration, not production financial services.

## Screenshots to add to your report

- DA1 scanned ER diagram (rotate clockwise to horizontal orientation)
- SQL Developer's PF_ tables / sample rows
- Flask dashboard
- UI insert, update, delete actions
- Q01, Q03, Q04, Q06, Q10, Q12 result pages
- Cursor `DBMS_OUTPUT` and trigger/audit output

Keep personally identifying student details in your cover page only, not in DB sample data. Record real execution evidence; **do not claim the project is tested against Oracle until you have actually run it locally**.
