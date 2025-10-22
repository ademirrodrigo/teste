[CmdletBinding()]
param(
    [string]$Host = "0.0.0.0",
    [int]$Port = 8000,
    [switch]$SkipRun
)

$ErrorActionPreference = "Stop"

Write-Host "==== Instalação do BPO Financeiro (Windows) ====" -ForegroundColor Cyan

function New-RandomString {
    param(
        [int]$Length = 32
    )
    $chars = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%*-_"
    -join ((1..$Length) | ForEach-Object { $chars[(Get-Random -Maximum $chars.Length)] })
}

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

$envFile = Join-Path $repoRoot ".env"
if (-not (Test-Path $envFile)) {
    $secretKey = New-RandomString -Length 64
    $adminPassword = New-RandomString -Length 16
    $adminEmail = "admin@bpo.local"
    $envContent = @(
        "BPO_SECRET_KEY=$secretKey",
        "BPO_ADMIN_EMAIL=$adminEmail",
        "BPO_ADMIN_PASSWORD=$adminPassword",
        "BPO_ADMIN_NAME=Administrador"
    )
    Set-Content -Path $envFile -Value $envContent -Encoding UTF8
    Write-Host "Arquivo .env criado em $envFile" -ForegroundColor Green
    Write-Host "Credenciais iniciais do administrador:" -ForegroundColor Yellow
    Write-Host "  E-mail: $adminEmail" -ForegroundColor Yellow
    Write-Host "  Senha:  $adminPassword" -ForegroundColor Yellow
    Write-Host "Altere esses valores no arquivo .env após o primeiro acesso." -ForegroundColor Yellow
} else {
    Write-Host "Arquivo .env já existe. Mantendo configurações atuais." -ForegroundColor Yellow
}

$env:PYTHONPATH = $repoRoot

Write-Host "Banco de dados será criado automaticamente ao iniciar o servidor." -ForegroundColor Green

if (-not $SkipRun) {
    Write-Host "Iniciando servidor em http://$Host:$Port" -ForegroundColor Green
    & $pythonExe -m uvicorn bpo_app.main:app --host $Host --port $Port
} else {
    Write-Host "Instalação concluída. Execute:" -ForegroundColor Green
    Write-Host "  $venvPath\Scripts\uvicorn.exe bpo_app.main:app --host $Host --port $Port"
}
