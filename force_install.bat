@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

REM Forca uma reinstalacao completa do ambiente Coletor Fiscal v3.2.
REM - Remove o ambiente virtual existente
REM - Cria um novo ambiente virtual
REM - Atualiza o pip e instala dependencias do requirements.txt com cache limpo

SET APP_DIR=%~dp0
SET VENV_DIR=%APP_DIR%\.venv

IF EXIST "%VENV_DIR%" (
    echo Removendo ambiente virtual antigo em %VENV_DIR% ...
    rmdir /s /q "%VENV_DIR%"
)

python -m venv "%VENV_DIR%"
IF ERRORLEVEL 1 (
    echo [ERRO] Falha ao criar ambiente virtual.
    EXIT /B 1
)

CALL "%VENV_DIR%\Scripts\activate.bat"

python -m pip install --upgrade pip
IF ERRORLEVEL 1 (
    echo [ERRO] Falha ao atualizar o pip.
    EXIT /B 1
)

python -m pip install --no-cache-dir -r "%APP_DIR%requirements.txt"
IF ERRORLEVEL 1 (
    echo [ERRO] Falha na instalacao das dependencias. Verifique sua conexao e tente novamente.
    EXIT /B 1
)

echo.
echo Reinstalacao concluida com sucesso.
ENDLOCAL
