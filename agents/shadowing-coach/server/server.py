"""DY-008 SHADOW 서버 — 내 Mac 안에서만 도는 작은 서버 (파이썬 기본 기능만).

하는 일
- 유튜브 주소 → yt-dlp로 소리만 내려받기 → Whisper(whisper-cli, 로컬)로 받아 적어 문장 단위로 나누기
- 내 녹음 저장(문장마다 날짜별로 쌓음) → Whisper로 받아 적어 원문과 단어 비교
- 화면(web/) 제공

모든 파일은 agents/shadowing-coach/data/ 에만 저장되고 git에서 제외된다. 외부 AI로 보내는 것 없음.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
import uuid
from datetime import datetime
from http import HTTPStatus
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
DATA = Path(os.environ.get("SHADOW_DATA", ROOT / "data"))
MODELS = ROOT / "models"
MODEL = Path(os.environ.get("SHADOW_MODEL", MODELS / "ggml-base.en.bin"))
MAX_MINUTES = int(os.environ.get("SHADOW_MAX_MINUTES", "60"))

PAID_KEYS = ("ANTHROPIC_API_KEY", "OPENAI_API_KEY")
VID_RE = re.compile(r"^[A-Za-z0-9_-]{6,20}$")
REC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_\d{6}$")


def refuse_paid_billing(environ=None):
    environ = os.environ if environ is None else environ
    found = [k for k in PAID_KEYS if environ.get(k)]
    if found:
        raise SystemExit(f"💸 유료 과금 키({', '.join(found)})가 설정돼 있어 실행하지 않습니다. 키를 지우고 다시 실행하세요.")


def tool_status():
    return {
        "yt-dlp": bool(shutil.which("yt-dlp")),
        "ffmpeg": bool(shutil.which("ffmpeg")),
        "whisper-cli": bool(shutil.which("whisper-cli")),
        "model": MODEL.exists(),
    }


# ── Whisper → 단어 → 문장 ─────────────────────────────────────────

def run(cmd, timeout=None):
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0:
        tail = (p.stderr or p.stdout or "").strip().splitlines()[-3:]
        raise RuntimeError(f"{Path(cmd[0]).name} 실패: " + " / ".join(tail))
    return p


def to_wav16k(src, dst):
    run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(src), "-ar", "16000", "-ac", "1", str(dst)])


def loudness_db(wav):
    """16bit wav에서 가장 큰 50ms 구간의 소리 크기(dBFS). 무음 녹음 거르기용."""
    import array
    import math
    import wave
    with wave.open(str(wav)) as f:
        a = array.array("h", f.readframes(f.getnframes()))
        win = max(1, f.getframerate() // 20)
    best = 0.0
    for i in range(0, max(1, len(a) - win + 1), win):
        chunk = a[i:i + win]
        if chunk:
            best = max(best, math.sqrt(sum(x * x for x in chunk) / len(chunk)))
    return 20 * math.log10(best / 32768) if best else -120.0


def whisper_words(wav, prompt=None):
    """whisper-cli로 받아 적고 단어 목록 [{w, s, e}] (초) 를 돌려준다."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "out"
        cmd = ["whisper-cli", "-m", str(MODEL), "-f", str(wav), "-l", "en", "-ojf", "-of", str(out), "-np"]
        if prompt:
            cmd += ["--prompt", prompt[:200]]
        run(cmd)
        data = json.loads((Path(tmp) / "out.json").read_text(encoding="utf-8"))
    return tokens_to_words(data)


def tokens_to_words(data):
    words = []
    for seg in data.get("transcription", []):
        for t in seg.get("tokens", []):
            text = t.get("text", "")
            if not text or text.startswith("[_") or text.startswith("<|"):
                continue
            s, e = t["offsets"]["from"] / 1000, t["offsets"]["to"] / 1000
            if text.startswith(" ") or not words:
                if text.strip():
                    words.append({"w": text.strip(), "s": s, "e": e})
            else:
                words[-1]["w"] += text
                words[-1]["e"] = max(words[-1]["e"], e)
    return drop_noise(words)


