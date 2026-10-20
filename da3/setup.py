"""Create a persistent local Neo4j container and seed the standalone dataset."""
from pathlib import Path
import secrets
import subprocess
import time

ROOT=Path(__file__).resolve().parent
IMAGE='docker.io/library/neo4j:2026.09.0'
CONTAINER='pf-da3-neo4j'


def wsl(*args,check=True,**kwargs):
    return subprocess.run(['wsl.exe','-d','Ubuntu','-u','root','--',*args],check=check,**kwargs)


def provision():
    from dotenv import load_dotenv, dotenv_values
    env=ROOT/'.env'
    if not env.exists():
        pw='Pf'+secrets.token_hex(16)
        env.write_text('NEO4J_URI=bolt://127.0.0.1:7687\nNEO4J_USER=neo4j\nNEO4J_PASSWORD='+pw+
                       '\nNEO4J_DATABASE=neo4j\nFLASK_SECRET_KEY='+secrets.token_hex(32)+
                       '\nAPP_HOST=127.0.0.1\nPORT=5001\n',encoding='utf-8')
    load_dotenv(env,override=True)
    pw=dotenv_values(env)['NEO4J_PASSWORD']
    config=ROOT/'.container.env'
    config.write_text('NEO4J_AUTH=neo4j/'+pw+'\nNEO4J_server_memory_heap_initial__size=256m\n'
        'NEO4J_server_memory_heap_max__size=512m\nNEO4J_server_memory_pagecache_size=256m\n',encoding='utf-8')
    installed=wsl('podman','--version',check=False,capture_output=True)
    if installed.returncode:
        print('Installing Podman in Ubuntu...',flush=True)
        wsl('sh','-lc','apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends podman')
    exists=wsl('podman','container','exists',CONTAINER,check=False,capture_output=True)
    if exists.returncode:
        print('Downloading and creating Neo4j Community...',flush=True)
        wsl('podman','pull',IMAGE)
        linux_path='/mnt/'+config.drive[0].lower()+config.as_posix()[2:]
        wsl('podman','run','-d','--name',CONTAINER,'--restart','unless-stopped',
            '-p','127.0.0.1:7474:7474','-p','127.0.0.1:7687:7687','--env-file',linux_path,
            '-v','pf-da3-neo4j-data:/data','-v','pf-da3-neo4j-logs:/logs',IMAGE)
    else:
        wsl('podman','start',CONTAINER)
    from database import driver, initialize
    deadline=time.monotonic()+240
    while True:
        try:
            driver().verify_connectivity()
            break
        except Exception:
            if time.monotonic()>deadline:
                raise RuntimeError('Neo4j did not become ready. Run: wsl -d Ubuntu -u root -- podman logs pf-da3-neo4j')
            time.sleep(3)
    seeded=initialize()
    print('Sample dataset imported.' if seeded else 'Existing demo records preserved.',flush=True)


if __name__=='__main__':
    provision()
