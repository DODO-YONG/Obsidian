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
FAKE_SB = b"""window.supabase={createClient:function(){var tok=localStorage.getItem('fake-tok');var cbs=[];
return {auth:{getSession:function(){return Promise.resolve({data:{session:tok?{access_token:tok}:null}})},
onAuthStateChange:function(f){cbs.push(f)},
signInWithOAuth:function(){tok='a';localStorage.setItem('fake-tok','a');cbs.forEach(function(f){f('SIGNED_IN',{})});return Promise.resolve({})},
signOut:function(){tok=null;localStorage.removeItem('fake-tok');return Promise.resolve({})}}}}};"""
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
        if self.path.split('?')[0] in ('/ccna/', '/ccna/index.html', '/ccna/admin.html'):
            f = DOCS + ('/ccna/index.html' if not self.path.startswith('/ccna/admin') else '/ccna/admin.html')
            b = open(f, 'rb').read().replace(b'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/dist/umd/supabase.min.js', b'/fake-supabase.js')
            self.send_response(200); self.send_header('Content-Type','text/html; charset=utf-8'); self.end_headers(); return self.wfile.write(b)
        return super().do_GET()
    def do_POST(self):
        if self.path.startswith('/api/'): return self._api('do_POST')
print('로컬 시험 화면: http://127.0.0.1:8799/ccna/  (가짜 DB·가짜 제미나이)')
ThreadingHTTPServer(('127.0.0.1', 8799), H).serve_forever()
