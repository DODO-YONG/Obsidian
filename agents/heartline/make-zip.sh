#!/bin/sh
# 다른 사람에게 줄 압축 파일 만들기 → wiki/projects/heartline/output/제출/YYYY_MM_DD_heartline_4_앱.zip
# 구조: Heartline/ (시작하기 안내서 · 더블클릭 실행 파일 · start.py · server/ · web/)
# 키(.env)·개인 설정·공개용 스크립트(start-public.sh)는 넣지 않는다.
set -e
cd "$(dirname "$0")"
REPO="$(cd ../.. && pwd)"
OUT="$REPO/wiki/projects/heartline/output/제출/$(date +%Y_%m_%d)_heartline_4_앱.zip"; mkdir -p "$(dirname "$OUT")"
TMP="$(mktemp -d)"; D="$TMP/Heartline"
mkdir -p "$D/server/tests/scenarios" "$D/web"
cp guide/시작하기.html guide/시작하기.txt "Heartline 실행.command" "Heartline 실행.bat" start.py "$D/"
cp server/server.py server/prompts.py server/safety.py server/gemini_client.py server/demo.py server/.env.example "$D/server/"
cp server/tests/*.py "$D/server/tests/"; cp server/tests/scenarios/*.json "$D/server/tests/scenarios/"
cp "$REPO/docs/heartline/index.html" "$REPO/docs/heartline/app.js" "$REPO/docs/heartline/app.css" "$D/web/"
chmod +x "$D/Heartline 실행.command"
rm -f "$OUT"
python3 - "$TMP" "$OUT" <<'PY'
import os, sys, zipfile, stat
root, out = sys.argv[1], sys.argv[2]
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:      # 한글 파일 이름은 UTF-8 표시로 저장(윈도우에서도 안 깨짐)
    for dp, dns, fns in os.walk(os.path.join(root, "Heartline")):
        dns.sort()
        for fn in sorted(fns):
            full = os.path.join(dp, fn); rel = os.path.relpath(full, root)
            zi = zipfile.ZipInfo.from_file(full, rel); zi.compress_type = zipfile.ZIP_DEFLATED
            mode = 0o755 if fn.endswith((".command", ".py")) else 0o644
            zi.external_attr = (stat.S_IFREG | mode) << 16
            with open(full, "rb") as f: z.writestr(zi, f.read())
PY
rm -rf "$TMP"
echo "압축 파일: $OUT"
python3 -c "import zipfile,sys;z=zipfile.ZipFile(sys.argv[1]);print(len(z.namelist()),'files', all(i.flag_bits & 0x800 or i.filename.isascii() for i in z.infolist()))" "$OUT"
