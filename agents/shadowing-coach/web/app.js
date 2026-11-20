import { decode16k, analyze, contour, similarity, draw } from './pitch.js';

const $ = s => document.querySelector(s);
const SR = 16000;
const api = (p, opt) => fetch(p, opt).then(async r => {
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.error || r.statusText);
  return j;
});
const fmt = t => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')}`;
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const grade = v => v == null ? '' : v >= 80 ? 'good' : v >= 55 ? 'mid' : 'low';

// ── 상태 ──────────────────────────────────────────
let video = null, sents = [], recSum = {}, cur = 0;
let origSamples = null, origReady = null;
const refCache = new Map();
let mine = null;            // { idx, url, contour, name }
let player = null, ytOk = true;
let segEnd = null;          // 구간 재생 끝 시각
let onSegDone = null;
const origAudio = new Audio();
const mineAudio = new Audio();
let stream = null, recorder = null, chunks = [], recT0 = 0, wantRec = false, recTimer = null;

const ytApi = new Promise(res => {
  if (window.YT && window.YT.Player) return res();
  const prev = window.onYouTubeIframeAPIReady;
  window.onYouTubeIframeAPIReady = () => { prev && prev(); res(); };
});

function status(msg, live = false) {
  const el = $('#status');
  el.innerHTML = msg;
  el.classList.toggle('live', live);
}

// ── 화면 전환 ──────────────────────────────────────
window.addEventListener('hashchange', route);
route();

function route() {
  const m = location.hash.match(/^#\/v\/([\w-]+)/);
  if (m) openVideo(m[1]); else showLibrary();
}

async function showLibrary() {
  stopAll();
  $('#library').hidden = false; $('#practice').hidden = true;
  $('#to-library').hidden = true; $('#video-title').textContent = '';
  const st = await api('/api/status').catch(() => null);
  if (st) {
    const miss = Object.entries(st.tools).filter(([, v]) => !v).map(([k]) => k);
    $('#tools').hidden = !miss.length;
    $('#tools').textContent = miss.length ? `⚠️ 준비 안 된 도구: ${miss.join(', ')} — 'SHADOW 실행.command'로 다시 켜 보세요.` : '';
  }
  const vids = await api('/api/videos').catch(() => []);
  $('#videos').innerHTML = vids.length ? vids.map(v => `
    <a class="video" href="#/v/${esc(v.id)}">
      <img src="https://i.ytimg.com/vi/${esc(v.id)}/mqdefault.jpg" alt="" loading="lazy">
      <div class="info"><div class="t">${esc(v.title)}</div>
      <div class="s">${esc(v.channel || '')} · ${fmt(v.duration || 0)} · ${v.sentences}문장</div></div>
    </a>`).join('') : '<p class="muted">아직 가져온 영상이 없어요. 위에 유튜브 주소를 넣어 보세요.</p>';
}

$('#import-form').addEventListener('submit', async e => {
  e.preventDefault();
  const job = $('#job');
  job.hidden = false; job.classList.remove('err'); job.textContent = '시작하는 중…';
  try {
    const { job: id } = await api('/api/videos', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url: $('#url').value }) });
    const t0 = Date.now();
    for (;;) {
      await new Promise(r => setTimeout(r, 1000));
      const j = await api('/api/jobs/' + id);
      job.textContent = `⏳ ${j.stage} · ${Math.round((Date.now() - t0) / 1000)}초`;
      if (j.done) {
        if (j.error) throw new Error(j.error);
        job.textContent = '✅ ' + j.stage;
        $('#url').value = '';
        location.hash = '#/v/' + j.vid;
        return;
      }
    }
  } catch (err) {
    job.classList.add('err'); job.textContent = '❌ ' + err.message;
  }
});

