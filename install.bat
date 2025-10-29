@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

REM Instalação do Coletor Fiscal em ambientes Windows 11.
REM - Detecta automaticamente o executável Python disponível
REM - Cria ambiente virtual isolado
REM - Atualiza o pip e instala dependências

SET "APP_DIR=%~dp0"
SET "VENV_DIR=%APP_DIR%\.venv"
SET "REQ_FILE=%APP_DIR%\requirements.txt"

CALL :find_python || EXIT /B 1

IF NOT EXIST "%REQ_FILE%" (
    echo [ERRO] Arquivo requirements.txt nao encontrado em %REQ_FILE%.
    EXIT /B 1
)

IF NOT EXIST "%VENV_DIR%" (
    echo [1/4] Criando ambiente virtual em %VENV_DIR% ...
    "%PYTHON_EXEC%" -m venv "%VENV_DIR%"
    IF ERRORLEVEL 1 (
        echo [ERRO] Falha ao criar o ambiente virtual.
        EXIT /B 1
    )
) ELSE (
    echo [1/4] Utilizando ambiente virtual existente em %VENV_DIR%.
)

CALL "%VENV_DIR%\Scripts\activate.bat" || EXIT /B 1

echo [2/4] Atualizando pip...
python -m pip install --upgrade pip --disable-pip-version-check
IF ERRORLEVEL 1 (
    echo [ERRO] Falha ao atualizar o pip.
    EXIT /B 1
)

echo [3/4] Instalando dependencias...
python -m pip install -r "%REQ_FILE%"
IF ERRORLEVEL 1 (
    echo [ERRO] Falha na instalacao das dependencias.
    EXIT /B 1
)

IF NOT DEFINED PORTA (
    SET "PORTA=8501"
)
IF NOT DEFINED ENDERECO (
    SET "ENDERECO=0.0.0.0"
)

echo [4/4] Ambiente instalado com sucesso.
echo Utilize o comando abaixo para iniciar o painel:
echo    start.bat

echo Para executar manualmente:
echo    python -m streamlit run web\app.py --server.port %PORTA% --server.address %ENDERECO%

echo Ajuste as variaveis com:
echo    set PORTA=8502   ^(cmd.exe^)

echo ou

echo    $env:PORTA=8502 ^(PowerShell^)

echo Certifique-se de preencher o arquivo .env com as variaveis corretas.
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
