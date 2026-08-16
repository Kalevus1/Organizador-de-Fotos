@echo off
REM Lanzador del Organizador de Fotos.
cd /d "%~dp0"

if exist ".venv\Scripts\pythonw.exe" (
  ".venv\Scripts\pythonw.exe" "organizador.py"
) else if exist "..\.venv_face\Scripts\pythonw.exe" (
  "..\.venv_face\Scripts\pythonw.exe" "organizador.py"
) else (
  echo No se encontro el entorno de Python.
  echo Ejecuta primero "instalar.bat".
  pause
)
