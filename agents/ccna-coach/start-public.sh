#!/bin/sh
# DY-003 TRACER를 다른 사람도 쓸 수 있게 연다.
#  1) 답변 서버(server.py)를 켜고  2) Cloudflare 임시 터널로 공개 주소를 만든 뒤
#  3) 손님에게 줄 '링크'와 '접속 코드'를 보여 준다.  끄기: Ctrl+C (서버·터널 함께 꺼짐)
# 비용 없음: Cloudflare 임시 터널(가입 불필요) + 제미나이 무료 등급.
cd "$(dirname "$0")" || exit 1
command -v cloudflared >/dev/null || { echo "cloudflared가 없습니다: brew install cloudflared"; exit 1; }

LOGDIR="${TMPDIR:-/tmp}/tracer"; mkdir -p "$LOGDIR"
SRV_LOG="$LOGDIR/server.log"; TUN_LOG="$LOGDIR/tunnel.log"

# 접속 코드: .env 의 CCNA_ACCESS_CODE, 없으면 이번 실행용으로 새로 만든다
CODE="$(grep -E '^CCNA_ACCESS_CODE=' ../../.env 2>/dev/null | cut -d= -f2-)"
[ -n "$CODE" ] || CODE="$(python3 -c 'import secrets;print(secrets.token_hex(3))')"
export CCNA_ACCESS_CODE="$CODE"

python3 server.py >"$SRV_LOG" 2>&1 &
SRV=$!
cleanup() { kill "$SRV" "$TUN" 2>/dev/null; echo "\n서버와 터널을 껐어요."; }
trap cleanup EXIT INT TERM
sleep 1
kill -0 "$SRV" 2>/dev/null || { cat "$SRV_LOG"; exit 1; }

cloudflared tunnel --no-autoupdate --url "http://127.0.0.1:${CCNA_PORT:-8765}" >"$TUN_LOG" 2>&1 &
TUN=$!
URL=""
for i in $(seq 1 30); do
  URL="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$TUN_LOG" | head -1)"
  [ -n "$URL" ] && break
  sleep 1
done
[ -n "$URL" ] || { echo "터널 주소를 받지 못했어요:"; tail -5 "$TUN_LOG"; exit 1; }

echo "🧠 DY-003 TRACER 공개 중"
echo ""
echo "  손님에게 보낼 링크:  https://dodo-yong.github.io/Obsidian/ccna/#server=$URL"
echo "  접속 코드:          $CODE      (링크와 따로 알려 주세요)"
echo ""
echo "  서버 주소만:        $URL"
echo "  손님 제한:          1명당 시간당 ${CCNA_GUEST_PER_HOUR:-30}번, 전체 하루 ${CCNA_DAILY_LIMIT:-300}번"
echo "  끄기:               Ctrl+C  (끄면 위 주소는 더 이상 동작하지 않아요. 다시 켜면 주소가 바뀝니다)"
echo ""
wait "$TUN"
