$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
# Only terminate processes whose command line matches this project's launcher.
foreach ($entry in @(@('flask', (Join-Path $PSScriptRoot 'app.py')), @('wsl', '-d Ubuntu -u root -- sleep infinity'))) {
    $pidPath = Join-Path $PSScriptRoot ('.runtime\' + $entry[0] + '.pid')
    if (Test-Path -LiteralPath $pidPath) {
        $demoProcessId = [int](Get-Content -LiteralPath $pidPath)
        $demoProcess = Get-CimInstance Win32_Process -Filter "ProcessId=$demoProcessId"
        if ($demoProcess -and $demoProcess.CommandLine -like ('*' + $entry[1] + '*')) {
            if ($entry[0] -eq 'wsl') {
                & wsl.exe -d Ubuntu -u root -- podman stop --time 60 pf-demo-oracle
                if ($LASTEXITCODE -ne 0) { throw 'Could not stop the Oracle container.' }
            }
            Stop-Process -Id $demoProcessId -ErrorAction SilentlyContinue
        }
        Remove-Item -LiteralPath $pidPath
    }
}
Write-Host 'Demo stopped. All database records are preserved.'
