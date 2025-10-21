[CmdletBinding()]
param(
    [string]$Host = "0.0.0.0",
    [int]$Port = 8000,
    [switch]$SkipRun
)

$ErrorActionPreference = "Stop"

Write-Host "==== Instalação do BPO Financeiro (Windows) ====" -ForegroundColor Cyan

function Get-PythonLauncher {
    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCmd) {
        return @{ Command = $pythonCmd.Source; Args = @() }
    }
    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        return @{ Command = $pyLauncher.Source; Args = @("-3") }
    }
    throw "Python 3 não encontrado. Instale o Python 3.9 ou superior antes de continuar."
}

$launcher = Get-PythonLauncher

function Invoke-Python {
    param(
        [string[]]$Args
    )
    & $launcher.Command @($launcher.Args + $Args)
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (Test-Path (Join-Path $scriptDir "requirements.txt")) {
    $repoRoot = $scriptDir
} else {
    $repoRoot = Split-Path -Parent $scriptDir
}

$venvPath = Join-Path $repoRoot ".venv"

if (-not (Test-Path $venvPath)) {
    Write-Host "Criando ambiente virtual em $venvPath" -ForegroundColor Green
    Invoke-Python -Args @("-m", "venv", $venvPath)
} else {
    Write-Host "Ambiente virtual já existe em $venvPath" -ForegroundColor Yellow
}

$pythonExe = Join-Path $venvPath "Scripts/python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "Não foi possível localizar $pythonExe. Verifique se o Python foi instalado corretamente."
}

Write-Host "Atualizando pip" -ForegroundColor Green
& $pythonExe -m pip install --upgrade pip

Write-Host "Instalando dependências" -ForegroundColor Green
$requirements = Join-Path $repoRoot "requirements.txt"
& $pythonExe -m pip install -r $requirements

$env:PYTHONPATH = $repoRoot

Write-Host "Banco de dados será criado automaticamente ao iniciar o servidor." -ForegroundColor Green

if (-not $SkipRun) {
    Write-Host "Iniciando servidor em http://$Host:$Port" -ForegroundColor Green
    & $pythonExe -m uvicorn bpo_app.main:app --host $Host --port $Port
} else {
    Write-Host "Instalação concluída. Execute:" -ForegroundColor Green
    Write-Host "  $venvPath\Scripts\uvicorn.exe bpo_app.main:app --host $Host --port $Port"
}
