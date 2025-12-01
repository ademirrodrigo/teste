@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

REM Inicializa o painel Streamlit do Coletor Fiscal v3.2.
REM - Garante ambiente virtual e dependencias
REM - Define porta e endereco de escuta
REM - Executa o painel web

SET APP_DIR=%~dp0
SET VENV_DIR=%APP_DIR%\.venv
SET STREAMLIT_ENTRY=%APP_DIR%web\app.py

IF NOT EXIST "%VENV_DIR%\Scripts\activate.bat" (
    echo [INFO] Ambiente virtual nao encontrado. Executando install.bat...
    CALL "%APP_DIR%install.bat"
)

IF NOT EXIST "%VENV_DIR%\Scripts\activate.bat" (
    echo [ERRO] Ambiente virtual nao foi criado. Verifique as mensagens anteriores.
    EXIT /B 1
)

CALL "%VENV_DIR%\Scripts\activate.bat"

python -c "import importlib.util, sys; sys.exit(0 if importlib.util.find_spec('streamlit') else 1)"
IF ERRORLEVEL 1 (
    echo [INFO] Dependencias ausentes. Instalando requirements...
    python -m pip install --upgrade pip
    python -m pip install -r "%APP_DIR%requirements.txt"
)

IF NOT DEFINED PORTA (
    SET PORTA=8501
)

IF NOT DEFINED ENDERECO (
    SET ENDERECO=0.0.0.0
)

echo Iniciando Streamlit em %ENDERECO%:%PORTA% ...
python -m streamlit run "%STREAMLIT_ENTRY%" --server.port %PORTA% --server.address %ENDERECO%

ENDLOCAL
