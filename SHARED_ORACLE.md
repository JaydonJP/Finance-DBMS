# Use one Oracle database from two laptops

Both DA2 Flask apps can connect to the same Oracle service and project schema.
Committed changes then appear on either laptop after refreshing the page. This
shares one database; it does not replicate or merge two separate databases.
The DA3 Neo4j store is independent.

## Information needed from the host laptop

- Reachable host IP or hostname. For the same Wi-Fi, use the host's active
  Wi-Fi/Ethernet IPv4 address from `ipconfig`, not a Docker/WSL internal address.
- Published TCP port, normally 1521. A Docker mapping `1521:1521` maps the host
  port to the database container's port.
- Oracle service name, normally FREEPDB1 for Oracle Free. Confirm it in the
  working SQL Developer connection or the container's listener status.
- Project schema username containing the PF_ tables. Use the same schema on
  both laptops. Enter its password only into the local hidden password prompt.

Different Wi-Fi networks require a reachable private VPN address or another
configured private network route. A local Wi-Fi address alone is not reachable
across unrelated networks. The host must stay awake with Oracle running.

## Select the shared database

Double-click **Connect Shared Oracle.cmd**. Enter the host, service, project
username and password. The helper connects and checks the required project
columns, view, function and enabled balance trigger using SELECT queries.
It does not initialize or seed the host database. If the preflight fails, the
current configuration is preserved.

On success, the helper saves the private connection to `.env`, preserves the
original local configuration in `.runtime/oracle-local.env`, and restarts this
project's Flask server. The usual **Start Demo.cmd** then uses shared mode
without starting or initializing this laptop's Oracle container.

To return to the saved local database, double-click **Use Local Oracle.cmd**.
The existing local data remains in its container volume.

Command-line form:

```powershell
.\.venv\Scripts\python.exe configure_oracle.py --host FRIEND_HOST --service FREEPDB1 --user PF_DA2
```

Use the actual host and project schema. The password is prompted interactively;
do not put it in the command line, Git, screenshots, or chat.

## Check reachability first

Once the friend supplies their address, from this laptop:

```powershell
Test-NetConnection -ComputerName FRIEND_HOST -Port 1521
```

If TCP fails, inspect the host's published port, network route, host firewall
and Wi-Fi client isolation. Keep access limited to the trusted LAN or private
VPN; public Internet exposure is unnecessary for two laptops.

### Existing container published only to localhost

If `docker port pf-oracle 1521` on the host shows `127.0.0.1:1521`, the host
can forward its LAN address to that existing local listener without recreating
the container. In an administrator PowerShell on the **host laptop**, substitute
its current LAN address for `HOST_IP` and the other laptop's address for `CLIENT_IP`:

```powershell
Start-Service iphlpsvc
netsh interface portproxy add v4tov4 listenaddress=HOST_IP listenport=1521 connectaddress=127.0.0.1 connectport=1521
New-NetFirewallRule -DisplayName "Oracle DA2 shared client" -Direction Inbound -Protocol TCP -LocalPort 1521 -RemoteAddress CLIENT_IP -Action Allow -Profile Any
netsh interface portproxy show all
```

This changes the host's network configuration. Limit the rule to the intended
client address and update it if DHCP assigns either laptop a different IP.
Remove this particular forwarding rule when sharing is no longer needed:

```powershell
netsh interface portproxy delete v4tov4 listenaddress=HOST_IP listenport=1521
Remove-NetFirewallRule -DisplayName "Oracle DA2 shared client"
```

Reference: [Microsoft portproxy syntax](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/netsh-interface).

Existing records from this laptop are not automatically copied to the host.
Inspect both datasets before planning any import. Do not run the fixed-ID seed
scripts on an already populated shared schema.

Reference: [Docker port publishing](https://docs.docker.com/engine/network/port-publishing/)
and [Oracle Python connections](https://python-oracledb.readthedocs.io/en/latest/user_guide/connection_handling.html).
