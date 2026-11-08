// 张力层（cat-social-psych 新增）：在语法画面之上、标题栏和字幕之下，给内容区加「情绪」。标题和字幕不跟着抖。
// spec.fx = {
//   vignette: 0..1,          // 四角压暗（悬疑 0.55、紧张 0.4、平叙 0.2）
//   creep: 0..0.1,           // 整镜缓慢推近的幅度（悬疑、紧张时用；0.05 = 推近 5%）
//   events: [                // 时间都是片内秒
//     {t, type:'shake', dur:0.35, amp:16},     // 震屏（重击、揭晓）
//     {t, type:'punch', dur:0.35, amp:0.05},   // 镜头冲一下再回来
//     {t, type:'flash', dur:0.18},             // 白闪
//     {t, type:'blackout', dur:0.3},           // 揭晓前的短暂黑场
//     {t, type:'pulse', dur:0.7},              // 四角红色脉冲（危险、警告）
//     {t, type:'glitch', dur:0.3},             // 故障撕裂（反转）
//     {t, type:'slam', text:'【37%】', sub:'的回答跟着错了', dur:99}   // 大字砸进画面：黑底撕边条＋白字，【】里黄色
//   ]
// }
// 一拍二（12fps）步进抖动，和 Vox 的手工感一致；所有随机都由时间决定，同一时刻渲两次逐像素一致。
(() => {
const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
const ease = p => p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2;
const backOut = p => { const s = 2.2, q = p - 1; return 1 + (s + 1) * q * q * q + s * q * q; };
const noise = (t, k) => { const q = Math.floor(t * 24) / 24; return Math.sin(q * 91.7 + k * 13.1) * 0.6 + Math.sin(q * 53.3 + k * 7.7 + 1.7) * 0.4; };
const segs = s => { const out = []; let hi = false; for (const ch of String(s || '')) { if (ch === '【') { hi = true; continue; } if (ch === '】') { hi = false; continue; } out.push({ ch, hi }); } return out; };

window.TENSION = {
  init(fx, ctx) {
    const { W, H, box, u, dur } = ctx;
    const pal = ctx.pal || { bg: '#E4DDCF', ink: '#171716', surface: '#EEEDEB', accent: '#B8433F' };
    const evs = (fx.events || []).map(e => ({ dur: 0.35, ...e }));
    const buf = document.createElement('canvas'); buf.width = W; buf.height = H; const bg = buf.getContext('2d');
    const cx = box.x + box.w / 2, cy = box.y + box.h / 2;
    const active = (e, t) => t >= e.t && t < e.t + e.dur;
    const local = (e, t) => clamp((t - e.t) / e.dur);
    // 震屏也由「重击」类事件自动带出：slam 自带一次
    for (const e of evs) if (e.type === 'slam' && !evs.some(x => x.type === 'shake' && Math.abs(x.t - e.t) < 0.05)) evs.push({ t: e.t, type: 'shake', dur: 0.3, amp: 14 });
    return (c, t) => {
      // ---- 变换：推近 ＋ 冲一下 ＋ 抖 ＋ 故障 ----
      let s = 1 + (fx.creep || 0) * ease(clamp(t / Math.max(0.5, dur))), dx = 0, dy = 0, glitch = null;
      for (const e of evs) {
        if (!active(e, t)) continue;
        const p = local(e, t);
        if (e.type === 'shake') { const a = (e.amp || 16) * u * Math.pow(1 - p, 1.6); dx += a * noise(t, 1); dy += a * noise(t, 2); }
        if (e.type === 'punch') s += (e.amp || 0.05) * Math.sin(Math.PI * p) * (1 - p * 0.3);
        if (e.type === 'glitch') glitch = { p, e };
      }
      if (s !== 1 || dx || dy || glitch) {
        s += (Math.abs(dx) + Math.abs(dy)) * 2 / Math.min(box.w, box.h);   // 抖的时候放大一点，边缘不露底
        bg.setTransform(1, 0, 0, 1, 0, 0); bg.clearRect(0, 0, W, H); bg.drawImage(c.canvas, 0, 0);
        c.save(); c.beginPath(); c.rect(box.x, box.y, box.w, box.h); c.clip();
        c.fillStyle = pal.bg; c.fillRect(box.x, box.y, box.w, box.h);
        c.translate(cx + dx, cy + dy); c.scale(s, s); c.translate(-cx, -cy);
        if (glitch) {                                                   // 横向撕裂：一条条错开
          const n = 9; for (let i = 0; i < n; i++) {
            const y0 = box.y + box.h * i / n, hh = box.h / n, off = noise(t * 3, i + 3) * 60 * u * (1 - glitch.p);
            c.drawImage(buf, box.x, y0, box.w, hh, box.x + off, y0, box.w, hh);
          }
          c.globalAlpha = 0.35 * (1 - glitch.p); c.globalCompositeOperation = 'lighter';
          c.drawImage(buf, 14 * u * (1 - glitch.p), 0); c.globalCompositeOperation = 'source-over'; c.globalAlpha = 1;
        } else c.drawImage(buf, 0, 0);
        c.restore();
      }
      c.save(); c.beginPath(); c.rect(box.x, box.y, box.w, box.h); c.clip();
      // ---- 四角压暗（情绪）＋ 红色脉冲 ----
      const v = fx.vignette || 0;
      if (v > 0) {
        const g = c.createRadialGradient(cx, cy, Math.min(box.w, box.h) * 0.32, cx, cy, Math.hypot(box.w, box.h) * 0.58);
        g.addColorStop(0, 'rgba(10,10,10,0)'); g.addColorStop(1, `rgba(10,10,10,${v})`); c.fillStyle = g; c.fillRect(box.x, box.y, box.w, box.h);
      }
      for (const e of evs) {
        if (!active(e, t)) continue; const p = local(e, t);
        if (e.type === 'pulse') {
          const a = 0.55 * Math.sin(Math.PI * p); const g = c.createRadialGradient(cx, cy, Math.min(box.w, box.h) * 0.3, cx, cy, Math.hypot(box.w, box.h) * 0.6);
          g.addColorStop(0, 'rgba(160,20,20,0)'); g.addColorStop(1, `rgba(170,25,25,${a})`); c.fillStyle = g; c.fillRect(box.x, box.y, box.w, box.h);
        }
        if (e.type === 'blackout') { const a = 0.92 * Math.min(1, p / 0.25, (1 - p) / 0.35); c.fillStyle = `rgba(8,8,8,${a})`; c.fillRect(box.x, box.y, box.w, box.h); }
      }
      // ---- 大字砸入 ----
      for (const e of evs) {
        if (e.type !== 'slam' || t < e.t || t >= e.t + (e.dur || 99)) continue;
        const p = clamp((Math.floor((t - e.t) * 12) / 12) / 0.25), k = 1.7 - 0.7 * backOut(p);   // 0.25 秒内从 1.7 倍砸到 1 倍（12fps 步进）
        const sg = segs(e.text); let size = (sg.length <= 4 ? 320 : 230) * u; c.font = `${size}px "PuHui-Black"`;
        const meas = () => sg.reduce((a, q) => a + c.measureText(q.ch).width, 0);
        while (meas() > box.w * 0.78 && size > 60 * u) { size *= 0.92; c.font = `${size}px "PuHui-Black"`; }
        const tw = meas(), sub = e.sub || '';
        let subSize = Math.round(size * 0.24), subW = 0;
        if (sub) {                                                       // 小字太长就缩小，黑条按大字和小字里更宽的那个定宽
          c.font = `${subSize}px "PuHui-Bold"`; subW = c.measureText(sub).width;
          while (subW > box.w * 0.74 && subSize > 30 * u) { subSize *= 0.92; c.font = `${subSize}px "PuHui-Bold"`; subW = c.measureText(sub).width; }
          c.font = `${size}px "PuHui-Black"`;
        }
        c.fillStyle = `rgba(10,10,10,${0.35 * Math.min(1, p * 2)})`; c.fillRect(box.x, box.y, box.w, box.h);
        c.save(); c.translate(cx, cy); c.rotate(-0.035); c.scale(k, k);
        const sw = Math.max(tw, subW) + 120 * u, sh = size * 1.25 + (sub ? subSize * 1.6 : 0);
        c.fillStyle = pal.ink; c.beginPath();                            // 黑底撕边条
        const jag = i => (Math.sin(i * 12.9898) * 43758.5453 % 1) * 10 * u;
        c.moveTo(-sw / 2, -sh / 2); for (let i = 0; i <= 24; i++) c.lineTo(-sw / 2 + sw * i / 24, -sh / 2 + jag(i));
        for (let i = 0; i <= 24; i++) c.lineTo(sw / 2 - sw * i / 24, sh / 2 - jag(i + 40)); c.closePath(); c.fill();
        let x = -tw / 2; c.textBaseline = 'alphabetic';
        for (const q of sg) { c.fillStyle = q.hi ? '#E2D51A' : '#FFFFFF'; c.fillText(q.ch, x, -sh / 2 + size * 1.02); x += c.measureText(q.ch).width; }
        if (sub) { c.font = `${subSize}px "PuHui-Bold"`; c.fillStyle = pal.surface; const sw2 = c.measureText(sub).width; c.fillText(sub, -sw2 / 2, sh / 2 - subSize * 0.7); }
        c.restore();
      }
      // ---- 白闪 ----
      for (const e of evs) if (e.type === 'flash' && active(e, t)) { c.fillStyle = `rgba(255,255,255,${0.85 * (1 - local(e, t))})`; c.fillRect(box.x, box.y, box.w, box.h); }
      c.restore();
    };
  },
};
})();
