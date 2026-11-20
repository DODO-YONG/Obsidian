#!/bin/sh
# 맥: 더블클릭하면 SHADOW 서버가 켜지고 브라우저가 열려요.
cd "$(dirname "$0")" || exit 1
python3 start.py
echo ""
printf "엔터를 누르면 창이 닫혀요..."; read _
