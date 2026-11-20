// 억양 분석: 음높이(YIN) 추출 → 반음 단위로 정규화 → 모양 비교(DTW) → 그리기
// 모든 계산은 브라우저 안에서만 한다.
const SR = 16000;
const FRAME = 640;   // 40ms
const HOP = 160;     // 10ms
const FMIN = 65, FMAX = 450;

export async function decode16k(arrayBuffer) {
  const ctx = new OfflineAudioContext(1, 1, SR);
  const buf = await ctx.decodeAudioData(arrayBuffer);
  return buf.getChannelData(0);
}

function yinFrame(x, off, tauMin, tauMax, d) {
  const W = FRAME - tauMax;
  for (let tau = 1; tau <= tauMax; tau++) {
    let s = 0;
    for (let i = 0; i < W; i++) {
      const v = x[off + i] - x[off + i + tau];
      s += v * v;
    }
    d[tau] = s;
  }
  // 누적 평균 정규화
  let run = 0;
  d[0] = 1;
  for (let tau = 1; tau <= tauMax; tau++) {
    run += d[tau];
    d[tau] = run ? d[tau] * tau / run : 1;
  }
  let best = -1;
  for (let tau = tauMin; tau <= tauMax; tau++) {
    if (d[tau] < 0.15) {
      while (tau + 1 <= tauMax && d[tau + 1] < d[tau]) tau++;
      best = tau;
      break;
    }
  }
  if (best < 0) return 0;
  // 포물선 보간
  const a = d[best - 1] ?? d[best], b = d[best], c = d[best + 1] ?? d[best];
  const den = a + c - 2 * b;
  const t = den ? best + (a - c) / (2 * den) : best;
  return SR / t;
}

// samples(16k) 구간 → {f0[], rms[], dt}
export function analyze(samples) {
  const tauMin = Math.floor(SR / FMAX), tauMax = Math.ceil(SR / FMIN);
  const d = new Float32Array(tauMax + 2);
  const f0 = [], rms = [];
  for (let off = 0; off + FRAME < samples.length; off += HOP) {
    let e = 0;
    for (let i = 0; i < FRAME; i++) e += samples[off + i] ** 2;
    rms.push(Math.sqrt(e / FRAME));
    f0.push(yinFrame(samples, off, tauMin, tauMax, d));
  }
  const maxR = Math.max(1e-6, ...rms);
  for (let i = 0; i < f0.length; i++) if (rms[i] < maxR * 0.06) f0[i] = 0;
  return { f0: medianSmooth(f0), rms, dt: HOP / SR, maxR };
}

function medianSmooth(f0) {
  const out = f0.slice();
  for (let i = 2; i < f0.length - 2; i++) {
    const win = f0.slice(i - 2, i + 3).filter(v => v > 0);
    if (f0[i] > 0 && win.length >= 3) {
      win.sort((a, b) => a - b);
      out[i] = win[Math.floor(win.length / 2)];
    } else if (f0[i] > 0 && win.length < 3) out[i] = 0; // 혼자 튄 값 제거
  }
  return out;
}

// 소리 있는 부분만 남기고, 말한 사람 평균 기준 반음으로 바꾼다
export function contour(a) {
  const thr = a.maxR * 0.12;
  let s = a.rms.findIndex(r => r > thr);
  let e = a.rms.length - 1 - [...a.rms].reverse().findIndex(r => r > thr);
  if (s < 0) { s = 0; e = a.rms.length - 1; }
  const f = a.f0.slice(s, e + 1), r = a.rms.slice(s, e + 1);
  const voiced = f.filter(v => v > 0).sort((x, y) => x - y);
  const med = voiced.length ? voiced[Math.floor(voiced.length / 2)] : 0;
  const st = f.map(v => {
    if (!v || !med) return null;
    const x = 12 * Math.log2(v / med);
    return Math.abs(x) > 12 ? null : x; // 옥타브 오류 제거
  });
  return { st, rms: r.map(v => v / a.maxR), t0: s * a.dt, dur: (e - s + 1) * a.dt, voicedRatio: voiced.length / Math.max(1, f.length) };
}

function resample(st, n = 100) {
  // 무성 구간은 앞뒤를 선으로 이어 채운 뒤 n개로 고르게 뽑는다
  const idx = st.map((v, i) => v == null ? -1 : i).filter(i => i >= 0);
  if (idx.length < 3) return null;
  const filled = st.map((v, i) => {
    if (v != null) return v;
    const prev = idx.filter(k => k < i).pop(), next = idx.find(k => k > i);
    if (prev == null) return st[next];
    if (next == null) return st[prev];
    return st[prev] + (st[next] - st[prev]) * (i - prev) / (next - prev);
  });
  const out = [];
  for (let k = 0; k < n; k++) {
    const p = k * (filled.length - 1) / (n - 1), i = Math.floor(p), fr = p - i;
    out.push(filled[i] + ((filled[i + 1] ?? filled[i]) - filled[i]) * fr);
  }
  return out;
}

