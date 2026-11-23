#!/bin/sh
# Claude가 제미나이(Antigravity CLI, agy)에게 일을 시킬 때 쓰는 입구.
# 규칙: wiki/_규칙/Claude·Gemini 협업 작업지시서.md
#   사용: scripts/gemini.sh [-m 모델] [-e 생각강도] "할 일"
#   예:   scripts/gemini.sh "raw/projects/ccna/ospf.pdf 를 읽고 요약 초안을 wiki/_inbox/ 에 써 줘"
#         scripts/gemini.sh -m gemini-3.8-flash-medium "OSPF hello 간격 기본값을 공식 문서로 확인해 줘"
# 안전장치:
#   - 사용자 Google AI Pro 로그인으로만 실행(API 키 변수는 지우고 실행 → 추가 요금 없음)
#   - scripts/agy-settings.json: private/·.env·reports/·.git 읽기 금지, 셸 명령 금지,
#     쓰기는 wiki/_inbox/ 만 허용. 허락이 필요한 동작은 자동 거부(헤드리스)
#   - 작업 폴더 = wiki/_inbox/ (git 제외 → 검토 전 초안은 공개되지 않음)
set -e
VAULT="$(cd "$(dirname "$0")/.." && pwd)"
AGY="${AGY:-$HOME/.local/bin/agy}"
MODEL="gemini-4-neon-high"
EFFORT=""
while getopts "m:e:" opt; do
  case "$opt" in
    m) MODEL="$OPTARG" ;;
    e) EFFORT="$OPTARG" ;;
    *) echo "사용: scripts/gemini.sh [-m 모델] [-e low|medium|high] \"할 일\"" >&2; exit 2 ;;
  esac
done
shift $((OPTIND - 1))
[ -n "$1" ] || { echo "할 일을 적어 주세요." >&2; exit 2; }
[ -x "$AGY" ] || { echo "agy가 없습니다. 위키 'Claude·Gemini 협업 작업지시서' 설치 방법을 보세요." >&2; exit 1; }

# 유료 API 경로를 막는다(구독 로그인만 사용)
unset GEMINI_API_KEY GOOGLE_API_KEY AGY_ADC_AUTH GOOGLE_GENAI_USE_VERTEXAI
if grep -q '"modelProvider": *"[^"]' "$HOME/.gemini/antigravity-cli/settings.json" 2>/dev/null; then
  echo "⛔ agy 설정에 modelProvider(API 키 방식)가 켜져 있어 멈춥니다. 추가 요금 방지." >&2
  exit 1
fi

mkdir -p "$VAULT/wiki/_inbox"
cd "$VAULT/wiki/_inbox"
set -- -p "$1" --model "$MODEL" --settings "$VAULT/scripts/agy-settings.json" --print-timeout 20m
[ -n "$EFFORT" ] && set -- "$@" --effort "$EFFORT"
exec "$AGY" "$@"