// ── 연습 화면 ──────────────────────────────────────
async function openVideo(id) {
  stopAll();
  let data;
  try { data = await api('/api/videos/' + id); } catch { location.hash = ''; return; }
  video = data.meta; sents = data.sentences; recSum = data.recs || {};
  refCache.clear(); mine = null;
  $('#library').hidden = true; $('#practice').hidden = false; $('#to-library').hidden = false;
  $('#video-title').textContent = video.title;
  renderList();
  origAudio.src = `/media/${id}/audio.mp3`;
  origSamples = null;
  origReady = fetch(`/media/${id}/audio.mp3`).then(r => r.arrayBuffer()).then(decode16k).then(s => (origSamples = s));
  setupPlayer(id);
  select(0, false);
}

async function setupPlayer(id) {
  ytOk = true;
  applyMode();
  await ytApi;
  if (player) { player.cueVideoById(id); return; }
  player = new YT.Player('yt', {
    videoId: id,
    playerVars: { playsinline: 1, rel: 0, modestbranding: 1, origin: location.origin },
    events: {
      onError: () => {
        ytOk = false; $('#mode-audio').checked = true; applyMode();
        status('이 영상은 다른 사이트에서 재생이 막혀 있어요. <b>원본 소리</b>로 재생할게요.');
      },
    },
  });
}

function useAudio() { return $('#mode-audio').checked || !ytOk; }
function applyMode() { $('#audio-only').hidden = !useAudio(); }
$('#mode-audio').addEventListener('change', () => { stopAll(); applyMode(); });

function renderList() {
  const done = Object.keys(recSum).length;
  $('#progress').textContent = `${done}/${sents.length} 연습함`;
  $('#sent-list').innerHTML = sents.map((s, i) => {
    const r = recSum[i];
    const b = r ? `<span class="badge ${grade(r.last)}" title="최근 발음 · 녹음 ${r.count}번">${r.last}%·${r.count}</span>` : '';
    return `<li data-i="${i}"><span class="n">${i + 1}</span><span class="tx">${esc(s.text)}</span>${b}</li>`;
  }).join('');
  markList();
}

function markList() {
  document.querySelectorAll('#sent-list li').forEach(li => li.classList.toggle('cur', +li.dataset.i === cur));
  const el = document.querySelector(`#sent-list li[data-i="${cur}"]`);
  el && el.scrollIntoView({ block: 'nearest' });
}

$('#sent-list').addEventListener('click', e => {
  const li = e.target.closest('li');
  if (li) select(+li.dataset.i, true);
});

function renderSentence(diff) {
  const s = sents[cur];
  $('#sent-pos').textContent = `문장 ${cur + 1} / ${sents.length} · ${fmt(s.start)}–${fmt(s.end)}`;
  if (diff) {
    const refOnly = diff.filter(d => !d.extra);
    $('#sent-text').innerHTML = refOnly.map(d => `<span class="w ${d.ok ? 'ok' : 'miss'}" data-w="${esc(d.w)}">${esc(d.w)}</span>`).join(' ');
  } else {
    $('#sent-text').innerHTML = s.words.map(w => `<span class="w" data-w="${esc(w.w)}">${esc(w.w)}</span>`).join(' ');
  }
}

async function select(i, play) {
  if (i < 0 || i >= sents.length) return;
  const changed = i !== cur || !mine || mine.idx !== i;
  cur = i;
  markList();
  if (changed) {
    mine = null;
    $('#b-mine').disabled = $('#b-cmp').disabled = true;
    $('#pitch-score').innerHTML = ''; $('#word-score').innerHTML = ''; $('#heard').innerHTML = '';
    renderSentence(null);
    $('#word-card').hidden = true;
    drawPitch();
    loadHistory(i, true);
  }
  if (play) playOrig();
}

// 원본 구간의 억양 곡선 (캐시)
async function refContour(i) {
  if (refCache.has(i)) return refCache.get(i);
  await origReady;
  const s = sents[i];
  const from = Math.max(0, s.start - 0.05), to = s.end + 0.15;
  const c = contour(analyze(origSamples.subarray(Math.floor(from * SR), Math.floor(to * SR))));
  const v = { c, from };
  refCache.set(i, v);
  return v;
}

