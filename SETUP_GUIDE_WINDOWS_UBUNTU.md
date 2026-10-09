# DBMS DA2 — Verified setup plan for Windows, Windows Home, and Ubuntu/Debian

This is a local **Oracle SQL / PL/SQL + Python Flask** project. Website is created by running `app.py`; `127.0.0.1` is not a hosted/public IP.

## Choose one platform

- **Recommended: Windows 11 Pro / Education / Enterprise:** install Oracle AI Database **26ai Free**, SQL Developer and Python on Windows, run all steps in Windows. The Oracle Windows installer does not officially list Windows Home.
- **Windows Home:** use Docker Desktop (Linux containers / WSL2) for Oracle, and run SQL Developer + Python in Windows. After Docker starts, use the *same* SQL Developer and Python instructions below.
- **Ubuntu/Debian:** use Docker Engine/Podman for the database (do not attempt to install an Oracle Linux RPM natively on Ubuntu), and run Python locally. Optionally use SQL Developer on Windows only if the Linux DB is reachable; otherwise use SQL*Plus inside the container.
- **Already have college Oracle SQL Developer/SQL*Plus connection?** Skip database installation and ask for host, TCP port, PDB service, username/password. Only if you have `CREATE TABLE`, `CREATE PROCEDURE`, `CREATE TRIGGER`, `CREATE VIEW`, `CREATE SEQUENCE`, and quota may you create project objects. If the college DB is reachable *only inside the lab*, the Flask app will also need to run on a computer that can reach the server.

## A. Windows fresh install (recommended)

### Step A1 — Install prerequisites

1. Install Python 3.12 or 3.13 from https://www.python.org/downloads/windows/ . During installation enable Python launcher / PATH integration. Check with `py --version` in **PowerShell**.
2. Install Oracle AI Database 26ai Free, Windows x64 package at https://www.oracle.com/database/free/get-started/ . Extract ZIP, run `setup.exe` as a Windows administrator and finish setup. Remember the administrator password, use the default installation path. Budget ~11 GB free disk. Do not install another Oracle DB if one is already installed.
3. Install SQL Developer from https://www.oracle.com/database/sqldeveloper/technologies/download/ . Choose the Windows 64-bit ZIP **with JDK included**; unzip and run `sqldeveloper.exe`. You need not separately install a JDK with this variant.
4. Optionally install VS Code (you can instead use Notepad).
5. Open `services.msc`; verify `OracleServiceFREE` and the Oracle listener service are running. If necessary start them. An Oracle database **and** a listener must be available for TCP connections.

### Step A2 — Create a non-admin project schema in SQL Developer

- New connection `system_local`:
  - Username: `system`
  - Password: database administrator password selected in installer
  - Hostname: `localhost`
  - Port: `1521`
  - Service name: `FREEPDB1` (**not** SID `FREE`)
- **Test** -> **Success** -> **Connect**. Before proceeding run:

```sql
SELECT SYS_CONTEXT('USERENV','CON_NAME') AS PDB FROM DUAL;
```

It must return `FREEPDB1` for the commands below. From the `system_local` connection run these commands **once** (replace the quoted password with a strong password of your choice):

```sql
CREATE USER PF_DA2 IDENTIFIED BY "ReplaceWithAStrongPassword123";
GRANT CREATE SESSION, CREATE TABLE, CREATE VIEW, CREATE SEQUENCE,
      CREATE PROCEDURE, CREATE TRIGGER TO PF_DA2;
ALTER USER PF_DA2 QUOTA 100M ON USERS;
```

Then make a **second** SQL Developer connection called `pf_project`:

- Username: `PF_DA2`
- Password: the new password you chose in `CREATE USER`
- Host: `localhost`, Port: `1521`, Service name: `FREEPDB1`
- Test -> Success -> Connect
- Verify `SELECT USER, SYS_CONTEXT('USERENV','CON_NAME') FROM DUAL;` returns `PF_DA2`, `FREEPDB1`.

**Run all project SQL with this new `pf_project` connection**, never with `system_local`.

### Step A3 — Unzip project, run Oracle scripts in precise order

Extract `DBMS_DA2_Project_Complete.zip`. Open **these four files one at a time in SQL Developer**, selecting the `pf_project` connection, and press **F5 / Run Script**:

1. `01_schema.sql`: 11 design tables + 1 audit table and 2 sequences.
2. `03_plsql.sql`: trigger, function, procedures, view.
3. `02_seed.sql`: test data; **run once only**.
4. `04_queries.sql`: 12 SQL SELECT reports.

**Validation SQL** (new SQL worksheet on `pf_project`):