def drop_noise(words):
    """[Music] (Applause) [Music playing] ♪ 같은 효과음 표시는 뺀다."""
    out, skip = [], False
    for w in words:
        t = w["w"]
        if not skip and t[:1] in "[(":
            skip = True
        if skip:
            if re.search(r"[\])][.,!?]?$", t):
                skip = False
            continue
        if "♪" in t or not re.search(r"[A-Za-z0-9]", t):
            continue
        out.append(w)
    return out


END_RE = re.compile(r"[.?!][\"')\]]*$")
ABBR = {"mr.", "mrs.", "ms.", "dr.", "st.", "vs.", "etc.", "e.g.", "i.e.", "u.s."}


def split_sentences(words, max_words=22, gap=1.2):
    sents, cur = [], []

    def flush():
        if cur:
            sents.append(list(cur))
            cur.clear()

    for i, w in enumerate(words):
        if cur and w["s"] - cur[-1]["e"] > gap:
            flush()
        cur.append(w)
        if END_RE.search(w["w"]) and w["w"].lower() not in ABBR:
            flush()
        elif len(cur) >= max_words:
            # 너무 길면 마지막 쉼표에서 자른다 (없으면 여기서)
            cut = max((k for k, x in enumerate(cur) if x["w"].endswith(",")), default=len(cur) - 1)
            head, tail = cur[: cut + 1], cur[cut + 1:]
            sents.append(head)
            cur[:] = tail
    flush()
    out = []
    for ws in sents:
        text = " ".join(x["w"] for x in ws).strip()
        if not re.search(r"[A-Za-z]", text):
            continue
        out.append({"text": text, "start": round(ws[0]["s"], 2), "end": round(ws[-1]["e"], 2),
                    "words": [{"w": x["w"], "s": round(x["s"], 2), "e": round(x["e"], 2)} for x in ws]})
    for i, s in enumerate(out):
        s["i"] = i
    return out


# ── 단어 비교 (발음 체크) ─────────────────────────────────────────

NUM = {"0": "zero", "1": "one", "2": "two", "3": "three", "4": "four", "5": "five", "6": "six",
       "7": "seven", "8": "eight", "9": "nine", "10": "ten"}


def norm(w):
    w = w.lower().replace("’", "'")
    w = re.sub(r"[^a-z0-9']", "", w).strip("'")
    return NUM.get(w, w)


def compare_words(ref, hyp):
    """ref: 원문 단어 문자열 목록, hyp: 내가 말한 단어 문자열 목록 → 정렬 결과와 점수."""
    a = [norm(x) for x in ref]
    b = [norm(x) for x in hyp]
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            dp[i][j] = dp[i + 1][j + 1] + 1 if a[i] and a[i] == b[j] else max(dp[i + 1][j], dp[i][j + 1])
    i = j = 0
    result = []  # {w, ok} for ref words; extra hyp words as {w, extra}
    while i < n and j < m:
        if a[i] and a[i] == b[j]:
            result.append({"w": ref[i], "ok": True}); i += 1; j += 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            result.append({"w": ref[i], "ok": False}); i += 1
        else:
            result.append({"w": hyp[j], "extra": True}); j += 1
    result += [{"w": ref[k], "ok": False} for k in range(i, n)]
    result += [{"w": hyp[k], "extra": True} for k in range(j, m)]
    counted = [x for x, k in zip(ref, a) if k]
    score = round(100 * dp[0][0] / len(counted)) if counted else 0
    return result, score


# ── 단어 뜻 (맥 내장 뉴에이스 영한사전, 인터넷·AI 없음) ─────────────

DICT_BIN = ROOT / "tools" / "dict-lookup"
DICT_CACHE = {}
SKIP_CLASSES = {"exg", "idmb", "xrg", "grnote", "etym", "subEntryBlock", "infg", "frmg", "sn", "syng", "usg"}


