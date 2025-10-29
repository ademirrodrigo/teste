@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

REM Inicializa o painel Streamlit do Coletor Fiscal v3.2.
REM - Ativa o ambiente virtual existente
REM - Detecta o executavel python apropriado dentro da venv
REM - Define porta e endereco de escuta
REM - Executa o painel web

SET "APP_DIR=%~dp0"
SET "VENV_DIR=%APP_DIR%\.venv"
SET "STREAMLIT_ENTRY=%APP_DIR%web\app.py"

IF NOT EXIST "%STREAMLIT_ENTRY%" (
    echo [ERRO] Arquivo de entrada Streamlit nao encontrado em %STREAMLIT_ENTRY%.
    EXIT /B 1
)

IF NOT EXIST "%VENV_DIR%\Scripts\activate.bat" (
    echo [ERRO] Ambiente virtual nao encontrado em %VENV_DIR%.
    echo Execute install.bat ou force_install.bat para preparar o ambiente.
    EXIT /B 1
)

CALL "%VENV_DIR%\Scripts\activate.bat" || EXIT /B 1

IF NOT DEFINED PORTA (
    SET "PORTA=8501"
)

IF NOT DEFINED ENDERECO (
    SET "ENDERECO=0.0.0.0"
)

echo Iniciando Streamlit em %ENDERECO%:%PORTA% ...
python -m streamlit run "%STREAMLIT_ENTRY%" --server.port %PORTA% --server.address %ENDERECO%

ENDLOCAL
EXIT /B 0
