@echo off
cd /d D:\dev\trading-dashboard

echo Ativando ambiente virtual...
call .venv\Scripts\activate

echo Iniciando API...
start cmd /k ".venv\Scripts\python.exe local_api.py"

timeout /t 3

echo Iniciando APP WEB...
start cmd /k ".venv\Scripts\python.exe app_web.py"

timeout /t 3

echo Abrindo navegador LOCAL...
start http://127.0.0.1:5000