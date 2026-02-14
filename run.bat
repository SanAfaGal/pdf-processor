@echo off
REM Run PDF Processor using the project .venv
set VENV=%~dp0.venv
set PY=%VENV%\Scripts\python.exe

if not exist "%PY%" (
    echo No se encontro el entorno virtual. Cree uno con:
    echo   python -m venv .venv
    echo   .venv\Scripts\activate.bat
    echo   pip install -r requirements.txt
    exit /b 1
)

"%PY%" "%~dp0main.py" %*
