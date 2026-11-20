#!/bin/sh
# SHADOW를 Mac 로그인 때 자동으로 켜기 (macOS 사용자 LaunchAgent). 관리자 권한 필요 없음.
#   ./autostart.sh on      켜기 (지금 바로 시작 + 다음 로그인부터 자동)
#   ./autostart.sh off     끄기 (자동 실행 해제 + 지금 서버 종료)
#   ./autostart.sh status  상태 보기
# 서버는 이 Mac 안(127.0.0.1:8777)에서만 열리고, 꺼지면 launchd가 다시 켠다.
cd "$(dirname "$0")" || exit 1
HERE="$(pwd)"
LABEL="com.dodo-yong.shadow"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
PY="$(command -v python3)"
UID_N="$(id -u)"

case "$1" in
  on)
    [ -n "$PY" ] || { echo "python3가 없어요."; exit 1; }
    mkdir -p "$HERE/data" "$HOME/Library/LaunchAgents"
    # 이미 손으로 켠 SHADOW가 8777을 쓰고 있으면 끈다 (자동 실행이 대신 맡음)
    OLD="$(lsof -tiTCP:8777 -sTCP:LISTEN 2>/dev/null)"
    [ -n "$OLD" ] && ps -p "$OLD" -o command= | grep -q "shadowing-coach\|start.py" && kill "$OLD" && sleep 1
    cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array><string>$PY</string><string>$HERE/start.py</string><string>--no-browser</string></array>
  <key>WorkingDirectory</key><string>$HERE</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key><string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    <key>SHADOW_NO_BROWSER</key><string>1</string>
    <key>PYTHONUNBUFFERED</key><string>1</string>
  </dict>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ProcessType</key><string>Background</string>
  <key>StandardOutPath</key><string>$HERE/data/shadow.log</string>
  <key>StandardErrorPath</key><string>$HERE/data/shadow.log</string>
</dict>
</plist>
EOF
    launchctl bootout "gui/$UID_N/$LABEL" 2>/dev/null
    launchctl bootstrap "gui/$UID_N" "$PLIST" && echo "✅ 자동 실행 켬: 지금 시작했고, 다음 로그인부터 자동으로 켜져요 → http://127.0.0.1:8777/"
    ;;
  off)
    launchctl bootout "gui/$UID_N/$LABEL" 2>/dev/null
    rm -f "$PLIST"
    echo "⏹ 자동 실행 해제. 필요할 때는 'SHADOW 실행.command'를 더블클릭하세요."
    ;;
  status)
    if launchctl print "gui/$UID_N/$LABEL" >/dev/null 2>&1; then echo "자동 실행: 켜짐"; else echo "자동 실행: 꺼짐"; fi
    if curl -s -m 2 http://127.0.0.1:8777/api/status >/dev/null; then echo "서버: 동작 중 → http://127.0.0.1:8777/"; else echo "서버: 꺼짐"; fi
    ;;
  *)
    echo "사용: ./autostart.sh on | off | status"; exit 1 ;;
esac
