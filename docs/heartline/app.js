/* Heartline 앱 — 메신저 화면, 브라우저 저장(IndexedDB), 위기 감지(서버 없이도), 답변 서버 연결 */
(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };

  /* ── 안전: 서버 safety.py 와 같은 목록. 고치면 두 곳을 같이 ── */
  var HIGH = ['죽고싶', '죽어버리고싶', '죽어버릴', '자살', '목숨을끊', '목숨끊', '손목을긋', '손목긋', '자해',
    '약을한꺼번에', '뛰어내리고싶', '뛰어내릴', '유서', '살고싶지않', '인생끝내', '인생을끝내',
    '죽는게나을', '죽는게낫', '없어지는게나아', '없어지는게낫', '죽으려고', '죽을래',
    'iwanttodie', 'killmyself', 'suicide', 'endmylife'];
  var LOW = ['다끝내고싶', '다끝내버리고', '사라지고싶', '사라져버리고싶', '눈안떴으면', '안깼으면', '안깨어났으면',
    '없어도아무도', '다정리하려', '작별인사', '살아야할이유', '살아갈이유', '버틸힘이없', '버틸수가없',
    '없어지고싶', '없어져도', '마지막대화', '이제안녕', '놓아버리고싶', '다놓고싶', 'nothingtolivefor', 'disappearforever'];
  function norm(t) { return (t || '').toLowerCase().replace(/[\s\p{P}\p{S}_]+/gu, ''); }
  function detectRisk(t) {
    var n = norm(t); if (!n) return 'none';
    if (HIGH.some(function (w) { return n.indexOf(w) > -1; })) return 'high';
    if (LOW.some(function (w) { return n.indexOf(w) > -1; })) return 'low';
    return 'none';
  }
  function maskPII(t) {
    return t.replace(/(?<!\d)\d{6}\s?-?\s?[1-4]\d{6}(?!\d)/g, '***')
      .replace(/[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}/g, '***')
      .replace(/(?:\+82[\s-]?)?(?<!\d)0?1[016789][\s-]?\d{3,4}[\s-]?\d{4}(?!\d)/g, '***');
  }

  /* ── 저장: IndexedDB (안 되면 메모리) ── */
  var mem = {}, dbp = null;
  function db() {
    if (dbp) return dbp;
    dbp = new Promise(function (res) {
      try {
        var r = indexedDB.open('heartline', 1);
        r.onupgradeneeded = function () { r.result.createObjectStore('kv'); };
        r.onsuccess = function () { res(r.result); };
        r.onerror = function () { res(null); };
      } catch (e) { res(null); }
    });
    return dbp;
  }
  function get(k) {
    return db().then(function (d) {
      if (!d) return mem[k];
      return new Promise(function (res) {
        try { var q = d.transaction('kv').objectStore('kv').get(k); q.onsuccess = function () { res(q.result); }; q.onerror = function () { res(mem[k]); }; }
        catch (e) { res(mem[k]); }
      });
    });
  }
  function put(k, v) {
    mem[k] = v;
    return db().then(function (d) {
      if (!d) return;
      try { d.transaction('kv', 'readwrite').objectStore('kv').put(v, k); } catch (e) {}
    });
  }
  function wipeAll() {
    mem = {};
    return db().then(function (d) {
      if (!d) return;
      return new Promise(function (res) { var t = d.transaction('kv', 'readwrite'); t.objectStore('kv').clear(); t.oncomplete = res; t.onerror = res; });
    });
  }

  /* ── 상태 ── */
  var S = { persona: null, messages: [], summary: '', sinceSummary: 0,
    settings: { english: false, level: 'B1', ratio: 'english', strength: 'light' } };
  var server = null, online = false, busy = false, gender = 'female';
  function saveMsgs() { put('messages', S.messages.slice(-400)); }
  function saveSettings() { put('settings', S.settings); }
  function uid() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 6); }

  /* ── 프리셋 ── */
  var PRESETS = [
    { key: 'warm', title: '다정한 연상', desc: '포근하게 들어 주고, 천천히 물어봐 주는 사람', emoji: '🌷',
      names: { female: '하린', male: '도윤' }, ageGroup: '30s', speech: '반말', emojiLevel: '조금', nicknameForUser: '자기야',
      traits: { warmth: 90, playful: 35, calm: 75, direct: 30 }, statusMessage: '오늘도 네 편이야 💗' },
    { key: 'play', title: '장난꾸러기 동갑', desc: '웃게 해 주고, 하루 얘기를 다 듣고 싶어 하는 사람', emoji: '🌻',
      names: { female: '유나', male: '준호' }, ageGroup: '20s', speech: '반말', emojiLevel: '많이', nicknameForUser: '자기',
      traits: { warmth: 75, playful: 90, calm: 30, direct: 55 }, statusMessage: '오늘 뭐 했어? 다 말해 줘 😆' },
    { key: 'calm', title: '차분한 지적인 타입', desc: '조용히 곁에 있어 주고, 같이 생각해 주는 사람', emoji: '🌙',
      names: { female: '서연', male: '지훈' }, ageGroup: '30s', speech: '존댓말', emojiLevel: '없음', nicknameForUser: '당신',
      traits: { warmth: 70, playful: 25, calm: 90, direct: 60 }, statusMessage: '천천히, 같이 생각해 봐요' }
  ];
  function today() { var d = new Date(); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); }
  function emojiFor(p) { return p.avatar || (p.gender === 'male' ? '🌿' : '🌷'); }

  /* ── 화면 전환 ── */
  function show(id) { ['gate', 'persona', 'chat'].forEach(function (s) { $(s).hidden = s !== id; }); }

  /* ── 입장 ── */
  function initGate() {
    var a = $('ageOk'), p = $('privOk'), go = $('gateGo');
    function upd() { go.disabled = !(a.checked && p.checked); }
    a.onchange = p.onchange = upd;
    go.onclick = function () { try { localStorage.setItem('hl-agreed', '1'); } catch (e) {} put('agreed', true); startAfterGate(); };
  }

  /* ── 페르소나 ── */
  function renderPresets() {
    $('presets').innerHTML = PRESETS.map(function (p, i) {
      return '<button class="preset" data-i="' + i + '"><span class="ava">' + p.emoji + '</span><span><b>' + p.names[gender] + ' · ' + p.title +
        '</b><small>' + p.desc + '</small></span></button>';
    }).join('');
  }
  function initPersona() {
    document.querySelectorAll('.seg button').forEach(function (b) {
      b.onclick = function () {
        gender = b.dataset.g;
        document.querySelectorAll('.seg button').forEach(function (x) { x.setAttribute('aria-pressed', x === b); });
        renderPresets();
      };
    });
    $('presets').onclick = function (e) {
      var b = e.target.closest('.preset'); if (!b) return;
      var p = PRESETS[+b.dataset.i];
      setPersona({ name: p.names[gender], gender: gender, nicknameForUser: p.nicknameForUser, ageGroup: p.ageGroup,
        traits: p.traits, speech: p.speech, emojiLevel: p.emojiLevel, relationshipStart: today(),
        statusMessage: p.statusMessage, avatar: p.emoji, preset: p.key });
    };
    $('pForm').relationshipStart.value = today();
    $('pForm').onsubmit = function (e) {
      e.preventDefault();
      var f = e.target, name = f.name.value.trim();
      if (!name) return;
      setPersona({ name: name, gender: gender, nicknameForUser: f.nicknameForUser.value.trim() || '너', ageGroup: f.ageGroup.value,
        traits: { warmth: +f.warmth.value, playful: +f.playful.value, calm: +f.calm.value, direct: +f.direct.value },
        speech: f.speech.value, emojiLevel: f.emojiLevel.value, relationshipStart: f.relationshipStart.value || today(),
        statusMessage: f.statusMessage.value.trim(), interests: f.interests.value.trim(), avatar: gender === 'male' ? '🌿' : '🌷' });
    };
    $('pBack').onclick = function () { if (S.persona) { show('chat'); scrollEnd(); } };
  }
  function greeting(p) {
    var n = p.nicknameForUser || '너';
    if (p.speech === '존댓말') return [n + ', 오셨네요.', '오늘 하루는 어떠셨어요? 편하게 이야기해 주세요.'];
    if (p.preset === 'play') return [n + '!! 왔다 😆', '오늘 뭐 했어? 하나도 빼지 말고 다 말해 줘'];
    return [n + ', 왔구나 😊', '오늘 하루 어땠어? 나한테는 편하게 말해도 돼.'];
  }
  function setPersona(p) {
    var first = !S.persona;
    S.persona = p; put('persona', p);
    applyPersona();
    show('chat');
    if (first || !S.messages.length) {
      S.messages = []; S.summary = ''; S.sinceSummary = 0; put('summary', ''); put('sinceSummary', 0);
      deliver(greeting(p), 400);
    } else {
      pushSys(p.name + ' 님으로 상대가 바뀌었어요');
    }
    renderAll();
  }
  function applyPersona() {
    var p = S.persona; if (!p) return;
    $('pName').textContent = p.name; $('profName').textContent = p.name;
    $('avaEmoji').textContent = emojiFor(p); $('profAva').textContent = emojiFor(p);
    $('pStatus').textContent = p.statusMessage || ''; $('profStatus').textContent = p.statusMessage || '';
    var d = dday(p.relationshipStart); $('dday').textContent = d ? '💞 D+' + d : ''; $('profD').textContent = d ? '우리 💞 D+' + d : '';
  }
  function dday(s) {
    if (!s) return 0; var a = new Date(s + 'T00:00:00'), b = new Date(today() + 'T00:00:00');
    return Math.max(1, Math.round((b - a) / 86400000) + 1);
  }

  /* ── 메시지 그리기 ── */
  var msgs = $('msgs');
  function hhmm(ts) { var d = new Date(ts); return String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0'); }
  function dayLabel(ts) { var d = new Date(ts); return d.getFullYear() + '년 ' + (d.getMonth() + 1) + '월 ' + d.getDate() + '일'; }
  function esc(t) { return String(t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function sosHTML() {
    return '<div class="sos-card" data-kind="sos"><b>🧡 혼자 견디지 않아도 돼요</b>' +
      '<a href="tel:109">📞 109 · 자살예방상담전화 (24시간)</a><a href="tel:15770199">📞 1577-0199 · 정신건강위기상담</a>' +
      '<a href="tel:112">🚨 지금 위험하면 112 · 119</a></div>';
  }
  function node(m, prev) {
    var out = '';
    if (!prev || dayLabel(prev.ts) !== dayLabel(m.ts)) out += '<div class="day">' + dayLabel(m.ts) + '</div>';
    if (m.role === 'sys') return out + '<div class="sys">' + esc(m.text) + '</div>';
    if (m.role === 'sos') return out + sosHTML();
    var me = m.role === 'user', cont = prev && prev.role === m.role && (m.ts - prev.ts) < 120000 && !me;
    var meta = '<div class="meta">' + (me && !m.read ? '<span class="read">1</span>' : '') + '<span>' + hhmm(m.ts) + '</span></div>';
    out += '<div class="row ' + (me ? 'me' : 'you') + (cont ? ' cont' : '') + '" data-id="' + m.id + '">' +
      (me ? '' : '<span class="ava sm" aria-hidden="true">' + emojiFor(S.persona || {}) + '</span>') +
      '<div class="b">' + esc(m.text) + (m.heart ? '<span class="heart">💗</span>' : '') + '</div>' + meta + '</div>';
    (m.corrections || []).forEach(function (c) {
      out += '<div class="fix">✏️ 더 자연스럽게<br><b>' + esc(c.corrected) + '</b>' + (c.reason ? '<br><span class="why">· ' + esc(c.reason) + '</span>' : '') + '</div>';
    });
    return out;
  }
  function renderAll() {
    var h = '';
    S.messages.forEach(function (m, i) { h += node(m, S.messages[i - 1]); });
    msgs.innerHTML = h; scrollEnd();
  }
  function scrollEnd() { requestAnimationFrame(function () { msgs.scrollTop = msgs.scrollHeight; }); }
  function push(m) { m.id = m.id || uid(); m.ts = m.ts || Date.now(); S.messages.push(m); saveMsgs(); renderAll(); return m; }
  function pushSys(t) { return push({ role: 'sys', text: t }); }
  var typingEl = null;
  function typing(on) {
    if (on && !typingEl) {
      typingEl = document.createElement('div'); typingEl.className = 'row you typing';
      typingEl.innerHTML = '<span class="ava sm">' + emojiFor(S.persona || {}) + '</span><div class="b"><i></i><i></i><i></i></div>';
      msgs.appendChild(typingEl); scrollEnd();
    } else if (!on && typingEl) { typingEl.remove(); typingEl = null; }
  }
  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
  function deliver(bubbles, firstDelay) {
    return bubbles.reduce(function (p, text, i) {
      return p.then(function () {
        typing(true);
        if (typingEl) msgs.appendChild(typingEl);
        return sleep(i === 0 ? (firstDelay || 300) : Math.min(1500, 450 + text.length * 22));
      }).then(function () { typing(false); push({ role: 'assistant', text: text }); });
    }, Promise.resolve());
  }

  /* 두 번 탭 → 💗 */
  msgs.addEventListener('dblclick', function (e) {
    var row = e.target.closest('.row.you'); if (!row) return;
    var m = S.messages.find(function (x) { return x.id === row.dataset.id; }); if (!m) return;
    m.heart = !m.heart; saveMsgs(); renderAll();
  });

  /* ── 서버 연결 ── */
  function findServer() {
    var h = location.hash.match(/server=([^&]+)/);
    if (h) { server = decodeURIComponent(h[1]).replace(/\/$/, ''); return Promise.resolve(server); }
    if (location.port === '8766') { server = ''; return Promise.resolve(server); }
    return fetch('server.json?t=' + Date.now(), { cache: 'no-store' }).then(function (r) { return r.json(); })
      .then(function (j) { server = j && j.url ? j.url.replace(/\/$/, '') : null; }).catch(function () { server = null; })
      .then(function () {
        if (server === null && /^(localhost|127\.0\.0\.1)$/.test(location.hostname)) server = 'http://127.0.0.1:8766';
        return server;
      });
  }
  function checkHealth() {
    if (server === null) { setOnline(false); return Promise.resolve(false); }
    return fetch(server + '/api/health', { cache: 'no-store' }).then(function (r) { return r.json(); })
      .then(function (j) { setOnline(!!(j && j.ok && j.ai)); return online; }).catch(function () { setOnline(false); return false; });
  }
  function setOnline(v) {
    online = v; $('aiDot').classList.toggle('on', v);
    $('aiDot').title = v ? 'AI 연결됨' : '지금은 답하기 어려워요';
  }

  /* ── 보내기 ── */
  function recentFor() {
    return S.messages.filter(function (m) { return m.role === 'user' || m.role === 'assistant'; }).slice(-21, -1)
      .map(function (m) { return { role: m.role, content: maskPII(m.text) }; });
  }
  function showSOS(forId) {
    if (S.messages.some(function (x) { return x.role === 'sos' && x.for === forId; })) return;
    push({ role: 'sos', for: forId });
    if (S.settings.english) setEnglish(false, '마음이 먼저예요. 영어 모드를 잠시 껐어요');
  }
  function send() {
    var input = $('input'), text = input.value.trim();
    if (!text || busy || !S.persona) return;
    if (text.length > 1000) { pushSys('메시지는 1,000자까지 보낼 수 있어요'); return; }
    input.value = ''; autoGrow();
    var m = push({ role: 'user', text: text, read: false });
    var risk = detectRisk(text);
    if (risk !== 'none') showSOS(m.id);
    busy = true; $('sendBtn').disabled = true;
    (online ? Promise.resolve(true) : checkHealth()).then(function (ok) {
      if (!ok) {
        return sleep(700).then(function () {
          pushSys('지금은 서버가 쉬는 중이라 답하기 어려워요.' + (risk !== 'none' ? ' 🆘 연락처는 언제든 눌러 줘.' : ''));
        });
      }
      return chat(m, risk);
    }).then(function () { busy = false; $('sendBtn').disabled = false; maybeSummarize(); });
  }
  function chat(m, localRisk) {
    var body = { persona: S.persona, mode: (S.settings.english && localRisk === 'none') ? 'english' : 'heart',
      settings: { level: S.settings.level, ratio: S.settings.ratio, strength: S.settings.strength },
      summary: S.summary, recent: recentFor(), message: maskPII(m.text) };
    typing(true);
    return fetch(server + '/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      .then(function (res) {
        if (!res.ok) {
          return res.json().catch(function () { return {}; }).then(function (j) {
            typing(false);
            pushSys(res.status === 429 ? (j.message || '오늘은 많이 이야기했어요. 조금 쉬고 다시 만나요.') : (j.message || '지금은 답하기 어려워요.'));
          });
        }
        return readStream(res, m);
      })
      .catch(function () { typing(false); setOnline(false); pushSys('연결이 끊겼어요. 잠시 뒤에 다시 말 걸어 줘.'); });
  }
  function readStream(res, m) {
    var reader = res.body.getReader(), dec = new TextDecoder(), buf = '', gotFirst = false, bubbles = null, err = null;
    function handle(ev, data) {
      if (!gotFirst && (ev === 'token' || ev === 'done')) { gotFirst = true; m.read = true; saveMsgs(); renderAll(); typing(true); }
      if (ev === 'risk' && data.level && data.level !== 'none') showSOS(m.id);
      if (ev === 'correction' && data.items && data.items.length) { m.corrections = data.items.slice(0, 2); saveMsgs(); renderAll(); typing(true); }
      if (ev === 'done') bubbles = data.bubbles || [];
      if (ev === 'error') err = data.message || '지금은 답하기 어려워요.';
    }
    function pump() {
      return reader.read().then(function (r) {
        if (r.done) return;
        buf += dec.decode(r.value, { stream: true });
        var parts = buf.split('\n\n'); buf = parts.pop();
        parts.forEach(function (block) {
          var ev = null, data = {};
          block.split('\n').forEach(function (line) {
            if (line.indexOf('event:') === 0) ev = line.slice(6).trim();
            else if (line.indexOf('data:') === 0) { try { data = JSON.parse(line.slice(5)); } catch (e) {} }
          });
          if (ev) handle(ev, data);
        });
        return pump();
      });
    }
    return pump().then(function () {
      if (err && !bubbles) { typing(false); pushSys(err); return; }
      if (!m.read) { m.read = true; saveMsgs(); renderAll(); }
      typing(false);
      S.sinceSummary++; put('sinceSummary', S.sinceSummary);
      var hasSOS = S.messages.some(function (x) { return x.role === 'sos' && x.for === m.id; });
      return deliver(bubbles || [], 250).then(function () {
        if (!hasSOS && Math.random() < 0.15) { m.heart = true; saveMsgs(); renderAll(); }
      });
    });
  }
  function maybeSummarize() {
    if (!online || S.sinceSummary < 20) return;
    S.sinceSummary = 0; put('sinceSummary', 0);
    var recent = S.messages.filter(function (m) { return m.role === 'user' || m.role === 'assistant'; }).slice(-30)
      .map(function (m) { return { role: m.role, content: maskPII(m.text) }; });
    fetch(server + '/api/summarize', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ persona: S.persona, summary: S.summary, recent: recent }) })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) { if (j && j.summary) { S.summary = j.summary; put('summary', S.summary); } }).catch(function () {});
  }

  /* ── 영어 모드 ── */
  function setEnglish(on, note) {
    S.settings.english = on; saveSettings();
    var b = $('enBtn'); b.setAttribute('aria-pressed', on); b.textContent = on ? '🇬🇧 ' + S.settings.level : '🇬🇧 OFF';
    $('app').classList.toggle('en', on);
    if (note !== false) pushSys(note || (on ? '— 영어 모드 ON · ' + S.settings.level + ' —' : '— 영어 모드 OFF —'));
  }

  /* ── 입력창 ── */
  function autoGrow() { var t = $('input'); t.style.height = 'auto'; t.style.height = Math.min(120, t.scrollHeight) + 'px'; }

  /* ── 시트 ── */
  function openSheet(id) { $(id).hidden = false; }
  document.querySelectorAll('.sheet').forEach(function (s) {
    s.addEventListener('click', function (e) { if (e.target === s || e.target.hasAttribute('data-close')) s.hidden = true; });
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') document.querySelectorAll('.sheet').forEach(function (s) { s.hidden = true; });
  });

  function initChat() {
    $('sendBtn').onclick = send;
    $('input').addEventListener('input', autoGrow);
    $('input').addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey && !e.isComposing && e.keyCode !== 229) { e.preventDefault(); send(); }
    });
    $('enBtn').onclick = function () { setEnglish(!S.settings.english); };
    $('sosBtn').onclick = function () { openSheet('sosSheet'); };
    $('profBtn').onclick = function () { openSheet('profSheet'); };
    $('setBtn').onclick = function () {
      $('sLevel').value = S.settings.level; $('sRatio').value = S.settings.ratio; $('sStrength').value = S.settings.strength;
      openSheet('setSheet');
    };
    $('sLevel').onchange = function () { S.settings.level = this.value; saveSettings(); if (S.settings.english) setEnglish(true, '— 레벨 ' + this.value + '로 바꿨어요 —'); };
    $('sRatio').onchange = function () { S.settings.ratio = this.value; saveSettings(); };
    $('sStrength').onchange = function () { S.settings.strength = this.value; saveSettings(); };
    $('themeBtn').onclick = function () {
      var r = document.documentElement, n = r.getAttribute('data-theme') !== 'light' ? 'light' : 'dark';
      r.setAttribute('data-theme', n); try { localStorage.setItem('hl-theme', n); } catch (e) {}
    };
    $('editPersona').onclick = function () {
      $('setSheet').hidden = true; $('pTitle').textContent = '상대 다시 만들기'; $('pBack').hidden = false; show('persona');
    };
    $('wipe').onclick = function () {
      if (!confirm('이 브라우저의 대화·상대·기억을 모두 지울까요? 되돌릴 수 없어요.')) return;
      wipeAll().then(function () {
        try { localStorage.removeItem('hl-agreed'); } catch (e) {}
        location.reload();
      });
    };
  }

  /* ── 시작 ── */
  function startAfterGate() {
    if (!S.persona) { show('persona'); renderPresets(); return; }
    applyPersona(); show('chat'); renderAll();
    var last = S.messages.filter(function (m) { return m.role === 'assistant' || m.role === 'user'; }).pop();
    if (last && Date.now() - last.ts > 3 * 3600 * 1000) {
      var n = S.persona.nicknameForUser || '너';
      deliver(S.persona.speech === '존댓말' ? [n + ', 다시 오셨네요.', '오늘은 좀 어떠세요?'] : [n + ', 왔구나 😊', '오늘은 좀 어때?'], 600);
    }
  }
  Promise.all([get('agreed'), get('persona'), get('messages'), get('summary'), get('sinceSummary'), get('settings')]).then(function (v) {
    var agreed = v[0]; try { agreed = agreed || localStorage.getItem('hl-agreed') === '1'; } catch (e) {}
    S.persona = v[1] || null; S.messages = v[2] || []; S.summary = v[3] || ''; S.sinceSummary = v[4] || 0;
    if (v[5]) S.settings = Object.assign(S.settings, v[5]);
    if (S.persona) gender = S.persona.gender || 'female';
    initGate(); initPersona(); initChat();
    setEnglish(!!S.settings.english, false);
    if (!agreed) show('gate'); else startAfterGate();
    findServer().then(checkHealth);
    setInterval(checkHealth, 60000);
  });
})();