class _EntryParser(HTMLParser):
    """사전 항목 HTML → {head, pron, groups:[{pos, senses:[...]}]} (예문·숙어·참조는 뺀다)."""

    def __init__(self):
        super().__init__()
        self.stack = []  # 열린 span들의 class 집합
        self.head = ""; self.pron = ""; self.pron_done = False; self.groups = []
        self.sense = None

    def _in(self, c):
        return any(c in s for s in self.stack)

    def handle_starttag(self, tag, attrs):
        if tag in ("br", "img", "d:prn", "d:pos", "d:def"):
            return
        cls = set((dict(attrs).get("class") or "").split())
        self.stack.append(cls)
        if any(self._in(c) for c in SKIP_CLASSES):
            return
        if "gramb" in cls:
            self.groups.append({"pos": "", "senses": []})
        if "semb" in cls and self.groups and not self._in_parent("semb"):
            self.sense = []
            self.groups[-1]["senses"].append(self.sense)

    def _in_parent(self, c):
        return any(c in s for s in self.stack[:-1])

    def handle_endtag(self, tag):
        if tag in ("br", "img", "d:prn", "d:pos", "d:def"):
            return
        if self.stack:
            cls = self.stack.pop()
            if "ph" in cls and self.pron:
                self.pron_done = True

    def handle_data(self, data):
        if not self.stack or any(self._in(c) for c in SKIP_CLASSES):
            return
        if self._in("hw") and not self._in("gp") and not self.groups:
            self.head += data
        elif self._in("ph") and not self.pron_done:
            self.pron += data
        elif self._in("ps") and self.groups and not self.groups[-1]["pos"]:
            self.groups[-1]["pos"] = data.strip()
        elif self._in("trg") and self.sense is not None:
            self.sense.append(data)


def _clean(s):
    s = "".join(s).replace("（", "(").replace("）", ")")
    s = re.sub(r"《[^》]*》|〔[^〕]*〕|【[^】]*】|\[[^\]]*\]|\(※[^)]*\)", "", s)
    s = re.sub(r"\(\s*\)", "", s)
    s = re.sub(r"\s+", " ", s).replace(" ;", ";").strip(" ;,.")
    parts = list(dict.fromkeys(  # 반복된 뜻 정리 (; 와 , 단위)
        ", ".join(dict.fromkeys(y.strip() for y in x.split(", ") if y.strip())) for x in s.split(";") if x.strip()))
    return "; ".join(parts)[:70]


def parse_entry(html):
    pr = _EntryParser()
    pr.feed(html)
    groups = []
    for g in pr.groups:
        senses = [x for x in (_clean(s) for s in g["senses"]) if x][:3]
        if senses:
            groups.append({"pos": g["pos"], "senses": senses})
    return {"head": pr.head.strip(), "pron": pr.pron.strip(), "groups": groups[:3]}


def _fetch_entries(w):
    try:
        p = subprocess.run([str(DICT_BIN), w], capture_output=True, text=True, timeout=10)
        recs = json.loads(p.stdout or "[]")
    except (subprocess.SubprocessError, json.JSONDecodeError):
        return []

    def hm(r):  # 동음이의어 번호 (story 1 이야기 → story 2 층)
        m = re.search(r'\bhm="(\d+)"', r["html"])
        return int(m[1]) if m else 0
    # 접두사·접미사 항목(the-, -i)은 뺀다
    recs = sorted((r for r in recs if not r["t"].startswith("-") and not r["t"].endswith("-")), key=hm)
    entries = []
    for r in recs:
        e = parse_entry(r["html"])
        if e["groups"]:
            e["plain"] = re.sub(r"[·\s]", "", e["head"])
            entries.append(e)
    return entries


def _lemmas(w):
    out = []
    if w.endswith("ied"):
        out.append(w[:-3] + "y")
    if w.endswith("ed"):
        out += [w[:-1], w[:-2], w[:-3] if len(w) > 4 and w[-3] == w[-4] else ""]
    if w.endswith("ing"):
        out += [w[:-3], w[:-3] + "e", w[:-4] if len(w) > 5 and w[-4] == w[-5] else ""]
    if w.endswith("ies"):
        out.append(w[:-3] + "y")
    if w.endswith("es"):
        out.append(w[:-2])
    if w.endswith("s") and not w.endswith("ss"):
        out.append(w[:-1])
    return [x for x in dict.fromkeys(out) if len(x) >= 2 and x != w]


