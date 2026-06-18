@echo off
cd /d D:\dev\trading-dashboard

echo Ativando ambiente virtual...
call .venv\Scripts\activate

echo Iniciando API...
start cmd /k ".venv\Scripts\python.exe local_api.py"

timeout /t 5

echo Iniciando NGROK...
start cmd /k "ngrok http 5001"

timeout /t 8

echo Abrindo navegador...
start https://trading-dashboard-su8v.onrender.com