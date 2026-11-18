#!/bin/sh
# 공개 사이트(docs/) 버전 올리기. 페이지는 열릴 때 version.json 과 자기 버전을 비교해,
# 더 새 버전이 있으면 한 번 자동 새로고침한다(브라우저 캐시 때문에 예전 화면이 보이는 문제 방지).
# docs/ 의 HTML을 고친 뒤 커밋 전에 실행:  scripts/bump-site-version.sh
cd "$(dirname "$0")/.." || exit 1
V="$(date +%Y%m%d%H%M%S)"
for f in docs/index.html docs/terminal.html docs/ccna/index.html; do
  sed -i '' -E "s/var SITE_V = '[0-9]+';/var SITE_V = '$V';/" "$f"
done
printf '{"v": "%s"}\n' "$V" > docs/version.json
echo "사이트 버전: $V"