async function drawPitch() {
  const i = cur;
  const ref = await refContour(i).catch(() => null);
  if (i !== cur || !ref) return;
  draw($('#pitch'), ref.c, mine && mine.idx === i ? mine.contour : null, sents[i].words, ref.from);
}
window.addEventListener('resize', () => !$('#practice').hidden && drawPitch());

// ── 재생 ──────────────────────────────────────────
function stopAll() {
  segEnd = null; onSegDone = null;
  origAudio.pause(); mineAudio.pause();
  try { player && player.pauseVideo && player.pauseVideo(); } catch { /* 준비 전 */ }
}

function ytPlaying() {
  try { return player && player.getPlayerState && player.getPlayerState() === YT.PlayerState.PLAYING; } catch { return false; }
}

function playSegment(s, done) {
  stopAll();
  onSegDone = done;
  if (useAudio() || !player || !player.seekTo) {
    origAudio.currentTime = Math.max(0, s.start - 0.1);
    segEnd = s.end + 0.25;
    origAudio.play();
  } else {
    player.seekTo(Math.max(0, s.start - 0.1), true);
    player.playVideo();
    segEnd = s.end + 0.25;
  }
}

function playOrig() {
  const s = sents[cur];
  status('🔊 원본 재생 중…');
  playSegment(s, () => status('이제 <kbd>Space</kbd>를 누르고 있는 동안 따라 말하세요. 떼면 바로 들려줘요.'));
}

function playMine() {
  if (!mine) return;
  stopAll();
  mineAudio.src = mine.url;
  mineAudio.play();
  status('🔁 내 녹음 재생 중…');
  mineAudio.onended = () => status('<kbd>C</kbd>로 원본과 이어서 비교하거나, <kbd>Space</kbd>로 다시 녹음하세요.');
}

function compare() {
  if (!mine) return;
  const s = sents[cur];
  stopAll();
  status('⇄ 원본 → 내 녹음');
  // 비교는 항상 원본 소리로 (정확한 구간 + 바로 이어서)
  origAudio.currentTime = Math.max(0, s.start - 0.1);
  segEnd = s.end + 0.25;
  onSegDone = () => setTimeout(() => { mineAudio.src = mine.url; mineAudio.play(); mineAudio.onended = () => status('비교 끝.'); }, 250);
  origAudio.play();
}

// 재생 위치 감시: 구간 끝에서 멈추고, 영상을 그냥 볼 때는 지금 문장을 따라간다
function tick() {
  let t = null, source = null;
  if (!origAudio.paused) { t = origAudio.currentTime; source = 'a'; }
  else if (ytPlaying()) { t = player.getCurrentTime(); source = 'y'; }
  if (t != null) {
    if (segEnd != null && t >= segEnd) {
      source === 'a' ? origAudio.pause() : player.pauseVideo();
      segEnd = null;
      const f = onSegDone; onSegDone = null; f && f();
    } else if (segEnd == null && source === 'y') {
      const i = sentenceAt(t);
      if (i !== cur) select(i, false);
    }
  }
  requestAnimationFrame(tick);
}
requestAnimationFrame(tick);

function sentenceAt(t) {
  let k = 0;
  for (let i = 0; i < sents.length; i++) if (sents[i].start - 0.2 <= t) k = i;
  return k;
}

// ── 녹음 ──────────────────────────────────────────
async function ensureMic() {
  if (stream) return true;
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false } });
    return true;
  } catch {
    status('🎤 마이크를 쓸 수 없어요. 브라우저 주소창의 마이크 권한을 허용해 주세요.');
    return false;
  }
}
// 이미 허용돼 있으면 미리 켜 둬서 누르자마자 녹음되게
navigator.permissions?.query({ name: 'microphone' }).then(p => { if (p.state === 'granted') ensureMic(); }).catch(() => {});

