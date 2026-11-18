#!/bin/sh
# private/ 폴더를 비공개 GitHub 저장소(DODO-YONG/Obsidian-private)에 백업한다.
# 바뀐 게 있을 때만 커밋·푸시. 푸시 전에 저장소가 '비공개'인지 확인하고, 아니면 멈춘다.
#   사용: scripts/backup-private.sh
set -e
VAULT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$VAULT/private" || { echo "private/ 폴더가 없습니다."; exit 1; }
[ -d .git ] || { echo "private/ 가 git 저장소가 아닙니다. 위키 '백업 현황' 페이지를 보세요."; exit 1; }

# 1) 비공개 저장소인지 확인 (공개면 절대 푸시하지 않음)
url="$(git remote get-url origin)"
repo="$(printf '%s' "$url" | sed -E 's#(https://github.com/|git@github.com:)##; s#\.git$##')"
vis="$(gh repo view "$repo" --json visibility --jq .visibility 2>/dev/null || true)"
if [ "$vis" != "PRIVATE" ]; then
  echo "⛔ $repo 가 비공개(PRIVATE)로 확인되지 않아 백업을 멈춥니다. (확인 결과: ${vis:-알 수 없음})"
  exit 1
fi

# 2) 바뀐 게 있을 때만 커밋 (커밋 전 키 검사는 ../.githooks 가 수행)
git add -A
if git diff --cached --quiet; then
  echo "바뀐 내용이 없습니다. (마지막 백업: $(git log -1 --format='%cd' --date=format:'%Y-%m-%d %H:%M'))"
  exit 0
fi
git commit -q -m "private 백업: $(date '+%Y-%m-%d %H:%M')"
git push -q
echo "✅ 비공개 저장소에 백업했습니다: $(git log -1 --format='%h %s')"
