#!/bin/sh
# 맥: 더블클릭하면 Heartline 이 켜지고 브라우저가 열려요.
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then
  python3 start.py
else
  echo "파이썬3가 필요해요. https://www.python.org/downloads/ 에서 설치한 뒤 다시 더블클릭하세요."
fi
echo ""
printf "엔터를 누르면 창이 닫혀요..."; read _