async function startRec() {
  if (recorder || wantRec || $('#practice').hidden) return;
  wantRec = true;
  if (ytPlaying() && segEnd == null) select(sentenceAt(player.getCurrentTime()), false);
  stopAll();
  const had = !!stream;
  if (!(await ensureMic())) { wantRec = false; return; }
  if (!had) { wantRec = false; status('🎤 마이크 준비 완료! 이제 <kbd>Space</kbd>를 누르고 있는 동안 말하세요.'); return; }
  if (!wantRec) return; // 그새 손을 뗌
  const type = ['audio/webm;codecs=opus', 'audio/mp4', 'audio/webm'].find(t => MediaRecorder.isTypeSupported(t)) || '';
  recorder = new MediaRecorder(stream, type ? { mimeType: type } : undefined);
  chunks = [];
  recorder.ondataavailable = e => e.data.size && chunks.push(e.data);
  const idx = cur;
  recorder.onstop = () => finishRec(new Blob(chunks, { type: recorder.mimeType }), idx, (performance.now() - recT0) / 1000);
  recorder.start();
  recT0 = performance.now();
  $('#b-rec').classList.add('on');
  recTimer = setInterval(() => status(`● 녹음 중 ${((performance.now() - recT0) / 1000).toFixed(1)}초 — 떼면 바로 재생`, true), 100);
}

function stopRec() {
  wantRec = false;
  if (!recorder) return;
  clearInterval(recTimer);
  $('#b-rec').classList.remove('on');
  // 마지막 음절이 잘리지 않게 살짝 더 받고 멈춘다
  const r = recorder;
  setTimeout(() => { r.stop(); }, 150);
}

async function finishRec(blob, idx, secs) {
  recorder = null;
  if (secs < 0.4) { status('너무 짧아요. <kbd>Space</kbd>를 누른 채로 말해 주세요.'); return; }
  const url = URL.createObjectURL(blob);
  mineAudio.src = url;
  mineAudio.play();                      // 떼자마자 바로 재생
  mineAudio.onended = () => status('<kbd>C</kbd> 원본과 비교 · <kbd>P</kbd> 다시 듣기 · <kbd>Space</kbd> 다시 녹음');
  status('🔁 내 녹음 재생 중… (분석은 동시에 진행)');
  mine = { idx, url, contour: null, name: null };
  $('#b-mine').disabled = $('#b-cmp').disabled = false;

  // 억양: 브라우저에서 바로
  const pitchP = (async () => {
    const c = contour(analyze(await decode16k(await blob.arrayBuffer())));
    if (mine && mine.url === url) mine.contour = c;
    const ref = await refContour(idx);
    const score = similarity(ref.c, c);
    if (cur === idx) { drawPitch(); showPitchScore(score); }
    return score;
  })().catch(() => null);

  // 발음: 서버의 Whisper
  $('#word-score').innerHTML = '<span class="muted">분석 중…</span>';
  try {
    const rec = await api(`/api/videos/${video.id}/sentences/${idx}/recordings`, { method: 'POST', headers: { 'Content-Type': blob.type || 'audio/webm' }, body: blob });
    if (rec.empty) {
      if (cur === idx) {
        $('#word-score').innerHTML = '<span class="miss">말소리가 안 들렸어요</span>';
        status('🎤 말소리가 거의 안 들렸어요. 마이크(시스템 설정 → 사운드 → 입력)와 목소리 크기를 확인하세요. 이 녹음은 기록에 남기지 않았어요.');
      }
      return;
    }
    if (mine && mine.url === url) mine.name = rec.name;
    if (cur === idx) showDiff(rec);
    const pitch = await pitchP;
    if (pitch != null) {
      rec.pitch = pitch;
      api(`/api/videos/${video.id}/sentences/${idx}/recordings/${rec.name}/pitch`, { method: 'POST', body: JSON.stringify({ pitch }) }).catch(() => {});
    }
    const prev = recSum[idx];
    recSum[idx] = { count: (prev?.count || 0) + 1, last: rec.score, best: Math.max(prev?.best || 0, rec.score), pitch };
    renderList();
    if (cur === idx) loadHistory(idx, false);
  } catch (err) {
    if (cur === idx) $('#word-score').innerHTML = `<span class="miss">분석 실패: ${esc(err.message)}</span>`;
  }
}

function showPitchScore(v) {
  $('#pitch-score').innerHTML = v == null ? '<span class="muted">목소리가 잘 안 잡혔어요</span>' : `억양 <b class="${grade(v)}">${v}%</b>`;
}

