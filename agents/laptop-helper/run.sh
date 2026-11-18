#!/bin/sh
# DY-006 SWEEPER 실행: .env가 있으면 읽고, 가상환경 파이썬으로 실행 (인자 없으면 대화 모드)
cd "$(dirname "$0")"
[ -f .env ] && set -a && . ./.env && set +a
PY=.venv/bin/python; [ -x "$PY" ] || PY=python3
exec "$PY" main.py "$@"
