/* TRACER 공통 대기 화면(이용 화면·관리자 화면). AI를 기다리는 동안 화면 아래에 뜨는 카드.
   - traceroute처럼: 패킷이 경로를 따라 움직이고, 지나간 '홉'(단계)이 터미널처럼 한 줄씩 찍힌다(걸린 ms 포함).
   - 진행 막대·경과 초·몇 초마다 바뀌는 팁(문제 화면은 CCNA 상식, 관리자 화면은 사용 팁).
   - 0.4초 안에 끝나면 아예 안 보인다(저장된 문제처럼 빠른 응답은 깜빡임 없이). 12초 넘으면 "평소보다 오래 걸려요".
   - 페이지의 색(--panel·--accent 등)을 그대로 써서 밝은/어두운 화면 모두 맞고, "동작 줄이기" 설정이면 움직임을 줄인다.
   쓰는 법: var w = TracerWait.start('grade'); … w.step(2); … w.done();   (kind: question|grade|explain|admin|sql)
*/
(function () {
  var KINDS = {
    question: { title: '문제를 준비하고 있어요', steps: ['브라우저', 'TRACER 서버', '문제은행 확인', '제미나이에게 출제 요청', '문제 도착'], expect: 6 },
    grade:    { title: '채점하고 있어요', steps: ['답안 전송', 'TRACER 서버', '정답 확인', '해설 준비', '결과 도착'], expect: 5 },
    explain:  { title: '제미나이가 해설을 쓰고 있어요', steps: ['문제 전송', 'TRACER 서버', '문제 읽는 중', '해설 쓰는 중', '정리 중'], expect: 10 },
    admin:    { title: '명령을 처리하고 있어요', steps: ['명령 문장', 'TRACER 서버', '제미나이 해석', '명령 범위 확인', '화면에서 실행'], expect: 5 },
    sql:      { title: '조회하고 있어요', steps: ['명령 문장', '제미나이가 SQL 작성', '읽기 전용 검사', 'SQL 엔진 준비', '모의 데이터에서 실행'], expect: 8 }
  };
  var TIPS = {
    study: [
      'traceroute는 TTL을 1씩 늘려 보내며, 응답한 라우터를 차례로 찾아요.',
      'OSPF의 기본 hello 간격은 브로드캐스트 링크에서 10초, dead 간격은 40초예요.',
      '/30 서브넷에서 쓸 수 있는 호스트는 2개예요. 점대점 링크에 자주 써요.',
      '관리 거리(AD): 직접 연결 0, 정적 1, eBGP 20, OSPF 110, RIP 120.',
      'DHCP는 DORA 순서예요: Discover → Offer → Request → Acknowledge.',
      'SSH는 TCP 22번, Telnet은 23번 포트를 써요. 원격 관리는 SSH로!',
      'IPv6 주소는 128비트, 링크 로컬 주소는 FE80::/10으로 시작해요.',
      'STP 루트 브리지는 브리지 ID(우선순위+MAC)가 가장 낮은 스위치예요.',
      'PAT(NAT 오버로드)는 포트 번호로 여러 내부 호스트를 공인 IP 하나로 내보내요.',
      '802.1Q 트렁크의 네이티브 VLAN 프레임에는 태그가 붙지 않아요.',
      'LACP는 EtherChannel을 자동으로 협상하는 IEEE 표준(802.3ad)이에요.',
      'WPA3는 PSK 대신 SAE로 비밀번호 추측 공격을 어렵게 만들어요.'
    ],
    admin: [
      '명령 기록 탭에서 지난 작업을 되돌리거나 다시 실행할 수 있어요.',
      'SELECT로 시작하는 문장은 제미나이 없이 SQL로 바로 실행돼요.',
      '"3번 되돌려줘", "승인한 거 되돌려줘"처럼 말로 되돌릴 수 있어요.',
      '기간은 "열흘", "45일"처럼 아무 숫자로 말해도 돼요.',
      '지우기·승인 같은 작업은 실행 전에 대상을 보여 주고 다시 물어봐요.',
      '조회 결과에서 행을 골라 바로 승인·차단할 수 있어요.',
      '해석 방식은 명령창 옆에서 "규칙 우선"으로 바꿀 수 있어요.'
    ]
  };
  var CSS = '' +
    '.tw{position:fixed;left:50%;bottom:20px;transform:translate(-50%,12px);opacity:0;z-index:30;width:min(520px,calc(100vw - 24px));' +
    'background:var(--panel,#151D1B);color:var(--ink,#E5EDEA);border:1px solid var(--accent,#5FC7B8);border-radius:16px;padding:14px 16px 12px;' +
    'box-shadow:0 12px 40px rgba(0,0,0,.35);transition:opacity .2s,transform .2s;font-size:13.5px;line-height:1.5}' +
    '.tw.on{opacity:1;transform:translate(-50%,0)}' +
    '.tw .hd{display:flex;align-items:center;gap:8px;font-weight:700;margin-bottom:8px}' +
    '.tw .hd .t{flex:1}.tw .hd .sec{font-family:var(--mono,ui-monospace,Menlo,monospace);font-weight:500;font-size:12px;color:var(--ink-3,#788683)}' +
    '.tw .live{width:8px;height:8px;border-radius:50%;background:var(--accent,#5FC7B8);box-shadow:0 0 0 0 var(--accent,#5FC7B8);animation:twPulse 1.4s infinite}' +
    '.tw svg{display:block;width:100%;height:44px;margin:2px 0 6px}' +
    '.tw .ln{stroke:var(--rule,#26322F);stroke-width:2;stroke-dasharray:4 5}.tw .ln.lit{stroke:var(--accent,#5FC7B8);stroke-dasharray:none}' +
    '.tw .nd{fill:var(--sunk,#1C2624);stroke:var(--rule,#26322F);stroke-width:2;transition:fill .3s,stroke .3s}' +
    '.tw .nd.lit{fill:var(--accent-soft,#15302C);stroke:var(--accent,#5FC7B8)}.tw .nd.cur{stroke:var(--part,#E8B04A)}' +
    '.tw .pk{fill:var(--part,#E8B04A);filter:drop-shadow(0 0 4px var(--part,#E8B04A))}' +
    '.tw .term{background:var(--term-bg,#0A0F0E);color:var(--term-ink,#D9E3E0);border-radius:10px;padding:8px 10px;font-family:var(--mono,ui-monospace,Menlo,monospace);' +
    'font-size:12px;min-height:78px;max-height:110px;overflow:hidden}' +
    '.tw .term div{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;animation:twIn .25s ease-out}' +
    '.tw .term .n{color:#7D8A88;display:inline-block;width:2.2em}.tw .term .ms{color:#7BD49C}.tw .term .now{color:#E8B04A}' +
    '.tw .term .cur::after{content:"▋";margin-left:3px;animation:twBlink 1s steps(1) infinite}' +
    '.tw .twbar{height:5px;border-radius:3px;background:var(--sunk,#1C2624);margin:10px 0 8px;overflow:hidden}' +
    '.tw .twbar i{display:block;height:100%;width:0;background:var(--accent,#5FC7B8);border-radius:3px;transition:width .5s ease-out}' +
    '.tw .tip{font-size:12.5px;color:var(--ink-2,#A6B4B0);min-height:2.6em}.tw .tip b{color:var(--accent,#5FC7B8);margin-right:4px}' +
    '.tw .tip span{display:inline;animation:twIn .35s ease-out}.tw .slow{font-size:12.5px;color:var(--part,#E8B04A);margin-top:4px}' +
    '@keyframes twPulse{0%{box-shadow:0 0 0 0 rgba(95,199,184,.6)}70%{box-shadow:0 0 0 8px rgba(95,199,184,0)}100%{box-shadow:0 0 0 0 rgba(95,199,184,0)}}' +
    '@keyframes twIn{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}@keyframes twBlink{50%{opacity:0}}' +
    '@media (prefers-reduced-motion:reduce){.tw,.tw *{animation:none!important;transition:none!important}.tw .pk{display:none}}' +
    '@media (max-width:560px){.tw{bottom:10px;padding:12px}.tw .term{min-height:64px}}';
  function el(h) { var d = document.createElement('div'); d.innerHTML = h; return d.firstChild; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  var cur = null, styled = false;

  function start(kind, opt) {
    opt = opt || {};
    if (cur) cur.done(true);
    if (!styled) { var st = document.createElement('style'); st.textContent = CSS; document.head.appendChild(st); styled = true; }
    var K = Object.assign({}, KINDS[kind] || KINDS.question, opt), steps = K.steps.slice(), tips = (TIPS[opt.tips || (kind === 'admin' || kind === 'sql' ? 'admin' : 'study')] || TIPS.study).slice();
    tips.sort(function () { return Math.random() - 0.5; });
    var t0 = performance.now(), at = 0, stepAt = [0], real = [true], shown = false, closed = false, timers = [], tipI = 0, node = null;
    var w = {
      kind: kind,
      step: function (i) { return adv(i, true); },
      setTitle: function (t) { K.title = t; if (node) node.querySelector('.t').textContent = t; return w; },
      done: function (quick) {
        if (closed) return; closed = true; timers.forEach(clearTimeout); timers.forEach(clearInterval);
        if (cur === w) cur = null;
        if (!node) return;
        if (quick) { node.remove(); return; }
        closed = false; adv(steps.length - 1, true); closed = true; bar();  // 마지막 단계(도착)를 찍고 막대 100%
        var n = node; setTimeout(function () { n.classList.remove('on'); setTimeout(function () { n.remove(); }, 220); }, 260);
      }
    };
    function adv(i, isReal) {  // isReal: 실제 일이 끝나서 넘어감(ms 표시) / 아니면 예상 시간으로 넘어감(✓)
      i = Math.min(Math.max(i, 0), steps.length - 1); if (i <= at || closed) return w;
      while (at < i) { at++; stepAt[at] = performance.now() - t0; real[at] = !!isReal; }
      paint(); return w;
    }
    function svg() {
      var n = steps.length, xs = steps.map(function (_, i) { return 16 + i * (468 / (n - 1)); });
      var lines = xs.slice(1).map(function (x, i) { return '<line class="ln' + (i < at ? ' lit' : '') + '" x1="' + (xs[i] + 9) + '" y1="22" x2="' + (x - 9) + '" y2="22"/>'; }).join('');
      var nodes = xs.map(function (x, i) { return '<circle class="nd' + (i <= at ? ' lit' : '') + (i === at ? ' cur' : '') + '" cx="' + x + '" cy="22" r="8"/>'; }).join('');
      var a = xs[at], b = xs[Math.min(at + 1, n - 1)];
      var pk = at < n - 1 ? '<circle class="pk" r="4" cy="22"><animate attributeName="cx" values="' + a + ';' + b + '" dur="1.1s" repeatCount="indefinite"/></circle>' : '';
      return '<svg viewBox="0 0 500 44" aria-hidden="true">' + lines + nodes + pk + '</svg>';
    }
    function term() {
      var rows = [];
      for (var i = 0; i <= at; i++) {
        var ms = i < at ? (real[i + 1] ? Math.max(1, Math.round(stepAt[i + 1] - stepAt[i])) + ' ms' : '✓') : '';
        rows.push('<div' + (i === at ? ' class="cur"' : '') + '><span class="n">' + (i + 1) + '</span>' + esc(steps[i]) + (ms ? '  <span class="ms">' + ms + '</span>' : i === at && at < steps.length - 1 ? '  <span class="now">* * *</span>' : '') + '</div>');
      }
      return '<div style="color:#7D8A88">$ traceroute ' + esc(kind === 'admin' || kind === 'sql' ? 'admin.tracer' : 'gemini.tracer') + '</div>' + rows.slice(-4).join('');
    }
    function paint() {
      if (!node) return;
      node.querySelector('.vis').innerHTML = svg();
      node.querySelector('.term').innerHTML = term();
      node.setAttribute('aria-label', K.title + ' · ' + steps[at]);
      node.querySelector('.sr').textContent = steps[at];
      bar();
    }
    function bar() {
      if (!node) return;
      var s = (performance.now() - t0) / 1000, exp = K.expect || 6;
      var p = closed ? 100 : Math.min(92, (1 - Math.exp(-s / exp * 1.6)) * 100);  // 처음엔 빠르게, 끝 근처에선 천천히(멈춘 것처럼 보이지 않게)
      p = Math.max(p, (at / (steps.length - 1)) * 85);
      node.querySelector('.twbar i').style.width = p + '%';
      node.querySelector('.sec').textContent = s.toFixed(1) + '초';
      var sl = node.querySelector('.slow');
      sl.textContent = s > 30 ? '응답이 늦어요. 잠시 뒤 다시 시도해 보세요(제미나이 무료 등급이 바쁠 수 있어요).' : s > 12 ? '제미나이가 평소보다 오래 걸려요… 조금만 기다려 주세요.' : '';
    }
    function tip() {
      if (!node || !tips.length) return;
      node.querySelector('.tip').innerHTML = '<b>' + (opt.tips === 'admin' || kind === 'admin' || kind === 'sql' ? 'TIP' : '알고 있었나요?') + '</b><span>' + esc(tips[tipI++ % tips.length]) + '</span>';
    }
    function mount() {
      if (closed) return;
      shown = true;
      node = el('<div class="tw" role="status" aria-live="polite"><div class="hd"><span class="live" aria-hidden="true"></span><span class="t">' + esc(K.title) + '</span><span class="sec">0.0초</span></div>' +
        '<div class="vis"></div><div class="term" aria-hidden="true"></div><div class="twbar" aria-hidden="true"><i></i></div><div class="tip"></div><div class="slow"></div>' +
        '<span class="sr" style="position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)"></span></div>');
      document.body.appendChild(node); paint(); tip();
      requestAnimationFrame(function () { node.classList.add('on'); });
      timers.push(setInterval(bar, 100));
      timers.push(setInterval(tip, 4500));
    }
    // 단계를 시간에 맞춰 조금씩 앞으로(마지막 단계는 실제로 끝날 때만)
    var auto = Math.max(500, (K.expect || 6) * 1000 / (steps.length));
    for (var k = 1; k < steps.length - 1; k++) (function (k) { timers.push(setTimeout(function () { adv(k, false); }, auto * k * (k > 2 ? 1.4 : 1))); })(k);
    timers.push(setTimeout(mount, opt.delay != null ? opt.delay : 400));
    cur = w;
    return w;
  }
  window.TracerWait = { start: start, current: function () { return cur; }, kinds: KINDS };
})();
