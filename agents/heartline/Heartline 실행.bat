@echo off
chcp 65001 >nul
rem 윈도우: 더블클릭하면 Heartline 이 켜지고 브라우저가 열려요.
cd /d "%~dp0"
where py >nul 2>nul && (py -3 start.py & goto end)
where python >nul 2>nul && (python start.py & goto end)
echo 파이썬이 필요해요. https://www.python.org/downloads/ 에서 설치할 때 "Add python.exe to PATH" 를 꼭 체크하세요.
:end
pause
