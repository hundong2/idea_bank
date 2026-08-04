$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$previousPythonPath = $env:PYTHONPATH

try {
    $env:PYTHONPATH = Join-Path $projectRoot "src"
    Push-Location $projectRoot
    python -m krtax.maintenance validate
    if ($LASTEXITCODE -ne 0) { throw "maintenance validation failed" }
    python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw "unit tests failed" }
    git diff --check
    if ($LASTEXITCODE -ne 0) { throw "git diff check failed" }
}
finally {
    Pop-Location
    $env:PYTHONPATH = $previousPythonPath
}
