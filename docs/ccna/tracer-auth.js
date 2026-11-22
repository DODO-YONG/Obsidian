/* TRACER 공용 로그인 부품 — 선택 화면(index)·소개(about)·이용(app) 페이지가 함께 쓴다.
   - <div data-auth data-auth-next="app.html"></div> 자리에 로그인 버튼 / (내 이름 + 로그아웃) 을 그린다.
   - Supabase 공개 값은 /api/config 에서 받는다(저장소에 키 없음).
   - 예전 GitHub Pages 주소로 오면 server.json 의 home(새 주소)으로 같은 페이지를 연다.
   - 다른 스크립트: TracerAuth.ready.then(client => …), TracerAuth.onChange(session => …), TracerAuth.token() */
(function () {
  var S = { client: null, session: null, cbs: [], ready: false };
  var G = '<svg class="g" viewBox="0 0 48 48" aria-hidden="true"><path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z"/><path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/><path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z"/><path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z"/></svg>';
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function nameOf(u) { var m = (u && u.user_metadata) || {}; return m.full_name || m.name || (u && u.email) || ''; }

  function render() {
    document.querySelectorAll('[data-auth]').forEach(function (el) {
      if (!S.ready) { el.innerHTML = '<span class="auth-wait">로그인 확인 중…</span>'; return; }
      if (!S.client) { el.innerHTML = '<span class="auth-wait">로그인 준비 중</span>'; return; }
      var u = S.session && S.session.user;
      if (!u) {
        el.innerHTML = '<button type="button" class="auth-login" data-auth-act="in">' + G + '<span class="long">Google로 로그인</span><span class="short">로그인</span></button>';
      } else {
        var n = nameOf(u);
        el.innerHTML = '<span class="auth-user" title="' + esc(u.email) + ' 로 로그인됨"><i aria-hidden="true">' + esc(n.trim().charAt(0).toUpperCase() || '?') + '</i>' +
          '<span class="auth-txt"><small>로그인됨</small><b>' + esc(n) + '</b></span></span>' +
          '<button type="button" class="auth-out" data-auth-act="out">로그아웃</button>';
      }
    });
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-auth-act]'); if (!b) return;
    var box = b.closest('[data-auth]');
    if (b.getAttribute('data-auth-act') === 'in') login(box && box.getAttribute('data-auth-next'));
    else logout();
  });

  function login(next) {
    if (!S.client) return;
    var url = new URL(next || location.pathname, location.href);
    S.client.auth.signInWithOAuth({ provider: 'google', options: { redirectTo: url.origin + url.pathname } });
  }
  function logout() {
    if (!S.client) return Promise.resolve();
    return S.client.auth.signOut().then(function () { S.session = null; emit(); });
  }
  function emit() { render(); S.cbs.forEach(function (f) { try { f(S.session); } catch (e) {} }); }

  var ready = (function () {
    // 예전 주소 → 새 주소의 같은 페이지. 단 소개(about.html)는 GitHub Pages가 공식 주소라 제외
    // (about.html은 반대로 Vercel → GitHub Pages로 넘기므로, 빼지 않으면 서로 무한히 넘김)
    if (/github\.io$/.test(location.hostname) && !/\/about\.html$/.test(location.pathname)) {
      return fetch('server.json?t=' + Date.now(), { cache: 'no-store' }).then(function (r) { return r.json(); }).then(function (j) {
        if (j && j.home) location.replace(j.home.replace(/\/+$/, '') + location.pathname.replace(/^\/Obsidian/, '') + location.search + location.hash);
        return null;
      }).catch(function () { return null; });
    }
    return fetch('/api/config').then(function (r) { return r.json(); }).then(function (c) {
      if (!c.supabase_url || !c.anon_key || !window.supabase) throw new Error('not ready');
      S.client = window.supabase.createClient(c.supabase_url, c.anon_key, { auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true, flowType: 'pkce' } });
      S.client.auth.onAuthStateChange(function (ev, session) {
        var had = !!(S.session && S.session.user), has = !!(session && session.user);
        S.session = session;
        if (had !== has && S.ready) setTimeout(emit, 0);
      });
      return S.client.auth.getSession().then(function (r) {
        S.session = r.data.session;
        if (/[?&]code=/.test(location.search)) history.replaceState(null, '', location.pathname + location.hash);
        return S.client;
      });
    }).catch(function () { return null; });
  })().then(function (c) { S.ready = true; emit(); return c; });

  render();
  window.TracerAuth = {
    ready: ready,
    onChange: function (fn) { S.cbs.push(fn); },
    session: function () { return S.session; },
    token: function () {
      if (!S.client) return Promise.resolve('');
      return S.client.auth.getSession().then(function (r) { return (r.data.session && r.data.session.access_token) || ''; }).catch(function () { return ''; });
    },
    login: login, logout: logout
  };
})();
