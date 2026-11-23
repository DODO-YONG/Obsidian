/* TRACER 모의 관리자(admin.html?demo=1) — 브라우저 안의 가짜 DB.
   실제 Supabase·실제 사용자와 연결되지 않는다. 사람 이름·이메일은 모두 지어낸 것(example.com). 새로고침하면 처음 상태로.
   명령 해석: 화면의 규칙이 먼저 처리하고, 안 되는 말만 /api/demo/ask(제미나이, 하루 30회 제한)로. 연결이 안 되면 '못 함'. */
(function () {
  var DAY = 864e5, now = Date.now();
  var ago = function (d) { return d == null ? null : new Date(now - d * DAY).toISOString(); };
  var seed = 7; function rnd() { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; }
  function pick(a) { return a[Math.floor(rnd() * a.length)]; }
  function clone(x) { return JSON.parse(JSON.stringify(x)); }

  // ── 사용자: [이름, 마지막 접속(며칠 전), 가입(며칠 전), 상태, 역할]
  var U = [
    ['데모 관리자', 0, 600, 'active', 'owner'], ['한지우', 0.05, 40, 'active', 'admin'], ['Alex Park', 0.2, 90, 'active', 'user'],
    ['서윤아', 1, 120, 'active', 'user'], ['Mina Choi', 2, 30, 'active', 'user'], ['이도현', 4, 210, 'active', 'user'],
    ['정하람', 9, 15, 'active', 'user'], ['Jordan Lee', 20, 70, 'active', 'user'], ['오세린', 45, 300, 'active', 'user'],
    ['Sam Kim', 100, 160, 'blocked', 'user'], ['윤태오', 190, 400, 'active', 'user'], ['Chris Han', 260, 380, 'active', 'user'],
    ['배수아', 380, 520, 'active', 'user'], ['Taylor Moon', 410, 430, 'active', 'user'], ['문가온', 700, 760, 'active', 'user'],
    ['권예린', null, 450, 'active', 'user'], ['신규 가입자 A', 0.5, 0.5, 'pending', 'user'], ['신규 가입자 B', 1.5, 1.5, 'pending', 'user']
  ];
  var users = U.map(function (u, i) {
    return { id: 'demo-u' + String(i).padStart(2, '0'), name: u[0], email: 'user' + String(i).padStart(2, '0') + '@example.com',
      role: u[4], status: u[3], can_practice: true, can_explain: i % 5 !== 3, daily_limit: 30, note: null,
      last_seen: ago(u[1]), created_at: ago(u[2]), delete_at: null, today_ai: u[1] != null && u[1] < 1 ? Math.floor(rnd() * 8) : 0,
      today_actions: 0, total_attempts: Math.floor(rnd() * 400) };
  });
  users[0].email = 'admin@demo.example';
  var me = users[0];

  // ── 문제은행(설명용 예시 몇 개만)
  var Q = [
    ['1.1', 'Which device forwards frames based on MAC addresses?', ['Hub', 'Switch', 'Router', 'Repeater'], 'B', 'flagged', 3, ['정답이 C 같아요', '해설이 부족해요', '보기가 애매함']],
    ['1.6', 'How many usable hosts are in a /27 subnet?', ['14', '30', '32', '62'], 'B', 'active', 0, []],
    ['2.1', 'Which command assigns access VLAN 10 to an interface?', ['vlan 10', 'switchport access vlan 10', 'switchport trunk vlan 10', 'access vlan 10'], 'B', 'active', 1, ['오타 있음']],
    ['3.4', 'What is the default OSPF hello interval on a broadcast link?', ['5 s', '10 s', '30 s', '40 s'], 'B', 'flagged', 2, ['정답이 둘', '정답이 D']],
    ['4.1', 'Which NAT type maps many inside hosts to one public address?', ['Static NAT', 'Dynamic NAT', 'PAT', 'NAT64'], 'C', 'active', 0, []],
    ['5.3', 'Which protocol provides encrypted remote CLI access?', ['Telnet', 'SSH', 'HTTP', 'TFTP'], 'B', 'hidden', 0, []],
    ['6.2', 'In SDN, which plane makes forwarding decisions centrally?', ['Data plane', 'Control plane', 'Management plane', 'Physical plane'], 'B', 'active', 0, []]
  ];
  var qs = Q.map(function (q, i) {
    var g = 10 + Math.floor(rnd() * 60), c = i === 0 || i === 3 ? Math.floor(g * 0.2) : Math.floor(g * (0.55 + rnd() * 0.35));
    return { id: 'demo-q' + i, sub: q[0], difficulty: pick(['easy', 'medium', 'hard']), qtype: 'mcq', question: q[1], choices: q[2], answer: q[3],
      explanation: '모의 화면용 예시 해설이에요.', option_notes: ['', '', '', ''], key_concept: '', cli_example: '', tip: '', model: 'demo',
      status: q[4], served: g + 5, graded: g, correct: c, reports: q[5], report_reasons: q[6], created_at: ago(30 + i) };
  });

  // ── 앱 신고(익명): [며칠 전, 문제, 이유, 메모, 처리됨, 앱 문제 ID]
  var AR = [
    [0.3, Q[0][1], 'answer', '정답이 C 같아요', false, 'a1b2c3'], [1.2, Q[0][1], 'explanation', null, false, 'a1b2c3'],
    [3, 'Which DNS record maps a hostname to an IPv6 address?', 'typo', 'Typo in choice B', false, 'f00d01'],
    [5, Q[3][1], 'both', 'B and D both look right', false, 'c0ffee'], [9, 'What does DHCP option 150 provide?', 'other', null, false, 'beef02'],
    [16, 'Which STP port state learns MACs but does not forward?', 'answer', null, true, 'dada03'],
    [40, Q[1][1], 'typo', '띄어쓰기', true, 'aa0404'], [75, 'What is the AD of eBGP?', 'answer', '20 아닌가요', true, 'bb0505']
  ];
  var reports = AR.map(function (r, i) {
    return { id: i + 1, app_qid: r[5], sub: '', question: r[1], reason: r[2], note: r[3], app_version: '1.0.' + (i % 3), lang: i % 2 ? 'en' : 'ko', resolved: r[4], at: ago(r[0]) };
  });

  // ── 활동 기록
  var ACTIONS = ['visit', 'question', 'grade', 'grade', 'question', 'subnet', 'explain', 'report', 'signup'];
  var activity = [];
  for (var i = 0; i < 160; i++) {
    var act = pick(ACTIONS), u = pick(users.filter(function (x) { return x.last_seen && (now - new Date(x.last_seen)) / DAY < 60; })), at = now - rnd() * 60 * DAY;
    var d = act === 'question' ? { sub: pick(['1.1', '2.1', '3.4', '4.1']), difficulty: 'medium', qtype: 'mcq', source: rnd() < 0.7 ? 'bank' : 'new' }
      : act === 'grade' ? { sub: '1.6', qtype: 'mcq', verdict: pick(['정답', '오답']) } : act === 'report' ? { reason: '정답이 이상해요' } : act === 'explain' ? { sub: '3.4' } : act === 'subnet' ? { verdict: '정답' } : {};
    activity.push({ id: i + 1, action: act, detail: d, ai: act === 'question' && d.source === 'new' || act === 'explain', device: pick(['Mac · Chrome', 'iPhone · Safari', 'Android · Chrome', 'Windows · Edge']), at: new Date(at).toISOString(), user_id: u.id });
  }
  function log(detail) { activity.push({ id: activity.length + 1, action: 'admin', detail: detail, ai: false, device: '모의 화면', at: new Date().toISOString(), user_id: me.id }); }

  // ── 가짜 API(실제 /api 와 같은 모양)
  function err(code, msg) { var e = new Error(msg); e.code = code; throw e; }
  function canTouch(t) { return t.id !== me.id && t.role !== 'owner' && (t.role !== 'admin' || me.role === 'owner'); }
  function daily(n) {
    var out = [];
    for (var k = n - 1; k >= 0; k--) {
      var day = new Date(now - k * DAY), s = Math.floor(day / DAY);
      var v = 3 + (s * 7) % 9, b = 6 + (s * 5) % 14;
      out.push({ day: day.toISOString().slice(0, 10), visitors: v, ai_calls: 4 + (s * 3) % 11, bank_serves: b, new_questions: 2 + (s * 11) % 6, answers: b + 5 + (s % 7) });
    }
    return out;
  }
  function attach(r) {
    var m = qs.find(function (q) { return q.question === r.question; });
    var same = reports.filter(function (x) { return x.app_qid === r.app_qid && !x.resolved; }).length;
    return Object.assign(clone(r), { bank: m ? { id: m.id, status: m.status, answer: m.answer } : null, open_same: same });
  }
  var GET = {
    'me': function () { return Object.assign(clone(me), { admin: true }); },
    'admin/summary': function (p) {
      var n = [7, 14, 30, 90].indexOf(+p.get('days')) >= 0 ? +p.get('days') : 14;
      return { days: n, users: users.length, blocked: users.filter(function (u) { return u.status === 'blocked'; }).length,
        pending: users.filter(function (u) { return u.status === 'pending'; }).length, today_ai: 17, today_counted: 14, global_daily_ai: 400,
        bank_active: qs.filter(function (q) { return q.status === 'active'; }).length, bank_flagged: qs.filter(function (q) { return q.status === 'flagged'; }).length,
        open_reports: qs.reduce(function (a, q) { return a + q.reports; }, 0), open_app_reports: reports.filter(function (r) { return !r.resolved; }).length,
        bank_min: 30, bank_ratio: 0.7, daily: daily(n) };
    },
    'admin/users': function () { return clone(users).sort(function (a, b) { return String(b.last_seen || '').localeCompare(String(a.last_seen || '')); }); },
    'admin/activity': function (p) {
      var since = now - (+p.get('days') || 7) * DAY;
      return activity.filter(function (a) { return new Date(a.at) >= since && (!p.get('user') || a.user_id === p.get('user')) && (!p.get('action') || a.action === p.get('action')); })
        .sort(function (a, b) { return b.at.localeCompare(a.at); }).slice(0, 500)
        .map(function (a) { var u = users.find(function (x) { return x.id === a.user_id; }) || {}; return Object.assign(clone(a), { profiles: { email: u.email, name: u.name } }); });
    },
    'admin/questions': function (p) {
      var rows = qs.filter(function (q) { return (!p.get('status') || q.status === p.get('status')) && (!p.get('sub') || q.sub === p.get('sub')); });
      if (p.get('low') === '1') rows = rows.filter(function (q) { return q.graded >= 5; }).sort(function (a, b) { return a.correct / a.graded - b.correct / b.graded; });
      var bk = {}; qs.forEach(function (q) { var k = q.sub + '|' + q.difficulty; bk[k] = bk[k] || { sub: q.sub, difficulty: q.difficulty, qtype: 'mcq', active: 0, flagged: 0, hidden: 0 }; bk[k][q.status]++; });
      return { questions: clone(rows), buckets: Object.keys(bk).sort().map(function (k) { return bk[k]; }), bank_min: 30 };
    },
    'admin/app-reports': function (p) {
      var days = +p.get('days') || 0;
      var rows = reports.filter(function (r) { return (p.get('open') === '0' || !r.resolved) && (!days || (now - new Date(r.at)) / DAY <= days); })
        .sort(function (a, b) { return b.at.localeCompare(a.at); });
      return { reports: rows.map(attach), open: reports.filter(function (r) { return !r.resolved; }).length };
    }
  };
  var POST = {
    'admin/user': function (b) {
      var t = users.find(function (u) { return u.id === b.id; }); if (!t) err(404, '사용자를 찾을 수 없어요.');
      if (!canTouch(t)) err(403, '이 계정은 바꿀 수 없어요.');
      ['role', 'status', 'can_practice', 'can_explain', 'daily_limit', 'note'].forEach(function (k) { if (k in b) t[k] = b[k]; });
      log({ email: t.email, set: b }); return clone(t);
    },
    'admin/users-bulk': function (b) {
      var done = [], skipped = 0;
      (b.ids || []).forEach(function (id) {
        var t = users.find(function (u) { return u.id === id; });
        if (!t || !canTouch(t) || (b.op === 'approve' && t.status !== 'pending')) { skipped++; return; }
        if (b.op === 'approve') t.status = 'active'; else t.delete_at = b.op === 'mark_delete' ? new Date().toISOString() : null;
        done.push(id);
      });
      log({ bulk: b.op, n: done.length }); return { ok: true, op: b.op, updated: done.length, skipped: skipped, ids: done };
    },
    'admin/question': function (b) {
      var q = qs.find(function (x) { return x.id === b.id; }); if (!q) err(404, '문제를 찾을 수 없어요.');
      ['status', 'question', 'choices', 'answer', 'explanation', 'option_notes'].forEach(function (k) { if (k in b) q[k] = b[k]; });
      if (b.resolve) { q.reports = 0; q.report_reasons = []; if (!b.status) q.status = 'active'; }
      log({ qid: q.id, set: Object.keys(b).filter(function (k) { return k !== 'id'; }) }); return clone(q);
    },
    'admin/app-report': function (b) {
      var r = reports.find(function (x) { return x.id === b.id; }); if (!r) err(404, '신고를 찾을 수 없어요.');
      var list = b.all_same ? reports.filter(function (x) { return x.app_qid === r.app_qid; }) : [r];
      list.forEach(function (x) { x.resolved = b.resolved !== false; });
      log({ app_report: b.id, resolved: b.resolved !== false, n: list.length }); return { ok: true, updated: list.length };
    },
    'admin/ask': function (b) {  // 규칙으로 안 된 말만 여기로 온다 → 실제 제미나이(모의 화면용, 하루 횟수 제한)
      return fetch('/api/demo/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt: b.prompt }) })
        .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { if (!r.ok) throw new Error(j.error || 'AI 연결 실패'); return j; }); })
        .catch(function (e) { return { command: 'none', kind: 'none', args: {}, source: 'ai', reply: 'AI로 해석하지 못했어요(' + e.message + '). 예시처럼 기간과 대상을 넣어 말하면 규칙으로 바로 알아들어요.' }; });
    }
  };
  window.TracerAdminDemo = {
    api: function (path, body) {
      var u = new URL(path, location.href), route = u.pathname.replace(/^\/api\//, '');
      return new Promise(function (res) { setTimeout(res, 120); }).then(function () {
        var f = body ? POST[route] : GET[route];
        if (!f) err(404, '없는 주소');
        return body ? f(body) : f(u.searchParams);
      });
    }
  };
})();
