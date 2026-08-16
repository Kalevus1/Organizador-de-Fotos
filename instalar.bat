@echo off
REM ============================================================
REM  Instalador del Organizador de Fotos
REM ============================================================
cd /d "%~dp0"

echo Creando entorno de Python (.venv) con Python 3.12...
py -3.12 -m venv .venv
if errorlevel 1 (
  echo ERROR: necesitas Python 3.12 instalado (https://www.python.org/downloads/).
  pause
  exit /b 1
)

echo Instalando librerias...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt

echo.
echo Listo. Ahora ejecuta "Organizar fotos.bat".
pause
