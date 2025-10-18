<#!
.SYNOPSIS
    Instalador único do monitor eCAC para Windows 11.
.DESCRIPTION
    Automatiza a execução de install.py localizando o interpretador Python 3 disponível.
    Gere este script e execute em um PowerShell com permissões adequadas.
!>

Write-Host "==== Monitor eCAC :: Instalador Windows 11 ====" -ForegroundColor Cyan

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path $scriptDir -Parent
Set-Location $projectRoot

$pythonExe = $null
$pythonArgs = @()

$pythonCandidates = @("py", "python3", "python")
foreach ($candidate in $pythonCandidates) {
    $command = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($null -ne $command) {
        if ($command.Name -eq "py") {
            $pythonExe = $command.Path
            $pythonArgs = @("-3", "install.py")
        } else {
            $pythonExe = $command.Path
            $pythonArgs = @("install.py")
        }
        break
    }
}

if (-not $pythonExe) {
    Write-Error "Python 3 não encontrado. Instale em https://www.python.org/downloads/ e marque 'Add Python to PATH'."
    exit 1
}

Write-Host "Usando Python em: $pythonExe" -ForegroundColor Yellow

try {
    & $pythonExe @pythonArgs
    if ($LASTEXITCODE -ne 0) {
        throw "install.py retornou código $LASTEXITCODE"
    }
    Write-Host "Instalação concluída. Consulte as instruções impressas acima para iniciar API, painel e monitor." -ForegroundColor Green
} catch {
    Write-Error "Falha ao executar install.py: $_"
    exit 1
}
