#!/bin/sh
# 공개 사이트(docs/) 버전 올리기. 페이지는 열릴 때 version.json 과 자기 버전을 비교해,
# 더 새 버전이 있으면 한 번 자동 새로고침한다(브라우저 캐시 때문에 예전 화면이 보이는 문제 방지).
# docs/ 의 HTML을 고친 뒤 커밋 전에 실행:  scripts/bump-site-version.sh
cd "$(dirname "$0")/.." || exit 1
V="$(date +%Y%m%d%H%M%S)"
for f in docs/index.html docs/terminal.html docs/ccna/index.html docs/ccna/about.html docs/ccna/app.html docs/heartline/prd.html docs/heartline/checklist.html docs/heartline/tests.html docs/heartline/index.html docs/heartline/deck.html; do
  sed -i '' -E "s/var SITE_V = '[0-9]+';/var SITE_V = '$V';/" "$f"
  sed -i '' -E "s/tracer-how\.(css|js)\?v=[0-9]+/tracer-how.\1?v=$V/g" "$f"
  sed -i '' -E "s/tracer-(site|auth)\.(css|js)\?v=[0-9]+/tracer-\1.\2?v=$V/g" "$f"
  sed -i '' -E "s/href=\"style\.css\?v=[0-9]+/href=\"style.css?v=$V/g" "$f"
  sed -i '' -E "s/([\"/])(how|app)\.(css|js)\?v=[0-9]+/\1\2.\3?v=$V/g" "$f"
done
printf '{"v": "%s"}\n' "$V" > docs/version.json
# 소개 페이지 맨 위 git log 상자도 실제 커밋 기록으로 갱신 (하루 커밋이 많으면 축약)
python3 scripts/update-site-log.py
echo "사이트 버전: $V"
