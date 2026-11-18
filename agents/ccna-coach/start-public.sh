#!/bin/sh
# DY-003 TRACER를 누구나 쓸 수 있게 연다.
#  1) 답변 서버(server.py)를 켜고  2) Cloudflare 임시 터널로 공개 주소를 만든 뒤
#  3) 그 주소를 docs/ccna/server.json 에 적어 GitHub에 올린다 → 공개 화면이 자동으로 연결.
#  끄기: Ctrl+C → 서버·터널을 끄고 server.json 을 '꺼짐'으로 올린다.
# 비용 없음: Cloudflare 임시 터널(가입 불필요) + 제미나이 무료 등급 + GitHub Pages.
cd "$(dirname "$0")" || exit 1
command -v cloudflared >/dev/null || { echo "cloudflared가 없습니다: brew install cloudflared"; exit 1; }

PORT="${CCNA_PORT:-8765}"
VAULT="$(cd ../.. && pwd)"
STATUS="$VAULT/docs/ccna/server.json"
LOGDIR="${TMPDIR:-/tmp}/tracer"; mkdir -p "$LOGDIR"
SRV_LOG="$LOGDIR/server.log"; TUN_LOG="$LOGDIR/tunnel.log"

publish() {  # $1 = 주소 또는 빈 값(꺼짐). server.json 만 커밋·푸시한다.
  [ "${CCNA_NO_PUBLISH:-}" = "1" ] && return 0
  if [ -n "$1" ]; then
    printf '{"url": "%s", "updated": "%s"}\n' "$1" "$(date '+%Y-%m-%dT%H:%M:%S%z')" > "$STATUS"
  else
    printf '{"url": null, "updated": "%s"}\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" > "$STATUS"
  fi
  ( cd "$VAULT" && git add docs/ccna/server.json \
    && git commit -q -m "TRACER 서버 주소 갱신: ${1:-꺼짐}" -- docs/ccna/server.json \
    && git push -q ) >/dev/null 2>&1 \
    && echo "  (공개 화면에 서버 ${1:+주소를}${1:-꺼짐을} 알렸어요. 1~2분 뒤 반영)" \
    || echo "  ⚠️ server.json을 GitHub에 올리지 못했어요. 손님은 아래 링크로 접속하게 해 주세요."
}

python3 server.py >"$SRV_LOG" 2>&1 &
SRV=$!
TUN=""
cleanup() {
  trap - EXIT INT TERM
  kill "$SRV" $TUN 2>/dev/null
  echo ""
  echo "서버와 터널을 껐어요."
  publish ""
  exit 0
}
trap cleanup EXIT INT TERM
sleep 1
kill -0 "$SRV" 2>/dev/null || { cat "$SRV_LOG"; trap - EXIT; exit 1; }

cloudflared tunnel --no-autoupdate --url "http://127.0.0.1:$PORT" >"$TUN_LOG" 2>&1 &
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
echo "  누구나 여기로:   https://dodo-yong.github.io/Obsidian/ccna/"
echo "  (바로 연결 링크: https://dodo-yong.github.io/Obsidian/ccna/#server=$URL )"
echo "  서버 주소:       $URL"
echo "  내 진도 보기:    http://127.0.0.1:$PORT  (이 Mac에서)"
echo "  손님 제한:       1명당 시간당 ${CCNA_GUEST_PER_HOUR:-30}번, 손님 전체 하루 ${CCNA_DAILY_LIMIT:-300}번"
echo "  끄기:            Ctrl+C"
publish "$URL"
echo ""
wait "$TUN"
