@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

REM Executa verificacoes rapidas do ambiente Coletor Fiscal v3.2.
REM - Valida existencia do ambiente virtual
REM - Checa conflitos de dependencias com "pip check"
REM - Compila o codigo fonte para garantir ausencia de erros de sintaxe

SET APP_DIR=%~dp0
SET VENV_DIR=%APP_DIR%\.venv

IF NOT EXIST "%VENV_DIR%\Scripts\activate.bat" (
    echo [ERRO] Ambiente virtual nao encontrado em %VENV_DIR%.
    echo Execute install.bat ou force_install.bat para preparar o ambiente.
    EXIT /B 1
)

CALL "%VENV_DIR%\Scripts\activate.bat" || EXIT /B 1

echo [1/3] Verificando versao do Python...
python --version || EXIT /B 1

echo [2/3] Conferindo dependencias com pip check...
python -m pip check
IF ERRORLEVEL 1 (
    echo.
    echo [AVISO] Conflitos detectados. Execute "force_install.bat" ou reinstale dependencias manualmente.
    EXIT /B 1
)

echo [3/3] Compilando fontes (app/ e web/)...
python -m compileall "%APP_DIR%app" "%APP_DIR%web"
IF ERRORLEVEL 1 (
    echo.
    echo [ERRO] Falha na compilacao. Analise as mensagens acima.
    EXIT /B 1
)

echo.
echo Ambiente validado com sucesso.

ENDLOCAL
EXIT /B 0
