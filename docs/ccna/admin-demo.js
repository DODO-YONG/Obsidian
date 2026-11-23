/* TRACER 모의 관리자(admin.html?demo=1) — 브라우저 안의 가짜 DB(생성기).
   실제 Supabase·실제 사용자와 연결되지 않는다. 이름·이메일은 모두 지어낸 것(example.com). 새로고침하면 처음 상태로.
   - 크기: 기본 사용자 500명, 활동은 최근 1년치. 주소에 &n=1000 처럼 주면 바꿀 수 있다(20~1000).
   - 문제는 지어낸 예시 문제(범위 52 × 난이도 3). 실제 문제은행(비공개)과 무관해서 고치거나 숨겨도 실제 서비스엔 영향이 없다.
   - 씨앗(seed)이 고정이라 같은 n이면 매번 같은 데이터가 만들어진다(시험이 흔들리지 않게). &seed=숫자 로 바꿀 수 있다.
   - 시험·확인용으로 window.TracerAdminDemo.db 에 표를 그대로 둔다.
   명령 해석: 화면의 규칙이 먼저 처리하고, 안 되는 말만 /api/demo/ask(제미나이, 하루 100회 제한)로. 연결이 안 되면 '못 함'. */
(function () {
  var qp = new URLSearchParams(location.search);
  var N = Math.max(20, Math.min(1000, parseInt(qp.get('n'), 10) || 500));
  var SPAN = 365;  // 활동 기록 기간(일)
  var SEED = parseInt(qp.get('seed'), 10) || 20261123;
  var DAY = 864e5, now = Date.now();
  // 같은 씨앗 → 같은 난수(mulberry32)
  var s = SEED >>> 0;
  function rnd() { s = (s + 0x6D2B79F5) >>> 0; var t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }
  function pick(a) { return a[Math.floor(rnd() * a.length)]; }
  function between(a, b) { return a + rnd() * (b - a); }
  function int(a, b) { return Math.floor(between(a, b + 1)); }
  function iso(t) { return new Date(t).toISOString(); }
  function clone(x) { return JSON.parse(JSON.stringify(x)); }
  function weighted(pairs) { var r = rnd(), acc = 0; for (var i = 0; i < pairs.length; i++) { acc += pairs[i][1]; if (r < acc) return pairs[i][0]; } return pairs[pairs.length - 1][0]; }

  // ── 범위(시험 범위 52개, topics.json과 같은 번호)
  var SUBS = [['1.1','네트워크 구성 요소'],['1.2','토폴로지 구조'],['1.3','물리 인터페이스와 케이블'],['1.4','인터페이스·케이블 문제'],['1.5','TCP와 UDP'],['1.6','IPv4 주소와 서브넷'],['1.7','사설 IPv4 주소'],['1.8','IPv6 주소와 접두사'],['1.9','IPv6 주소 유형'],['1.10','클라이언트 IP 설정'],['1.11','무선 원리'],['1.12','가상화 기초'],['1.13','스위칭 개념'],
    ['2.1','VLAN'],['2.2','트렁크'],['2.3','CDP·LLDP'],['2.4','EtherChannel'],['2.5','RSTP'],['2.6','무선 아키텍처'],['2.7','WLAN 물리 연결'],['2.8','장비 관리 접속'],['2.9','WLAN GUI 설정'],
    ['3.1','라우팅 테이블'],['3.2','경로 선택'],['3.3','정적 라우팅'],['3.4','OSPFv2'],['3.5','FHRP'],
    ['4.1','NAT'],['4.2','NTP'],['4.3','DHCP와 DNS'],['4.4','SNMP'],['4.5','Syslog'],['4.6','DHCP 릴레이'],['4.7','QoS'],['4.8','SSH 설정'],['4.9','TFTP와 FTP'],
    ['5.1','보안 개념'],['5.2','보안 프로그램'],['5.3','장비 비밀번호'],['5.4','MFA·인증서'],['5.5','IPsec VPN'],['5.6','ACL'],['5.7','L2 보안'],['5.8','AAA'],['5.9','무선 보안'],
    ['6.1','자동화 영향'],['6.2','컨트롤러 기반 네트워크'],['6.3','SDN'],['6.4','AI·머신러닝'],['6.5','REST API'],['6.6','Ansible·Terraform'],['6.7','JSON']];
  var DIFFS = ['easy', 'medium', 'hard'];

  // ── 사용자 N명. 마지막 접속 분포를 넓게(오늘~3년 전·한 번도 안 옴) 퍼뜨려 기간 필터를 시험할 수 있게
  var SUR = '김이박최정강조윤장임한오서신권황안송류전홍고문양손배백허유남심노하곽성차주우구민진나지엄채원천방공현함변염여추도소석선설마길연위표명기반왕금옥육인맹제모탁국어은편용'.split('');
  var GIV = ['민준','서연','도윤','하은','시우','지우','예준','수아','주원','지아','하준','서윤','지호','하린','준서','다은','건우','채원','우진','소율','현우','지민','선우','예린','연우','수빈','유준','윤서','정우','가은','승현','민서','지환','유나','승우','다인','시윤','하율','지훈','은서'];
  var EN = ['Alex','Sam','Jordan','Taylor','Chris','Morgan','Casey','Riley','Jamie','Avery','Priya','Arjun','Rahul','Ananya','Vikram','Neha','Rohan','Kavya','Aditya','Isha','Liam','Noah','Emma','Olivia','Mia','Lucas','Ethan','Sofia','Leo','Zoe'];
  var ENL = ['Kim','Lee','Park','Smith','Patel','Sharma','Singh','Gupta','Nguyen','Brown','Garcia','Khan','Reddy','Iyer','Chen','Wong','Lopez','Moore','Clark','Das'];
  var users = [];
  function addUser(name, role, lastDays, createdDays, status) {
    var i = users.length, id = 'demo-u' + String(i).padStart(4, '0');
    var last = lastDays == null ? null : now - lastDays * DAY;
    users.push({ id: id, name: name, email: 'user' + String(i).padStart(4, '0') + '@example.com', role: role, status: status,
      can_practice: rnd() > 0.04, can_explain: rnd() > 0.12, daily_limit: weighted([[30, 0.8], [10, 0.08], [50, 0.07], [100, 0.05]]),
      note: rnd() < 0.03 ? pick(['스터디 그룹', '문의 메일 보냄', '테스트 계정']) : null,
      last_seen: last == null ? null : iso(last), created_at: iso(now - createdDays * DAY), delete_at: null,
      today_ai: 0, today_actions: 0, total_attempts: 0 });
    return users[i];
  }
  var me = addUser('데모 관리자', 'owner', 0, 700, 'active'); me.email = 'admin@demo.example';
  addUser('한지우', 'admin', 0.1, 400, 'active'); addUser('Priya Sharma', 'admin', 3, 300, 'active');
  var LAST = [[[0, 1], 0.15], [[1, 7], 0.22], [[7, 30], 0.2], [[30, 90], 0.15], [[90, 180], 0.1], [[180, 365], 0.08], [[365, 1100], 0.08], [null, 0.02]];
  while (users.length < N) {
    var band = weighted(LAST), name = rnd() < 0.55 ? pick(SUR) + pick(GIV) : pick(EN) + ' ' + pick(ENL);
    var lastD = band ? between(band[0], band[1]) : null;
    var createdD = lastD == null ? between(5, 900) : lastD + (rnd() < 0.15 ? between(0, 2) : between(2, 600));
    if (lastD != null && lastD < 0.3 && rnd() < 0.2) createdD = lastD + between(0, 0.2);  // 오늘 가입한 사람도 몇 명
    var status = createdD < 4 && rnd() < 0.6 ? 'pending' : rnd() < 0.03 ? 'blocked' : 'active';
    var u = addUser(name, 'user', lastD, createdD, status);
    if (lastD != null && lastD > 365 && rnd() < 0.25) u.delete_at = iso(now - between(1, 20) * DAY);  // 이미 삭제 예정인 사람도 몇 명
  }

  // ── 문제은행: 범위마다 2~4문제(상태·신고·정답률을 섞어서)
  var REASONS = ['정답이 틀린 것 같아요', '정답이 둘이에요', '해설이 문제와 안 맞아요', '보기에 오타', '문제가 애매해요', 'Answer key looks wrong'];
  var qs = [];
  SUBS.forEach(function (sb) { DIFFS.forEach(function (df) {
    for (var k = int(2, 4); k > 0; k--) {
      var i = qs.length, st = weighted([['active', 0.8], ['flagged', 0.12], ['hidden', 0.08]]), graded = int(0, 120), low = rnd() < 0.08;
      var nrep = st === 'flagged' ? int(3, 6) : rnd() < 0.1 ? int(1, 2) : 0;
      qs.push({ id: 'demo-q' + String(i).padStart(4, '0'), sub: sb[0], difficulty: df, qtype: 'mcq',
        question: '[' + sb[0] + ' ' + sb[1] + '] 모의 문제 ' + (i + 1) + ': 다음 중 ' + sb[1] + '에 대한 설명으로 옳은 것은?',
        choices: ['보기 A (모의)', '보기 B (모의)', '보기 C (모의)', '보기 D (모의)'], answer: pick(['A', 'B', 'C', 'D']),
        explanation: '모의 화면용 예시 해설이에요.', option_notes: ['', '', '', ''], key_concept: '', cli_example: '', tip: '', model: 'demo',
        status: st, served: graded + int(0, 30), graded: graded, correct: Math.round(graded * (low ? between(0.05, 0.25) : between(0.45, 0.92))),
        reports: nrep, report_reasons: Array.from({ length: nrep }, function () { return pick(REASONS); }), created_at: iso(now - between(5, 360) * DAY) });
    }
  }); });

  // ── 앱 신고(익명): 최근 1년, 최근 것일수록 미처리가 많게. 일부는 같은 문제에 여러 건, 일부는 웹 문제은행과 같은 문제
  var AR_REASON = ['answer', 'both', 'explanation', 'typo', 'other'], NOTES = [null, null, '정답이 C 같아요', 'B and D both look right', '해설이 다른 문제 내용이에요', 'Typo in choice B', '띄어쓰기', '20 아닌가요?'];
  var APP_ONLY = ['Which DNS record maps a hostname to an IPv6 address?', 'What does DHCP option 150 provide?', 'Which STP port state learns MACs but does not forward?', 'What is the administrative distance of eBGP?', 'Which command shows the OSPF neighbor table?', 'How many bits are in an IPv6 address?'];
  var reports = [], NR = Math.max(12, Math.round(N * 0.5));
  for (var r = 0; r < NR; r++) {
    var dAgo = Math.pow(rnd(), 1.6) * SPAN, linked = rnd() < 0.4, q = linked ? pick(qs) : null;
    var text = q ? q.question : pick(APP_ONLY) + (rnd() < 0.5 ? '' : ' (#' + int(1, 40) + ')');
    var dup = reports.length && rnd() < 0.2 ? pick(reports) : null;  // 같은 문제에 신고가 또
    if (dup) text = dup.question;
    reports.push({ id: r + 1, app_qid: dup ? dup.app_qid : (Math.floor(rnd() * 0xffffffffff)).toString(16).padStart(10, '0'), sub: q ? q.sub : pick(SUBS)[0],
      question: text, reason: pick(AR_REASON), note: pick(NOTES), app_version: pick(['1.0.0', '1.0.1', '1.0.2', '1.1.0']), lang: rnd() < 0.6 ? 'en' : 'ko',
      resolved: rnd() < Math.min(0.95, dAgo / 30), at: iso(now - dAgo * DAY) });
  }

  // ── 활동 기록: 최근 1년. 사람마다 접속 횟수를 다르게, 마지막 접속 시각이 그 사람의 마지막 기록이 되게
  var DEV = ['Mac · Chrome', 'Windows · Chrome', 'Windows · Edge', 'iPhone · Safari', 'Android · Chrome', 'iPad · Safari'];
  var activity = [], aid = 1;
  function act(u, at, action, detail, ai) { activity.push({ id: aid++, action: action, detail: detail || {}, ai: !!ai, device: u._dev, at: iso(at), user_id: u.id }); }
  users.forEach(function (u) {
    u._dev = pick(DEV);
    var created = new Date(u.created_at).getTime();
    if (created > now - SPAN * DAY) act(u, created, 'signup', {});
    if (!u.last_seen) return;
    var last = new Date(u.last_seen).getTime(), start = Math.max(created, now - SPAN * DAY);
    if (last < now - SPAN * DAY) return;
    var heavy = weighted([[1, 0.4], [3, 0.35], [8, 0.2], [20, 0.05]]), sessions = Math.max(1, Math.round(heavy * (last - start) / (21 * DAY)) + 1);
    for (var k = 0; k < sessions; k++) {
      var t = k === sessions - 1 ? last : between(start, last);
      act(u, t, 'visit', {});
      if (u.status !== 'active') continue;
      for (var n = int(0, heavy > 3 ? 8 : 4); n > 0; n--) {
        var sb = pick(SUBS)[0], src = rnd() < 0.75 ? 'bank' : 'new', tt = t + n * 40000;
        act(u, tt, 'question', { sub: sb, difficulty: pick(DIFFS), qtype: 'mcq', source: src }, src === 'new');
        if (rnd() < 0.85) { act(u, tt + 20000, 'grade', { sub: sb, qtype: 'mcq', verdict: rnd() < 0.68 ? '정답' : '오답' }); u.total_attempts++; }
      }
      if (rnd() < 0.15) act(u, t + 600000, 'subnet', { verdict: rnd() < 0.7 ? '정답' : '오답' });
      if (rnd() < 0.06 && u.can_explain) act(u, t + 700000, 'explain', { sub: pick(SUBS)[0] }, true);
      if (rnd() < 0.02) act(u, t + 800000, 'report', { reason: pick(REASONS) });
    }
    u.total_attempts += int(0, 60);
  });
  var today0 = new Date(); today0.setHours(0, 0, 0, 0);
  activity.forEach(function (a) {
    if (new Date(a.at) >= today0) { var u = users.find(function (x) { return x.id === a.user_id; }); u.today_actions++; if (a.ai) u.today_ai++; }
  });
  users.forEach(function (u) { delete u._dev; });
  activity.sort(function (a, b) { return b.at.localeCompare(a.at); });
  function log(detail) { activity.unshift({ id: aid++, action: 'admin', detail: detail, ai: false, device: '모의 화면', at: new Date().toISOString(), user_id: me.id }); }

  // ── 가짜 API(실제 /api 와 같은 모양)
  function err(code, msg) { var e = new Error(msg); e.code = code; throw e; }
  function canTouch(t) { return t.id !== me.id && t.role !== 'owner' && (t.role !== 'admin' || me.role === 'owner'); }
  function dayKey(t) { var d = new Date(t); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); }
  function daily(n) {  // 활동 기록에서 그대로 계산(숫자가 서로 맞게)
    var out = {}, keys = [];
    for (var k = n - 1; k >= 0; k--) { var key = dayKey(today0.getTime() - k * DAY); keys.push(key); out[key] = { day: key, v: {}, visitors: 0, ai_calls: 0, bank_serves: 0, new_questions: 0, answers: 0, signups: 0 }; }
    activity.forEach(function (a) {
      var o = out[dayKey(a.at)]; if (!o) return;
      o.v[a.user_id] = 1; if (a.ai) o.ai_calls++;
      if (a.action === 'question') a.detail.source === 'bank' ? o.bank_serves++ : o.new_questions++;
      if (a.action === 'grade' || a.action === 'subnet') o.answers++;
    });
    users.forEach(function (u) { var o = out[dayKey(u.created_at)]; if (o) o.signups++; });
    return keys.map(function (k) { var o = out[k]; o.visitors = Object.keys(o.v).length; delete o.v; return o; });
  }
  // 기간 합계: [from, to) 사이(고유 접속자·채점·AI·가입·정답률)
  function period(from, to) {
    var v = {}, o = { visitors: 0, answers: 0, ai_calls: 0, signups: 0, correct: 0, graded: 0 };
    activity.forEach(function (a) {
      var t = new Date(a.at).getTime(); if (t < from || t >= to) return;
      v[a.user_id] = 1; if (a.ai) o.ai_calls++;
      if (a.action === 'grade' || a.action === 'subnet') o.answers++;
      if (a.action === 'grade') { o.graded++; if (a.detail.verdict === '정답') o.correct++; }
    });
    users.forEach(function (u) { var t = new Date(u.created_at).getTime(); if (t >= from && t < to) o.signups++; });
    o.visitors = Object.keys(v).length; o.rate = o.graded ? Math.round(o.correct / o.graded * 1000) / 10 : null;
    return o;
  }
  function attach(r) {
    var m = qs.find(function (q) { return q.question === r.question; });
    var same = reports.filter(function (x) { return x.app_qid === r.app_qid && !x.resolved; }).length;
    return Object.assign(clone(r), { bank: m ? { id: m.id, status: m.status, answer: m.answer } : null, open_same: same });
  }
  var GET = {
    'me': function () { return Object.assign(clone(me), { admin: true, admin_ai: true }); },
    'admin/summary': function (p) {
      var n = Math.max(1, Math.min(365, parseInt(p.get('days'), 10) || 14));
      var todayAi = activity.filter(function (a) { return a.ai && new Date(a.at) >= today0; }).length;
      return { days: n, users: users.length, blocked: users.filter(function (u) { return u.status === 'blocked'; }).length,
        pending: users.filter(function (u) { return u.status === 'pending'; }).length, today_ai: todayAi, today_counted: todayAi, global_daily_ai: 400,
        bank_active: qs.filter(function (q) { return q.status === 'active'; }).length, bank_flagged: qs.filter(function (q) { return q.status === 'flagged'; }).length,
        open_reports: qs.reduce(function (a, q) { return a + q.reports; }, 0), open_app_reports: reports.filter(function (r) { return !r.resolved; }).length,
        bank_min: 30, bank_ratio: 0.7, daily: daily(n),
        period: period(now - n * DAY, now), prev: period(now - 2 * n * DAY, now - n * DAY) };
    },
    'admin/sub-stats': function (p) {  // 범위별 정답률(기간 안 채점 기록)
      var n = +p.get('days') || 30, from = now - n * DAY, by = {};
      activity.forEach(function (a) {
        if (a.action !== 'grade' || new Date(a.at).getTime() < from) return;
        var k = a.detail.sub; by[k] = by[k] || { sub: k, graded: 0, correct: 0, users: {} };
        by[k].graded++; if (a.detail.verdict === '정답') by[k].correct++; by[k].users[a.user_id] = 1;
      });
      var names = {}; SUBS.forEach(function (x) { names[x[0]] = x[1]; });
      return { days: n, subs: Object.keys(by).map(function (k) { var o = by[k]; return { sub: k, name: names[k] || '', graded: o.graded, correct: o.correct, users: Object.keys(o.users).length, rate: Math.round(o.correct / o.graded * 1000) / 10 }; })
        .sort(function (a, b) { return a.rate - b.rate; }) };
    },
    'admin/users': function () { return clone(users).sort(function (a, b) { return String(b.last_seen || '').localeCompare(String(a.last_seen || '')); }); },
    'admin/activity': function (p) {
      var since = now - (+p.get('days') || 7) * DAY, lim = Math.min(5000, +p.get('limit') || 300);
      var out = [];
      for (var i = 0; i < activity.length && out.length < lim; i++) {
        var a = activity[i]; if (new Date(a.at) < since) break;
        if ((p.get('user') && a.user_id !== p.get('user')) || (p.get('action') && a.action !== p.get('action'))) continue;
        var u = users.find(function (x) { return x.id === a.user_id; }) || {};
        out.push(Object.assign(clone(a), { profiles: { email: u.email, name: u.name } }));
      }
      return out;
    },
    'admin/questions': function (p) {
      var rows = qs.filter(function (q) { return (!p.get('status') || q.status === p.get('status')) && (!p.get('sub') || q.sub === p.get('sub')); });
      if (p.get('low') === '1') rows = rows.filter(function (q) { return q.graded >= 5; }).sort(function (a, b) { return a.correct / a.graded - b.correct / b.graded; });
      else rows.sort(function (a, b) { return b.reports - a.reports; });
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
      var done = [], skipped = 0, byId = {};
      users.forEach(function (u) { byId[u.id] = u; });
      if (b.op === 'restore') {  // 되돌리기: 작업 전 값으로
        (b.items || []).forEach(function (x) { var t = byId[x.id]; if (t && canTouch(t)) { t.status = x.status; t.delete_at = x.delete_at; done.push(x.id); } });
        log({ bulk: 'restore', n: done.length }); return { ok: true, op: 'restore', updated: done.length, skipped: 0, ids: done };
      }
      (b.ids || []).forEach(function (id) {
        var t = byId[id];
        var bad = !t || !canTouch(t) || (b.op === 'approve' && t.status !== 'pending') || (b.op === 'unblock' && t.status !== 'blocked') || (b.op === 'block' && t.status === 'blocked')
          || (b.op === 'mark_delete' && t.delete_at) || (b.op === 'unmark_delete' && !t.delete_at);
        if (bad) { skipped++; return; }
        if (b.op === 'approve' || b.op === 'unblock') t.status = 'active';
        else if (b.op === 'block') t.status = 'blocked';
        else t.delete_at = b.op === 'mark_delete' ? new Date().toISOString() : null;
        done.push(id);
      });
      log({ bulk: b.op, n: done.length }); return { ok: true, op: b.op, updated: done.length, skipped: skipped, ids: done };
    },
    'admin/questions-bulk': function (b) {
      var done = [], byId = {};
      qs.forEach(function (q) { byId[q.id] = q; });
      if (b.op === 'restore') (b.items || []).forEach(function (x) { var q = byId[x.id]; if (q) { q.status = x.status; q.reports = x.reports; q.report_reasons = x.report_reasons; done.push(x.id); } });
      else (b.ids || []).forEach(function (id) {
        var q = byId[id]; if (!q) return;
        if (b.op === 'hide') q.status = 'hidden'; else if (b.op === 'flag') q.status = 'flagged';
        else if (b.op === 'resolve') { q.status = 'active'; q.reports = 0; q.report_reasons = []; } else return;
        done.push(id);
      });
      log({ bulk: 'questions ' + b.op, n: done.length }); return { ok: true, updated: done.length, ids: done };
    },
    'admin/app-reports-bulk': function (b) {
      var done = [], byId = {};
      reports.forEach(function (r) { byId[r.id] = r; });
      if (b.op === 'restore') (b.items || []).forEach(function (x) { var r = byId[x.id]; if (r) { r.resolved = x.resolved; done.push(x.id); } });
      else (b.ids || []).forEach(function (id) { var r = byId[id]; if (r && r.resolved !== !!b.resolved) { r.resolved = !!b.resolved; done.push(id); } });
      log({ bulk: 'app_reports ' + (b.op || (b.resolved ? 'done' : 'reopen')), n: done.length }); return { ok: true, updated: done.length, ids: done };
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
    'demo/add-users': function (b) {  // 모의 데이터 도구: 가상 사용자 더 만들기(승인 대기 등)
      var st = ['pending', 'active', 'blocked'].indexOf(b.status) >= 0 ? b.status : 'pending', n = Math.max(1, Math.min(50, +b.n || 10)), made = [];
      for (var k = 0; k < n; k++) {
        var nm = (rnd() < 0.55 ? pick(SUR) + pick(GIV) : pick(EN) + ' ' + pick(ENL)), ago = between(0, 0.3);
        var u = addUser(nm, 'user', ago, ago + between(0, 0.05), st); u._dev = pick(DEV);
        act(u, new Date(u.created_at).getTime(), 'signup', {}); delete u._dev; made.push(u.id);
      }
      activity.sort(function (a, b2) { return b2.at.localeCompare(a.at); });
      log({ bulk: 'demo add ' + st, n: n }); return { ok: true, added: n, status: st, ids: made };
    },
    'admin/ask': function (b) {  // 규칙으로 안 된 말만 여기로 온다 → 실제 제미나이(모의 화면용, 하루 100회 제한)
      return fetch('/api/demo/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ prompt: b.prompt }) })
        .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { if (!r.ok) throw new Error(j.error || 'AI 연결 실패'); return j; }); })
        .catch(function (e) { return { command: 'none', kind: 'none', args: {}, source: 'ai', error: true, reply: 'AI로 해석하지 못했어요(' + e.message + ').' }; });
    }
  };
  window.TracerAdminDemo = {
    size: N, seed: SEED,
    db: { users: users, questions: qs, app_reports: reports, activity: activity },  // 시험·확인용(실제 DB 아님)
    api: function (path, body) {
      var u = new URL(path, location.href), route = u.pathname.replace(/^\/api\//, '');
      return new Promise(function (res) { setTimeout(res, 80); }).then(function () {
        var f = body ? POST[route] : GET[route];
        if (!f) err(404, '없는 주소');
        return body ? f(body) : f(u.searchParams);
      });
    }
  };
})();
