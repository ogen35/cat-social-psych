// 片段 · 喵喵剧团 Vox 拼贴（照 references/动画语法/y2_vox.md 与 demos/y2_vox 的做法；竖屏 1080×1920）
// 一张桌面＝世界（世界坐标＝相机 z=1 时的屏幕坐标），相机 60fps 平滑；桌上的东西（滑入、打字、荧光笔、红笔、红线、盖章、猫贴纸张嘴）按 12fps 一拍二步进。
// 配色只用 Vox 三色：纸白、近黑、一种红；荧光黄只划字。照片、视频一律灰度网点冲印件（白边、旧纸色、两条胶带）。
// 猫：真实照片抠图做成剪纸贴纸（纸白描边、灰度网点）；说话时下巴那一块剪纸往下掉、头一顿一顿（拼贴式张嘴）。
// 红圈、荧光笔只落在「这一句正在说的那个词」上：剪报的标题词、索引卡上的词、时刻表上的时间、分数——不圈脸。
//
// cue（全部写在 cues 里，素材才会被加载；位置、参数写在 data 里）：
//   photo     image|frames；data {x,y,w,h,rot,cell(网点格,默认5),fx,fy,label,labelAt,tape}
//   cat       image（抠图 png）；data {x,y(脚底),h,rot,flip,mouth:[nx,my,chin],jaw(半宽,0.13),drop(0.05),talk:[[a,b]..],cell(4),enter}
//   clipping  data {x,y,w,rot,kicker,head:[..],body:[..],bars(3),marks:[..],type(cps)}       剪报
//   card      data {x,y,w,rot,lines:[..],size,marks,type}                                    横线索引卡
//   strip     data {x,y,w,rot,lines:[..],size,marks,type,dark}                               撕边纸条大标题（dark：黑卡上的白纸条）
//   label     data {x,y,text,size,rot,bg:'ink'|'red'}                                          黑底撕边标签（12fps 弹出）
//   string    data {a:[x,y],b:[x,y],sag,dur,label}                                             红线（钉子＋按长度描出）
//   stamp     data {x,y,text,size,rot}                                                         红色印章（砸下）
//   circle    data {x,y,rx,ry,dur}                                                             红笔圈（世界坐标）
//   blackcard data {x,y,w,h,rot}                                                               桌上的大黑卡纸
//   marks（文字块里）：{at, kind:'hl'|'circle'|'strike', line, sub}  → 荧光笔扫 / 红圈 / 红笔划掉 这一行里的 sub
// spec.data：cam [{t,x,y,z,ease:'sine'|'tail'|'punch'|'cut'}]、caps [{t0,t1,text,who,hi:[..]}]、topbar {text,hi}、fy（画面焦点高度，默认 820）
CLIPS.cat_vox = (() => {
const { clamp, lerp, rng } = U;
const C = { desk: '#e4ddcf', ink: '#171716', red: '#b8433f', hl: 'rgba(218,207,8,.92)', yel: '#dacf08', paper: '#eeedeb', card: '#f6f4ee',
  black: '#1b1b1a', news: '#ebe5d4', mouth: '#231b19', htPaper: '#e8e3d6', htInk: '#1d1c1a' };
const FB = '"PuHui-Black"', FH = '"PuHui-Heavy"', FBo = '"PuHui-Bold"', FM = '"PuHui-Medium"';
const EASE = { sine: MO.sineInOut, tail: MO.longTail, punch: MO.cubicOut, linear: MO.linear };
let W, H, FY, items, cam, caps, topbar, meas;
const ls = (t, at) => MO.step(t - at + 1e-6, 12) + 1 / 12;           // 一拍二的片内时间：at 这一帧就 >0
const prog = (t, at, dur) => clamp(ls(t, at) / dur);

// ---------- 灰度网点（不缓存版：视频每帧现算；静图走 PAINT.cached） ----------
function halftoneInto(g, src, w, h, { cell = 5, fx = 0.5, fy = 0.5, contrast = 1.3, bright = 0, alphaFrom = null } = {}) {
  const s = UI.scratch('cv_ht_src', Math.ceil(w), Math.ceil(h)), sg = s.getContext('2d', { willReadFrequently: true });
  sg.clearRect(0, 0, s.width, s.height);
  MD.cover(sg, src, { x: 0, y: 0, w: s.width, h: s.height, fx, fy });
  const d = sg.getImageData(0, 0, s.width, s.height).data, sw = s.width, sh = s.height;
  g.fillStyle = C.htPaper; g.fillRect(0, 0, w, h);
  g.fillStyle = C.htInk; g.beginPath();
  const a = Math.PI / 4, ca = Math.cos(a), sa = Math.sin(a), R = Math.hypot(w, h) / 2 + cell;
  for (let v = -R; v < R; v += cell) for (let u = -R; u < R; u += cell) {
    const x = w / 2 + u * ca - v * sa, y = h / 2 + u * sa + v * ca; if (x < -cell || y < -cell || x > w + cell || y > h + cell) continue;
    const ix = clamp(x | 0, 0, sw - 1), iy = clamp(y | 0, 0, sh - 1), i = (iy * sw + ix) * 4;
    if (d[i + 3] < 20) continue;
    let L = (d[i] * .3 + d[i + 1] * .59 + d[i + 2] * .11) / 255; L = clamp((L - 0.5) * contrast + 0.52 + bright);
    const rr = cell * 0.66 * Math.sqrt(1 - L); if (rr < 0.35) continue;
    g.moveTo(x + rr, y); g.arc(x, y, rr, 0, Math.PI * 2);
  }
  g.fill();
  if (alphaFrom) { g.globalCompositeOperation = 'destination-in'; g.drawImage(alphaFrom, 0, 0, w, h); g.globalCompositeOperation = 'source-over'; }
}
// 冲印件：白边＋旧纸色＋投影＋两条胶带；内容是网点
function drawPrint(g, it, t, ctx) {
  const q = it.q, D = q.data, w = D.w, h = D.h, b = D.border ?? 18, PW = w + 2 * b, PH = h + 2 * b;
  const paint = (pg, src) => {
    pg.fillStyle = '#f4f1e9'; pg.fillRect(0, 0, PW, PH);
    pg.save(); pg.translate(b, b); halftoneInto(pg, src, w, h, { cell: D.cell ?? 5, fx: D.fx ?? 0.5, fy: D.fy ?? 0.5, contrast: D.contrast ?? 1.3, bright: D.bright ?? 0 }); pg.restore();
    pg.save(); pg.globalCompositeOperation = 'multiply'; pg.fillStyle = 'rgba(214,205,185,.22)'; pg.fillRect(0, 0, PW, PH); pg.restore();
  };
  let sp;
  if (q.frames) { sp = UI.scratch('cv_print_' + it.k, Math.ceil(PW), Math.ceil(PH)); const pg = sp.getContext('2d'); pg.clearRect(0, 0, sp.width, sp.height); paint(pg, ctx.frame(q, t)); }
  else sp = PAINT.cached('cvprint_' + it.k + '_' + w + 'x' + h, Math.ceil(PW), Math.ceil(PH), pg => paint(pg, ctx.still(q)));
  CL.shadowed(g, () => g.drawImage(sp, -PW / 2, -PH / 2), { blur: 14, x: 3, y: 8, col: 'rgba(30,22,10,.3)' });
  if (D.tape !== false) { CL.tape(g, -w / 2 + 40, -PH / 2 + 6, -0.6, 120); CL.tape(g, w / 2 - 40, -PH / 2 + 6, 0.55, 120); }
  if (D.label) MD.label(g, D.label, -PW / 2 - 10, PH / 2 - 30, { t, at: D.labelAt ?? q.at + 0.25, size: D.labelSize ?? 46, r: -0.02, bg: C.ink, fg: C.paper });
}

// ---------- 猫贴纸（拼贴式张嘴） ----------
function catSprite(it, ctx) {
  const q = it.q, D = q.data, im = ctx.still(q), [iw, ih] = MD.size(im), h = D.h, w = Math.round(h * iw / ih), e = D.edge ?? 13;
  const key = 'cvcat_' + it.k + '_' + h;
  const body = PAINT.cached(key + '_b', w + 2 * e, h + 2 * e, (g) => {
    const raw = PAINT.canvas(w, h), rg = raw.getContext('2d', { willReadFrequently: true }); rg.drawImage(im, 0, 0, w, h);
    { const id = rg.getImageData(0, 0, w, h), px = id.data; for (let i = 3; i < px.length; i += 4) px[i] = px[i] > 150 ? 255 : 0; rg.putImageData(id, 0, 0); }   // 剪纸是硬边：抠图里半透明的背景雾一律去掉
    const ht = PAINT.canvas(w, h), hg = ht.getContext('2d'); halftoneInto(hg, raw, w, h, { cell: D.cell ?? 4, contrast: D.contrast ?? 1.25, alphaFrom: raw });
    const sil = PAINT.canvas(w + 2 * e, h + 2 * e), sg = sil.getContext('2d');
    for (let k = 0; k < 20; k++) sg.drawImage(raw, e + Math.cos(k / 20 * 6.283) * e, e + Math.sin(k / 20 * 6.283) * e);
    sg.globalCompositeOperation = 'source-in'; sg.fillStyle = '#f3f0e8'; sg.fillRect(0, 0, w + 2 * e, h + 2 * e);
    g.drawImage(sil, 0, 0); g.drawImage(ht, e, e);
  });
  const [nx, my, chin] = D.mouth || [0.5, 0.5, 0.56], jw = (D.jaw ?? 0.12) * w, cx = e + nx * w, y0 = e + my * h, y1 = e + chin * h;
  const arch = jw * 0.35;                                                 // 剪口是一道上拱的弧（像嘴角），不是直线：张嘴时露出的缝才像嘴
  const path = (g) => { g.beginPath(); g.moveTo(cx - jw, y0 + arch); g.quadraticCurveTo(cx, y0 - arch, cx + jw, y0 + arch); g.ellipse(cx, y0 + arch, jw, Math.max(10, y1 - y0), 0, 0, Math.PI); g.closePath(); };
  const jaw = PAINT.cached(key + '_j', w + 2 * e, h + 2 * e, (g) => { g.save(); path(g); g.clip(); g.drawImage(body, 0, 0); g.restore(); });
  return { body, jaw, path, w: w + 2 * e, h: h + 2 * e, e, cx, y0, y1, jw };
}
function talkAmt(D, t) {
  for (const [a, b] of (D.talk || [])) if (t >= a && t < b) {
    const k = Math.floor((t - a) * 12 + 1e-6), r = rng(k * 7 + 3)();
    return k % 2 === 0 ? 0.55 + 0.45 * r : 0.08 * r;
  }
  return 0;
}
function drawCat(g, it, t, ctx) {
  const D = it.q.data, S = it.spr || (it.spr = catSprite(it, ctx)), o = talkAmt(D, t), st = MO.step(t, 12);
  const talking = (D.talk || []).some(([a, b]) => t >= a && t < b), k = Math.floor(st * 12);
  const bob = talking ? -o * 0.012 * S.h : 0, rot = talking ? ((k >> 1) % 2 ? 1 : -1) * 0.012 : 0, d = o * (D.drop ?? 0.04) * S.h;
  g.save(); if (D.flip) g.scale(-1, 1); g.rotate(rot); g.translate(-S.w / 2, -S.h + bob);
  CL.shadowed(g, () => g.drawImage(S.body, 0, 0), { blur: 12, x: 4, y: 8, col: 'rgba(20,16,10,.35)' });
  if (d > 0.5) {
    g.save(); S.path(g); g.fillStyle = C.mouth; g.fill(); g.restore();      // 整块下巴的位置先涂成嘴里的深色，再把下巴剪纸往下挪：露出来的就是一道弧形的嘴
    g.save(); g.translate(S.cx, S.y0); g.rotate(-o * 0.03); g.translate(-S.cx, -S.y0 + d); g.drawImage(S.jaw, 0, 0); g.restore();
  }
  g.restore();
}

// ---------- 文字块：剪报 / 索引卡 / 纸条 ----------
function layoutText(q) {
  const D = q.data, k = q.kind, w = D.w ?? (k === 'clipping' ? 860 : k === 'card' ? 780 : 900), L = [];
  if (k === 'clipping') {
    let y = 70; const pad = 52;
    if (D.kicker) { L.push({ text: D.kicker, font: `26px ${FBo}`, size: 26, x: pad, y, col: '#3a352e' }); y += 18; }
    const rules = y; y += 26;
    for (const s of D.head || []) { y += D.headSize ?? 74; L.push({ text: s, font: `${D.headSize ?? 74}px ${FB}`, size: D.headSize ?? 74, x: pad, y, col: C.ink }); y += 14; }
    y += 22;
    for (const s of D.body || []) { y += 38; L.push({ text: s, font: `34px ${FM}`, size: 34, x: pad, y, col: '#2a2723' }); y += 18; }
    const bars = D.bars ?? 3, bt = y + 26; y = bt + bars * 34 + 30;
    return { w, h: y, lines: L, rules, bars, bt, pad };
  }
  if (k === 'card') {
    const size = D.size ?? 56, lh = size * 1.5; let y = 92;
    for (const s of D.lines || []) { y += lh; L.push({ text: s, font: `${size}px ${FH}`, size, x: 56, y: y - lh * 0.28, col: C.ink }); }
    return { w, h: y + 46, lines: L, lh, top: 92 };
  }
  const size = D.size ?? 78, lh = size * 1.28; let y = 36;                    // strip
  for (const s of D.lines || []) { y += lh; L.push({ text: s, font: `${size}px ${FB}`, size, x: 44, y: y - lh * 0.2, col: C.ink }); }
  return { w, h: y + 40, lines: L };
}
function textBg(it) {
  const q = it.q, T = it.T, key = 'cvtxt_' + it.k + '_' + Math.round(T.w) + 'x' + Math.round(T.h);
  return PAINT.cached(key, Math.ceil(T.w), Math.ceil(T.h), (g) => {
    if (q.kind === 'clipping') {
      g.save(); CL.tornRect(g, T.w, T.h, 21 + it.k, 4); g.clip();
      g.fillStyle = g.createPattern(CL.paperTile('cvnews', C.news, { amt: 9, fibers: 160 }), 'repeat'); g.fillRect(0, 0, T.w, T.h);
      const yel = g.createRadialGradient(T.w * .4, T.h * .4, 40, T.w * .5, T.h * .5, T.w * .8); yel.addColorStop(0, 'rgba(255,255,255,0)'); yel.addColorStop(1, 'rgba(170,150,110,.22)'); g.fillStyle = yel; g.fillRect(0, 0, T.w, T.h);
      g.fillStyle = C.ink; g.fillRect(T.pad, T.rules, T.w - 2 * T.pad, 3); g.fillRect(T.pad, T.rules + 6, T.w - 2 * T.pad, 1);
      g.fillStyle = 'rgba(40,36,30,.28)'; for (let i = 0; i < T.bars; i++) g.fillRect(T.pad, T.bt + i * 34, (T.w - 2 * T.pad) * [0.92, 0.84, 0.56, 0.7][i % 4], 13);
      g.restore();
    } else if (q.kind === 'card') {
      g.fillStyle = C.card; g.fillRect(0, 0, T.w, T.h);
      g.strokeStyle = 'rgba(80,140,200,.28)'; g.lineWidth = 2; for (let y = T.top + T.lh; y < T.h; y += T.lh) { g.beginPath(); g.moveTo(0, y); g.lineTo(T.w, y); g.stroke(); }
      g.strokeStyle = 'rgba(184,67,63,.5)'; g.beginPath(); g.moveTo(0, T.top - 30); g.lineTo(T.w, T.top - 30); g.stroke();
    } else {
      g.fillStyle = q.data.dark ? '#f1eee6' : C.paper; CL.tornRect(g, T.w, T.h, 61 + it.k, 4); g.fill();
    }
  });
}
function subRect(it, m) {
  const ln = it.T.lines[m.line]; if (!ln) return null;
  meas.font = ln.font; const i = ln.text.indexOf(m.sub ?? ln.text); if (i < 0) return null;
  const x0 = ln.x + meas.measureText(ln.text.slice(0, i)).width, w = meas.measureText(m.sub ?? ln.text).width;
  return { x: x0, y: ln.y - ln.size * 0.92, w, h: ln.size * 1.18 };
}
function drawText(g, it, t, ctx) {
  const q = it.q, D = q.data, T = it.T, bg = textBg(it);
  CL.shadowed(g, () => g.drawImage(bg, -T.w / 2, -T.h / 2), { blur: 10, x: 3, y: 6 });
  g.save(); g.translate(-T.w / 2, -T.h / 2);
  // 荧光笔先画（压在字下，multiply）
  for (const m of D.marks || []) if (m.kind === 'hl' && t >= m.at) { const r = subRect(it, m); if (r) CL.highlight(g, r.x - 8, r.y - 2, r.w + 16, r.h + 4, MO.sineInOut(prog(t, m.at, m.dur ?? 0.6)), C.hl); }
  const typed = D.type ? Math.ceil(ls(t, q.at + 0.1) * D.type) : 1e9; let n = 0;
  g.textBaseline = 'alphabetic';
  for (const ln of T.lines) { g.font = ln.font; g.fillStyle = ln.col; let x = ln.x;
    for (const ch of ln.text) { if (n < typed) g.fillText(ch, x, ln.y); x += g.measureText(ch).width; n++; } }
  for (const m of D.marks || []) {
    if (t < m.at || m.kind === 'hl') continue; const r = subRect(it, m); if (!r) continue;
    if (m.kind === 'circle') { const p = MO.cubicOut(prog(t, m.at, m.dur ?? 0.6)), pts = DG.hand(DG.ellipsePts(r.x + r.w / 2, r.y + r.h / 2, r.w / 2 + 26, r.h / 2 + 16, -2.6, 1.1, 44), { amp: 2.4, seed: 7 + it.k }), L = DG.cum(pts);
      g.save(); g.strokeStyle = C.red; g.lineWidth = 7; g.lineCap = 'round'; g.lineJoin = 'round'; DG.drawPartial(g, pts, L, L[L.length - 1] * p); g.restore(); }
    if (m.kind === 'strike') { const p = MO.sineInOut(prog(t, m.at, m.dur ?? 0.4)), pts = DG.hand([[r.x - 10, r.y + r.h * 0.6], [r.x + r.w + 10, r.y + r.h * 0.45]], { amp: 1.5, seed: 3 }), L = DG.cum(pts);
      g.save(); g.strokeStyle = C.red; g.lineWidth = Math.max(10, r.h * 0.16); g.lineCap = 'round'; DG.drawPartial(g, pts, L, L[L.length - 1] * p); g.restore(); }
  }
  g.restore();
}

// ---------- 其他小件 ----------
function drawStamp(g, it, t) {
  const D = it.q.data, size = D.size ?? 70, l = t - it.q.at, s = l < 1 / 12 ? 1.5 : l < 2 / 12 ? 1.12 : 1;
  meas.font = `${size}px ${FB}`; const tw = meas.measureText(D.text).width, pw = tw + size * 0.8, ph = size * 1.45;
  g.save(); g.scale(s, s); g.globalAlpha = 0.95;   // 不用 multiply：黑卡上会变成黑的
  const col = D.onDark ? '#d0544c' : C.red; g.strokeStyle = col; g.lineWidth = 7; g.beginPath(); g.roundRect(-pw / 2, -ph / 2, pw, ph, 12); g.stroke();
  g.fillStyle = col; g.font = `${size}px ${FB}`; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(D.text, 0, 4);
  g.restore();
}
function drawBlackCard(g, it) {
  const D = it.q.data, w = D.w ?? 980, h = D.h ?? 1080;
  CL.shadowed(g, () => { g.fillStyle = C.black; g.save(); g.translate(-w / 2, -h / 2); CL.tornRect(g, w, h, 91 + it.k, 4); g.fill(); g.restore(); }, { blur: 16, x: 4, y: 10 });
  g.save(); g.translate(-w / 2, -h / 2); CL.tornRect(g, w, h, 91 + it.k, 4); g.clip();
  g.fillStyle = g.createPattern(CL.paperTile('cvblack', C.black, { amt: 5, fibers: 90, fiberCol: [90, 90, 85] }), 'repeat'); g.fillRect(0, 0, w, h); g.restore();
}

return {
  fonts: ['PuHui-Black', 'PuHui-Heavy', 'PuHui-Bold', 'PuHui-Medium'],
  safe: true,
  init(ctx) {
    W = ctx.W; H = ctx.H; FY = ctx.data.fy ?? 820;
    meas = document.createElement('canvas').getContext('2d');
    items = ctx.cues.map((q, k) => ({ q, k }));
    for (const it of items) if (['clipping', 'card', 'strip'].includes(it.q.kind)) it.T = layoutText(it.q);
    const keys = (ctx.data.cam && ctx.data.cam.length) ? ctx.data.cam : [{ t: 0, x: W / 2, y: FY, z: 1 }];
    cam = keys.map(k => ({ ...k, ease: k.ease === 'cut' ? (p => p >= 1 ? 1 : 0) : (EASE[k.ease] || MO.sineInOut) }));
    caps = ctx.data.caps || []; topbar = ctx.data.topbar;
  },
  draw(c, t, ctx) {
    const camAt = tt => { const k = CAM.at(cam, tt); return k; }, cm = camAt(t);
    const buf = UI.scratch('cv_buf', W, H), g = buf.getContext('2d'); g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, W, H);
    g.save(); g.translate(0, FY - H / 2); CAM.apply(g, cm);
    g.fillStyle = g.createPattern(CL.paperTile('cvdesk', C.desk, { amt: 12, fibers: 320, fiberCol: [110, 95, 70] }), 'repeat');
    const s = 3 / cm.z; g.fillRect(cm.x - W * s, cm.y - H * s, W * 2 * s, H * 2 * s);
    for (const it of items) {
      const q = it.q, D = q.data || {}; if (t < q.at - 1e-6) continue;
      if (q.kind === 'string') { const p = MO.sineInOut(prog(t, q.at, D.dur ?? 0.6)), pts = CL.stringPts(D.a, D.b, D.sag ?? 0.06), L = DG.cum(pts);
        CL.string(g, pts, L, L[L.length - 1] * p, { col: C.red, lw: 6 }); CL.pin(g, D.a[0], D.a[1], C.red); if (p >= 1) CL.pin(g, D.b[0], D.b[1], C.red);
        if (D.label && p >= 1) { const mx = (D.a[0] + D.b[0]) / 2, my = (D.a[1] + D.b[1]) / 2 + Math.hypot(D.b[0] - D.a[0], D.b[1] - D.a[1]) * (D.sag ?? 0.06) * 0.5;
          MD.label(g, D.label, mx, my, { t, at: q.at + (D.dur ?? 0.6), size: D.labelSize ?? 44, r: -0.03, bg: C.red, fg: C.paper, align: 'center' }); }
        continue; }
      if (q.kind === 'circle') { const p = MO.cubicOut(prog(t, q.at, D.dur ?? 0.6)), pts = DG.hand(DG.ellipsePts(D.x, D.y, D.rx, D.ry, -2.6, 1.1, 48), { amp: 3, seed: 11 + it.k }), L = DG.cum(pts);
        g.save(); g.strokeStyle = C.red; g.lineWidth = 8; g.lineCap = 'round'; g.lineJoin = 'round'; DG.drawPartial(g, pts, L, L[L.length - 1] * p); g.restore(); continue; }
      const enter = D.enter ?? (q.at > 0.05 ? 'slide' : 'cut');
      const body = gg => {
        if (q.kind === 'photo') drawPrint(gg, it, t, ctx);
        else if (q.kind === 'cat') drawCat(gg, it, t, ctx);
        else if (q.kind === 'label') MD.label(gg, D.text, 0, 0, { t, at: q.at, size: D.size ?? 48, bg: D.bg === 'red' ? C.red : C.ink, fg: C.paper, align: 'center' });
        else if (q.kind === 'stamp') drawStamp(gg, it, t);
        else if (q.kind === 'blackcard') drawBlackCard(gg, it);
        else if (it.T) drawText(gg, it, t, ctx);
      };
      if (enter === 'slide' && !['label', 'stamp'].includes(q.kind)) CL.slideIn(g, t, q.at, D.x, D.y, D.rot || 0, body, { from: D.from || [160, 420], tilt: 0.16, dur: 0.45, fps: 12 });
      else CL.placed(g, D.x, D.y, D.rot || 0, body);
    }
    g.restore();
    c.fillStyle = C.desk; c.fillRect(0, 0, W, H);
    const [vx, vy] = CAM.velocity(camAt, t);
    if (Math.hypot(vx, vy) >= 1.5) c.drawImage(buf, 0, 0);
    CAM.motionBlur(c, buf, vx * 0.6, vy * 0.6, 7);
    const v = PAINT.cached('cv_vig' + W + 'x' + H, W, H, gg => { const r = gg.createRadialGradient(W / 2, H * 0.45, Math.min(W, H) * 0.42, W / 2, H * 0.45, Math.max(W, H) * 0.66); r.addColorStop(0, 'rgba(40,30,20,0)'); r.addColorStop(1, 'rgba(40,30,20,.32)'); gg.fillStyle = r; gg.fillRect(0, 0, W, H); });
    c.drawImage(v, 0, 0);
    // 顶部标题：黑底撕边标签，关键词荧光黄字
    if (topbar) drawLine(c, topbar.text, topbar.hi || [], W / 2, 246, 50, C.ink, FH, 0);
    // 字幕：黑底撕边条＋纸白字，关键词荧光黄；角色名：红底小标签
    for (const cp of caps) if (t >= cp.t0 && t < cp.t1) {
      if (cp.who) drawLine(c, cp.who, [], W / 2, 1392, 36, C.red, FH, -0.02);
      drawLine(c, cp.text, cp.hi || [], W / 2, 1470, 58, C.ink, FH, 0, 1000);
      break;
    }
  },
};
function drawLine(c, text, hi, x, y, size, bg, fam, r = 0, maxW = 1000) {
  c.save(); c.font = `${size}px ${fam}`; let tw = c.measureText(text).width;
  if (tw + size * 0.9 > maxW) { size = size * (maxW - size * 0.9) / tw; c.font = `${size}px ${fam}`; tw = c.measureText(text).width; }
  const padX = size * 0.45, w = tw + padX * 2, h = size * 1.5, key = 'cvline_' + text + size + bg;
  const sp = PAINT.cached(key, Math.ceil(w), Math.ceil(h), g => { g.fillStyle = bg; CL.tornRect(g, w, h, [...text].length * 5 + 3, 3); g.fill(); });
  c.translate(x, y); c.rotate(r); c.drawImage(sp, -w / 2, -h / 2);
  c.textBaseline = 'middle'; let cx = -w / 2 + padX; const marks = [];
  for (const hword of hi) { const i = text.indexOf(hword); if (i >= 0) marks.push([i, i + hword.length]); }
  [...text].forEach((ch, i) => { c.fillStyle = marks.some(([a, b]) => i >= a && i < b) ? C.yel : C.paper; c.fillText(ch, cx, size * 0.05); cx += c.measureText(ch).width; });
  c.restore();
}
})();