def dict_lookup(word):
    """단어 → {word, entries:[{head, pron, groups}]} (최대 3개). 없으면 None."""
    w = re.sub(r"[^A-Za-z'\-]", "", word).strip("'-")
    if not w or not DICT_BIN.exists():
        return None
    if w in DICT_CACHE:
        return DICT_CACHE[w]
    entries = _fetch_entries(w)
    # 철자가 같은 표제어가 있으면 그것만 (I → 'I'·'i', 요오드 기호는 뺌), 대소문자까지 같은 것을 앞에
    same = [e for e in entries if e["plain"].lower() == w.lower()]
    if same:
        entries = sorted(same, key=lambda e: e["plain"] != w)
        # graduated(형용사)만 있으면 기본형 graduate(동사) 뜻도 함께
        for lem in _lemmas(w.lower()):
            extra = [e for e in _fetch_entries(lem) if e["plain"].lower() == lem]
            if extra and w.lower().endswith(("ed", "ing")):
                # -ed·-ing은 동사에서 온 말이므로 기본형의 동사 뜻을 먼저
                extra[0]["groups"].sort(key=lambda g: "동사" not in g["pos"])
            if extra:
                entries += extra[:1]
                break
    out, seen = [], set()
    for e in entries:
        sig = json.dumps([e["head"], e["groups"]], ensure_ascii=False)
        if sig not in seen:
            seen.add(sig)
            out.append({k: e[k] for k in ("head", "pron", "groups")})
    result = {"word": w, "entries": out[:3]} if out else None
    DICT_CACHE[w] = result
    return result


# ── 저장소 ────────────────────────────────────────────────────────

def vdir(vid):
    if not VID_RE.match(vid or ""):
        raise ValueError("잘못된 영상 id")
    return DATA / vid


def read_json(p, default=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def write_json(p, obj):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(p)


def list_videos():
    out = []
    if DATA.exists():
        for d in DATA.iterdir():
            if not d.is_dir():  # shadow.log 같은 파일은 건너뜀
                continue
            meta = read_json(d / "meta.json")
            if meta and meta.get("ready"):
                out.append(meta)
    return sorted(out, key=lambda m: m.get("added", ""), reverse=True)


def list_recordings(vid, n):
    d = vdir(vid) / "rec" / str(n)
    recs = []
    if d.exists():
        for f in sorted(d.glob("*.json")):
            r = read_json(f)
            if r:
                recs.append(r)
    return recs


def rec_summary(vid):
    d = vdir(vid) / "rec"
    summary = {}
    if d.exists():
        for sd in d.iterdir():
            recs = [read_json(f) for f in sd.glob("*.json")]
            recs = [r for r in recs if r]
            if recs:
                recs.sort(key=lambda r: r["name"])
                summary[sd.name] = {"count": len(recs), "last": recs[-1].get("score"),
                                    "best": max(r.get("score", 0) for r in recs),
                                    "pitch": recs[-1].get("pitch")}
    return summary


# ── 가져오기 작업 (내려받기 → 받아 적기) ─────────────────────────

JOBS = {}
JOBS_LOCK = threading.Lock()


def set_job(jid, **kw):
    with JOBS_LOCK:
        JOBS[jid].update(kw)


def import_video(jid, url):
    try:
        set_job(jid, stage="영상 정보 확인 중")
        info = json.loads(run(["yt-dlp", "--no-playlist", "--no-warnings", "-J", url], timeout=120).stdout)
        vid = info["id"]
        dur = info.get("duration") or 0
        if dur and dur > MAX_MINUTES * 60:
            raise RuntimeError(f"영상이 {round(dur / 60)}분이에요. {MAX_MINUTES}분 이하만 가져올 수 있어요.")
        d = vdir(vid)
        meta = read_json(d / "meta.json") or {}
        if meta.get("ready"):
            set_job(jid, stage="이미 가져온 영상이에요", done=True, vid=vid)
            return
        d.mkdir(parents=True, exist_ok=True)
        meta = {"id": vid, "title": info.get("title", vid), "channel": info.get("channel") or info.get("uploader"),
                "duration": dur, "url": f"https://www.youtube.com/watch?v={vid}",
                "added": datetime.now().isoformat(timespec="seconds"), "ready": False}
        write_json(d / "meta.json", meta)

        set_job(jid, stage="소리 내려받는 중", vid=vid)
        for old in d.glob("source.*"):
            old.unlink()
        run(["yt-dlp", "--no-playlist", "--no-warnings", "-f", "bestaudio[ext=m4a]/bestaudio",
             "-o", str(d / "source.%(ext)s"), url], timeout=1800)
        src = next(d.glob("source.*"))
        set_job(jid, stage="소리 변환 중")
        run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(src), "-ac", "1", "-ar", "24000", "-b:a", "64k",
             str(d / "audio.mp3")])
        wav = d / "audio16k.wav"
        to_wav16k(src, wav)
        src.unlink()

        set_job(jid, stage=f"받아 적는 중 (Whisper · 영상 길이의 약 1/10~1/5 시간)")
        words = whisper_words(wav)
        wav.unlink()
        write_json(d / "words.json", words)
        sents = split_sentences(words)
        if not sents:
            raise RuntimeError("영어 문장을 찾지 못했어요.")
        write_json(d / "sentences.json", sents)
        meta.update(ready=True, sentences=len(sents))
        write_json(d / "meta.json", meta)
        set_job(jid, stage="완료", done=True, vid=vid)
    except Exception as e:  # noqa: BLE001
        set_job(jid, stage="실패", error=str(e), done=True)


