$ErrorActionPreference='Stop'
& wsl.exe -d Ubuntu -u root -- podman stop --time 60 pf-da3-neo4j
if ($LASTEXITCODE -ne 0) { throw 'Could not stop Neo4j.' }
foreach ($entry in @(@('server',(Join-Path $PSScriptRoot 'app.py')), @('keeper','finance-da3-keeper'))) {
    $demoPidFile=Join-Path $PSScriptRoot ('.runtime\'+$entry[0]+'.pid')
    if (Test-Path -LiteralPath $demoPidFile) {
        $demoProcessId=[int](Get-Content -LiteralPath $demoPidFile)
        $demoProcess=Get-CimInstance Win32_Process -Filter "ProcessId=$demoProcessId"
        if ($demoProcess -and $demoProcess.CommandLine.Contains($entry[1])) {
            Stop-Process -Id $demoProcessId -ErrorAction SilentlyContinue
        }
        Remove-Item -LiteralPath $demoPidFile
    }
}
Write-Host 'DA3 stopped. All Neo4j data is preserved.'
