param([switch]$PortableBuild)
$ErrorActionPreference = 'Stop'
$projectPath = $PSScriptRoot
$pythonPath = Join-Path $projectPath '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    python -m venv (Join-Path $projectPath '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12+ is required.' }
}
& $pythonPath -m pip install -r (Join-Path $projectPath 'backend\requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
$env:DATABASE_URL = 'sqlite:///' + ((Join-Path $projectPath 'backend\sana.db') -replace '\\', '/')
$env:AI_MODE = 'mock'
Push-Location (Join-Path $projectPath 'backend')
try {
    & $pythonPath -m alembic upgrade head
    if ($LASTEXITCODE -ne 0) { throw 'Migration failed.' }
    & $pythonPath -m app.seed
    if ($LASTEXITCODE -ne 0) { throw 'Seed failed.' }
} finally { Pop-Location }
Push-Location (Join-Path $projectPath 'frontend')
try {
    npm install
    if ($LASTEXITCODE -ne 0) { throw 'Frontend installation failed.' }
    if ($PortableBuild) { npm run build:portable } else { npm run build }
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed.' }
    $apiProcess = Start-Process -FilePath $pythonPath -ArgumentList @('-m','uvicorn','app.main:app','--host','127.0.0.1','--port','8000') -WorkingDirectory (Join-Path $projectPath 'backend') -WindowStyle Hidden -PassThru
    try {
        Write-Host 'AI Sana: http://127.0.0.1:5173 (Ctrl+C stops both services)'
        node scripts/preview-portable.mjs
    } finally {
        if (-not $apiProcess.HasExited) { Stop-Process -Id $apiProcess.Id }
    }
} finally { Pop-Location }
