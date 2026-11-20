/* DY-003 TRACER 작동 방식 — 재생형 구성도 + 역할 트리 + 설계 이유.
   소개 페이지(docs/index.html#how)와 TRACER 소개(docs/ccna/about.html)가 함께 쓴다. 여기만 고치면 두 곳이 같이 바뀐다.
   구조(2026-11-20~): 브라우저 → 구글 로그인(Supabase Auth) · TRACER 서버(Vercel) → 데이터베이스(Supabase, 문제은행) · 제미나이.
   쓰는 법: <div class="tq-how" data-tracer-how></div> 를 두고 tracer-how.css · tracer-how.js 를 불러온다. */
(function () {
  var LOCK = "<span class=\"tq-lock\" aria-label=\"브라우저로 나가지 않음\"><svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.4\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"5\" y=\"11\" width=\"14\" height=\"10\" rx=\"2\"/><path d=\"M8 11V7a4 4 0 0 1 8 0v4\"/></svg></span>";
  var TEMPLATE = "<div class=\"tq-stage\">\n<div class=\"tq-top\">\n<div class=\"tq-tabs\" role=\"tablist\" aria-label=\"장면\">\n<button type=\"button\" role=\"tab\" data-t=\"login\" aria-selected=\"true\">🔑 로그인<small>처음 한 번</small></button>\n<button type=\"button\" role=\"tab\" data-t=\"ask\" aria-selected=\"false\">📝 문제 받기<small>핵심</small></button>\n<button type=\"button\" role=\"tab\" data-t=\"grade\" aria-selected=\"false\">✅ 채점·해설</button>\n<button type=\"button\" role=\"tab\" data-t=\"sub\" aria-selected=\"false\">🧮 서브넷<small>로그인 없이</small></button>\n</div>\n<div class=\"tq-ctl\">\n<button type=\"button\" data-r=\"prev\" aria-label=\"이전 단계\"><svg viewBox=\"0 0 16 16\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M10 3L5 8l5 5\"/></svg></button>\n<button type=\"button\" data-r=\"play\" class=\"play\">▶ 재생</button>\n<button type=\"button\" data-r=\"next\" aria-label=\"다음 단계\"><svg viewBox=\"0 0 16 16\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M6 3l5 5-5 5\"/></svg></button>\n</div>\n</div>\n<div class=\"tq-svg\" data-r=\"svg\" role=\"img\" aria-label=\"TRACER 구성도: 브라우저, 구글 로그인, TRACER 서버, 데이터베이스, 제미나이\"></div>\n<div class=\"tq-cap\">\n<div class=\"tq-prog\" data-r=\"prog\"></div>\n<div class=\"tq-cap-row\" aria-live=\"polite\"><span class=\"tq-n\" data-r=\"num\">01</span><p data-r=\"cap\"></p></div>\n</div>\n</div>\n<h3 class=\"tq-h3\">어디서 무엇을 하나</h3>\n<p class=\"tq-sub\">TRACER를 이루는 다섯 부분과 각자 맡은 일입니다. @@LOCK@@ 표시는 내 브라우저로 내려오지 않고 서버 쪽에만 있는 것입니다.</p>\n<div class=\"tq-tree\">\n<div class=\"tq-root\"><span><i aria-hidden=\"true\"></i>DY-003 TRACER</span></div>\n<ul class=\"tq-branches\">\n<li class=\"b-web\">\n<div class=\"tq-head\"><span class=\"tq-ic\"><svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><rect x=\"3\" y=\"4\" width=\"18\" height=\"16\" rx=\"2.5\"/><path d=\"M3 9h18M6.5 6.5h.01M9.5 6.5h.01\"/></svg></span><div><strong>브라우저</strong><small>TRACER 화면</small></div></div>\n<ul class=\"tq-leaves\">\n<li><span>범위 고르고 문제 풀기</span></li>\n<li><span><b>서브넷 문제</b>는 화면이 직접 출제·채점</span></li>\n<li><span>XP·레벨·배지 표시</span></li>\n</ul>\n</li>\n<li class=\"b-login\">\n<div class=\"tq-head\"><span class=\"tq-ic\"><svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><circle cx=\"8\" cy=\"15\" r=\"4\"/><path d=\"M11 12l9-9M17 6l3 3M14 9l2 2\"/></svg></span><div><strong>구글 로그인</strong><small>Supabase Auth</small></div></div>\n<ul class=\"tq-leaves\">\n<li><span>구글 계정으로 <b>로그인·로그아웃</b></span></li>\n<li><span>비밀번호는 구글이 처리 (TRACER는 모름)</span></li>\n<li><span>로그인 표(토큰)를 브라우저에 줌</span></li>\n</ul>\n</li>\n<li class=\"b-mac\">\n<div class=\"tq-head\"><span class=\"tq-ic\"><svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><rect x=\"4\" y=\"4\" width=\"16\" height=\"6\" rx=\"1.5\"/><rect x=\"4\" y=\"14\" width=\"16\" height=\"6\" rx=\"1.5\"/><path d=\"M8 7h.01M8 17h.01\"/></svg></span><div><strong>TRACER 서버</strong><small>Vercel · 무료</small></div></div>\n<ul class=\"tq-leaves\">\n<li>@@LOCK@@<span><b>AI 키</b> 보관</span></li>\n<li><span>로그인·권한·하루 한도 확인</span></li>\n<li>@@LOCK@@<span><b>정답</b> 비교·채점</span></li>\n</ul>\n</li>\n<li class=\"b-db\">\n<div class=\"tq-head\"><span class=\"tq-ic\"><svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><ellipse cx=\"12\" cy=\"6\" rx=\"7\" ry=\"3\"/><path d=\"M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3\"/></svg></span><div><strong>데이터베이스</strong><small>Supabase · 무료</small></div></div>\n<ul class=\"tq-leaves\">\n<li>@@LOCK@@<span><b>문제은행</b>: 문제·정답·해설</span></li>\n<li><span>내 진도·레벨 (다른 기기에서도)</span></li>\n<li>@@LOCK@@<span>이용 기록 (IP는 저장 안 함)</span></li>\n</ul>\n</li>\n<li class=\"b-ai\">\n<div class=\"tq-head\"><span class=\"tq-ic\"><svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><path d=\"M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM18.5 15.5l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z\"/></svg></span><div><strong>제미나이</strong><small>Google · 무료 등급</small></div></div>\n<ul class=\"tq-leaves\">\n<li><span>문제은행에 없을 때만 <b>새 문제</b></span></li>\n<li><span>정답·해설까지 한 번에</span></li>\n<li><span>주관식 답 채점</span></li>\n</ul>\n</li>\n</ul>\n</div>\n<div class=\"tq-why\">\n<div><span class=\"k\">LOGIN</span><h4>구글로 바로 로그인</h4><p>가입 양식 없이 구글 계정 하나로 시작하고, 진도는 계정에 남습니다.</p></div>\n<div><span class=\"k\">KEY</span><h4>키·정답은 서버에만</h4><p>화면 코드를 열어 봐도 AI 키와 정답은 보이지 않습니다.</p></div>\n<div><span class=\"k\">BANK</span><h4>문제은행으로 절약</h4><p>한 번 만든 문제는 저장해 다시 냅니다. 쌓일수록 AI를 덜 부르고 더 빨라집니다.</p></div>\n<div><span class=\"k\">₩0</span><h4>추가 비용 없음</h4><p>Vercel·Supabase·제미나이 모두 무료 등급만 씁니다.</p></div>\n</div>";
  function mount(root) {
    root.innerHTML = TEMPLATE.split('@@LOCK@@').join(LOCK);
    var R = function (k) { return root.querySelector('[data-r="' + k + '"]'); };
    var host = R('svg');
  var NODES = {"login": {"k": "login", "t": "구글 로그인", "s": "Supabase Auth", "ico": "<circle cx=\"8\" cy=\"15\" r=\"4\"/><path d=\"M11 12l9-9M17 6l3 3M14 9l2 2\"/>"}, "web": {"k": "web", "t": "브라우저", "s": "TRACER 화면", "ico": "<rect x=\"3\" y=\"4\" width=\"18\" height=\"16\" rx=\"2.5\"/><path d=\"M3 9h18M6.5 6.5h.01M9.5 6.5h.01\"/>"}, "api": {"k": "mac", "t": "TRACER 서버", "s": "Vercel · 키·정답", "ico": "<rect x=\"4\" y=\"4\" width=\"16\" height=\"6\" rx=\"1.5\"/><rect x=\"4\" y=\"14\" width=\"16\" height=\"6\" rx=\"1.5\"/><path d=\"M8 7h.01M8 17h.01\"/>"}, "db": {"k": "db", "t": "데이터베이스", "s": "문제은행·진도", "ico": "<ellipse cx=\"12\" cy=\"6\" rx=\"7\" ry=\"3\"/><path d=\"M5 6v12c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12c0 1.7 3.1 3 7 3s7-1.3 7-3\"/>"}, "ai": {"k": "ai", "t": "제미나이", "s": "무료 등급", "ico": "<path d=\"M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM18.5 15.5l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z\"/>"}};
  var LAYOUT = {"h": {"w": 1120, "h": 310, "cw": 200, "ch": 84, "pos": {"login": [300, 52], "db": [820, 52], "web": [140, 240], "api": [560, 240], "ai": [980, 240]}, "links": {"web-login": {"p": [[140, 198], [140, 52], [200, 52]], "l": "\ub85c\uadf8\uc778", "lp": [140, 125]}, "web-api": {"p": [[240, 240], [460, 240]], "l": "HTTPS", "lp": [350, 240]}, "api-login": {"p": [[510, 198], [510, 52], [400, 52]], "l": "\ud655\uc778", "lp": [455, 52]}, "api-db": {"p": [[610, 198], [610, 52], [720, 52]], "l": "\uc77d\uae30\u00b7\uc4f0\uae30", "lp": [665, 52]}, "api-ai": {"p": [[660, 240], [880, 240]], "l": "API", "lp": [770, 240]}}}, "v": {"w": 420, "h": 588, "cw": 250, "ch": 76, "pos": {"login": [210, 44], "web": [210, 164], "api": [210, 284], "db": [210, 404], "ai": [210, 524]}, "links": {"web-login": {"p": [[210, 126], [210, 82]], "l": "\ub85c\uadf8\uc778", "lp": [210, 104]}, "web-api": {"p": [[210, 202], [210, 246]], "l": "HTTPS", "lp": [210, 224]}, "api-db": {"p": [[210, 322], [210, 366]], "l": "\uc77d\uae30\u00b7\uc4f0\uae30", "lp": [210, 344]}, "api-login": {"p": [[85, 284], [40, 284], [40, 44], [85, 44]], "l": "\ud655\uc778", "lp": [40, 164]}, "api-ai": {"p": [[335, 284], [380, 284], [380, 524], [335, 524]], "l": "API", "lp": [380, 404]}}}};
  var WHO = {"web": ["w", "브라우저"], "login": ["b", "구글 로그인"], "api": ["m", "TRACER 서버"], "db": ["d", "데이터베이스"], "ai": ["a", "제미나이"]};
  var SCEN = {
 "login": {
  "dim": [
   "ai"
  ],
  "steps": [
   {
    "p": null,
    "on": [
     "web"
    ],
    "w": "web",
    "t": "오른쪽 위 \"Google로 로그인\"을 눌러요.",
    "s": "서브넷 문제는 로그인 없이도 바로 풀 수 있어요."
   },
   {
    "p": [
     "web",
     "login"
    ],
    "on": [
     "web",
     "login"
    ],
    "w": "web",
    "t": "구글 로그인 창으로 이동해 내 구글 계정을 골라요.",
    "tag": "로그인 요청",
    "s": "비밀번호는 구글이 확인해요. TRACER는 비밀번호를 받지 않아요."
   },
   {
    "p": [
     "login",
     "web"
    ],
    "on": [
     "login",
     "web"
    ],
    "w": "login",
    "t": "확인이 끝나면 브라우저에 \"로그인 표(토큰)\"가 생기고, 위쪽에 내 이름과 \"로그아웃\" 버튼이 보여요.",
    "tag": "로그인 표"
   },
   {
    "p": [
     "web",
     "api"
    ],
    "on": [
     "web",
     "api"
    ],
    "w": "web",
    "t": "이제 문제를 요청할 때마다 이 표를 같이 보내요.",
    "tag": "요청 + 로그인 표"
   },
   {
    "p": [
     "api",
     "login"
    ],
    "on": [
     "api",
     "login"
    ],
    "w": "api",
    "t": "서버가 \"진짜 로그인한 사람인지\" 구글 로그인 쪽에 확인해요.",
    "tag": "확인"
   },
   {
    "p": [
     "api",
     "db"
    ],
    "on": [
     "api",
     "db"
    ],
    "w": "api",
    "t": "처음 온 사람이면 사용자로 등록하고, 접속 기록을 남겨요.",
    "tag": "사용자 등록",
    "s": "이메일·이름·기기 종류만 저장해요. IP 주소는 저장하지 않아요."
   }
  ]
 },
 "ask": {
  "dim": [
   "login"
  ],
  "steps": [
   {
    "p": null,
    "on": [
     "web"
    ],
    "w": "web",
    "t": "단원·세부 범위, 난이도, 객관식·주관식을 고르고 \"문제 받기\"를 눌러요."
   },
   {
    "p": [
     "web",
     "api"
    ],
    "on": [
     "web",
     "api"
    ],
    "w": "web",
    "t": "고른 범위가 서버로 가요.",
    "tag": "범위·난이도"
   },
   {
    "p": [
     "api",
     "db"
    ],
    "on": [
     "api",
     "db"
    ],
    "w": "api",
    "t": "서버가 권한과 오늘 남은 사용량을 확인하고, 문제은행에 그 범위 문제가 있는지 찾아요.",
    "tag": "저장된 문제?"
   },
   {
    "p": [
     "db",
     "api"
    ],
    "on": [
     "db",
     "api"
    ],
    "w": "db",
    "t": "문제가 30개 이상 쌓여 있으면, 아직 내가 안 푼 문제를 바로 꺼내요.",
    "tag": "안 푼 문제",
    "s": "AI를 부르지 않아서 빠르고, 무료 한도도 아껴요."
   },
   {
    "p": [
     "api",
     "ai"
    ],
    "on": [
     "api",
     "ai"
    ],
    "w": "api",
    "t": "문제가 부족하면 제미나이에게 실제 시험 같은 영어 문제를 새로 만들어 달라고 해요.",
    "tag": "출제 요청"
   },
   {
    "p": [
     "ai",
     "api",
     "db"
    ],
    "on": [
     "ai",
     "api",
     "db"
    ],
    "w": "ai",
    "t": "제미나이가 문제·보기·정답·해설을 한 번에 돌려주면, 서버가 문제은행에 저장해요.",
    "tag": "문제+정답+해설",
    "s": "다음 사람은 이 문제를 AI 없이 받아요."
   },
   {
    "p": [
     "api",
     "web"
    ],
    "on": [
     "web"
    ],
    "w": "api",
    "t": "화면에는 문제와 보기만 도착해요.",
    "tag": "문제·보기만",
    "s": "정답은 서버 쪽에만 있어요."
   }
  ]
 },
 "grade": {
  "dim": [
   "login"
  ],
  "steps": [
   {
    "p": null,
    "on": [
     "web"
    ],
    "w": "web",
    "t": "보기를 고르거나 주관식 답을 적고 \"채점하고 해설 받기\"를 눌러요."
   },
   {
    "p": [
     "web",
     "api"
    ],
    "on": [
     "web",
     "api"
    ],
    "w": "web",
    "t": "내 답이 서버로 가요.",
    "tag": "내 답"
   },
   {
    "p": [
     "api",
     "db"
    ],
    "on": [
     "api",
     "db"
    ],
    "w": "api",
    "t": "서버가 문제은행에서 정답과 저장된 해설을 꺼내요.",
    "tag": "정답·해설"
   },
   {
    "p": null,
    "on": [
     "api"
    ],
    "w": "api",
    "t": "객관식은 서버의 코드가 정답과 비교해 바로 채점해요.",
    "s": "해설도 저장된 것을 써서 AI를 부르지 않아요."
   },
   {
    "p": [
     "api",
     "ai"
    ],
    "on": [
     "api",
     "ai"
    ],
    "w": "api",
    "t": "주관식만 제미나이가 뜻이 맞는지 보고 판정해요.",
    "tag": "주관식 판정"
   },
   {
    "p": [
     "api",
     "db"
    ],
    "on": [
     "api",
     "db"
    ],
    "w": "api",
    "t": "풀이 기록을 내 계정에 저장해요.",
    "tag": "풀이 기록",
    "s": "그래서 다른 기기에서도 진도가 이어져요."
   },
   {
    "p": [
     "api",
     "web"
    ],
    "on": [
     "web"
    ],
    "w": "api",
    "t": "화면에 정답·오답, 해설, 고른 보기가 왜 틀렸는지가 떠요. XP도 올라가요.",
    "tag": "판정 + 해설"
   }
  ]
 },
 "sub": {
  "dim": [
   "login",
   "api",
   "db",
   "ai"
  ],
  "steps": [
   {
    "p": null,
    "on": [
     "web"
    ],
    "w": "web",
    "t": "서브넷 문제는 화면의 코드가 직접 만들어요. (예: 192.168.10.77/27의 네트워크 주소는?)",
    "s": "로그인도, 서버도, AI도 필요 없어요."
   },
   {
    "p": null,
    "on": [
     "web"
    ],
    "w": "web",
    "t": "답을 내면 화면이 직접 계산해 채점하고, 풀이 과정을 영어로 보여 줘요.",
    "s": "AI가 틀리기 쉬운 계산이라 일부러 코드로 했어요."
   },
   {
    "p": null,
    "on": [
     "web"
    ],
    "w": "web",
    "t": "XP·퀘스트·배지도 쌓여요. 로그인하면 기록이 계정에 남아요."
   }
  ]
 }
};
  var mqV = window.matchMedia('(max-width: 700px)');
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var scen = 'login', idx = 0, playing = false, started = false, timer = null, raf = null, L, svg, packet;
  var btnPlay = R('play'), cap = R('cap'), num = R('num'), prog = R('prog');
  function pts(a) { return a.map(function (q) { return q.join(','); }).join(' '); }
  function pill(cls, x, y, text, h) {
    return '<g class="' + cls + '" transform="translate(' + x + ' ' + y + ')"><rect rx="' + h / 2 + '" height="' + h + '" y="' + (-h / 2) + '"/><text>' + text + '</text></g>';
  }
  function build() {
    L = LAYOUT[mqV.matches ? 'v' : 'h'];
    var h = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + L.w + ' ' + L.h + '" aria-hidden="true">';
    Object.keys(L.links).forEach(function (k) {
      var ln = L.links[k];
      h += '<polyline class="track' + (ln.dash ? ' dash' : '') + '" data-k="' + k + '" points="' + pts(ln.p) + '"/>';
    });
    Object.keys(L.links).forEach(function (k) { var ln = L.links[k]; h += pill('elab', ln.lp[0], ln.lp[1], ln.l, 26).replace('class="elab"', 'class="elab" data-k="' + k + '"'); });
    Object.keys(NODES).forEach(function (id) {
      var n = NODES[id], p = L.pos[id], x0 = -L.cw / 2;
      h += '<g class="node k-' + n.k + '" data-id="' + id + '" transform="translate(' + p[0] + ' ' + p[1] + ')">' +
        '<rect class="card" x="' + x0 + '" y="' + (-L.ch / 2) + '" width="' + L.cw + '" height="' + L.ch + '" rx="16"/>' +
        '<rect class="tile" x="' + (x0 + 16) + '" y="-22" width="44" height="44" rx="12"/>' +
        '<g class="ico" transform="translate(' + (x0 + 26) + ' -12)">' + n.ico + '</g>' +
        '<text class="ttl" x="' + (x0 + 74) + '" y="-10">' + n.t + '</text><text class="sub" x="' + (x0 + 74) + '" y="14">' + n.s + '</text></g>';
    });
    h += pill('packet', 0, 0, '', 30).replace('<g class="packet"', '<g class="packet" style="display:none"') + '</svg>';
    host.innerHTML = h;
    svg = host.firstChild; packet = svg.querySelector('.packet');
    // 이름표 폭 맞추기
    measure();
  }
  // 소개가 접혀(숨겨져) 있을 때 만들어지면 글자 폭이 0이라, 보이게 되면 다시 잰다
  function measure() {
    svg.querySelectorAll('.elab').forEach(function (g) {
      var w = g.querySelector('text').getComputedTextLength(); if (!w) return;
      var r = g.querySelector('rect'); r.setAttribute('width', w + 20); r.setAttribute('x', -(w + 20) / 2);
    });
  }
  function route(path) {
    var out = [], used = [];
    for (var i = 0; i < path.length - 1; i++) {
      var a = path[i], b = path[i + 1], ln = L.links[a + '-' + b], seg;
      if (ln) { seg = ln.p.slice(); used.push(a + '-' + b); }
      else { ln = L.links[b + '-' + a]; seg = ln.p.slice().reverse(); used.push(b + '-' + a); }
      out = out.concat(seg);
    }
    return { pts: out, used: used };
  }
  function setPacket(x, y) { packet.setAttribute('transform', 'translate(' + x + ' ' + y + ')'); }
  function animate(r, tag, done) {
    cancelAnimationFrame(raf);
    if (!r) { packet.style.display = 'none'; return done(); }
    var P = r.pts, t = packet.querySelector('text'), rc = packet.querySelector('rect');
    packet.style.display = ''; t.textContent = tag;
    var w = t.getComputedTextLength() + 26; rc.setAttribute('width', w); rc.setAttribute('x', -w / 2);
    var seg = [], tot = 0;
    for (var i = 0; i < P.length - 1; i++) { var d = Math.hypot(P[i + 1][0] - P[i][0], P[i + 1][1] - P[i][1]); seg.push(d); tot += d; }
    if (reduce) { setPacket(P[P.length - 1][0], P[P.length - 1][1]); return done(); }
    var dur = Math.max(900, tot / 0.38), t0 = null;
    function step(ts) {
      if (t0 === null) t0 = ts;
      var k = Math.min(1, (ts - t0) / dur);
      k = k < .5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      var dist = k * tot, j = 0;
      while (j < seg.length - 1 && dist > seg[j]) { dist -= seg[j]; j++; }
      var u = seg[j] ? Math.min(1, dist / seg[j]) : 1;
      setPacket(P[j][0] + (P[j + 1][0] - P[j][0]) * u, P[j][1] + (P[j + 1][1] - P[j][1]) * u);
      if (k < 1) raf = requestAnimationFrame(step); else done();
    }
    raf = requestAnimationFrame(step);
  }
  function renderProg() {
    prog.innerHTML = SCEN[scen].steps.map(function (s, i) { return '<button type="button" data-i="' + i + '" aria-label="' + (i + 1) + '단계: ' + s.t.replace(/"/g, '') + '"></button>'; }).join('');
  }
  function show(i, anim) {
    var st = SCEN[scen].steps, s = st[i], dim = SCEN[scen].dim; idx = i;
    var r = s.p ? route(s.p) : null, used = r ? r.used : [];
    num.textContent = (i + 1 < 10 ? '0' : '') + (i + 1);
    var who = WHO[s.w];
    cap.innerHTML = '<span class="tq-who ' + who[0] + '">' + who[1] + '</span><br>' + s.t + (s.s ? '<small>' + s.s + '</small>' : '');
    svg.querySelectorAll('.node').forEach(function (g) {
      var id = g.getAttribute('data-id');
      g.classList.toggle('on', s.on.indexOf(id) > -1);
      g.classList.toggle('dim', dim.indexOf(id) > -1 && s.on.indexOf(id) < 0);
    });
    svg.querySelectorAll('.track, .elab').forEach(function (el) {
      var k = el.getAttribute('data-k'), ab = k.split('-'), hot = used.indexOf(k) > -1;
      el.classList.toggle('hot', hot);
      el.classList.toggle('dim', !hot && (dim.indexOf(ab[0]) > -1 || dim.indexOf(ab[1]) > -1));
    });
    prog.querySelectorAll('button').forEach(function (b, k) { b.className = k < i ? 'done' : (k === i ? 'cur' : ''); });
    clearTimeout(timer);
    var after = function () {
      if (!playing) return;
      timer = setTimeout(function () {
        if (idx < st.length - 1) show(idx + 1, true); else show(0, true); /* 끝나면 처음부터 반복 */
      }, reduce ? 3200 : 1900);
    };
    if (anim) animate(r, s.tag, after); else { cancelAnimationFrame(raf); packet.style.display = 'none'; after(); }
  }
  function syncBtn() { btnPlay.textContent = playing ? '❚❚ 일시정지' : '▶ 재생'; }
  function stop() { playing = false; clearTimeout(timer); syncBtn(); }
  function play() {
    if (playing) { stop(); return; }
    var last = SCEN[scen].steps.length - 1;
    var next = !started ? 0 : (idx >= last ? 0 : idx + 1);
    playing = true; started = true; syncBtn();
    show(next, true);
  }
  function go(i) { stop(); started = true; show(i, true); }
  function setScen(n) {
    scen = n; stop(); started = false;
    root.querySelectorAll('[data-t]').forEach(function (b) { b.setAttribute('aria-selected', b.getAttribute('data-t') === n); });
    renderProg(); show(0, false);
    if (!reduce) play(); /* 장면을 바꾸면 그 장면을 반복 재생 */
  }
  btnPlay.addEventListener('click', play);
  R('prev').addEventListener('click', function () { go(Math.max(0, idx - 1)); });
  R('next').addEventListener('click', function () { go(Math.min(SCEN[scen].steps.length - 1, idx + 1)); });
  root.querySelectorAll('[data-t]').forEach(function (b) { b.addEventListener('click', function () { setScen(b.getAttribute('data-t')); }); });
  prog.addEventListener('click', function (e) { var b = e.target.closest('button'); if (b) go(+b.getAttribute('data-i')); });
  var onMq = function () { build(); show(idx, false); };
  mqV.addEventListener ? mqV.addEventListener('change', onMq) : mqV.addListener(onMq);
  build(); renderProg(); show(0, false);
  if ('ResizeObserver' in window) new ResizeObserver(function () { if (host.offsetWidth) measure(); }).observe(host);
  if (!reduce && 'IntersectionObserver' in window) {
    var seen = new IntersectionObserver(function (en) {
      if (en[0].isIntersecting) { seen.disconnect(); if (!started) play(); }
    }, { threshold: .4 });
    seen.observe(host);
  }
  }

  function init() { Array.prototype.forEach.call(document.querySelectorAll('[data-tracer-how]'), mount); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
