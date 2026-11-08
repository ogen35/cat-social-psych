// 抖音竖屏版式层（cat-social-psych 新增）：顶部标题栏 + 底部字幕，画在语法画面之上。
// spec.overlay = {
//   tag:   '社会心理学 · 第6章',            // 标题上方的小胶囊（可空）
//   title: '你家猫【装没听见】？',           // 顶部大标题，【】里的字用高亮色；最多两行，放不下自动缩字号
//   titleIn: true,                          // true = 本镜开头标题弹入（换了标题的那一镜才写 true，连续同标题的镜头写 false 免得闪）
//   subs:  [{from: 0, to: 1.8, text: '这是一句【字幕】'}],   // 片内秒；【】高亮
//   style: {title, hi, sub, stroke, tagBg, tagFg}           // 可选，不写从 spec.theme 派生
// }
// 位置：标题落在 safe.top 带里（贴着内容框上沿），字幕落在 safe.bottom 带的上部（抖音底部 UI 从约 H−420 起，字幕在它上面）。
// 文字先画到离屏画布再贴回主画布：audit 只查语法自己的版面，不把版式层当成「压进安全区的字」。
(() => {
const parse = s => { const out = []; let hi = false; for (const ch of String(s || '')) { if (ch === '【') { hi = true; continue; } if (ch === '】') { hi = false; continue; } out.push({ ch, hi }); } return out; };
// 按宽度断行（逐字量），返回 [[{ch,hi,w}...], ...]
function wrap(g, segs, maxW) {
  const lines = [[]]; let w = 0;
  for (const s of segs) { const cw = g.measureText(s.ch).width;
    if (w + cw > maxW && lines[lines.length - 1].length) { lines.push([]); w = 0; if (/[，。！？、,.!?\s]/.test(s.ch)) continue; }
    lines[lines.length - 1].push({ ...s, w: cw }); w += cw; }
  return lines;
}
const lineW = l => l.reduce((a, s) => a + s.w, 0);
function drawLine(g, line, cx, y, col, hi, stroke, sw) {
  let x = cx - lineW(line) / 2;
  if (stroke) { g.lineWidth = sw; g.strokeStyle = stroke; g.lineJoin = 'round'; for (const s of line) { g.strokeText(s.ch, x, y); x += s.w; } x = cx - lineW(line) / 2; }
  for (const s of line) { g.fillStyle = s.hi ? hi : col; g.fillText(s.ch, x, y); x += s.w; }
}
// 在 maxLines 行内放下：从 size 起每次缩 6%
function fitLines(g, segs, maxW, size, font, maxLines, min) {
  let s = size, lines;
  for (;;) { g.font = `${s}px ${font}`; lines = wrap(g, segs, maxW); if (lines.length <= maxLines || s <= min) break; s = Math.round(s * 0.94); }
  // 两行时把两行排匀：不留「选？」这种只有一两个字的孤行
  if (lines.length === 2) {
    const all = lines.flat(), tot = all.reduce((a, c) => a + c.w, 0);
    // 优先在中间附近的标点处断（「明知是错的，/ 你也会跟着选？」），两行都放得下才用
    let best = null;
    all.forEach((c, i) => { if (!/[，,、：:；;？?！!。]/.test(c.ch) || i < all.length * 0.2 || i > all.length * 0.8) return;   // 句中的问号、感叹号也能断：「以为会难过一辈子？/ 你高估了」
      const a1 = all.slice(0, i + 1), a2 = all.slice(i + 1), w1 = lineW(a1), w2 = lineW(a2);
      if (w1 <= maxW && w2 <= maxW && (!best || Math.abs(w1 - w2) < best.d)) best = { l: [a1, a2], d: Math.abs(w1 - w2) }; });
    if (best) lines = best.l;
    else for (let w = tot / 2; w <= maxW; w += s * 0.5) { const t = wrap(g, segs, w); if (t.length === 2) { lines = t; break; } }   // 没有合适的标点：两行排匀
  }
  return { lines: lines.slice(0, maxLines), size: s };
}
window.DOUYIN = {
  init(ov, ctx) {
    const { W, H, safe, pal } = ctx, u = ctx.u;
    const P = pal || { ink: '#171716', surface: '#F6F4EE', accent: '#C4552D', bg: '#E4DDCF' };
    const dark = PAL.lum(safe.fill || P.ink) < 0.3;
    const st = { title: dark ? '#FFFFFF' : P.ink, hi: '#E2D51A', sub: '#FFFFFF', stroke: 'rgba(10,10,10,.92)', tagBg: P.accent, tagFg: '#FFFFFF', ...(ov.style || {}) };
    if (!dark && !(ov.style && ov.style.hi)) st.hi = P.accent;
    const buf = document.createElement('canvas'); buf.width = W; buf.height = H; const g = buf.getContext('2d');
    const T = safe.top, B = safe.bottom, padX = 60 * u;
    // 标题版面一次算好
    let tl = null;
    if (ov.title && T > 120 * u) { g.font = `80px "PuHui-Black"`; tl = fitLines(g, parse(ov.title), W - padX * 2, Math.round(84 * u), '"PuHui-Black"', 2, Math.round(52 * u)); }
    const subs = (ov.subs || []).map(s => ({ ...s, segs: parse(s.text) }));
    return (c, t) => {
      g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, W, H); g.textBaseline = 'alphabetic';
      // ---- 顶部：标签胶囊 + 大标题 ----
      if (tl) {
        const k = ov.titleIn ? MO.backOut(U.clamp(MO.step(t + 1e-6, 12) / 0.35)) : 1, a = ov.titleIn ? U.clamp(MO.step(t + 1e-6, 12) / 0.15) : 1;
        const lh = tl.size * 1.22, base = T - 44 * u - (tl.lines.length - 1) * lh;
        g.save(); g.globalAlpha = a; g.translate(W / 2, base - lh / 2); g.scale(k, k); g.translate(-W / 2, -(base - lh / 2));
        g.font = `${tl.size}px "PuHui-Black"`;
        tl.lines.forEach((ln, i) => drawLine(g, ln, W / 2, base + i * lh, st.title, st.hi, dark ? null : null, 0));
        g.restore();
        if (ov.tag) { const fs = Math.round(34 * u); g.font = `${fs}px "PuHui-Bold"`; const tw = g.measureText(ov.tag).width, ph = fs * 1.6, py = base - tl.size * 0.95 - 22 * u - ph;
          if (py > 96 * u) { g.globalAlpha = a; g.fillStyle = st.tagBg; const px = W / 2 - tw / 2 - 26 * u; g.beginPath(); g.roundRect(px, py, tw + 52 * u, ph, ph / 2); g.fill();
            g.fillStyle = st.tagFg; g.fillText(ov.tag, W / 2 - tw / 2, py + ph / 2 + fs * 0.36); g.globalAlpha = 1; } }
      }
      // ---- 底部：字幕 ----
      const cur = subs.find(s => t >= s.from - 1e-6 && t < s.to);
      if (cur && B > 0) {
        const r = fitLines(g, cur.segs, W - padX * 2, Math.round(58 * u), '"PuHui-Heavy"', 2, Math.round(40 * u));
        g.font = `${r.size}px "PuHui-Heavy"`;
        const y0 = H - B + 40 * u + r.size;
        r.lines.forEach((ln, i) => drawLine(g, ln, W / 2, y0 + i * r.size * 1.25, st.sub, st.hi, st.stroke, 9 * u));
      }
      c.drawImage(buf, 0, 0);
    };
  },
};
})();