def save_recording(vid, n, body, ctype):
    d = vdir(vid)
    sents = read_json(d / "sentences.json")
    if not sents or not (0 <= n < len(sents)):
        raise ValueError("문장이 없어요")
    ref = sents[n]
    rd = d / "rec" / str(n)
    rd.mkdir(parents=True, exist_ok=True)
    name = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    ext = ".mp4" if "mp4" in (ctype or "") else ".ogg" if "ogg" in (ctype or "") else ".webm"
    raw = rd / (name + ext)
    raw.write_bytes(body)
    wav = rd / (name + ".wav")
    try:
        to_wav16k(raw, wav)
    finally:
        raw.unlink(missing_ok=True)
    # 거의 무음이면 Whisper가 말을 지어내므로(예: "You") 아예 보내지 않는다
    words = whisper_words(wav) if loudness_db(wav) > -45 else []
    if not words:  # 아무 말도 못 알아들음(무음·마이크 문제) → 기록에 남기지 않는다
        wav.unlink(missing_ok=True)
        return {"empty": True}
    diff, score = compare_words([w["w"] for w in ref["words"]], [w["w"] for w in words])
    rec = {"name": name, "date": name[:10], "time": f"{name[11:13]}:{name[13:15]}",
           "text": " ".join(w["w"] for w in words), "words": words, "diff": diff, "score": score}
    write_json(rd / (name + ".json"), rec)
    return rec


# ── HTTP ─────────────────────────────────────────────────────────

CTYPES = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
          ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml", ".mp3": "audio/mpeg",
          ".wav": "audio/wav", ".json": "application/json"}


