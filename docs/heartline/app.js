/* Heartline 앱 — 나만의 가상 연인(여러 명), 메신저 대화방, 브라우저 저장(IndexedDB), 답변 서버 연결 */
(function () {
  'use strict';
  var $ = function (id) { return document.getElementById(id); };
  var MAX_LOVERS = 5;

  /* ── 기본 안전: 서버 safety.py 와 같은 목록. 고치면 두 곳을 같이 ── */
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
    return db().then(function (d) { if (d) try { d.transaction('kv', 'readwrite').objectStore('kv').put(v, k); } catch (e) {} });
  }
  function del(k) {
    delete mem[k];
    return db().then(function (d) { if (d) try { d.transaction('kv', 'readwrite').objectStore('kv').delete(k); } catch (e) {} });
  }
  function wipeAll() {
    mem = {};
    return db().then(function (d) {
      if (!d) return;
      return new Promise(function (res) { var t = d.transaction('kv', 'readwrite'); t.objectStore('kv').clear(); t.oncomplete = res; t.onerror = res; });
    });
  }

  /* ── 상태 ── */
  var S = { lovers: [], activeId: null, chats: {}, settings: { english: false, level: 'B1', ratio: 'english', strength: 'light' } };
  var server = null, online = false, busy = false;
  function uid() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 6); }
  function active() { return S.lovers.find(function (l) { return l.id === S.activeId; }) || null; }
  function chatOf(id) { return S.chats[id] || (S.chats[id] = { messages: [], summary: '', since: 0 }); }
  function saveLovers() { put('lovers', S.lovers); put('activeId', S.activeId); }
  function saveChat(id) { var c = chatOf(id); c.messages = c.messages.slice(-400); put('chat:' + id, c); }
  function saveSettings() { put('settings', S.settings); }

  /* ── 페르소나 재료 ── */
  var AVATARS = ['🌷', '🌻', '🌙', '🦊', '🐰', '🐻', '☁️', '🌿'];
  var COLORS = { rose: ['#FFB4C2', '#FF8A7A'], peach: ['#FFD3A8', '#FF9F7A'], lav: ['#CBB8FF', '#9D8CF0'],
    mint: ['#A8E8D4', '#4CB8A0'], sky: ['#A9D6FF', '#6C9CF0'], sand: ['#EAD7B7', '#C79B6A'] };
  var KEYWORDS = ['다정', '츤데레', '장난꾸러기', '어른스러움', '수줍음', '시크', '낙천적', '다혈질'];
  var STAGES = { some: '썸', lover: '연인', longterm: '오래된 연인' };
  var PRESETS = [
    { key: 'warm', title: '다정한 연상', desc: '포근하게 들어 주고 천천히 물어봐 줘요', avatar: '🌷', color: 'rose', names: { female: '하린', male: '도윤' },
      ageGroup: '30s', speech: '반말', emojiLevel: '조금', nicknameForUser: '자기야', keywords: ['다정', '어른스러움'],
      traits: { warmth: 90, playful: 35, calm: 75, direct: 30 }, relationshipStage: 'lover', statusMessage: '오늘도 네 편이야 💗', job: '동네 꽃집 사장', likes: '비 오는 날 산책' },
    { key: 'play', title: '장난꾸러기 동갑', desc: '웃게 해 주고 하루 얘기를 다 듣고 싶어 해요', avatar: '🌻', color: 'peach', names: { female: '유나', male: '민재' },
      ageGroup: '20s', speech: '반말', emojiLevel: '많이', nicknameForUser: '자기', keywords: ['장난꾸러기', '낙천적'],
      traits: { warmth: 75, playful: 90, calm: 30, direct: 55 }, relationshipStage: 'lover', statusMessage: '오늘 뭐 했어? 다 말해 줘 😆', job: '게임 회사 디자이너', likes: '떡볶이, 노래방' },
    { key: 'calm', title: '차분한 지적인 타입', desc: '조용히 곁에서 같이 생각해 줘요', avatar: '🌙', color: 'lav', names: { female: '서연', male: '지훈' },
      ageGroup: '30s', speech: '존댓말', emojiLevel: '없음', nicknameForUser: '당신', keywords: ['어른스러움', '다정'],
      traits: { warmth: 70, playful: 25, calm: 90, direct: 60 }, relationshipStage: 'lover', statusMessage: '천천히, 같이 생각해 봐요', job: '도서관 사서', likes: '따뜻한 차, 책' },
    { key: 'tsun', title: '츤데레', desc: '퉁명스러운 척, 누구보다 챙겨 줘요', avatar: '🦊', color: 'peach', names: { female: '지아', male: '준호' },
      ageGroup: '20s', speech: '반말', emojiLevel: '없음', nicknameForUser: '너', keywords: ['츤데레', '시크'], catchphrase: '~거든?',
      traits: { warmth: 70, playful: 40, calm: 50, direct: 80 }, relationshipStage: 'lover', statusMessage: '딱히 기다린 건 아니거든?', job: '카페 바리스타', dislikes: '빈말' },
    { key: 'shy', title: '수줍은 연하', desc: '부끄러움이 많지만 마음은 솔직해요', avatar: '🐰', color: 'rose', names: { female: '소은', male: '시우' },
      ageGroup: '20s', speech: '반말', emojiLevel: '조금', nicknameForUser: '자기', keywords: ['수줍음', '다정'],
      traits: { warmth: 85, playful: 30, calm: 60, direct: 25 }, relationshipStage: 'some', statusMessage: '오늘도 연락해 줄 거지…?', job: '대학원생' },
    { key: 'steady', title: '듬직한 어른', desc: '든든하게 기대게 해 주는 사람', avatar: '🐻', color: 'sand', names: { female: '은재', male: '강현' },
      ageGroup: '40s', speech: '반말', emojiLevel: '조금', nicknameForUser: '자기', keywords: ['어른스러움', '다정'],
      traits: { warmth: 85, playful: 30, calm: 85, direct: 60 }, relationshipStage: 'longterm', statusMessage: '힘들면 기대도 돼', job: '건축가' }
  ];
  function today() { var d = new Date(); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); }
  function avaStyle(p) { var c = COLORS[p && p.color] || COLORS.rose; return 'background:linear-gradient(135deg,' + c[0] + ',' + c[1] + ')'; }
  function setAva(el, p) { el.textContent = (p && p.avatar) || '🌷'; el.setAttribute('style', avaStyle(p)); }
  function dday(s) { if (!s) return 0; var a = new Date(s + 'T00:00:00'), b = new Date(today() + 'T00:00:00'); return Math.max(1, Math.round((b - a) / 86400000) + 1); }
  function stageLabel(p) { var d = dday(p.relationshipStart); return (p.relationshipStage === 'some' ? '💗 썸' : '💞') + (d ? ' D+' + d : ''); }
  function stripEmoji(t) { return t.replace(/[\p{Extended_Pictographic}‍️]/gu, '').replace(/\s{2,}/g, ' ').trim(); }
  function has(p, k) { return (p.keywords || []).indexOf(k) > -1; }
  function greeting(p) {
    var n = p.nicknameForUser || '너', b;
    if (p.speech === '존댓말') b = [n + ', 오셨네요 🙂', '오늘 하루는 어떠셨어요? 편하게 이야기해 주세요.'];
    else if (has(p, '츤데레')) b = ['왔어? …딱히 기다린 건 아니고.', '오늘 뭐 했는지 말해 봐. 궁금해서 그런 거 아니거든?'];
    else if (has(p, '장난꾸러기')) b = [n + '!! 왔다 😆', '오늘 뭐 했어? 하나도 빼지 말고 다 말해 줘'];
    else if (has(p, '수줍음')) b = ['아, ' + n + '… 왔구나 ☺️', '오늘 하루 어땠어? 듣고 싶어서…'];
    else if (has(p, '어른스러움')) b = [n + ', 왔어? 오늘도 수고 많았어.', '무슨 일 있었는지 천천히 얘기해 줘.'];
    else if (has(p, '시크')) b = ['왔네.', '오늘 어땠어.'];
    else b = [n + ', 왔구나 😊', '오늘 하루 어땠어? 나한테는 편하게 말해도 돼.'];
    if (p.relationshipStage === 'some' && p.speech !== '존댓말') b[0] = b[0].replace('왔구나', '연락 와서 좋다');
    if (p.relationshipStage === 'longterm' && p.speech !== '존댓말' && !has(p, '츤데레')) b.push('오늘도 같이 있어서 좋다 💞');
    if (p.catchphrase && !/^~/.test(p.catchphrase)) b.push(p.catchphrase);
    if (p.emojiLevel === '없음') b = b.map(stripEmoji);
    if (p.emojiLevel === '많이') b[b.length - 1] += ' 💕✨';
    return b;
  }

  /* ── 화면 전환 ── */
  function show(id) { ['gate', 'list', 'editor', 'chat'].forEach(function (s) { $(s).hidden = s !== id; }); }

  /* ── 입장 ── */
  function initGate() {
    var a = $('ageOk'), p = $('privOk'), go = $('gateGo');
    a.onchange = p.onchange = function () { go.disabled = !(a.checked && p.checked); };
    go.onclick = function () { try { localStorage.setItem('hl-agreed', '1'); } catch (e) {} put('agreed', true); openList(); };
  }

  /* ── 대화 목록 ── */
  function hhmm(ts) { var d = new Date(ts); return String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0'); }
  function when(ts) {
    if (!ts) return ''; var d = new Date(ts), t = new Date();
    if (d.toDateString() === t.toDateString()) return hhmm(ts);
    var y = new Date(); y.setDate(t.getDate() - 1);
    if (d.toDateString() === y.toDateString()) return '어제';
    return (d.getMonth() + 1) + '/' + d.getDate();
  }
  function esc(t) { return String(t == null ? '' : t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function openList() {
    show('list');
    var ul = $('lovers');
    if (!S.lovers.length) {
      ul.innerHTML = '<li class="empty"><b>💌</b>아직 연인이 없어요.<br>내 취향대로 첫 번째 연인을 만들어 볼까요?</li>';
    } else {
      var sorted = S.lovers.slice().sort(function (a, b) { return lastTs(b) - lastTs(a); });
      ul.innerHTML = sorted.map(function (p) {
        var last = lastMsg(p.id);
        return '<li class="lover" data-id="' + p.id + '" tabindex="0"><span class="ava" style="' + avaStyle(p) + '">' + esc(p.avatar) + '</span>' +
          '<div class="li"><b>' + esc(p.name) + '</b><span class="stage">' + stageLabel(p) + '</span><small>' + esc(last ? last.text : p.statusMessage || '') + '</small></div>' +
          '<time>' + when(last && last.ts) + '</time></li>';
      }).join('');
    }
    $('lCount').textContent = S.lovers.length ? S.lovers.length + '/' + MAX_LOVERS : '';
    var full = S.lovers.length >= MAX_LOVERS;
    $('newLover').disabled = full; $('maxNote').hidden = !full;
  }
  function lastMsg(id) { var m = chatOf(id).messages.filter(function (x) { return x.role === 'user' || x.role === 'assistant'; }); return m[m.length - 1]; }
  function lastTs(p) { var m = lastMsg(p.id); return m ? m.ts : (p.createdAt || 0); }
  function initList() {
    $('lovers').addEventListener('click', function (e) { var li = e.target.closest('.lover'); if (li) openChat(li.dataset.id); });
    $('lovers').addEventListener('keydown', function (e) { var li = e.target.closest('.lover'); if (li && e.key === 'Enter') openChat(li.dataset.id); });
    $('newLover').onclick = function () { openEditor(null); };
    $('listSet').onclick = openSettings;
  }

  /* ── 페르소나 편집기 ── */
  var draft = null, editingId = null, gender = 'female';
  function blank() {
    return { name: '', gender: gender, ageGroup: '30s', avatar: '🌷', color: 'rose', traits: { warmth: 70, playful: 50, calm: 60, direct: 40 },
      keywords: [], speech: '반말', emojiLevel: '조금', nicknameForUser: '', catchphrase: '', relationshipStage: 'lover',
      relationshipStart: today(), job: '', interests: '', likes: '', dislikes: '', statusMessage: '' };
  }
  function fromPreset(pr) {
    var d = blank();
    Object.keys(pr).forEach(function (k) { if (['key', 'title', 'desc', 'names'].indexOf(k) < 0) d[k] = JSON.parse(JSON.stringify(pr[k])); });
    d.name = pr.names[gender]; d.gender = gender; d.preset = pr.key; d.relationshipStart = today();
    return d;
  }
  function renderPresets() {
    $('presets').innerHTML = PRESETS.map(function (p, i) {
      return '<button type="button" class="preset' + (draft && draft.preset === p.key ? ' on' : '') + '" data-i="' + i + '"><span class="ava" style="' + avaStyle(p) + '">' + p.avatar +
        '</span><b>' + p.names[gender] + ' · ' + p.title + '</b><small>' + p.desc + '</small></button>';
    }).join('');
  }
  function renderPickers() {
    $('avatarPick').innerHTML = AVATARS.map(function (a) { return '<button type="button" role="radio" aria-checked="' + (draft.avatar === a) + '" data-a="' + a + '" style="' + avaStyle({ color: draft.color }) + '">' + a + '</button>'; }).join('');
    $('colorPick').innerHTML = Object.keys(COLORS).map(function (c) { return '<button type="button" role="radio" aria-label="' + c + '" aria-checked="' + (draft.color === c) + '" data-c="' + c + '" style="' + avaStyle({ color: c }) + '"></button>'; }).join('');
    $('kwPick').innerHTML = KEYWORDS.map(function (k) { return '<button type="button" aria-pressed="' + (draft.keywords.indexOf(k) > -1) + '" data-k="' + k + '">' + k + '</button>'; }).join('');
    document.querySelectorAll('#stagePick button').forEach(function (b) { b.setAttribute('aria-pressed', b.dataset.v === draft.relationshipStage); });
  }
  function fillForm() {
    var f = $('pForm');
    ['name', 'ageGroup', 'gender', 'speech', 'emojiLevel', 'nicknameForUser', 'catchphrase', 'relationshipStart', 'job', 'interests', 'likes', 'dislikes', 'statusMessage']
      .forEach(function (k) { if (f[k]) f[k].value = draft[k] || ''; });
    ['warmth', 'playful', 'calm', 'direct'].forEach(function (k) { f[k].value = draft.traits[k]; });
    renderPickers(); updatePreview();
  }
  function readForm() {
    var f = $('pForm');
    ['name', 'ageGroup', 'gender', 'speech', 'emojiLevel', 'nicknameForUser', 'catchphrase', 'relationshipStart', 'job', 'interests', 'likes', 'dislikes', 'statusMessage']
      .forEach(function (k) { if (f[k]) draft[k] = f[k].value.trim(); });
    ['warmth', 'playful', 'calm', 'direct'].forEach(function (k) { draft.traits[k] = +f[k].value; });
  }
  function updatePreview() {
    var p = draft;
    setAva($('pvAva'), p);
    $('pvName').textContent = p.name || '이름 없음';
    $('pvMeta').textContent = [STAGES[p.relationshipStage], (p.keywords || []).join(' · ')].filter(Boolean).join(' · ');
    $('pvBubbles').innerHTML = greeting(p).map(function (t) { return '<div class="b">' + esc(t) + '</div>'; }).join('');
  }
  function openEditor(id) {
    editingId = id;
    var p = id ? S.lovers.find(function (l) { return l.id === id; }) : null;
    gender = p ? (p.gender || 'female') : gender;
    draft = p ? JSON.parse(JSON.stringify(p)) : fromPreset(PRESETS[0]);
    draft.keywords = draft.keywords || []; draft.traits = draft.traits || blank().traits;
    $('eTitle').textContent = p ? p.name + ' 프로필 고치기' : '새 연인 만들기';
    $('presetBox').hidden = !!p;
    $('eSave').textContent = p ? '저장하기' : '이 사람과 대화하기';
    $('eDelete').hidden = !p;
    document.querySelectorAll('#presetBox .seg button').forEach(function (x) { x.setAttribute('aria-pressed', x.dataset.g === gender); });
    renderPresets(); fillForm(); show('editor');
    $('editor').querySelector('.ebody').scrollTop = 0;
  }
  function initEditor() {
    document.querySelectorAll('#presetBox .seg button').forEach(function (b) {
      b.onclick = function () {
        gender = b.dataset.g;
        document.querySelectorAll('#presetBox .seg button').forEach(function (x) { x.setAttribute('aria-pressed', x === b); });
        var pr = PRESETS.find(function (x) { return x.key === draft.preset; });
        if (pr) { draft = fromPreset(pr); fillForm(); } else { draft.gender = gender; $('pForm').gender.value = gender; updatePreview(); }
        renderPresets();
      };
    });
    $('presets').onclick = function (e) {
      var b = e.target.closest('.preset'); if (!b) return;
      draft = fromPreset(PRESETS[+b.dataset.i]); fillForm(); renderPresets();
    };
    $('avatarPick').onclick = function (e) { var b = e.target.closest('button'); if (!b) return; draft.avatar = b.dataset.a; renderPickers(); updatePreview(); };
    $('colorPick').onclick = function (e) { var b = e.target.closest('button'); if (!b) return; draft.color = b.dataset.c; renderPickers(); updatePreview(); };
    $('kwPick').onclick = function (e) {
      var b = e.target.closest('button'); if (!b) return;
      var k = b.dataset.k, i = draft.keywords.indexOf(k);
      if (i > -1) draft.keywords.splice(i, 1); else if (draft.keywords.length < 3) draft.keywords.push(k);
      draft.preset = null; renderPickers(); updatePreview(); renderPresets();
    };
    $('stagePick').onclick = function (e) { var b = e.target.closest('button'); if (!b) return; draft.relationshipStage = b.dataset.v; renderPickers(); updatePreview(); };
    $('pForm').addEventListener('input', function () { readForm(); updatePreview(); });
    $('pForm').addEventListener('change', function () { readForm(); updatePreview(); });
    $('pForm').onsubmit = function (e) {
      e.preventDefault(); readForm();
      if (!draft.name) { $('pForm').name.focus(); return; }
      if (editingId) {
        var i = S.lovers.findIndex(function (l) { return l.id === editingId; });
        S.lovers[i] = Object.assign({}, draft, { id: editingId });
        saveLovers(); pushSys(editingId, '— 프로필을 바꿨어요. 다음 답장부터 새 모습으로 이야기해요 —');
        openChat(editingId);
      } else {
        if (S.lovers.length >= MAX_LOVERS) return openList();
        var p = Object.assign({}, draft, { id: uid(), createdAt: Date.now() });
        S.lovers.push(p); saveLovers();
        openChat(p.id, true);
      }
    };
    $('eDelete').onclick = function () {
      var p = S.lovers.find(function (l) { return l.id === editingId; }); if (!p) return;
      if (!confirm(p.name + '와(과)의 대화와 기억을 모두 지울까요? 되돌릴 수 없어요.')) return;
      S.lovers = S.lovers.filter(function (l) { return l.id !== editingId; });
      delete S.chats[editingId]; del('chat:' + editingId);
      if (S.activeId === editingId) S.activeId = null;
      saveLovers(); openList();
    };
    $('eBack').onclick = function () { if (editingId) openChat(editingId); else openList(); };
  }

  /* ── 대화방 ── */
  var msgs = $('msgs');
  function dayLabel(ts) { var d = new Date(ts); return d.getFullYear() + '년 ' + (d.getMonth() + 1) + '월 ' + d.getDate() + '일'; }
  function sosHTML() {
    return '<div class="sos-card"><b>🧡 혼자 견디지 않아도 돼요</b>' +
      '<a href="tel:109">📞 109 · 자살예방상담전화 (24시간)</a><a href="tel:15770199">📞 1577-0199 · 정신건강위기상담</a>' +
      '<a href="tel:112">🚨 지금 위험하면 112 · 119</a></div>';
  }
  function node(m, prev, p) {
    var out = '';
    if (!prev || dayLabel(prev.ts) !== dayLabel(m.ts)) out += '<div class="day">' + dayLabel(m.ts) + '</div>';
    if (m.role === 'sys') return out + '<div class="sys">' + esc(m.text) + '</div>';
    if (m.role === 'sos') return out + sosHTML();
    var me = m.role === 'user', cont = prev && prev.role === m.role && (m.ts - prev.ts) < 120000 && !me;
    var meta = '<div class="meta">' + (me && !m.read ? '<span class="read">1</span>' : '') + '<span>' + hhmm(m.ts) + '</span></div>';
    out += '<div class="row ' + (me ? 'me' : 'you') + (cont ? ' cont' : '') + '" data-id="' + m.id + '">' +
      (me ? '' : '<span class="ava sm" aria-hidden="true" style="' + avaStyle(p) + '">' + esc(p.avatar) + '</span>') +
      '<div class="b">' + esc(m.text) + (m.heart ? '<span class="heart">💗</span>' : '') + '</div>' + meta + '</div>';
    (m.corrections || []).forEach(function (c) {
      out += '<div class="fix">✏️ 더 자연스럽게<br><b>' + esc(c.corrected) + '</b>' + (c.reason ? '<br><span class="why">· ' + esc(c.reason) + '</span>' : '') + '</div>';
    });
    return out;
  }
  function renderChat() {
    var p = active(); if (!p) return;
    var list = chatOf(p.id).messages, h = '';
    list.forEach(function (m, i) { h += node(m, list[i - 1], p); });
    msgs.innerHTML = h; if (typingEl) msgs.appendChild(typingEl); scrollEnd();
  }
  function scrollEnd() { requestAnimationFrame(function () { msgs.scrollTop = msgs.scrollHeight; }); }
  function push(id, m) {
    m.id = m.id || uid(); m.ts = m.ts || Date.now();
    chatOf(id).messages.push(m); saveChat(id);
    if (id === S.activeId && !$('chat').hidden) renderChat();
    return m;
  }
  function pushSys(id, t) { return push(id, { role: 'sys', text: t }); }
  var typingEl = null;
  function typing(on) {
    var p = active();
    if (on && !typingEl && p) {
      typingEl = document.createElement('div'); typingEl.className = 'row you typing';
      typingEl.innerHTML = '<span class="ava sm" style="' + avaStyle(p) + '">' + esc(p.avatar) + '</span><div class="b"><i></i><i></i><i></i></div>';
      msgs.appendChild(typingEl); scrollEnd();
    } else if (!on && typingEl) { typingEl.remove(); typingEl = null; }
  }
  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
  function deliver(id, bubbles, firstDelay) {
    return bubbles.reduce(function (pr, text, i) {
      return pr.then(function () {
        if (id === S.activeId) typing(true);
        return sleep(i === 0 ? (firstDelay || 300) : Math.min(1500, 450 + text.length * 22));
      }).then(function () { typing(false); push(id, { role: 'assistant', text: text }); });
    }, Promise.resolve());
  }
  function applyHeader(p) {
    $('pName').textContent = p.name; $('profBtn').setAttribute('style', avaStyle(p)); $('avaEmoji').textContent = p.avatar;
    $('pStatus').textContent = p.statusMessage || '';
    var d = dday(p.relationshipStart); $('dday').textContent = stageLabel(p);
    $('profName').textContent = p.name; setAva($('profAva'), p);
    $('profStatus').textContent = p.statusMessage || '';
    $('profD').textContent = (STAGES[p.relationshipStage] || '연인') + (d ? ' · 💞 D+' + d : '');
    $('profKw').innerHTML = (p.keywords || []).map(function (k) { return '<span>' + esc(k) + '</span>'; }).join('');
    $('profStory').textContent = [p.job, p.likes && '좋아하는 것: ' + p.likes, p.catchphrase && '말버릇: ' + p.catchphrase].filter(Boolean).join(' · ');
  }
  function openChat(id, isNew) {
    var p = S.lovers.find(function (l) { return l.id === id; }); if (!p) return openList();
    S.activeId = id; saveLovers(); typing(false);
    applyHeader(p); show('chat'); renderChat();
    var c = chatOf(id);
    if (isNew || !c.messages.length) return deliver(id, greeting(p), 450);
    var last = c.messages.filter(function (m) { return m.role === 'assistant' || m.role === 'user'; }).pop();
    if (last && Date.now() - last.ts > 3 * 3600 * 1000) {
      var n = p.nicknameForUser || '너';
      deliver(id, p.speech === '존댓말' ? [n + ', 다시 오셨네요.', '오늘은 좀 어떠세요?'] : [has(p, '츤데레') ? '…왔네. 늦었잖아.' : n + ', 왔구나 😊', '오늘은 좀 어때?'], 600);
    }
  }
  msgs.addEventListener('dblclick', function (e) {
    var row = e.target.closest('.row.you'); if (!row || !S.activeId) return;
    var m = chatOf(S.activeId).messages.find(function (x) { return x.id === row.dataset.id; }); if (!m) return;
    m.heart = !m.heart; saveChat(S.activeId); renderChat();
  });

  /* ── 서버 연결 ── */
  function findServer() {
    var h = location.hash.match(/server=([^&]+)/);
    if (h) { server = decodeURIComponent(h[1]).replace(/\/$/, ''); return Promise.resolve(server); }
    // 서버가 이 화면을 직접 보여 주는 경우(압축 파일·로컬 실행): 같은 주소에 서버가 있다
    return fetch('/api/health', { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; })
      .then(function (j) {
        if (j && j.ok) { server = ''; return server; }
        return fetchBoard();
      });
  }
  function fetchBoard() {
    return fetch('server.json?t=' + Date.now(), { cache: 'no-store' }).then(function (r) { return r.json(); })
      .then(function (j) { server = j && j.url ? j.url.replace(/\/$/, '') : null; }).catch(function () { server = null; })
      .then(function () { if (server === null && /^(localhost|127\.0\.0\.1)$/.test(location.hostname)) server = 'http://127.0.0.1:8766'; return server; });
  }
  function checkHealth() {
    if (server === null) { setOnline(false); return Promise.resolve(false); }
    return fetch(server + '/api/health', { cache: 'no-store' }).then(function (r) { return r.json(); })
      .then(function (j) { setOnline(!!(j && j.ok && j.ai)); $('demoNote').hidden = !(j && j.demo); return online; }).catch(function () { setOnline(false); return false; });
  }
  function setOnline(v) { online = v; $('aiDot').classList.toggle('on', v); $('aiDot').title = v ? 'AI 연결됨' : '지금은 답하기 어려워요'; }

  /* ── 보내기 ── */
  function recentFor(id) {
    return chatOf(id).messages.filter(function (m) { return m.role === 'user' || m.role === 'assistant'; }).slice(-21, -1)
      .map(function (m) { return { role: m.role, content: maskPII(m.text) }; });
  }
  function personaCard(p) {
    var c = {}; ['name', 'gender', 'ageGroup', 'nicknameForUser', 'speech', 'emojiLevel', 'traits', 'keywords', 'catchphrase', 'relationshipStage',
      'relationshipStart', 'job', 'interests', 'likes', 'dislikes'].forEach(function (k) { if (p[k] != null && p[k] !== '') c[k] = p[k]; });
    return c;
  }
  function showSOS(id, forId) {
    if (chatOf(id).messages.some(function (x) { return x.role === 'sos' && x.for === forId; })) return;
    push(id, { role: 'sos', for: forId });
    if (S.settings.english) setEnglish(false, '마음이 먼저예요. 영어 모드를 잠시 껐어요');
  }
  function send() {
    var input = $('input'), text = input.value.trim(), p = active();
    if (!text || busy || !p) return;
    if (text.length > 1000) { pushSys(p.id, '메시지는 1,000자까지 보낼 수 있어요'); return; }
    input.value = ''; autoGrow();
    var id = p.id, m = push(id, { role: 'user', text: text, read: false }), risk = detectRisk(text);
    if (risk !== 'none') showSOS(id, m.id);
    busy = true; $('sendBtn').disabled = true;
    (online ? Promise.resolve(true) : checkHealth()).then(function (ok) {
      if (!ok) return sleep(700).then(function () { pushSys(id, '지금은 서버가 쉬는 중이라 답하기 어려워요.'); });
      return chat(p, m, risk);
    }).then(function () { busy = false; $('sendBtn').disabled = false; maybeSummarize(p); });
  }
  function chat(p, m, localRisk) {
    var id = p.id, c = chatOf(id);
    var body = { persona: personaCard(p), mode: (S.settings.english && localRisk === 'none') ? 'english' : 'heart',
      settings: { level: S.settings.level, ratio: S.settings.ratio, strength: S.settings.strength },
      summary: c.summary, recent: recentFor(id), message: maskPII(m.text) };
    typing(true);
    return fetch(server + '/api/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
      .then(function (res) {
        if (!res.ok) return res.json().catch(function () { return {}; }).then(function (j) {
          typing(false); pushSys(id, res.status === 429 ? (j.message || '오늘은 많이 이야기했어요. 조금 쉬고 다시 만나요.') : (j.message || '지금은 답하기 어려워요.'));
        });
        return readStream(res, id, m);
      })
      .catch(function () { typing(false); setOnline(false); pushSys(id, '연결이 끊겼어요. 잠시 뒤에 다시 말 걸어 줘.'); });
  }
  function readStream(res, id, m) {
    var reader = res.body.getReader(), dec = new TextDecoder(), buf = '', gotFirst = false, bubbles = null, err = null;
    function handle(ev, data) {
      if (!gotFirst && (ev === 'token' || ev === 'done')) { gotFirst = true; m.read = true; saveChat(id); if (id === S.activeId) renderChat(); }
      if (ev === 'risk' && data.level && data.level !== 'none') showSOS(id, m.id);
      if (ev === 'correction' && data.items && data.items.length) { m.corrections = data.items.slice(0, 2); saveChat(id); if (id === S.activeId) renderChat(); }
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
      typing(false);
      if (err && !bubbles) { pushSys(id, err); return; }
      if (!m.read) { m.read = true; saveChat(id); }
      var c = chatOf(id); c.since++; saveChat(id);
      var hasSOS = c.messages.some(function (x) { return x.role === 'sos' && x.for === m.id; });
      return deliver(id, bubbles || [], 250).then(function () {
        if (!hasSOS && Math.random() < 0.15) { m.heart = true; saveChat(id); if (id === S.activeId) renderChat(); }
      });
    });
  }
  function maybeSummarize(p) {
    var c = chatOf(p.id);
    if (!online || c.since < 20) return;
    c.since = 0; saveChat(p.id);
    var recent = c.messages.filter(function (m) { return m.role === 'user' || m.role === 'assistant'; }).slice(-30)
      .map(function (m) { return { role: m.role, content: maskPII(m.text) }; });
    fetch(server + '/api/summarize', { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ persona: personaCard(p), summary: c.summary, recent: recent }) })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) { if (j && j.summary) { c.summary = j.summary; saveChat(p.id); } }).catch(function () {});
  }

  /* ── 영어 모드 ── */
  function setEnglish(on, note) {
    S.settings.english = on; saveSettings();
    var b = $('enBtn'); b.setAttribute('aria-pressed', on); b.textContent = on ? '🇬🇧 ' + S.settings.level : '🇬🇧 OFF';
    $('app').classList.toggle('en', on);
    if (note !== false && S.activeId) pushSys(S.activeId, note || (on ? '— 영어 모드 ON · ' + S.settings.level + ' —' : '— 영어 모드 OFF —'));
  }

  /* ── 시트 ── */
  function autoGrow() { var t = $('input'); t.style.height = 'auto'; t.style.height = Math.min(120, t.scrollHeight) + 'px'; }
  function openSheet(id) { $(id).hidden = false; }
  function openSettings() { $('sLevel').value = S.settings.level; $('sRatio').value = S.settings.ratio; $('sStrength').value = S.settings.strength; openSheet('setSheet'); }
  document.querySelectorAll('.sheet').forEach(function (s) {
    s.addEventListener('click', function (e) { if (e.target === s || e.target.hasAttribute('data-close')) s.hidden = true; });
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') document.querySelectorAll('.sheet').forEach(function (s) { s.hidden = true; }); });

  function initChat() {
    $('sendBtn').onclick = send;
    $('input').addEventListener('input', autoGrow);
    $('input').addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey && !e.isComposing && e.keyCode !== 229) { e.preventDefault(); send(); }
    });
    $('cBack').onclick = function () { typing(false); openList(); };
    $('enBtn').onclick = function () { setEnglish(!S.settings.english); };
    $('sosBtn').onclick = function () { openSheet('sosSheet'); };
    $('profBtn').onclick = function () { openSheet('profSheet'); };
    $('profEdit').onclick = function () { $('profSheet').hidden = true; openEditor(S.activeId); };
    $('setBtn').onclick = openSettings;
    $('sLevel').onchange = function () { S.settings.level = this.value; saveSettings(); if (S.settings.english) setEnglish(true, '— 레벨 ' + this.value + '로 바꿨어요 —'); };
    $('sRatio').onchange = function () { S.settings.ratio = this.value; saveSettings(); };
    $('sStrength').onchange = function () { S.settings.strength = this.value; saveSettings(); };
    $('themeBtn').onclick = function () {
      var r = document.documentElement, n = r.getAttribute('data-theme') !== 'light' ? 'light' : 'dark';
      r.setAttribute('data-theme', n); try { localStorage.setItem('hl-theme', n); } catch (e) {}
    };
    $('wipe').onclick = function () {
      if (!confirm('이 브라우저의 연인·대화·기억을 모두 지울까요? 되돌릴 수 없어요.')) return;
      wipeAll().then(function () { try { localStorage.removeItem('hl-agreed'); } catch (e) {} location.reload(); });
    };
  }

  /* ── 시작 (이전 버전의 한 명짜리 데이터는 목록으로 옮김) ── */
  Promise.all([get('agreed'), get('lovers'), get('activeId'), get('settings'), get('persona'), get('messages'), get('summary')]).then(function (v) {
    var agreed = v[0]; try { agreed = agreed || localStorage.getItem('hl-agreed') === '1'; } catch (e) {}
    S.lovers = v[1] || []; S.activeId = v[2] || null;
    if (v[3]) S.settings = Object.assign(S.settings, v[3]);
    if (!S.lovers.length && v[4]) {
      var old = Object.assign({ id: uid(), createdAt: Date.now(), color: 'rose', keywords: [], relationshipStage: 'lover' }, v[4]);
      S.lovers = [old]; S.chats[old.id] = { messages: v[5] || [], summary: v[6] || '', since: 0 };
      saveLovers(); saveChat(old.id); del('persona'); del('messages'); del('summary');
    }
    return Promise.all(S.lovers.map(function (l) { return get('chat:' + l.id).then(function (c) { if (c) S.chats[l.id] = c; }); })).then(function () { return agreed; });
  }).then(function (agreed) {
    initGate(); initList(); initEditor(); initChat();
    setEnglish(!!S.settings.english, false);
    if (!agreed) show('gate'); else openList();
    findServer().then(checkHealth);
    setInterval(checkHealth, 60000);
  });
})();
