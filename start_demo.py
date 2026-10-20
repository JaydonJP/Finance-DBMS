"""Start the installed WSL Oracle container and local Flask app for the demo."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import hashlib
from urllib.error import URLError
from urllib.request import urlopen
import webbrowser
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / '.runtime'
URL = 'http://127.0.0.1:5000'
CONTAINER = 'pf-demo-oracle'


def wsl(*args, **kwargs):
    return subprocess.run(['wsl.exe', '-d', 'Ubuntu', '-u', 'root', '--', *args],
                          check=True, **kwargs)


def healthy():
    try:
        with urlopen(URL + '/db-check', timeout=3) as response:
            result = json.load(response)
            config = dotenv_values(ROOT / '.env')
            expected = hashlib.sha256((config.get('ORACLE_DSN', '') + '\0' +
                                       config.get('ORACLE_USER', '')).encode()).hexdigest()[:16]
            return result.get('status') == 'ok' and result.get('connection_id') == expected
    except (OSError, URLError, ValueError):
        return False


def stop_owned_server():
    """Restart only this project's Flask process when the database changes."""
    pidfile = RUNTIME / 'flask.pid'
    if not pidfile.exists():
        return
    pid = int(pidfile.read_text())
    app_path = str(ROOT / 'app.py').replace("'", "''")
    script = (f"$p=Get-CimInstance Win32_Process -Filter 'ProcessId={pid}'; "
              f"if ($p -and $p.CommandLine.Contains('{app_path}')) "
              f"{{ Stop-Process -Id {pid} -ErrorAction Stop }}")
    subprocess.run(['powershell.exe', '-NoProfile', '-Command', script], check=True,
                   capture_output=True)
    pidfile.unlink(missing_ok=True)


def start(open_browser=True):
    os.chdir(ROOT)
    RUNTIME.mkdir(exist_ok=True)
    if healthy():
        print('The demo is already running:', URL)
        if open_browser:
            webbrowser.open(URL)
        return
    config = dotenv_values(ROOT / '.env')
    remote = config.get('ORACLE_MODE', 'local').lower() == 'remote'
    if remote:
        print('Connecting to the shared Oracle database...', flush=True)
    else:
        print('Starting Oracle in Ubuntu WSL. Please wait...', flush=True)
        keeper = subprocess.Popen(
            ['wsl.exe', '-d', 'Ubuntu', '-u', 'root', '--', 'sleep', 'infinity'],
            creationflags=subprocess.CREATE_NO_WINDOW)
        (RUNTIME / 'wsl.pid').write_text(str(keeper.pid))
        wsl('podman', 'start', CONTAINER)
    from app import get_connection
    deadline = time.monotonic() + (20 if remote else 300)
    while True:
        try:
            with get_connection():
                break
        except Exception:
            if time.monotonic() >= deadline:
                raise RuntimeError('Oracle did not become ready. See DEMO_GUIDE.md for diagnostics.')
            time.sleep(3)
    if remote:
        # Shared databases are validated read-only. Never seed somebody else's store.
        from configure_oracle import verify_schema
        with get_connection() as conn:
            verify_schema(conn)
    else:
        from setup_database import initialize
        initialize()
    if healthy():
        print('Demo ready:', URL)
        if open_browser:
            webbrowser.open(URL)
        return
    print('Oracle is ready. Starting the website...', flush=True)
    stop_owned_server()
    with (RUNTIME / 'flask.log').open('a', encoding='utf-8') as log:
        server = subprocess.Popen([sys.executable, str(ROOT / 'app.py')],
                                  cwd=ROOT, stdout=log, stderr=log,
                                  creationflags=subprocess.CREATE_NO_WINDOW)
    (RUNTIME / 'flask.pid').write_text(str(server.pid))
    for _ in range(30):
        if healthy():
            print('Demo ready:', URL)
            if open_browser:
                webbrowser.open(URL)
            return
        if server.poll() is not None:
            raise RuntimeError('Website failed to start. Check .runtime/flask.log.')
        time.sleep(1)
    raise RuntimeError('Website did not become ready. Check .runtime/flask.log.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    try:
        start(not args.no_browser)
    except Exception as exc:
        print('Could not start the demo:', exc)
        sys.exit(1)