class Handler(BaseHTTPRequestHandler):
    server_version = "SHADOW"

    def log_message(self, fmt, *args):  # 조용히
        pass

    # helpers
    def send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path):
        path = Path(path)
        if not path.is_file():
            return self.send_json({"error": "없음"}, 404)
        data = path.read_bytes()
        size = len(data)
        rng = self.headers.get("Range")
        start, end = 0, size - 1
        if rng and rng.startswith("bytes="):
            a, _, b = rng[6:].partition("-")
            start = int(a) if a else max(0, size - int(b))
            end = int(b) if (a and b) else size - 1
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        else:
            self.send_response(200)
        self.send_header("Content-Type", CTYPES.get(path.suffix, "application/octet-stream"))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(data[start:end + 1])

    def body(self, limit=30_000_000):
        n = int(self.headers.get("Content-Length") or 0)
        if n > limit:
            raise ValueError("너무 커요")
        return self.rfile.read(n) if n else b""

    def local_only(self):
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in ("127.0.0.1", "localhost")

    # routes
    def do_GET(self):
        if not self.local_only():
            return self.send_json({"error": "로컬 전용"}, 403)
        p = unquote(urlparse(self.path).path)
        try:
            if p == "/":
                return self.send_file(WEB / "index.html")
            if p.startswith("/static/"):
                f = (WEB / p[8:]).resolve()
                if WEB.resolve() not in f.parents:
                    return self.send_json({"error": "없음"}, 404)
                return self.send_file(f)
            if p == "/api/status":
                return self.send_json({"tools": tool_status(), "model": MODEL.name})
            if p == "/api/videos":
                return self.send_json(list_videos())
            if p == "/api/dict":
                q = parse_qs(urlparse(self.path).query).get("w", [""])[0][:40]
                return self.send_json(dict_lookup(q) or {"word": q, "entries": [],
                                                         "missing": not DICT_BIN.exists()})
            m = re.fullmatch(r"/api/jobs/([a-f0-9]+)", p)
            if m:
                with JOBS_LOCK:
                    job = dict(JOBS.get(m[1]) or {"error": "작업 없음", "done": True})
                return self.send_json(job)
            m = re.fullmatch(r"/api/videos/([\w-]+)", p)
            if m:
                d = vdir(m[1])
                meta = read_json(d / "meta.json")
                if not meta:
                    return self.send_json({"error": "없음"}, 404)
                return self.send_json({"meta": meta, "sentences": read_json(d / "sentences.json", []),
                                       "recs": rec_summary(m[1])})
            m = re.fullmatch(r"/api/videos/([\w-]+)/sentences/(\d+)/recordings", p)
            if m:
                return self.send_json(list_recordings(m[1], int(m[2])))
            m = re.fullmatch(r"/media/([\w-]+)/audio\.mp3", p)
            if m:
                return self.send_file(vdir(m[1]) / "audio.mp3")
            m = re.fullmatch(r"/media/([\w-]+)/rec/(\d+)/([\d_-]+)\.wav", p)
            if m and REC_RE.match(m[3]):
                return self.send_file(vdir(m[1]) / "rec" / m[2] / f"{m[3]}.wav")
            return self.send_json({"error": "없음"}, 404)
        except ValueError as e:
            return self.send_json({"error": str(e)}, 400)

    def do_POST(self):
        if not self.local_only():
            return self.send_json({"error": "로컬 전용"}, 403)
        p = urlparse(self.path).path
        try:
            if p == "/api/videos":
                url = (json.loads(self.body(10_000) or b"{}").get("url") or "").strip()
                if not re.match(r"^https?://(www\.|m\.|music\.)?(youtube\.com|youtu\.be)/", url):
                    return self.send_json({"error": "유튜브 주소만 넣을 수 있어요"}, 400)
                jid = uuid.uuid4().hex[:12]
                with JOBS_LOCK:
                    JOBS[jid] = {"id": jid, "stage": "시작", "done": False, "t": time.time()}
                threading.Thread(target=import_video, args=(jid, url), daemon=True).start()
                return self.send_json({"job": jid})
            m = re.fullmatch(r"/api/videos/([\w-]+)/sentences/(\d+)/recordings", p)
            if m:
                rec = save_recording(m[1], int(m[2]), self.body(), self.headers.get("Content-Type"))
                return self.send_json(rec)
            m = re.fullmatch(r"/api/videos/([\w-]+)/sentences/(\d+)/recordings/([\d_-]+)/pitch", p)
            if m and REC_RE.match(m[3]):
                f = vdir(m[1]) / "rec" / m[2] / f"{m[3]}.json"
                rec = read_json(f)
                if not rec:
                    return self.send_json({"error": "없음"}, 404)
                rec["pitch"] = int(json.loads(self.body(1000) or b"{}").get("pitch", 0))
                write_json(f, rec)
                return self.send_json({"ok": True})
            return self.send_json({"error": "없음"}, 404)
        except (ValueError, RuntimeError) as e:
            return self.send_json({"error": str(e)}, 400)


def make_server(host="127.0.0.1", port=8777):
    DATA.mkdir(parents=True, exist_ok=True)
    return ThreadingHTTPServer((host, port), Handler)
