/* DY-003 TRACER 작동 방식 — 재생형 구성도 + 역할 트리 + 설계 이유.
   소개 페이지(docs/index.html)와 TRACER 사이트(docs/ccna/)가 함께 쓴다. 여기만 고치면 두 곳이 같이 바뀐다.
   쓰는 법: <div class="tq-how" data-tracer-how></div> 를 두고 tracer-how.css · tracer-how.js 를 불러온다. */
(function () {
  var LOCK = "<span class=\"tq-lock\" aria-label=\"개인 서버 밖으로 안 나감\"><svg viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.4\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><rect x=\"5\" y=\"11\" width=\"14\" height=\"10\" rx=\"2\"/><path d=\"M8 11V7a4 4 0 0 1 8 0v4\"/></svg></span>";
  var TEMPLATE = "<div class=\"tq-stage\">\n<div class=\"tq-top\">\n<div class=\"tq-tabs\" role=\"tablist\" aria-label=\"장면\">\n<button type=\"button\" role=\"tab\" data-t=\"setup\" aria-selected=\"true\">🔌 서버 켜기<small>처음 한 번</small></button>\n<button type=\"button\" role=\"tab\" data-t=\"ask\" aria-selected=\"false\">📝 문제 받기<small>핵심</small></button>\n<button type=\"button\" role=\"tab\" data-t=\"grade\" aria-selected=\"false\">✅ 채점·해설</button>\n<button type=\"button\" role=\"tab\" data-t=\"sub\" aria-selected=\"false\">🧮 서브넷<small>서버 꺼져도 OK</small></button>\n</div>\n<div class=\"tq-ctl\">\n<button type=\"button\" data-r=\"prev\" aria-label=\"이전 단계\"><svg viewBox=\"0 0 16 16\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M10 3L5 8l5 5\"/></svg></button>\n<button type=\"button\" data-r=\"play\" class=\"play\">▶ 재생</button>\n<button type=\"button\" data-r=\"next\" aria-label=\"다음 단계\"><svg viewBox=\"0 0 16 16\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2.2\" stroke-linecap=\"round\" stroke-linejoin=\"round\" aria-hidden=\"true\"><path d=\"M6 3l5 5-5 5\"/></svg></button>\n</div>\n</div>\n<div class=\"tq-svg\" data-r=\"svg\" role=\"img\" aria-label=\"TRACER 구성도: 주소 안내판, 브라우저, 임시 터널, 개인 서버, 제미나이\"></div>\n<div class=\"tq-cap\">\n<div class=\"tq-prog\" data-r=\"prog\"></div>\n<div class=\"tq-cap-row\" aria-live=\"polite\"><span class=\"tq-n\" data-r=\"num\">01</span><p data-r=\"cap\"></p></div>\n</div>\n</div>\n<h3 class=\"tq-h3\">어디서 무엇을 하나</h3>\n<p class=\"tq-sub\">TRACER를 이루는 다섯 부분과 각자 맡은 일입니다. @@LOCK@@ 표시는 개인 서버 밖으로 나가지 않는 것입니다.</p>\n<div class=\"tq-tree\">\n<div class=\"tq-root\"><span><i aria-hidden=\"true\"></i>DY-003 TRACER</span></div>\n<ul class=\"tq-branches\">\n<li class=\"b-web\">\n<div class=\"tq-head\"><span class=\"tq-ic\"><svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><rect x=\"3\" y=\"4\" width=\"18\" height=\"16\" rx=\"2.5\"/><path d=\"M3 9h18M6.5 6.5h.01M9.5 6.5h.01\"/></svg></span><div><strong>브라우저</strong><small>공개 화면</small></div></div>\n<ul class=\"tq-leaves\">\n<li><span>단원·범위 고르고 문제 풀기</span></li>\n<li><span><b>서브넷 문제</b> 출제·채점 (AI 없이)</span></li>\n<li><span><b>XP·레벨·배지</b> 저장 (각자 브라우저)</span></li>\n<li><span>서버 주소 읽고 <b>자동 연결</b> · 꺼지면 서브넷만</span></li>\n</ul>\n</li>\n<li class=\"b-board\">\n<div class=\"tq-head\"><span class=\"tq-ic\"><svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><circle cx=\"12\" cy=\"12\" r=\"9\"/><path d=\"M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18\"/></svg></span><div><strong>GitHub Pages</strong><small>무료 호스팅</small></div></div>\n<ul class=\"tq-leaves\">\n<li><span>화면 파일 (HTML·출제 범위)</span></li>\n<li><span><b>주소 안내판</b> server.json</span></li>\n<li><span>start-public.sh가 <b>주소만</b> 자동 커밋·푸시</span></li>\n</ul>\n</li>\n<li class=\"b-tun\">\n<div class=\"tq-head\"><span class=\"tq-ic\"><svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><path d=\"M7 18a4.5 4.5 0 0 1-.6-8.96A6 6 0 0 1 18 8.5a4.5 4.5 0 0 1-.5 9.5z\"/></svg></span><div><strong>임시 터널</strong><small>Cloudflare · 무료</small></div></div>\n<ul class=\"tq-leaves\">\n<li><span>개인 서버에 임시 공개 주소 연결</span></li>\n<li><span>켤 때마다 주소가 바뀜 → 안내판이 해결</span></li>\n</ul>\n</li>\n<li class=\"b-mac\">\n<div class=\"tq-head\"><span class=\"tq-ic\"><svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><rect x=\"4\" y=\"5\" width=\"16\" height=\"11\" rx=\"1.5\"/><path d=\"M2 19.5h20\"/></svg></span><div><strong>개인 서버</strong><small>개인 컴퓨터 환경 · server.py</small></div></div>\n<ul class=\"tq-leaves\">\n<li>@@LOCK@@<span><b>AI 키</b> (.env)</span></li>\n<li>@@LOCK@@<span><b>정답</b> 보관·채점</span></li>\n<li><span><b>사용량 제한</b> 1명 시간당 30 · 하루 300</span></li>\n<li>@@LOCK@@<span>운영자 풀이 기록 → 진도 분석</span></li>\n</ul>\n</li>\n<li class=\"b-ai\">\n<div class=\"tq-head\"><span class=\"tq-ic\"><svg viewBox=\"0 0 24 24\" aria-hidden=\"true\"><path d=\"M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM18.5 15.5l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z\"/></svg></span><div><strong>제미나이</strong><small>Google · 무료 등급</small></div></div>\n<ul class=\"tq-leaves\">\n<li><span><b>영어</b> 문제 출제</span></li>\n<li><span><b>영어</b> 해설 작성</span></li>\n<li><span>바쁘면 다른 모델로 (3개)</span></li>\n</ul>\n</li>\n</ul>\n</div>\n<div class=\"tq-why\">\n<div><span class=\"k\">KEY</span><h4>키는 개인 서버에만</h4><p>공개 화면에 키를 넣으면 누구나 볼 수 있어서, AI 호출은 서버만 합니다.</p></div>\n<div><span class=\"k\">ANSWER</span><h4>정답은 서버에만</h4><p>화면 코드를 열어 봐도 답이 보이지 않게 했습니다.</p></div>\n<div><span class=\"k\">NO AI</span><h4>계산은 코드로</h4><p>AI가 틀리기 쉬운 서브넷 계산은 화면이 직접 계산해 정확합니다.</p></div>\n<div><span class=\"k\">₩0</span><h4>추가 비용 없음</h4><p>GitHub Pages, 무료 터널, 제미나이 무료 등급만 씁니다.</p></div>\n</div>";

  function mount(root) {
    root.innerHTML = TEMPLATE.split('@@LOCK@@').join(LOCK);
    var R = function (k) { return root.querySelector('[data-r="' + k + '"]'); };
    var host = R('svg');
  var NODES = {
    board: { k: 'board', t: '주소 안내판', s: 'server.json', ico: '<rect x="5" y="3.5" width="14" height="17" rx="2"/><path d="M9 3.5V2.5h6v1M8.5 9h7M8.5 13h7M8.5 17h4"/>' },
    web:   { k: 'web',   t: '브라우저',    s: '공개 화면', ico: '<rect x="3" y="4" width="18" height="16" rx="2.5"/><path d="M3 9h18M6.5 6.5h.01M9.5 6.5h.01"/>' },
    tun:   { k: 'tun',   t: '임시 터널',   s: 'Cloudflare', ico: '<path d="M7 18a4.5 4.5 0 0 1-.6-8.96A6 6 0 0 1 18 8.5a4.5 4.5 0 0 1-.5 9.5z"/>' },
    mac:   { k: 'mac',   t: '개인 서버', s: '키 · 정답 보관', ico: '<rect x="4" y="5" width="16" height="11" rx="1.5"/><path d="M2 19.5h20"/>' },
    ai:    { k: 'ai',    t: '제미나이',    s: '무료 등급', ico: '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM18.5 15.5l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z"/>' }
  };
  var LAYOUT = {
    h: { w: 1120, h: 310, cw: 200, ch: 84,
      pos: { board: [420, 52], web: [140, 240], tun: [420, 240], mac: [700, 240], ai: [980, 240] },
      links: {
        'web-tun':   { p: [[240, 240], [320, 240]], l: 'HTTPS', lp: [280, 240] },
        'tun-mac':   { p: [[520, 240], [600, 240]], l: '터널', lp: [560, 240] },
        'mac-ai':    { p: [[800, 240], [880, 240]], l: 'API', lp: [840, 240] },
        'board-web': { p: [[320, 52], [140, 52], [140, 198]], l: '주소 읽기', lp: [140, 125] },
        'board-mac': { p: [[520, 52], [700, 52], [700, 198]], l: '주소 등록', lp: [700, 125], dash: 1 }
      } },
    v: { w: 400, h: 588, cw: 270, ch: 76,
      pos: { board: [150, 44], web: [150, 164], tun: [150, 284], mac: [150, 404], ai: [150, 524] },
      links: {
        'board-web': { p: [[150, 82], [150, 126]], l: '주소 읽기', lp: [150, 104] },
        'web-tun':   { p: [[150, 202], [150, 246]], l: 'HTTPS', lp: [150, 224] },
        'tun-mac':   { p: [[150, 322], [150, 366]], l: '터널', lp: [150, 344] },
        'mac-ai':    { p: [[150, 442], [150, 486]], l: 'API', lp: [150, 464] },
        'board-mac': { p: [[285, 44], [348, 44], [348, 404], [285, 404]], l: '등록', lp: [348, 224], dash: 1 }
      } }
  };
  var WHO = { web: ['w', '브라우저'], mac: ['m', '개인 서버'], ai: ['a', '제미나이'], board: ['b', '주소 안내판'], tun: ['b', 'Cloudflare 터널'] };
  var SCEN = {
    setup: { dim: ['ai'], steps: [
      { p: null, on: ['mac'], w: 'mac', t: '운영자가 start-public.sh를 실행하면, 개인 컴퓨터에서 TRACER 서버(server.py)가 켜져요.', s: '아직은 그 컴퓨터 안(127.0.0.1)에서만 접속할 수 있어요.' },
      { p: ['mac', 'tun'], on: ['mac', 'tun'], tag: '터널 열어 줘', w: 'mac', t: '스크립트가 cloudflared를 실행해 Cloudflare에 임시 터널을 요청해요.', s: '가입도 비용도 없는 무료 터널이에요.' },
      { p: ['tun', 'mac'], on: ['tun', 'mac'], tag: 'https://….trycloudflare.com', w: 'tun', t: 'Cloudflare가 서버로 이어지는 임시 공개 주소를 만들어 줘요.', s: '켤 때마다 주소가 바뀌어서, 화면 코드에 미리 적어 둘 수 없어요.' },
      { p: ['mac', 'board'], on: ['mac', 'board'], tag: 'server.json 푸시', w: 'mac', t: '스크립트가 그 주소를 server.json에 적고, 이 파일 하나만 GitHub에 커밋·푸시해요.', s: '코드는 바뀌지 않아요. 1~2분 뒤 공개 사이트에 반영되고, 사람이 할 일은 없어요.' },
      { p: ['board', 'web'], on: ['board', 'web'], tag: '주소', w: 'web', t: '누구든 사이트를 열면, 화면이 server.json을 읽어 그 주소로 자동 연결해요.', s: '위쪽에 "AI 연결됨"이 떠요. 가입·설치 없이 링크만 열면 돼요.' },
      { p: ['web', 'tun', 'mac'], on: ['web', 'mac'], tag: '연결 확인', w: 'web', t: '이제부터 모든 문제 요청은 이 터널 주소를 거쳐 개인 서버로 가요.' },
      { p: ['mac', 'board'], on: ['mac', 'board'], tag: '꺼짐', w: 'mac', t: 'Ctrl+C로 끄면 서버·터널이 꺼지고, server.json을 "꺼짐"으로 다시 푸시해요.', s: '화면은 "AI 꺼짐 · 서브넷만"으로 바뀌어요. 서브넷 탭에서 이어서 볼 수 있어요.' }
    ] },
    ask: { dim: ['board'], steps: [
      { p: null, on: ['web'], w: 'web', t: '단원(예: IP Connectivity)과 세부 범위, 난이도, 객관식·주관식을 고르고 "문제 받기"를 눌러요.' },
      { p: ['web', 'tun', 'mac'], on: ['web', 'mac'], tag: '범위·난이도', w: 'web', t: '고른 범위만 터널을 거쳐 개인 서버로 보내요.', s: '내 이름이나 기록은 보내지 않아요.' },
      { p: null, on: ['mac'], w: 'mac', t: '서버가 내 사이트에서 온 요청인지, 사용량이 남았는지 확인해요.', s: '방문자 1명 시간당 30번, 전체 하루 300번. 무료 한도를 지키려는 장치예요.' },
      { p: ['mac', 'ai'], on: ['mac', 'ai'], tag: '출제 지시 + 범위', w: 'mac', t: '"실제 시험처럼, 답이 하나뿐인 영어 문제" 같은 출제 지시를 붙여 제미나이에 요청해요.' },
      { p: ['ai', 'mac'], on: ['ai', 'mac'], tag: '문제 + 보기 + 정답', w: 'ai', t: '제미나이가 영어 문제·보기 4개·정답을 정해진 형식(JSON)으로 돌려줘요.', s: '모델이 바쁘면 서버가 다른 모델(3개 중)로 바꿔 다시 시도해요.' },
      { p: null, on: ['mac'], w: 'mac', t: '서버가 정답을 따로 떼어 보관해요.', s: '정답은 개인 서버 밖으로 나가지 않아요.' },
      { p: ['mac', 'tun', 'web'], on: ['web'], tag: '문제·보기만', w: 'mac', t: '화면에는 문제와 보기만 도착해요.', s: '화면 코드를 열어 봐도 정답은 없어요.' }
    ] },
    grade: { dim: ['board'], steps: [
      { p: null, on: ['web'], w: 'web', t: '보기를 고르거나 주관식 답을 적어 "제출"을 눌러요.' },
      { p: ['web', 'tun', 'mac'], on: ['web', 'mac'], tag: '내 답', w: 'web', t: '내 답만 서버로 보내요.' },
      { p: null, on: ['mac'], w: 'mac', t: '객관식은 서버가 보관한 정답과 직접 비교해 맞다·틀리다를 정해요.', s: 'AI가 아니라 코드가 판정해서 채점이 흔들리지 않아요. 주관식은 AI가 의미를 보고 판단해요.' },
      { p: ['mac', 'ai'], on: ['mac', 'ai'], tag: '문제 + 정답 + 내 답', w: 'mac', t: '문제·정답·내 답·판정을 함께 보내 해설을 요청해요.' },
      { p: ['ai', 'mac'], on: ['ai', 'mac'], tag: '영어 해설', w: 'ai', t: '제미나이가 왜 맞고 틀렸는지, 어떤 개념을 헷갈렸는지 쉬운 영어로 해설해요.' },
      { p: ['mac', 'tun', 'web'], on: ['web'], tag: '판정 + 해설', w: 'mac', t: '화면에 정답·오답과 해설, 핵심 개념이 떠요.' },
      { p: null, on: ['web'], w: 'web', t: 'XP가 오르고, 오늘의 퀘스트·배지·칭호가 갱신돼요.', s: '게임 기록은 각자 브라우저에만 저장돼요.' }
    ] },
    sub: { dim: ['tun', 'mac', 'ai'], steps: [
      { p: ['board', 'web'], on: ['web', 'board'], tag: '꺼짐', w: 'web', t: '서버가 꺼져 있으면, 화면이 안내판에서 "꺼짐"을 읽고 "AI 꺼짐 · 서브넷만"으로 바뀌어요.' },
      { p: null, on: ['web'], w: 'web', t: '서브넷 문제는 화면의 코드가 직접 만들어요. (예: 192.168.10.77/27의 네트워크 주소는?)', s: '서버도 AI도 필요 없어요.' },
      { p: null, on: ['web'], w: 'web', t: '답을 내면 화면이 직접 계산해 채점하고, 풀이 과정을 영어로 보여 줘요.', s: 'AI가 틀리기 쉬운 계산이라 일부러 코드로 했어요.' },
      { p: null, on: ['web'], w: 'web', t: 'XP·퀘스트·배지도 그대로 쌓여요.', s: '서버가 꺼져 있어도 공부는 계속할 수 있어요.' }
    ] }
  };
  var mqV = window.matchMedia('(max-width: 700px)');
  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var scen = 'setup', idx = 0, playing = false, started = false, timer = null, raf = null, L, svg, packet;
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
