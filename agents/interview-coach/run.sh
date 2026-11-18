#!/bin/sh
# 면접 코치 실행: .env가 있으면 읽고, 가상환경 파이썬으로 실행
cd "$(dirname "$0")"
[ -f .env ] && set -a && . ./.env && set +a
exec .venv/bin/python main.py
