#!/bin/sh
# Heartline을 누구나 쓸 수 있게 연다.
#  1) 답변 서버(server.py)를 켜고  2) Cloudflare 임시 터널로 공개 주소를 받은 뒤
#  3) 그 주소를 docs/heartline/server.json 에 적어 그 파일만 GitHub에 올린다 → 공개 화면이 자동으로 연결.
#  끄기: Ctrl+C → 서버·터널을 끄고 server.json 을 '꺼짐'으로 올린다.
# 비용 없음: Cloudflare 임시 터널(가입 불필요) + 제미나이 무료 등급 + GitHub Pages.
cd "$(dirname "$0")" || exit 1
command -v cloudflared >/dev/null || { echo "cloudflared가 없습니다: brew install cloudflared"; exit 1; }

PORT="${HEARTLINE_PORT:-8766}"
REPO="$(cd ../../.. && pwd)"
STATUS="$REPO/docs/heartline/server.json"
LOGDIR="${TMPDIR:-/tmp}/heartline"; mkdir -p "$LOGDIR"
SRV_LOG="$LOGDIR/server.log"; TUN_LOG="$LOGDIR/tunnel.log"

publish() {  # $1 = 주소 또는 빈 값(꺼짐). server.json 만 커밋·푸시한다.
  [ "${HEARTLINE_NO_PUBLISH:-}" = "1" ] && return 0
  if [ -n "$1" ]; then
    printf '{"url": "%s", "updated": "%s"}\n' "$1" "$(date '+%Y-%m-%dT%H:%M:%S%z')" > "$STATUS"
  else
    printf '{"url": null, "updated": "%s"}\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" > "$STATUS"
  fi
  ( cd "$REPO" && git add docs/heartline/server.json \
    && git commit -q -m "Heartline 서버 주소 갱신: ${1:-꺼짐}" -- docs/heartline/server.json \
    && git push -q ) >/dev/null 2>&1 \
    && echo "  (공개 화면에 서버가 $([ -n "$1" ] && echo 켜졌다고 || echo 꺼졌다고) 알렸어요. 1~2분 뒤 반영)" \
    || echo "  ⚠️ server.json을 GitHub에 올리지 못했어요."
}

python3 server.py >"$SRV_LOG" 2>&1 &
SRV=$!
TUN=""
cleanup() {
  trap - EXIT INT TERM
  kill "$SRV" $TUN 2>/dev/null
  echo ""; echo "서버와 터널을 껐어요."
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

echo "💗 Heartline 공개 중"
echo "  서버 주소:  $URL"
echo "  이 컴퓨터:  http://127.0.0.1:$PORT"
echo "  손님 제한:  1명당 시간당 ${HEARTLINE_GUEST_PER_HOUR:-30}번, 전체 하루 ${HEARTLINE_DAILY_LIMIT:-300}번"
echo "  끄기:       Ctrl+C"
publish "$URL"
wait "$TUN"
