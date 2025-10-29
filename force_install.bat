@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

REM Forca uma reinstalacao completa do ambiente Coletor Fiscal v3.2.
REM - Remove o ambiente virtual existente
REM - Detecta o executavel Python disponivel
REM - Cria um novo ambiente virtual
REM - Atualiza o pip e reinstala dependencias sem cache

SET "APP_DIR=%~dp0"
SET "VENV_DIR=%APP_DIR%\.venv"
SET "REQ_FILE=%APP_DIR%\requirements.txt"

CALL :find_python || EXIT /B 1

IF EXIST "%VENV_DIR%" (
    echo [1/5] Removendo ambiente virtual antigo em %VENV_DIR% ...
    rmdir /s /q "%VENV_DIR%"
    IF EXIST "%VENV_DIR%" (
        echo [ERRO] Nao foi possivel remover o ambiente antigo. Feche janelas que possam estar usando-o e tente novamente.
        EXIT /B 1
    )
) ELSE (
    echo [1/5] Nenhum ambiente anterior encontrado.
)

echo [2/5] Criando novo ambiente virtual...
"%PYTHON_EXEC%" -m venv "%VENV_DIR%"
IF ERRORLEVEL 1 (
    echo [ERRO] Falha ao criar o novo ambiente virtual.
    EXIT /B 1
)

CALL "%VENV_DIR%\Scripts\activate.bat" || EXIT /B 1

echo [3/5] Atualizando pip...
python -m pip install --upgrade pip --disable-pip-version-check
IF ERRORLEVEL 1 (
    echo [ERRO] Falha ao atualizar o pip.
    EXIT /B 1
)

IF NOT EXIST "%REQ_FILE%" (
    echo [ERRO] Arquivo requirements.txt nao encontrado em %REQ_FILE%.
    EXIT /B 1
)

echo [4/5] Instalando dependencias sem utilizar cache...
python -m pip install --no-cache-dir -r "%REQ_FILE%"
IF ERRORLEVEL 1 (
    echo [ERRO] Falha na instalacao das dependencias. Verifique sua conexao e tente novamente.
    EXIT /B 1
)

echo [5/5] Reinstalacao concluida com sucesso.
ENDLOCAL
EXIT /B 0

:find_python
FOR %%P IN (py.exe python.exe) DO (
    WHERE %%P >NUL 2>&1
    IF NOT ERRORLEVEL 1 (
        SET "PYTHON_EXEC=%%P"
        EXIT /B 0
    )
)

echo [ERRO] Python 3 nao encontrado no PATH. Instale-o de https://www.python.org/downloads/windows/ e tente novamente.
EXIT /B 1