// 억양 유사도 0~100: 말 빠르기 차이는 DTW로 맞추고, 오르내림 모양의 상관으로 점수
export function similarity(ref, mine) {
  const a = resample(ref.st), b = resample(mine.st);
  if (!a || !b) return null;
  const n = a.length, band = 15, INF = 1e9;
  const D = Array.from({ length: n + 1 }, () => new Float64Array(n + 1).fill(INF));
  D[0][0] = 0;
  for (let i = 1; i <= n; i++)
    for (let j = Math.max(1, i - band); j <= Math.min(n, i + band); j++)
      D[i][j] = Math.abs(a[i - 1] - b[j - 1]) + Math.min(D[i - 1][j - 1], D[i - 1][j], D[i][j - 1]);
  const pairs = [];
  let i = n, j = n;
  while (i > 0 && j > 0) {
    pairs.push([a[i - 1], b[j - 1]]);
    const m = Math.min(D[i - 1][j - 1], D[i - 1][j], D[i][j - 1]);
    if (m === D[i - 1][j - 1]) { i--; j--; } else if (m === D[i - 1][j]) i--; else j--;
  }
  const mx = pairs.reduce((s, p) => s + p[0], 0) / pairs.length;
  const my = pairs.reduce((s, p) => s + p[1], 0) / pairs.length;
  let sxy = 0, sxx = 0, syy = 0;
  for (const [x, y] of pairs) { sxy += (x - mx) * (y - my); sxx += (x - mx) ** 2; syy += (y - my) ** 2; }
  if (sxx < 1e-6 || syy < 1e-6) return 50;
  const r = sxy / Math.sqrt(sxx * syy);
  return Math.round(Math.max(0, r) * 100);
}

// 그리기: ref(파랑) · mine(주황) · 원문 단어 위치
export function draw(canvas, ref, mine, words, segStart) {
  const dpr = window.devicePixelRatio || 1;
  const W = canvas.clientWidth, H = canvas.clientHeight;
  canvas.width = W * dpr; canvas.height = H * dpr;
  const g = canvas.getContext('2d');
  g.scale(dpr, dpr);
  const css = getComputedStyle(document.documentElement);
  const col = k => css.getPropertyValue(k).trim();
  g.clearRect(0, 0, W, H);
  const padL = 34, padR = 10, top = 10, bottom = 40;
  const ph = H - top - bottom, pw = W - padL - padR;
  const all = [ref, mine].filter(Boolean).flatMap(c => c.st.filter(v => v != null));
  const lim = Math.max(4, Math.ceil(Math.max(...all.map(Math.abs), 0)));
  const y = v => top + ph / 2 - (v / lim) * (ph / 2);
  // 눈금
  g.strokeStyle = col('--grid'); g.lineWidth = 1; g.fillStyle = col('--muted'); g.font = '11px system-ui';
  for (const v of [-lim, -lim / 2, 0, lim / 2, lim]) {
    g.beginPath(); g.moveTo(padL, y(v)); g.lineTo(W - padR, y(v)); g.stroke();
    g.fillText((v > 0 ? '+' : '') + Math.round(v), 4, y(v) + 4);
  }
  // 크기(강세) 막대
  const loud = (c, color, yBase) => {
    if (!c) return;
    g.fillStyle = color;
    const n = c.rms.length;
    for (let i = 0; i < n; i++) {
      const h = c.rms[i] * 14;
      g.fillRect(padL + (i / n) * pw, yBase - h, Math.max(1, pw / n), h);
    }
  };
  loud(ref, col('--ref-soft'), H - 22);
  loud(mine, col('--mine-soft'), H - 22);
  const line = (c, color, width) => {
    if (!c) return;
    g.strokeStyle = color; g.lineWidth = width; g.lineJoin = 'round'; g.lineCap = 'round';
    const n = c.st.length;
    let pen = false;
    g.beginPath();
    for (let i = 0; i < n; i++) {
      const v = c.st[i];
      if (v == null) { pen = false; continue; }
      const x = padL + (i / (n - 1)) * pw;
      pen ? g.lineTo(x, y(v)) : g.moveTo(x, y(v));
      pen = true;
    }
    g.stroke();
  };
  line(ref, col('--ref'), 3);
  line(mine, col('--mine'), 2.5);
  // 원문 단어 위치
  if (ref && words) {
    g.fillStyle = col('--text'); g.font = '12px system-ui'; g.textBaseline = 'alphabetic';
    let lastX = -1e9;
    for (const w of words) {
      const rel = (w.s - segStart - ref.t0) / ref.dur;
      if (rel < -0.05 || rel > 1.02) continue;
      const x = padL + Math.max(0, rel) * pw;
      g.strokeStyle = col('--grid'); g.beginPath(); g.moveTo(x, top); g.lineTo(x, H - 26); g.stroke();
      if (x - lastX > 28) { g.fillText(w.w.replace(/[^\w']/g, ''), x + 2, H - 4); lastX = x + g.measureText(w.w).width; }
    }
  }
}
