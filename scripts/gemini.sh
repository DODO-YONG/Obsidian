#!/bin/sh
# Claude가 제미나이(Antigravity CLI, agy)에게 일을 시킬 때 쓰는 입구.
# 규칙: wiki/_규칙/Claude·Gemini 협업 작업지시서.md
#   사용: scripts/gemini.sh [-m 모델] [-e 생각강도] "할 일"
#   예:   scripts/gemini.sh "raw/projects/ccna/ospf.pdf 를 읽고 요약 초안을 wiki/_inbox/ 에 써 줘"
#         scripts/gemini.sh -m gemini-3.8-flash-medium "OSPF hello 간격 기본값을 공식 문서로 확인해 줘"
# 안전장치:
#   - 사용자 Google AI Pro 로그인으로만 실행(API 키 변수는 지우고 실행 → 추가 요금 없음)
#   - 유료 AI 크레딧 사용 끔(useG1Credits=false, 켜져 있으면 멈춤). 한도가 다 되면 주간 리필까지 기다림
#   - scripts/agy-settings.json: 볼트 전체 읽기·쓰기·셸·git 커밋 허용(Claude와 같은 권한).
#     셸은 OS 샌드박스(네트워크 없음 → 푸시는 Obsidian 자동 백업).
#     막는 것은 .env(키) 읽기(도구·셸 모두), raw/ 쓰기, 훅 건너뛰기뿐
#   - 작업 폴더 = 볼트 루트(GEMINI.md·CLAUDE.md 규칙을 따름)
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

# 유료 크레딧(한도 초과 시 AI credits 사용)이 켜져 있으면 멈춘다 — 한도가 다 되면 기다린다
if grep -q '"useG1Credits": *true' "$HOME/.gemini/antigravity-cli/settings.json" 2>/dev/null; then
  echo "⛔ agy 설정에 useG1Credits(유료 AI 크레딧)가 켜져 있어 멈춥니다. /config → Use AI Credits 끄기." >&2
  exit 1
fi
# 제미나이 모델만 쓴다(목록의 Claude 등 다른 회사 모델은 크레딧 차감 가능성)
case "$MODEL" in gemini-*) ;; *) echo "⛔ 제미나이 모델만 씁니다: $MODEL" >&2; exit 1 ;; esac

mkdir -p "$VAULT/wiki/_inbox"
cd "$VAULT"
set -- -p "$1" --model "$MODEL" --settings "$VAULT/scripts/agy-settings.json" --print-timeout 20m
[ -n "$EFFORT" ] && set -- "$@" --effort "$EFFORT"
exec "$AGY" "$@"
