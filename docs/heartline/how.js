/* Heartline 작동 방식 — 재생형 통신 흐름 그림 + 역할 트리 + 설계 이유 (prd.html).
   쓰는 법: <div class="hl-how" data-hl-how></div> 를 두고 how.css · how.js 를 불러온다. */
(function () {
  var LOCK = '<span class="hw-lock" aria-label="밖으로 안 나감"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg></span>';
  var ICO = {
    board: '<rect x="5" y="3.5" width="14" height="17" rx="2"/><path d="M9 3.5V2.5h6v1M8.5 9h7M8.5 13h7M8.5 17h4"/>',
    web: '<rect x="6.5" y="2.5" width="11" height="19" rx="2.5"/><path d="M10.5 18.5h3"/>',
    tun: '<path d="M7 18a4.5 4.5 0 0 1-.6-8.96A6 6 0 0 1 18 8.5a4.5 4.5 0 0 1-.5 9.5z"/>',
    srv: '<rect x="4" y="5" width="16" height="11" rx="1.5"/><path d="M2 19.5h20"/>',
    ai: '<path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8zM18.5 15.5l.7 2 2 .7-2 .7-.7 2-.7-2-2-.7 2-.7z"/>'
  };
  function ic(k) { return '<svg viewBox="0 0 24 24" aria-hidden="true">' + ICO[k] + '</svg>'; }
  var CTL = '<div class="hw-ctl">' +
    '<button type="button" data-r="prev" aria-label="이전 단계"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10 3L5 8l5 5"/></svg></button>' +
    '<button type="button" data-r="play" class="play">▶ 재생</button>' +
    '<button type="button" data-r="next" aria-label="다음 단계"><svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 3l5 5-5 5"/></svg></button></div>';
  function leaf(t, lock) { return '<li>' + (lock ? LOCK : '') + '<span>' + t + '</span></li>'; }
  function branch(cls, k, t, s, leaves) {
    return '<li class="' + cls + '"><div class="hw-head"><span class="hw-ic">' + ic(k) + '</span><div><strong>' + t + '</strong><small>' + s + '</small></div></div><ul class="hw-leaves">' + leaves.join('') + '</ul></li>';
  }
  var TEMPLATE =
    '<div class="hw-stage"><div class="hw-top">' +
    '<div class="hw-tabs" role="tablist" aria-label="장면">' +
    '<button type="button" role="tab" data-t="setup" aria-selected="true">🔌 서버 켜기<small>처음 한 번</small></button>' +
    '<button type="button" role="tab" data-t="heart" aria-selected="false">💞 마음 대화</button>' +
    '<button type="button" role="tab" data-t="crisis" aria-selected="false">🆘 위기 대응<small>서버 꺼져도 OK</small></button>' +
    '<button type="button" role="tab" data-t="english" aria-selected="false">🇬🇧 영어 모드</button>' +
    '</div>' + CTL + '</div>' +
    '<div class="hw-svg" data-r="svg" role="img" aria-label="Heartline 구성도: 주소 안내판, 사용자 화면, 임시 터널, 답변 서버, 제미나이"></div>' +
    '<div class="hw-cap"><div class="hw-prog" data-r="prog"></div><div class="hw-cap-row" aria-live="polite"><span class="hw-n" data-r="num">01</span><p data-r="cap"></p></div></div></div>' +
    '<h3 class="hw-h3">어디서 무엇을 하나</h3>' +
    '<p class="hw-sub">Heartline을 이루는 다섯 부분과 각자 맡은 일이에요. ' + LOCK + ' 표시는 그곳 밖으로 나가지 않는 것이에요.</p>' +
    '<div class="hw-tree"><div class="hw-root"><span>💗 Heartline</span></div><ul class="hw-branches">' +
    branch('hb-web', 'web', '사용자 화면', '휴대폰·PC 브라우저', [
      leaf('<b>메신저 대화방</b> · 입력 중 · 말풍선 · 💗'),
      leaf('<b>대화·페르소나 저장</b> (각자 브라우저)', 1),
      leaf('<b>위기 키워드 감지 · 🆘 카드</b> (서버 없이)'),
      leaf('전화번호·이메일 <b>가리고</b> 보내기')
    ]) +
    branch('hb-board', 'board', '무료 호스팅', 'GitHub Pages 등', [
      leaf('화면 파일 (HTML·CSS·JS)'),
      leaf('<b>주소 안내판</b> server.json'),
      leaf('start-public.sh가 <b>주소만</b> 자동 커밋·푸시')
    ]) +
    branch('hb-tun', 'tun', '임시 터널', 'Cloudflare · 무료', [
      leaf('답변 서버에 임시 공개 주소 연결'),
      leaf('켤 때마다 주소가 바뀜 → 안내판이 해결')
    ]) +
    branch('hb-srv', 'srv', '답변 서버', '운영자 컴퓨터 · Python', [
      leaf('<b>AI 키</b> (.env)', 1),
      leaf('<b>안전 검사</b> · 미성년 페르소나 거부'),
      leaf('<b>지시 조립</b>: 안전 → 페르소나 → 모드 → 기억'),
      leaf('<b>대화 저장 안 함</b> · 사용량 제한')
    ]) +
    branch('hb-ai', 'ai', '제미나이', 'Google · 무료 등급', [
      leaf('<b>마음 대화</b> 답장'),
      leaf('<b>영어 대화</b> + 교정'),
      leaf('위기 신호 판단 (2중 감지의 하나)')
    ]) +
    '</ul></div>' +
    '<div class="hw-why">' +
    '<div><span class="k">SOS</span><h4>🆘는 서버 없이</h4><p>위기 감지와 도움 카드는 화면 코드가 직접 해요. 서버가 꺼져 있어도 동작해요.</p></div>' +
    '<div><span class="k">PRIVACY</span><h4>대화는 내 브라우저에</h4><p>서버는 답만 만들고 대화를 저장하지 않아요. 개인정보는 보내기 전에 가려요.</p></div>' +
    '<div><span class="k">KEY</span><h4>키는 서버에만</h4><p>공개 화면에 키를 넣으면 누구나 볼 수 있어서, AI 호출은 서버만 해요.</p></div>' +
    '<div><span class="k">₩0</span><h4>추가 비용 없음</h4><p>무료 호스팅, 무료 터널, 제미나이 무료 등급만 써요.</p></div>' +
    '</div>';

  var NODES = {
    board: { k: 'board', t: '주소 안내판', s: 'server.json' },
    web: { k: 'web', t: '사용자 화면', s: '메신저 대화방' },
    tun: { k: 'tun', t: '임시 터널', s: 'Cloudflare' },
    srv: { k: 'srv', t: '답변 서버', s: '키 · 안전 검사' },
    ai: { k: 'ai', t: '제미나이', s: '무료 등급' }
  };
  var LAYOUT = {
    h: { w: 1120, h: 310, cw: 200, ch: 84,
      pos: { board: [420, 52], web: [140, 240], tun: [420, 240], srv: [700, 240], ai: [980, 240] },
      links: {
        'web-tun': { p: [[240, 240], [320, 240]], l: 'HTTPS', lp: [280, 240] },
        'tun-srv': { p: [[520, 240], [600, 240]], l: '터널', lp: [560, 240] },
        'srv-ai': { p: [[800, 240], [880, 240]], l: 'API', lp: [840, 240] },
        'board-web': { p: [[320, 52], [140, 52], [140, 198]], l: '주소 읽기', lp: [140, 125] },
        'board-srv': { p: [[520, 52], [700, 52], [700, 198]], l: '주소 등록', lp: [700, 125], dash: 1 }
      } },
    v: { w: 400, h: 588, cw: 270, ch: 76,
      pos: { board: [150, 44], web: [150, 164], tun: [150, 284], srv: [150, 404], ai: [150, 524] },
      links: {
        'board-web': { p: [[150, 82], [150, 126]], l: '주소 읽기', lp: [150, 104] },
        'web-tun': { p: [[150, 202], [150, 246]], l: 'HTTPS', lp: [150, 224] },
        'tun-srv': { p: [[150, 322], [150, 366]], l: '터널', lp: [150, 344] },
        'srv-ai': { p: [[150, 442], [150, 486]], l: 'API', lp: [150, 464] },
        'board-srv': { p: [[285, 44], [348, 44], [348, 404], [285, 404]], l: '등록', lp: [348, 224], dash: 1 }
      } }
  };
  var WHO = { web: ['w', '사용자 화면'], srv: ['s', '답변 서버'], ai: ['a', '제미나이'], board: ['b', '주소 안내판'], tun: ['b', 'Cloudflare 터널'] };
  var SCEN = {
    setup: { dim: ['ai'], steps: [
      { p: null, on: ['srv'], w: 'srv', t: '운영자가 start-public.sh를 실행하면, 운영자 컴퓨터에서 답변 서버(server.py)가 켜져요.', s: '아직은 그 컴퓨터 안(127.0.0.1)에서만 접속할 수 있어요.' },
      { p: ['srv', 'tun'], on: ['srv', 'tun'], tag: '터널 열어 줘', w: 'srv', t: '스크립트가 cloudflared를 실행해 Cloudflare에 임시 터널을 요청해요.', s: '가입도 비용도 없는 무료 터널이에요.' },
      { p: ['tun', 'srv'], on: ['tun', 'srv'], tag: 'https://….trycloudflare.com', w: 'tun', t: 'Cloudflare가 서버로 이어지는 임시 공개 주소를 만들어 줘요.', s: '켤 때마다 주소가 바뀌어서, 화면 코드에 미리 적어 둘 수 없어요.' },
      { p: ['srv', 'board'], on: ['srv', 'board'], tag: 'server.json 푸시', w: 'srv', t: '스크립트가 그 주소를 server.json에 적고, 이 파일 하나만 GitHub에 커밋·푸시해요.', s: '.py 코드는 바뀌지 않아요. 1~2분 뒤 공개 사이트에 반영돼요. 사람이 직접 할 일은 없어요.' },
      { p: ['board', 'web'], on: ['board', 'web'], tag: '주소', w: 'web', t: '사용자가 앱을 열면, 화면이 server.json을 읽어 그 주소로 자동 연결해요.', s: '위쪽에 "AI 연결됨"이 떠요. 가입·설치 없이 링크만 열면 돼요.' },
      { p: ['web', 'tun', 'srv'], on: ['web', 'srv'], tag: '연결 확인', w: 'web', t: '이제부터 모든 메시지는 이 터널 주소를 거쳐 답변 서버로 가요.' },
      { p: ['srv', 'board'], on: ['srv', 'board'], tag: '꺼짐', sos: 1, w: 'srv', t: 'Ctrl+C로 끄면 서버·터널이 꺼지고, server.json을 "꺼짐"으로 다시 푸시해요.', s: '화면은 "지금은 답하기 어려워요"로 바뀌고, 🆘는 계속 동작해요.' }
    ] },
    heart: { dim: [], steps: [
      { p: null, on: ['web'], w: 'web', t: '서버가 연결된 상태에서 "오늘 아무랑도 말 안 했어"를 보내면, 화면이 먼저 개인정보를 가리고 위기 표현이 있는지 살펴요.' },
      { p: ['web', 'tun', 'srv'], on: ['web', 'srv'], tag: '페르소나 + 최근 대화', w: 'web', t: '페르소나와 최근 대화, 새 메시지를 서버로 보내요.', s: '대화 원본은 내 브라우저에 있어요.' },
      { p: null, on: ['srv'], w: 'srv', t: '서버가 내 앱에서 온 요청인지, 사용량이 남았는지, 안전한지 확인해요.', s: '서버는 대화를 저장하지 않아요.' },
      { p: ['srv', 'ai'], on: ['srv', 'ai'], tag: '안전 → 페르소나 → 마음 → 기억', w: 'srv', t: '안전 규칙을 맨 앞에 두고, 페르소나·마음 대화 규칙·기억 요약을 붙여 제미나이에 요청해요.' },
      { p: ['ai', 'srv'], on: ['ai', 'srv'], tag: '공감 답장', w: 'ai', t: '제미나이가 판단 없이 공감하는 답장을 글자 단위로 보내요.' },
      { p: ['srv', 'tun', 'web'], on: ['web'], tag: '말풍선 2~3개', w: 'srv', t: '"···" 입력 중 표시 뒤에 짧은 말풍선이 차례로 도착해요.', s: '진짜 연인과 톡하는 느낌이에요.' },
      { p: null, on: ['web'], w: 'web', t: '대화는 내 브라우저에만 저장되고, 몇 턴마다 기억 요약이 갱신돼요.', s: '다음에 오면 "그 일은 좀 어때?"라고 먼저 물어봐요.' }
    ] },
    crisis: { dim: [], steps: [
      { p: null, on: ['web'], w: 'web', sos: 1, t: '위험한 표현을 보내면, 화면이 키워드로 바로 알아차려요.', s: '서버를 기다리지 않아요.' },
      { p: null, on: ['web'], w: 'web', sos: 1, t: '곧바로 🆘 도움 카드(109 · 1577-0199 · 112 · 119)를 띄워요.', s: '서버가 꺼져 있어도 여기까지는 항상 동작해요.' },
      { p: ['web', 'tun', 'srv'], on: ['srv'], tag: '메시지', sos: 1, w: 'web', t: '서버가 켜져 있으면 메시지도 서버로 보내요.' },
      { p: ['srv', 'ai'], on: ['ai'], tag: '안전 규칙 우선', sos: 1, w: 'srv', t: '안전 규칙이 맨 앞이라, 제미나이는 캐릭터 연기보다 안부 확인을 먼저 해요.' },
      { p: ['ai', 'srv'], on: ['srv'], tag: '안부 + 위기 신호', sos: 1, w: 'ai', t: '진지한 안부 답장과 함께 "위기 신호"를 표시해 돌려줘요.', s: '화면 키워드 + AI 판단, 2중으로 감지해요.' },
      { p: ['srv', 'tun', 'web'], on: ['web'], tag: '"지금 안전한 곳에 있어?"', sos: 1, w: 'web', t: '상대가 "지금 안전한 곳에 있어?"라고 묻고, 대화를 끊지 않고 곁에 있어 줘요.', s: '영어 모드였다면 자동으로 꺼져요.' }
    ] },
    english: { dim: ['board'], steps: [
      { p: null, on: ['web'], w: 'web', t: '🇬🇧 토글을 켜면 같은 상대·같은 기억으로 영어 대화가 시작돼요.' },
      { p: ['web', 'tun', 'srv'], on: ['srv'], tag: 'I go to park alone.', w: 'web', t: '틀린 영어 문장도 편하게 보내요.' },
      { p: ['srv', 'ai'], on: ['ai'], tag: '영어 모드 지시', w: 'srv', t: '"자연스럽게 대화하고, 교정은 최대 2개" 같은 영어 모드 지시를 붙여요.' },
      { p: ['ai', 'srv'], on: ['srv'], tag: '답장 + 교정', w: 'ai', t: '제미나이가 영어 답장과 교정을 함께 보내요.' },
      { p: null, on: ['srv'], w: 'srv', t: '서버가 교정을 답장 본문과 분리해요.', s: '대화 흐름을 깨지 않으려고 본문에선 지적하지 않아요.' },
      { p: ['srv', 'tun', 'web'], on: ['web'], tag: '말풍선 + 교정 카드', w: 'web', t: '말풍선 아래에 "I went to the park alone." 교정 카드가 작게 붙어요.', s: '힘든 얘기가 나오면 영어보다 마음이 먼저예요.' }
    ] }
  };

  function mount(root) {
    root.innerHTML = TEMPLATE;
    var R = function (k) { return root.querySelector('[data-r="' + k + '"]'); };
    var host = R('svg'), btnPlay = R('play'), cap = R('cap'), num = R('num'), prog = R('prog');
    var mqV = window.matchMedia('(max-width: 700px)');
    var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var scen = 'setup', idx = 0, playing = false, started = false, timer = null, raf = null, L, svg, packet;
    function pts(a) { return a.map(function (q) { return q.join(','); }).join(' '); }
    function pill(cls, x, y, text, h, extra) {
      return '<g class="' + cls + '"' + (extra || '') + ' transform="translate(' + x + ' ' + y + ')"><rect rx="' + h / 2 + '" height="' + h + '" y="' + (-h / 2) + '"/><text>' + text + '</text></g>';
    }
    function build() {
      L = LAYOUT[mqV.matches ? 'v' : 'h'];
      var h = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + L.w + ' ' + L.h + '" aria-hidden="true">';
      Object.keys(L.links).forEach(function (k) { var ln = L.links[k]; h += '<polyline class="track' + (ln.dash ? ' dash' : '') + '" data-k="' + k + '" points="' + pts(ln.p) + '"/>'; });
      Object.keys(L.links).forEach(function (k) { var ln = L.links[k]; h += pill('elab', ln.lp[0], ln.lp[1], ln.l, 26, ' data-k="' + k + '"'); });
      Object.keys(NODES).forEach(function (id) {
        var n = NODES[id], p = L.pos[id], x0 = -L.cw / 2;
        h += '<g class="node k-' + n.k + '" data-id="' + id + '" transform="translate(' + p[0] + ' ' + p[1] + ')">' +
          '<rect class="card" x="' + x0 + '" y="' + (-L.ch / 2) + '" width="' + L.cw + '" height="' + L.ch + '" rx="18"/>' +
          '<rect class="tile" x="' + (x0 + 16) + '" y="-22" width="44" height="44" rx="13"/>' +
          '<g class="ico" transform="translate(' + (x0 + 26) + ' -12)">' + ICO[n.k] + '</g>' +
          '<text class="ttl" x="' + (x0 + 74) + '" y="-10">' + n.t + '</text><text class="sub" x="' + (x0 + 74) + '" y="14">' + n.s + '</text></g>';
      });
      h += pill('packet', 0, 0, '', 30, ' style="display:none"') + '</svg>';
      host.innerHTML = h;
      svg = host.firstChild; packet = svg.querySelector('.packet');
      measure();
    }
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
    function animate(r, tag, sos, done) {
      cancelAnimationFrame(raf);
      if (!r) { packet.style.display = 'none'; return done(); }
      var P = r.pts, t = packet.querySelector('text'), rc = packet.querySelector('rect');
      packet.style.display = ''; packet.classList.toggle('sos', !!sos); t.textContent = tag;
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
      prog.innerHTML = SCEN[scen].steps.map(function (s, i) { return '<button type="button" data-i="' + i + '" aria-label="' + (i + 1) + '단계"></button>'; }).join('');
    }
    function show(i, anim) {
      var st = SCEN[scen].steps, s = st[i], dim = SCEN[scen].dim; idx = i;
      var r = s.p ? route(s.p) : null, used = r ? r.used : [];
      num.textContent = (i + 1 < 10 ? '0' : '') + (i + 1);
      var who = WHO[s.w];
      cap.innerHTML = '<span class="hw-who ' + who[0] + '">' + who[1] + '</span><br>' + s.t + (s.s ? '<small>' + s.s + '</small>' : '');
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
      if (anim) animate(r, s.tag, s.sos, after); else { cancelAnimationFrame(raf); packet.style.display = 'none'; after(); }
    }
    function syncBtn() { btnPlay.textContent = playing ? '❚❚ 일시정지' : '▶ 재생'; }
    function stop() { playing = false; clearTimeout(timer); syncBtn(); }
    function play() {
      if (playing) { stop(); return; }
      var last = SCEN[scen].steps.length - 1;
      var next = !started ? 0 : (idx >= last ? 0 : idx + 1); /* 멈춘 곳 다음 단계부터 이어서 */
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
  function init() { Array.prototype.forEach.call(document.querySelectorAll('[data-hl-how]'), mount); }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init); else init();
})();
