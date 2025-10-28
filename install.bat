@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

REM Instalação do Coletor Fiscal em ambientes Windows 11.
REM - Cria ambiente virtual
REM - Instala dependências

SET APP_DIR=%~dp0
SET VENV_DIR=%APP_DIR%\.venv

IF NOT EXIST "%VENV_DIR%" (
    python -m venv "%VENV_DIR%"
)

CALL "%VENV_DIR%\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r "%APP_DIR%\requirements.txt"

echo.
echo Ambiente instalado com sucesso.
echo Execute: streamlit run web/app.py --server.port %PORTA% --server.address 0.0.0.0
echo Certifique-se de preencher o arquivo .env com as variaveis corretas.
ENDLOCAL
