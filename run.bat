@echo off
cd /d "%~dp0"
"C:\Users\omen\.conda\envs\diary-time-tracker\python.exe" test\process_new.py
start http://127.0.0.1:5001
"C:\Users\omen\.conda\envs\diary-time-tracker\python.exe" run.py
pause