```sql
SELECT COUNT(*) AS table_count FROM USER_TABLES WHERE TABLE_NAME LIKE 'PF_%';
SELECT COUNT(*) AS user_count FROM PF_USERS;
SELECT COUNT(*) AS transaction_count FROM PF_TRANSACTION;
SELECT balance FROM PF_ACCOUNT WHERE account_id = 1001;
SELECT object_name, object_type, status FROM USER_OBJECTS
WHERE object_name LIKE 'PF_%' AND status <> 'VALID';
SELECT name, type, line, text FROM USER_ERRORS
WHERE name LIKE 'PF_%' ORDER BY name, sequence;
```

Expected: **12 tables**, **5 users**, **12 transactions**, account 1001 balance **66800**, no invalid project objects and no compile errors. If the first script fails, stop and inspect before proceeding. A `COMMIT` is included in `02_seed.sql`.

### Step A4 — Install Python dependencies in PowerShell

Go to the folder containing `app.py` (for example `C:\Users\<you>\Downloads\DBMS_DA2_Project`). Use **PowerShell**, not a SQL worksheet:

```powershell
cd "$HOME\Downloads\DBMS_DA2_Project"
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

Adjust the `cd` path if you extracted somewhere else. The `.venv\Scripts\python.exe` approach does not require PowerShell script execution-policy changes.

Edit `.env` so values match the `pf_project` SQL Developer connection:

```dotenv
ORACLE_USER=PF_DA2
ORACLE_PASSWORD=replace_with_the_password_you_chose
ORACLE_DSN=localhost:1521/FREEPDB1
FLASK_SECRET_KEY=any_long_random_value_for_local_demo
APP_HOST=127.0.0.1
PORT=5000
```

Only use the `XEPDB1` service if you **actually have Oracle XE**; the latest Oracle Free uses `FREEPDB1`. Do **not** put your `.env` file or actual database passwords in the report or share them in screenshots.

### Step A5 — Separate Oracle test from website test

```powershell
.\.venv\Scripts\python.exe check_connection.py
```

Expected `SUCCESS` and the same 5 users / 12 transactions / balance. Only when this succeeds start Flask:

```powershell
.\.venv\Scripts\python.exe app.py
```

**Leave the PowerShell terminal open.** It should say `Running on http://127.0.0.1:5000`.

Open these URLs in the **same Windows computer**:

1. `http://127.0.0.1:5000/health` — should show `"status":"ok"`; checks Flask only.
2. `http://127.0.0.1:5000/db-check` — should show `"status":"ok"`, schema `PF_DA2`, 5 users; checks Oracle.
3. `http://127.0.0.1:5000/` — dashboard.
4. `http://127.0.0.1:5000/queries` — 12 SQL report pages.

No public hosting or domain name is involved.

### Step A6 — Test full CRUD and triggers

- Users page: Add `106`, `Demo User`, DOB `2004-01-15`, household `3`, employer blank; Save; edit `Demo Student`; delete row `106`.
- Accounts: note account `1001` balance `66800`.
- Transactions: add transaction `50`, account `1001`, category `2`, date `2026-10-09`, type `EXPENSE`, amount `250`; balance becomes `66550`.
- Edit `50` amount to `300`; balance becomes `66500`.
- Delete transaction `50`; balance returns to `66800`. Check Query Q12 to see audit events.
- Open each of Q01–Q12 in the website and capture selected screenshots.
- In SQL Developer run the function/cursor/procedure samples in `README.md` and capture results.
- Insert screenshots in `DA2_Report.docx`, supply real test results and fill in student details. Export to PDF if your teacher asks for PDF.

## B. Windows Home alternative — use Docker Desktop for the Oracle database

