"""로컬 화면 시험 서버 (python3 agents/ccna-coach/dev/harness.py): docs/ 정적 파일 + /api(가짜 DB·가짜 제미나이). 실제 Supabase·제미나이 호출 없음."""
import os, sys, json, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fakes  # noqa  (가짜 DB·제미나이·로그인 설치)
fakes.users["a"]["email"] = "owner@example.com"   # 화면 시험: 로그인하면 주인(관리자 화면까지)
for tok in ("b",): fakes.core.current_user(tok)   # 다른 사용자 한 명
fakes.core.BANK_MIN = 3
os.environ["SUPABASE_URL"] = "http://fake"; os.environ["SUPABASE_ANON_KEY"] = "fake-anon"
import index as api
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
DOCS = str(__import__("pathlib").Path(__file__).resolve().parents[3] / "docs")
FAKE_SB = b"""window.supabase={createClient:function(){var cbs=[];
function sess(){var t=localStorage.getItem('fake-tok');return t?{access_token:t,user:{email:'owner@example.com',user_metadata:{full_name:'Test Owner'}}}:null}
return {auth:{getSession:function(){return Promise.resolve({data:{session:sess()}})},
onAuthStateChange:function(f){cbs.push(f)},
signInWithOAuth:function(){localStorage.setItem('fake-tok','a');cbs.forEach(function(f){f('SIGNED_IN',sess())});return Promise.resolve({})},
signOut:function(){localStorage.removeItem('fake-tok');cbs.forEach(function(f){f('SIGNED_OUT',null)});return Promise.resolve({})}}}}};"""
class H(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=DOCS, **k)
    def log_message(self, *a): pass
    def _api(self, m):
        h = api.handler.__new__(api.handler)
        h.__dict__.update(self.__dict__)
        getattr(api.handler, m)(h)
    def do_GET(self):
        if self.path.startswith('/api/'): return self._api('do_GET')
        if self.path.startswith('/fake-supabase.js'):
            self.send_response(200); self.send_header('Content-Type','text/javascript'); self.end_headers(); return self.wfile.write(FAKE_SB)
        pth = self.path.split('?')[0]
        if pth.startswith('/ccna/') and (pth.endswith('.html') or pth == '/ccna/'):
            f = DOCS + (pth + 'index.html' if pth.endswith('/') else pth)
            b = open(f, 'rb').read().replace(b'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/dist/umd/supabase.min.js', b'/fake-supabase.js')
            self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.end_headers(); return self.wfile.write(b)
        return super().do_GET()
    def do_POST(self):
        if self.path.startswith('/api/'): return self._api('do_POST')
PORT = int(os.environ.get("TRACER_HARNESS_PORT", "8799"))   # e2e 시험은 다른 포트로 띄움
print(f'로컬 시험 화면: http://127.0.0.1:{PORT}/ccna/  (선택 화면 · about.html 소개 · app.html 이용, 가짜 DB·가짜 제미나이)', flush=True)
ThreadingHTTPServer(('127.0.0.1', PORT), H).serve_forever()
