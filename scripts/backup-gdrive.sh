#!/bin/sh
# 옵시디언 볼트 전체(.env 등 GitHub 제외 파일 포함)를 구글 드라이브에 백업한다.
# 변경·삭제된 기존 파일은 드라이브의 _archive/날짜 폴더에 따로 보관해 실수 삭제를 복구할 수 있다.
#   사용:
#     scripts/backup-gdrive.sh            # 실제 백업 실행
#     scripts/backup-gdrive.sh --dry-run  # 올릴 목록만 미리 보기
#   환경변수(선택):
#     RCLONE_REMOTE=gdrive                # rclone 리모트 이름
#     GDRIVE_DEST=Obsidian-backup         # 구글 드라이브 루트 폴더 이름
set -eu

VAULT="$(cd "$(dirname "$0")/.." && pwd)"
REMOTE="${RCLONE_REMOTE:-gdrive}"
DEST_ROOT="${GDRIVE_DEST:-Obsidian-backup}"
DEST_LATEST="${REMOTE}:${DEST_ROOT}/latest"
DEST_ARCHIVE="${REMOTE}:${DEST_ROOT}/_archive/$(date '+%Y-%m-%d_%H%M')"
LOCK_DIR="/tmp/obsidian-gdrive-backup.lock"

DRY_RUN=""
if [ "${1:-}" = "--dry-run" ]; then
  DRY_RUN="--dry-run"
fi

if ! command -v rclone >/dev/null 2>&1; then
  echo "⛔ rclone이 설치되어 있지 않습니다. 'brew install rclone'으로 설치해 주세요."
  exit 1
fi

if ! rclone listremotes 2>/dev/null | grep -qx "${REMOTE}:"; then
  echo "⛔ rclone에 '${REMOTE}:' 리모트가 설정되어 있지 않습니다."
  echo "   터미널에서 아래 명령으로 구글 드라이브 로그인을 한 번 진행해 주세요:"
  echo "   rclone config create ${REMOTE} drive scope=drive"
  exit 1
fi

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  echo "⏳ 이미 구글 드라이브 백업이 실행 중입니다."
  exit 0
fi
trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 구글 드라이브 백업 시작 → ${DEST_LATEST}"

# .env·로컬 전용 문서·리포트 등 모두 포함하고, 재생성 가능한 무거운 부산물과 .git 만 제외
rclone sync "$VAULT" "$DEST_LATEST" \
  --backup-dir "$DEST_ARCHIVE" \
  --exclude ".git/**" \
  --exclude "**/.git/**" \
  --exclude "node_modules/**" \
  --exclude "**/node_modules/**" \
  --exclude ".venv/**" \
  --exclude "**/.venv/**" \
  --exclude "venv/**" \
  --exclude "**/venv/**" \
  --exclude "__pycache__/**" \
  --exclude "**/__pycache__/**" \
  --exclude "*.pyc" \
  --exclude ".pytest_cache/**" \
  --exclude "**/.pytest_cache/**" \
  --exclude "dist/**" \
  --exclude "build/**" \
  --exclude "test-results/**" \
  --exclude ".trash/**" \
  --exclude ".DS_Store" \
  --exclude "*.log" \
  --fast-list \
  --transfers 4 \
  --checkers 8 \
  --stats-one-line \
  --stats 30s \
  -v \
  $DRY_RUN

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ 구글 드라이브 백업 완료"