1. Install Docker Desktop (https://www.docker.com/products/docker-desktop/); enable WSL2 backend and use **Linux containers**. Start Docker Desktop.
2. In PowerShell (Docker must be running):

```powershell
docker pull container-registry.oracle.com/database/free:latest
docker volume create pf_oracle_data
docker run -d --name pf-oracle -p 127.0.0.1:1521:1521 -e ORACLE_PWD=ChangeMeStrong123 -v pf_oracle_data:/opt/oracle/oradata container-registry.oracle.com/database/free:latest
docker logs -f pf-oracle
```

Use your own administrator password instead of `ChangeMeStrong123`. The `ORACLE_PWD` command-line environment value is visible to some local tools: appropriate for an isolated classroom demo, not a shared production computer. Wait for **DATABASE IS READY TO USE!**; stop following logs using Ctrl+C (container remains running).
3. Create `pf_project` Oracle schema in SQL Developer exactly as Step A2 using username `system`, password from Docker, host `localhost`, port `1521`, service `FREEPDB1`.
4. Continue Steps A3–A6 in **Windows PowerShell**. On future boots use `docker start pf-oracle` if needed. Do not create a second container with the same volume/name.

## C. Ubuntu or Debian alternative — Docker + Python

**Note:** Oracle's downloadable RPM is for Oracle Linux/RHEL, not Ubuntu or Debian. Use Docker instead. Docker Engine installation details vary with the distro; use https://docs.docker.com/engine/install/ubuntu/ or https://docs.docker.com/engine/install/debian/ if `docker` is absent.

Once Docker works, run:

```bash
sudo docker pull container-registry.oracle.com/database/free:latest
sudo docker volume create pf_oracle_data
sudo docker run -d --name pf-oracle -p 127.0.0.1:1521:1521 \
  -e ORACLE_PWD='ChangeMeStrong123' \
  -v pf_oracle_data:/opt/oracle/oradata \
  container-registry.oracle.com/database/free:latest
sudo docker logs -f pf-oracle
```

After `DATABASE IS READY TO USE!`, press Ctrl+C, then:

```bash
sudo docker exec -it pf-oracle sqlplus system@//localhost:1521/FREEPDB1
```

Enter the `ORACLE_PWD` password when prompted. Confirm `SELECT SYS_CONTEXT('USERENV','CON_NAME') FROM DUAL;` returns `FREEPDB1`. Then run the same 3 `CREATE USER` / `GRANT` / `ALTER USER` statements in Step A2.

To run the SQL scripts in the container without installing SQL Developer, from the **folder holding the project SQL files**:

```bash
for file in 01_schema.sql 03_plsql.sql 02_seed.sql 04_queries.sql; do
  sudo docker cp "$file" "pf-oracle:/tmp/$file"
done
sudo docker exec -it pf-oracle sqlplus PF_DA2@//localhost:1521/FREEPDB1
```

Enter your project user's password, then **at the `SQL>` prompt**:

```sql
@/tmp/01_schema.sql
@/tmp/03_plsql.sql
@/tmp/02_seed.sql
@/tmp/04_queries.sql
```

Now install/run Python in Ubuntu/Debian terminal from the project folder:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
nano .env
./.venv/bin/python check_connection.py
./.venv/bin/python app.py
```

Use the `.env` values from Step A4. Open the URLs from Step A5 in a browser running **in Ubuntu**. Do not assume a Windows browser can reach localhost of a separate dual-boot OS. If Python runs in WSL2, Windows localhost forwarding may work but depends on configuration: keep Oracle and the Python app in the same OS environment to simplify it.

## D. Website/IP troubleshooting — work in this exact order

1. **Site says "refused to connect" or "not reachable"?** Flask may not be running. Start `python app.py` and **leave terminal open**. Use `http://127.0.0.1:5000/health` (HTTP, not HTTPS) on the same computer.
2. **`/health` works but `/db-check` fails?** The website is actually running: inspect `.env`, Oracle service, listener, user privileges and script execution. With Windows native Oracle check `services.msc`; with Docker check `docker ps` and `docker logs pf-oracle`. Windows can check DB port using `Test-NetConnection 127.0.0.1 -Port 1521`.
3. **`/db-check` passes but the dashboard fails?** Some project tables may not exist or the same schema was not used. Rerun validation queries; do **not** rerun `02_seed.sql` blindly.
4. **`ORA-12514` / `DPY-6005`:** wrong Oracle service or closed PDB. Verify the service `FREEPDB1` (or `XEPDB1` for XE), plus `lsnrctl status` when available.
5. **`ORA-01017`:** wrong username/password. Verify case and which database user/schema you're connecting as.
6. **`ORA-00942`:** tables do not exist in the connected schema or a script failed. `SELECT USER FROM DUAL` must match `.env` username.
7. **Port 5000 already in use?** Change `PORT=5001` in `.env`, restart app, open `http://127.0.0.1:5001/health`.
8. **Want to open the demo with your laptop's `192.168.x.x` / `10.x.x.x` IP from another device on your private Wi-Fi?** Original app listened only on `127.0.0.1`. The patched app supports changing `.env` to `APP_HOST=0.0.0.0`, then restarting it. Find your laptop IPv4 from `ipconfig` (Windows) or `hostname -I` (Ubuntu). Open `http://<laptop-private-ip>:5000` from the other device. The device must be on the same LAN, and the OS firewall must allow inbound TCP 5000. Keep this limited to a trusted classroom/private network; **there is no login or CSRF protection**. Switch back to `APP_HOST=127.0.0.1` afterward.
9. **Do not forward port 5000 on your router or deploy this code publicly**: it's a demo-only database administration interface.

## E. Screenshots to capture for the submission report

- Oracle object list and populated tables.
- Successful `SELECT COUNT(*)` and sample account balance verification.
- Flask dashboard, Users add/edit/delete before-and-after.
- Transaction add/edit/delete and corresponding changed account balances.
- Query Q01, Q03, Q04, Q06, Q10, Q12 results.
- PL/SQL cursor output, function result, and transaction trigger/audit result.

**Success criteria:** All scripts run without errors; 12 tables exist; `check_connection.py` succeeds; `/health`, `/db-check`, and `/` respond; all CRUD actions work and are reflected in Oracle; 12 report pages show Oracle output; Word report has authentic screenshots and student details.
