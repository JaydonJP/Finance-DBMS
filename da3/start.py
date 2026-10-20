"""Start the offline DA3 demo and open its dashboard."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from urllib.request import urlopen
import webbrowser

ROOT=Path(__file__).resolve().parent
RUNTIME=ROOT/'.runtime'
URL='http://127.0.0.1:5001'


def ready():
    try:
        with urlopen(URL+'/health',timeout=2) as r:
            if json.load(r).get('project')!='finance-da3':
                return False
        with urlopen(URL+'/db-check',timeout=2) as r:
            return json.load(r).get('status')=='ok'
    except (OSError,ValueError):
        return False


def main(open_browser=True):
    RUNTIME.mkdir(exist_ok=True)
    if not ready():
        print('Starting Finance Graph DA3. Please wait...',flush=True)
        # Keep a Windows-owned WSL session alive independently of this terminal.
        pidfile=RUNTIME/'keeper.pid'
        old=int(pidfile.read_text()) if pidfile.exists() else None
        # Check the specific keeper before creating another background session.
        probe=subprocess.run(['powershell.exe','-NoProfile','-Command',
            f"$p=Get-CimInstance Win32_Process -Filter 'ProcessId={old or 0}'; if ($p.CommandLine -like '*finance-da3-keeper*') {{ exit 0 }} else {{ exit 1 }}"],capture_output=True)
        if probe.returncode:
            keeper=subprocess.Popen(['wsl.exe','-d','Ubuntu','-u','root','--','bash','-c',
                'exec -a finance-da3-keeper sleep infinity'],creationflags=subprocess.CREATE_NO_WINDOW)
            pidfile.write_text(str(keeper.pid))
        from setup import provision
        provision()
        if not ready():
            with (RUNTIME/'server.log').open('a',encoding='utf-8') as log:
                process=subprocess.Popen([sys.executable,str(ROOT/'app.py')],cwd=ROOT,
                    stdout=log,stderr=log,creationflags=subprocess.CREATE_NO_WINDOW)
            (RUNTIME/'server.pid').write_text(str(process.pid))
            for _ in range(40):
                if ready():
                    break
                if process.poll() is not None:
                    raise RuntimeError('Website failed to start; see .runtime/server.log')
                time.sleep(1)
            else:
                raise RuntimeError('Website did not become ready; see .runtime/server.log')
    print('DA3 demo ready: '+URL,flush=True)
    if open_browser:
        webbrowser.open(URL)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args()
    try:
        main(not args.no_browser)
    except Exception as exc:
        print('Startup failed:',exc)
        sys.exit(1)