function showDiff(rec) {
  $('#word-score').innerHTML = `알아들음 <b class="${grade(rec.score)}">${rec.score}%</b>`;
  renderSentence(rec.diff);
  $('#heard').innerHTML = rec.diff.map(d => `<span class="${d.extra ? 'extra' : d.ok ? 'ok' : 'miss'}" data-w="${esc(d.w)}">${esc(d.w)}</span>`).join(' ')
    + `<span class="said">Whisper가 들은 문장: “${esc(rec.text || '(없음)')}”</span>`;
}

// ── 단어 뜻 (맥 내장 영한사전) ─────────────────────────
const dictCache = new Map();
let wordReq = 0;

async function showWord(word, el) {
  const card = $('#word-card');
  document.querySelectorAll('.sent-text .w.sel').forEach(x => x.classList.remove('sel'));
  el && el.classList.add('sel');
  const key = word.replace(/[^A-Za-z'\-]/g, '');
  if (!key) return;
  card.hidden = false;
  card.innerHTML = `<span class="muted">“${esc(key)}” 찾는 중…</span>`;
  const my = ++wordReq;
  let d = dictCache.get(key.toLowerCase());
  if (!d) {
    d = await api('/api/dict?w=' + encodeURIComponent(key)).catch(() => null);
    if (d) dictCache.set(key.toLowerCase(), d);
  }
  if (my !== wordReq) return;
  const close = '<button class="wc-close" title="닫기">×</button>';
  if (!d || !d.entries.length) {
    card.innerHTML = close + (d && d.missing ? '단어 사전 도우미가 준비되지 않았어요. SHADOW를 다시 실행해 주세요.' : `<b>${esc(key)}</b> <span class="muted">— 사전에 없어요 (이름·고유명사일 수 있어요)</span>`);
    return;
  }
  const render = full => close + d.entries.slice(0, full ? 3 : 2).map(e => `
    <div class="wc-entry"><span class="wc-head">${esc(e.head)}</span>${e.pron ? `<span class="wc-pron">/${esc(e.pron)}/</span>` : ''}
      ${e.groups.slice(0, full ? 3 : 2).map(g => `<div class="wc-g">${g.pos ? `<span class="wc-pos">${esc(g.pos.replace(/^동사,\s*/, ''))}</span>` : ''}${esc(g.senses.slice(0, full ? 3 : 2).join(' · '))}</div>`).join('')}
    </div>`).join('')
    + (!full && needsMore(d) ? '<button class="wc-more">뜻 더 보기</button>' : '');
  card.innerHTML = render(false);
  card.onclick = e => {
    if (e.target.closest('.wc-close')) { card.hidden = true; document.querySelectorAll('.sent-text .w.sel').forEach(x => x.classList.remove('sel')); }
    else if (e.target.closest('.wc-more')) card.innerHTML = render(true);
  };
}
const needsMore = d => d.entries.length > 2 || d.entries.some(e => e.groups.length > 2 || e.groups.some(g => g.senses.length > 2));

$('#sent-text').addEventListener('click', e => { const w = e.target.closest('[data-w]'); if (w) showWord(w.dataset.w, w); });
$('#heard').addEventListener('click', e => { const w = e.target.closest('[data-w]'); if (w) showWord(w.dataset.w, null); });

// ── 날짜별 기록 ────────────────────────────────────
async function loadHistory(i, showLatest) {
  const list = await api(`/api/videos/${video.id}/sentences/${i}/recordings`).catch(() => []);
  if (i !== cur) return;
  const box = $('#history');
  if (!list.length) { box.innerHTML = '아직 녹음이 없어요.'; return; }
  const byDay = {};
  list.slice().reverse().forEach(r => (byDay[r.date] ||= []).push(r));
  box.innerHTML = Object.entries(byDay).map(([day, rs]) => `<div class="day">${day}</div>` + rs.map(r => `
    <div class="row"><span class="tm">${r.time}</span>
      <span>발음 <b class="${grade(r.score)}">${r.score}%</b></span>
      <span>억양 <b class="${grade(r.pitch)}">${r.pitch ?? '–'}${r.pitch != null ? '%' : ''}</b></span>
      <button class="btn" data-name="${r.name}" title="이 녹음을 불러와 듣고 그래프로 보기">▶</button></div>`).join('')).join('');
  box._recs = list;
  if (showLatest && !mine) loadRec(i, list[list.length - 1], false);
}

$('#history').addEventListener('click', e => {
  const b = e.target.closest('button[data-name]');
  if (!b) return;
  const rec = $('#history')._recs.find(r => r.name === b.dataset.name);
  if (rec) loadRec(cur, rec, true);
});

async function loadRec(i, rec, play) {
  const url = `/media/${video.id}/rec/${i}/${rec.name}.wav`;
  mine = { idx: i, url, contour: null, name: rec.name };
  $('#b-mine').disabled = $('#b-cmp').disabled = false;
  showDiff(rec);
  if (play) playMine();
  try {
    const c = contour(analyze(await decode16k(await fetch(url).then(r => r.arrayBuffer()))));
    if (!mine || mine.url !== url) return;
    mine.contour = c;
    const ref = await refContour(i);
    const score = similarity(ref.c, c);
    showPitchScore(score);
    drawPitch();
    if (rec.pitch == null && score != null) {   // 억양 점수가 없던 녹음은 채워 둔다
      rec.pitch = score;
      await api(`/api/videos/${video.id}/sentences/${i}/recordings/${rec.name}/pitch`, { method: 'POST', body: JSON.stringify({ pitch: score }) });
      if (cur === i) loadHistory(i, false);
    }
  } catch { /* 무시 */ }
}

// ── 버튼·단축키 ────────────────────────────────────
$('#b-prev').onclick = () => select(cur - 1, true);
$('#b-next').onclick = () => select(cur + 1, true);
$('#b-orig').onclick = playOrig;
$('#b-mine').onclick = playMine;
$('#b-cmp').onclick = compare;
const recBtn = $('#b-rec');
recBtn.addEventListener('pointerdown', e => { e.preventDefault(); startRec(); });
['pointerup', 'pointerleave', 'pointercancel'].forEach(ev => recBtn.addEventListener(ev, stopRec));

window.addEventListener('keydown', e => {
  if ($('#practice').hidden || e.target.matches('input, textarea') || e.metaKey || e.ctrlKey) return;
  // 한글 입력 상태에서도 되도록 글자(e.key)가 아니라 키 위치(e.code)로 판단한다 (R=ㄱ, P=ㅔ, C=ㅊ)
  const k = e.code;
  if (k === 'Space') { e.preventDefault(); if (!e.repeat) startRec(); }
  else if (e.repeat) return;
  else if (k === 'KeyR' || k === 'Enter' || k === 'NumpadEnter') { e.preventDefault(); playOrig(); }
  else if (k === 'KeyP') { e.preventDefault(); playMine(); }
  else if (k === 'KeyC') { e.preventDefault(); compare(); }
  else if (k === 'ArrowLeft' || k === 'ArrowUp') { e.preventDefault(); select(cur - 1, true); }
  else if (k === 'ArrowRight' || k === 'ArrowDown') { e.preventDefault(); select(cur + 1, true); }
});
window.addEventListener('keyup', e => { if (e.code === 'Space') { e.preventDefault(); stopRec(); } });
// 녹음 중에 창을 벗어나면 멈춤
window.addEventListener('blur', () => {
  stopRec();
  // 유튜브 영상을 클릭하면 키보드가 영상으로 넘어가므로 다시 가져온다
  setTimeout(() => {
    const a = document.activeElement;
    if (a && a.tagName === 'IFRAME') { a.blur(); window.focus(); }
  }, 150);
});
// 버튼을 클릭한 뒤 Space가 버튼 클릭으로 처리되지 않게
document.querySelectorAll('.controls .btn').forEach(b => b.addEventListener('keydown', e => e.key === ' ' && e.preventDefault()));
