"""故事道具卡与角色剧照卡（make_card.py 调用）。拟人化猫咪故事靠这些「网感纸件」讲情节，Vox 桌面上它们就是证据。

卡型：scene（角色剧照）chat（聊天记录）moments（动态）memo（会议纪要/通知）diary（日记）hot（热搜榜）。
字段见 make_card.py 开头。所有照片（背景、贴纸、头像、配图）都转灰度网点或灰度，和片子里的照片同一种画面语言；
用到的源图路径写进 sidecar 的 sources，build_episode.py 据此在发布文案里署名。
"""
import json, re
from pathlib import Path

INK_OUTLINE = 'paint-order:stroke;stroke:#fff;stroke-width:7px;stroke-linejoin:round'

# ---------------------------------------------------------------- 角色表
def find_cast(start):
    """从 start 往上找 角色库/角色.json；找不到就用 skill 自带的 assets/角色库。返回 (dict, 角色库目录)。"""
    for d in [Path(start).resolve(), *Path(start).resolve().parents]:
        f = d / '角色库' / '角色.json'
        if f.exists():
            return json.loads(f.read_text()), f.parent
    f = Path(__file__).resolve().parent.parent / 'assets' / '角色库' / '角色.json'
    if f.exists():
        return json.loads(f.read_text()), f.parent
    return {}, None


# ---------------------------------------------------------------- 网点（与引擎 CL.halftone 同算法；透明 PNG 只在猫身上出网点）
HT_JS = r'''
<script>
window.__pending = 0; window.__done = false;
window.htDraw = (cv, uri, o) => {
  window.__pending++;
  const im = new Image();
  im.onload = () => {
    const W = cv.width, H = cv.height, g = cv.getContext('2d');
    const t = document.createElement('canvas'); t.width = W; t.height = H; const tg = t.getContext('2d');
    if (o.fit === 'contain') { const s = Math.min(W / im.width, H / im.height); tg.drawImage(im, (W - im.width * s) / 2, (H - im.height * s) / 2, im.width * s, im.height * s); }
    else { const s = Math.max(W / im.width, H / im.height), sw = W / s, sh = H / s;
      const sx = Math.min(Math.max(im.width * o.fx - sw / 2, 0), im.width - sw), sy = Math.min(Math.max(im.height * o.fy - sh / 2, 0), im.height - sh);
      tg.drawImage(im, sx, sy, sw, sh, 0, 0, W, H); }
    const d = tg.getImageData(0, 0, W, H).data, cell = o.cell, ca = Math.cos(Math.PI / 4), sa = Math.sin(Math.PI / 4), R = Math.hypot(W, H);
    // 自动色阶：取主体（不透明像素）亮度的 2%–98% 拉满。黑猫不再糊成一块黑、白猫不再和纸混在一起
    const hist = new Uint32Array(256); let nPix = 0;
    for (let i = 0; i < d.length; i += 16) if (d[i + 3] > 10) { hist[(d[i] * .3 + d[i + 1] * .59 + d[i + 2] * .11) | 0]++; nPix++; }
    let lo = 0, hi = 255, acc = 0; for (let v = 0; v < 256; v++) { acc += hist[v]; if (acc > nPix * 0.02) { lo = v; break; } }
    acc = 0; for (let v = 255; v >= 0; v--) { acc += hist[v]; if (acc > nPix * 0.02) { hi = v; break; } }
    const span = Math.max(40, hi - lo);
    g.fillStyle = o.paper; g.fillRect(0, 0, W, H); g.fillStyle = o.ink; g.beginPath();
    for (let v = -R; v < R; v += cell) for (let u = -R; u < R; u += cell) {
      const x = W / 2 + u * ca - v * sa, y = H / 2 + u * sa + v * ca; if (x < -cell || y < -cell || x > W + cell || y > H + cell) continue;
      const i = (Math.min(Math.max(y | 0, 0), H - 1) * W + Math.min(Math.max(x | 0, 0), W - 1)) * 4; if (d[i + 3] < 10) continue;
      let L = ((d[i] * .3 + d[i + 1] * .59 + d[i + 2] * .11) - lo) / span; L = Math.min(Math.max((L - .5) * o.contrast + .5, 0), 1);
      const rr = cell * 0.66 * Math.sqrt(1 - L); if (rr < 0.35) continue; g.moveTo(x + rr, y); g.arc(x, y, rr, 0, Math.PI * 2);
    }
    g.fill();
    if (o.mask) { g.globalCompositeOperation = 'destination-in'; g.drawImage(t, 0, 0); g.globalCompositeOperation = 'source-over'; }
    if (--window.__pending === 0) window.__finish();
  };
  im.src = uri;
};
window.__finish = async () => { if (window.__fin) return; window.__fin = true; await document.fonts.ready; (window.__after || []).forEach(f => f()); window.__done = true; };
window.addEventListener('load', () => setTimeout(() => { if (window.__pending === 0) window.__finish(); }, 50));
</script>'''

# ---------------------------------------------------------------- 漫画符号与贴纸（SVG，自己画的，没有版权问题）
SYMBOLS = {
    'sweat':    '<path d="M50 6 C50 6 18 52 18 68 A32 32 0 0 0 82 68 C82 52 50 6 50 6Z" fill="#fff" stroke="{ink}" stroke-width="7"/><path d="M36 64 Q34 76 44 82" fill="none" stroke="{ink}" stroke-width="5" stroke-linecap="round"/>',
    'anger':    '<g fill="none" stroke="{red}" stroke-width="11" stroke-linecap="round"><path d="M38 8 Q40 36 10 38"/><path d="M62 8 Q60 36 90 38"/><path d="M10 62 Q40 64 38 92"/><path d="M90 62 Q60 64 62 92"/></g>',
    'question': '<text x="50" y="86" text-anchor="middle" style="font:900 96px H9;fill:{ink};' + INK_OUTLINE + '">?</text>',
    'exclaim':  '<text x="50" y="86" text-anchor="middle" style="font:900 96px H9;fill:{red};' + INK_OUTLINE + '">!</text>',
    'sparkle':  '<path d="M50 2 C54 38 62 46 98 50 C62 54 54 62 50 98 C46 62 38 54 2 50 C38 46 46 38 50 2Z" fill="#fff" stroke="{ink}" stroke-width="5"/>',
    'gloom':    '<g stroke="{ink}" stroke-width="6" stroke-linecap="round"><path d="M14 8 V70"/><path d="M32 8 V92"/><path d="M50 8 V60"/><path d="M68 8 V86"/><path d="M86 8 V66"/></g>',
    'dots':     '<g fill="{ink}" stroke="#fff" stroke-width="4"><circle cx="18" cy="56" r="10"/><circle cx="50" cy="56" r="10"/><circle cx="82" cy="56" r="10"/></g>',
    'heart':    '<path d="M50 88 C20 66 6 50 6 32 A20 20 0 0 1 50 24 A20 20 0 0 1 94 32 C94 50 80 66 50 88Z" fill="{red}" stroke="#fff" stroke-width="5"/>',
    'shock':    '<g stroke="{ink}" stroke-width="6" stroke-linecap="round">' + ''.join(
        f'<path d="M{50 + 30 * __import__("math").cos(a):.1f} {50 + 30 * __import__("math").sin(a):.1f} L{50 + 48 * __import__("math").cos(a):.1f} {50 + 48 * __import__("math").sin(a):.1f}"/>'
        for a in [i * 0.785 for i in range(8)]) + '</g>',
}
PROPS = {   # viewBox 0 0 200 100（宽是高的两倍；tie / badge / crown / gradcap 用 0 0 100 100）
    'glasses': ('0 0 200 100', '<g fill="rgba(255,255,255,.18)" stroke="{ink}" stroke-width="9"><circle cx="52" cy="54" r="36"/><circle cx="148" cy="54" r="36"/></g><path d="M88 50 Q100 40 112 50" fill="none" stroke="{ink}" stroke-width="8"/>'),
    'shades':  ('0 0 160 40', '<g fill="{ink}"><rect x="0" y="0" width="160" height="10"/><rect x="10" y="10" width="60" height="20"/><rect x="90" y="10" width="60" height="20"/><rect x="20" y="30" width="40" height="10"/><rect x="100" y="30" width="40" height="10"/></g>'
                '<g fill="#fff"><rect x="20" y="10" width="10" height="10"/><rect x="30" y="20" width="10" height="10"/><rect x="100" y="10" width="10" height="10"/><rect x="110" y="20" width="10" height="10"/></g>'),
    'tie':     ('0 0 60 160', '<path d="M18 4 H42 L38 26 H22Z" fill="{red}" stroke="{ink}" stroke-width="4" stroke-linejoin="round"/><path d="M22 26 H38 L50 120 L30 154 L10 120Z" fill="{red}" stroke="{ink}" stroke-width="4" stroke-linejoin="round"/>'
                '<g stroke="{ink}" stroke-width="3" opacity=".5"><path d="M18 60 L44 48"/><path d="M15 88 L47 74"/><path d="M14 116 L48 100"/></g>'),
    'badge':   ('0 0 100 150', '<path d="M30 0 L46 40 M70 0 L54 40" stroke="{red}" stroke-width="5"/><rect x="10" y="40" width="80" height="106" rx="8" fill="#fff" stroke="{ink}" stroke-width="5"/>'
                '<rect x="10" y="40" width="80" height="22" rx="6" fill="{ink}"/><text x="50" y="57" text-anchor="middle" style="font:800 14px H8;fill:#fff">{org}</text>'
                '<rect x="30" y="70" width="40" height="40" fill="#ddd" stroke="{ink}" stroke-width="3"/><text x="50" y="136" text-anchor="middle" style="font:900 20px H9;fill:{ink}">{text}</text>'),
    'crown':   ('0 0 100 70', '<path d="M6 62 L10 18 L32 40 L50 6 L68 40 L90 18 L94 62Z" fill="#DACF08" stroke="{ink}" stroke-width="5" stroke-linejoin="round"/><circle cx="50" cy="44" r="6" fill="{red}"/>'),
    'gradcap': ('0 0 120 80', '<path d="M60 6 L116 28 L60 50 L4 28Z" fill="{ink}" stroke="#fff" stroke-width="3"/><path d="M28 40 V62 Q60 78 92 62 V40 L60 52Z" fill="{ink}"/><path d="M110 30 V60" stroke="#DACF08" stroke-width="4"/><circle cx="110" cy="62" r="5" fill="#DACF08"/>'),
    'mic':     ('0 0 60 120', '<rect x="14" y="4" width="32" height="50" rx="16" fill="{ink}"/><path d="M8 40 Q8 70 30 70 Q52 70 52 40" fill="none" stroke="{ink}" stroke-width="5"/><path d="M30 70 V110 M14 112 H46" stroke="{ink}" stroke-width="6"/>'),
    'phone':   ('0 0 60 110', '<rect x="4" y="4" width="52" height="102" rx="8" fill="{ink}"/><rect x="9" y="14" width="42" height="78" fill="#cfd6d8"/><circle cx="30" cy="99" r="3" fill="#888"/>'),
}


def svg_symbol(name, P):
    if name not in SYMBOLS: raise SystemExit(f'不认识的符号 {name}（可用：{" ".join(SYMBOLS)}）')
    return f'<svg viewBox="0 0 100 100" width="100%" height="100%" style="overflow:visible">{SYMBOLS[name].format(ink=P["ink"], red=P["accent"])}</svg>'


def svg_prop(name, P, text='', org='喵喵公司'):
    if name not in PROPS: raise SystemExit(f'不认识的道具 {name}（可用：{" ".join(PROPS)}）')
    vb, body = PROPS[name]
    return f'<svg viewBox="{vb}" width="100%" style="overflow:visible;display:block">{body.format(ink=P["ink"], red=P["accent"], text=text, org=org)}</svg>'


# ---------------------------------------------------------------- 工具
def avatar_html(name, cx, size=88, radius='14%'):
    """角色头像：角色库里的照片按焦点裁方、转灰度；没有就画一个首字圆。"""
    info = cx['cast'].get(name) or {}
    if info.get('avatar') and cx['cast_dir']:
        f = (cx['cast_dir'] / info['avatar']).resolve()
        if f.exists():
            cx['sources'].append(str(f))
            fx, fy = info.get('avatar_focus', [0.5, 0.4])
            return f'<div style="width:{size}px;height:{size}px;border-radius:{radius};overflow:hidden;flex:none;background:#ccc"><img src="{cx["uri"](f)}" style="width:100%;height:100%;object-fit:cover;object-position:{fx * 100:.0f}% {fy * 100:.0f}%;filter:grayscale(1) contrast(1.15)"></div>'
    return f'<div style="width:{size}px;height:{size}px;border-radius:{radius};flex:none;background:var(--ink);color:var(--surface);display:flex;align-items:center;justify-content:center;font:{size * 0.5:.0f}px H9">{cx["esc"](name[:1])}</div>'


def strike(s):
    """日记里的 ~~删掉的字~~：红色删除线。"""
    return re.sub(r'~~(.+?)~~', lambda m: f'<s style="text-decoration-color:var(--accent);text-decoration-thickness:5px;color:var(--sub)">{m.group(1)}</s>', s)


def ht_canvas(cid, f, cx, w, h, fx=0.5, fy=0.4, fit='cover', mask=False, cell=5, style=''):
    cx['sources'].append(str(f))
    cx['js'].append(f"htDraw(document.getElementById('{cid}'), '{cx['uri'](f)}', {{fx:{fx},fy:{fy},fit:'{fit}',mask:{str(mask).lower()},cell:{cell},contrast:1.32,paper:getComputedStyle(document.getElementById('card')).getPropertyValue('--surface'),ink:getComputedStyle(document.getElementById('card')).getPropertyValue('--ink')}});")
    return f'<canvas id="{cid}" width="{int(w)}" height="{int(h)}" style="{style}"></canvas>'


# ---------------------------------------------------------------- 卡型
def scene(c, P, cx):
    W, H = c['_w'], c['_h']
    parts, n = [], 0
    if c.get('bg'):
        fx, fy = c.get('focus', [0.5, 0.45])
        parts.append(ht_canvas('bg', cx['path'](c['bg']), cx, W, H, fx, fy, style='position:absolute;inset:0'))
    else:
        parts.append('<div style="position:absolute;inset:0;background:var(--bg)"></div>')
    tails = []
    for it in c.get('items', []):
        n += 1
        x, y, rot = it.get('x', 0.5) * W, it.get('y', 0.5) * H, it.get('rot', 0)
        if 'cat' in it:   # 抠图贴纸：白边＋投影，猫身上是网点
            f = cx['path'](it['cat']); iw, ih = cx['size'](f)
            hh = it.get('h', 0.8) * H; ww = hh * iw / ih
            flip = ' scaleX(-1)' if it.get('flip') else ''
            parts.append(f'<div class="stk" style="position:absolute;left:{x - ww / 2:.0f}px;top:{y - hh / 2:.0f}px;width:{ww:.0f}px;height:{hh:.0f}px;transform:rotate({rot}deg){flip};'
                         'filter:drop-shadow(5px 0 0 #fff) drop-shadow(-5px 0 0 #fff) drop-shadow(0 5px 0 #fff) drop-shadow(0 -5px 0 #fff) drop-shadow(3px 9px 10px rgba(0,0,0,.35))">'
                         + ht_canvas(f'cat{n}', f, cx, ww * 1.5, hh * 1.5, fit='contain', mask=True, cell=6, style='width:100%;height:100%') + '</div>')
        elif 'bubble' in it:
            st = it.get('style', 'speech'); fs = it.get('size', 52); bw = max(it.get('w', 0.42) * W, fs * 6.5)   # w＝最大宽度；至少放得下一行五六个字
            shape = {'speech': 'border-radius:44px', 'think': 'border-radius:50%/42%', 'shout': 'clip-path:polygon(0 12%,8% 0,20% 8%,34% 0,48% 9%,62% 0,76% 8%,90% 0,100% 14%,94% 30%,100% 48%,94% 64%,100% 82%,90% 100%,76% 90%,62% 100%,48% 91%,34% 100%,20% 90%,8% 100%,0 86%,6% 66%,0 48%,6% 30%)'}[st]
            pad = '34px 40px' if st != 'shout' else '56px 62px'
            border = 'border:6px solid var(--ink);' if st != 'shout' else ''
            # 气泡按字数自动定宽（w 是最大宽度）：短台词不会被挤成一字一行
            parts.append(f'<div class="bub" id="b{n}" style="position:absolute;left:{x:.0f}px;top:{y:.0f}px;width:max-content;max-width:{bw:.0f}px;transform:translate(-50%,-50%) rotate({rot}deg);background:#fff;{border}{shape};padding:{pad};text-wrap:balance;'
                         f'font:{fs}px/1.32 H8;color:var(--ink);text-align:center;z-index:{20 + n}">{cx["marked"](it["bubble"])}</div>')
            if it.get('to'):
                tails.append((f'b{n}', it['to'][0] * W, it['to'][1] * H, st))
        elif 'symbol' in it:
            s = it.get('s', 0.11) * W
            # 白色外发光：符号压在深色猫毛上也看得见
            parts.append(f'<div style="position:absolute;left:{x - s / 2:.0f}px;top:{y - s / 2:.0f}px;width:{s:.0f}px;height:{s:.0f}px;transform:rotate({rot}deg);z-index:40;filter:drop-shadow(0 0 3px #fff) drop-shadow(0 0 3px #fff) drop-shadow(0 0 2px #fff)">{svg_symbol(it["symbol"], P)}</div>')
        elif 'prop' in it:
            s = it.get('s', 0.2) * W
            parts.append(f'<div style="position:absolute;left:{x - s / 2:.0f}px;top:{y:.0f}px;width:{s:.0f}px;transform:translateY(-50%) rotate({rot}deg);z-index:30;filter:drop-shadow(2px 5px 4px rgba(0,0,0,.3))">{svg_prop(it["prop"], P, cx["esc"](it.get("text", "")), cx["esc"](it.get("org", "喵喵公司")))}</div>')
        elif 'tag' in it:   # Vox 黑底撕边标签：角色名、地点、时间
            parts.append(f'<div class="lab" style="position:absolute;left:{x:.0f}px;top:{y:.0f}px;transform:rotate({rot or -2}deg);z-index:50;font-size:{it.get("size", 50)}px">{cx["marked"](it["tag"])}</div>')
        elif 'text' in it:  # 画面里的手写批注
            parts.append(f'<div style="position:absolute;left:{x:.0f}px;top:{y:.0f}px;transform:translate(-50%,-50%) rotate({rot}deg);font:{it.get("size", 56)}px/1.3 KAI;color:var(--accent);z-index:45;white-space:nowrap;text-shadow:0 0 6px #fff,0 0 6px #fff,0 0 3px #fff">{cx["marked"](it["text"])}</div>')
        else:
            raise SystemExit(f'scene 的 items 里有不认识的元素：{it}')
    if tails:   # 气泡尾巴：从气泡边缘指向说话的猫（排版完成后按实际尺寸画）
        cx['after'].append('''(() => { const card = document.getElementById('card').getBoundingClientRect(), svg = document.getElementById('tails');
  for (const [id, tx, ty, st] of %s) { const b = document.getElementById(id).getBoundingClientRect();
    const cx = b.left + b.width / 2 - card.left, cy = b.top + b.height / 2 - card.top, a = Math.atan2(ty - cy, tx - cx);
    const ex = cx + Math.cos(a) * b.width * 0.36, ey = cy + Math.sin(a) * b.height * 0.36, n = [-Math.sin(a), Math.cos(a)], k = Math.min(b.width, b.height) * 0.16;
    if (st === 'think') { for (let i = 1; i <= 3; i++) { const t = 0.55 + i * 0.14, r = 22 - i * 5; svg.insertAdjacentHTML('beforeend', `<circle cx="${ex + (tx - ex) * t}" cy="${ey + (ty - ey) * t}" r="${r}" fill="#fff" stroke="var(--ink)" stroke-width="6"/>`); } }
    else svg.insertAdjacentHTML('beforeend', `<path d="M${ex + n[0] * k} ${ey + n[1] * k} L${tx} ${ty} L${ex - n[0] * k} ${ey - n[1] * k}Z" fill="#fff" stroke="var(--ink)" stroke-width="6" stroke-linejoin="round"/>`); } })();''' % json.dumps(tails))
    parts.append('<svg id="tails" style="position:absolute;inset:0;z-index:19;overflow:visible" width="100%" height="100%"></svg>')
    return ''.join(parts)


def chat(c, P, cx):
    me = c.get('me')
    rows = []
    for m in c['messages']:
        if 'time' in m:
            rows.append(f'<div class="ct">{cx["esc"](m["time"])}</div>'); continue
        if 'system' in m:
            rows.append(f'<div class="ct sys">{cx["marked"](m["system"])}</div>'); continue
        who, mine = m['who'], m['who'] == me
        body = cx['marked'](m['text'])
        if m.get('image'):
            f = cx['path'](m['image']); cx['sources'].append(str(f))
            body = f'<img src="{cx["uri"](f)}" style="max-width:360px;max-height:300px;display:block;filter:grayscale(1) contrast(1.15);border-radius:10px">'
        name = '' if mine else f'<div class="cn">{cx["esc"](who)}</div>'
        rows.append(f'<div class="cm {"me" if mine else ""}">{avatar_html(who, cx)}<div class="cb">{name}<div class="bb">{body}</div></div></div>')
    return f'''<style>
#card{{background:#E6E3DB}}
.ch{{display:flex;align-items:center;padding:24px 34px;background:var(--surface);border-bottom:2px solid #d5d0c4;font:44px H8}}
.ch .t{{flex:1;text-align:center}} .ch i{{font:48px H7;font-style:normal;color:var(--sub);width:60px}}
.cl{{flex:1;padding:18px 34px;display:flex;flex-direction:column;gap:22px;overflow:hidden}}
.ct{{align-self:center;font:30px H5;color:#8e887c;padding:2px 14px}} .ct.sys{{background:rgba(0,0,0,.06);border-radius:8px}}
.cm{{display:flex;gap:20px;align-items:flex-start}} .cm.me{{flex-direction:row-reverse}}
.cb{{max-width:74%;display:flex;flex-direction:column}} .cm.me .cb{{align-items:flex-end}}
.cn{{font:28px H5;color:#8e887c;margin:0 0 6px 4px}}
.bb{{background:#fff;border-radius:14px;padding:18px 26px;font:42px/1.42 H7;color:var(--ink);box-shadow:0 1px 0 rgba(0,0,0,.08);text-wrap:pretty}}
.cm.me .bb{{background:var(--ink);color:var(--surface)}} .cm.me .bb .mk{{color:#E2D51A}}
.cbar{{height:96px;background:var(--surface);border-top:2px solid #d5d0c4;display:flex;align-items:center;gap:20px;padding:0 30px}}
.cbar div{{flex:1;height:58px;background:#fff;border-radius:10px}} .cbar b{{width:54px;height:54px;border:4px solid #8e887c;border-radius:50%}}
</style>
<div class="ch"><i>‹</i><div class="t">{cx["esc"](c.get("title", "聊天"))}</div><i style="text-align:right">···</i></div>
<div class="cl">{"".join(rows)}</div><div class="cbar"><b></b><div></div><b></b></div>'''


def moments(c, P, cx):
    img = ''
    if c.get('image'):
        f = cx['path'](c['image']); fx, fy = c.get('focus', [0.5, 0.45])
        img = ht_canvas('mi', f, cx, 640, 480, fx, fy, cell=4, style='display:block;margin-top:20px;width:640px;height:480px')
    likes = f'<div class="lk"><span style="color:var(--accent)">♥</span> {cx["esc"]("，".join(c["likes"]))}</div>' if c.get('likes') else ''
    cm = ''.join(f'<div><b>{cx["esc"](w)}</b>：{cx["marked"](t)}</div>' for w, t in c.get('comments', []))
    cm = f'<div class="cmt">{cm}</div>' if cm else ''
    return f'''<style>
.mo{{display:flex;gap:28px;padding:56px 56px 60px}} .mo .nm{{font:46px H8;color:#4d5f7a;margin-bottom:10px}}
.mo .tx{{font:54px/1.45 H7;color:var(--ink)}} .mo .tm{{font:30px H5;color:#9a9488;margin-top:18px;display:flex;justify-content:space-between}}
.lk,.cmt{{background:#ECE8DF;font:34px/1.5 H7;color:#4d5f7a;padding:12px 20px}} .lk{{margin-top:16px;border-bottom:2px solid #ddd8cc}}
.cmt div{{color:var(--ink);font:34px/1.5 H5}} .cmt b{{color:#4d5f7a;font-family:H7}}
</style>
<div class="mo">{avatar_html(c["who"], cx, 110)}<div style="flex:1"><div class="nm">{cx["esc"](c["who"])}</div><div class="tx">{cx["marked"](c["text"])}</div>{img}
<div class="tm"><span>{cx["esc"](c.get("time", "刚刚"))}</span><span style="font:40px H9;color:#4d5f7a">··</span></div>{likes}{cm}</div></div>'''


def memo(c, P, cx):
    org = c.get('org', '喵喵公司')
    meta = ''.join(f'<tr><td class="k">{cx["esc"](k)}</td><td>{cx["marked"](v)}</td></tr>' for k, v in c.get('meta', []))
    items = ''.join(f'<li>{cx["marked"](t)}</li>' for t in c.get('items', []))
    stamp_txt = cx['esc'](c.get('stamp', org))
    stamp = f'''<svg viewBox="0 0 200 200" width="250" height="250" style="position:absolute;right:70px;bottom:46px;transform:rotate(-14deg);opacity:.82;mix-blend-mode:multiply">
<defs><path id="arc" d="M30 100 A70 70 0 1 1 170 100"/></defs><circle cx="100" cy="100" r="88" fill="none" stroke="{P["accent"]}" stroke-width="8"/>
<text style="font:900 30px H9;fill:{P["accent"]};letter-spacing:6px"><textPath href="#arc" startOffset="50%" text-anchor="middle">{stamp_txt}</textPath></text>
<path d="M100 82 L107 102 L128 102 L111 114 L118 134 L100 122 L82 134 L89 114 L72 102 L93 102Z" fill="{P["accent"]}"/><text x="100" y="166" text-anchor="middle" style="font:800 22px H8;fill:{P["accent"]}">{cx["esc"](c.get("stamp_sub", "专用章"))}</text></svg>''' if c.get('stamp', True) is not False else ''
    return f'''<style>
.mh{{text-align:center;padding:54px 60px 18px;border-bottom:7px double var(--accent);margin:0 50px}}
.mh .o{{font:66px H9;color:var(--accent);letter-spacing:10px}} .mh .t{{font:46px H8;margin-top:8px;letter-spacing:6px}}
.mt{{margin:26px 70px 0;border-collapse:collapse;font:38px/1.5 H7}} .mt td{{padding:6px 0}} .mt .k{{color:var(--sub);padding-right:28px;white-space:nowrap}}
.mi{{margin:22px 70px 290px 120px;font:44px/1.6 H7}} .mi li{{margin:6px 0}}
.sg{{position:absolute;left:70px;bottom:60px;font:36px KAI;color:var(--sub)}}
</style>
<div class="mh"><div class="o">{cx["esc"](org)}</div><div class="t">{cx["esc"](c.get("title", "会议纪要"))}</div></div>
<table class="mt">{meta}</table>{f'<ol class="mi">{items}</ol>' if c.get('numbered', True) else f'<ul class="mi" style="list-style:none;margin-left:70px">{items}</ul>'}<div class="sg">{cx["esc"](c.get("sign", ""))}</div>{stamp}'''


def diary(c, P, cx):
    head = f'{cx["esc"](c.get("date", ""))}　　天气：{cx["esc"](c.get("weather", "晴"))}'
    paw = cx['PAW'].format(s=70, c=P['sub'])
    return f'''<style>
#card{{background:#F4F0E4;background-image:repeating-linear-gradient(0deg,transparent 0 92px,rgba(80,140,200,.30) 92px 95px);background-position:0 26px}}
.dh{{padding:46px 80px 0 120px;font:40px KAI;color:var(--sub);height:140px}} .dm{{position:absolute;left:96px;top:0;bottom:0;width:4px;background:var(--accent);opacity:.5}}
.dt{{padding:0 80px 190px 120px;font:62px/95px KAI;color:var(--ink)}} .dt .mk{{color:var(--accent);font-family:KAI;background:linear-gradient(transparent 58%,rgba(218,207,8,.75) 58%)}}
.dw{{position:absolute;right:80px;bottom:56px;font:48px KAI;color:var(--sub);display:flex;align-items:center;gap:14px;opacity:.85}}
</style><div class="dm"></div><div class="dh">{head}</div><div class="dt">{strike(cx["marked"](c["text"]))}</div>
<div class="dw">—— {cx["esc"](c.get("who", ""))}的日记 {paw}</div>'''


def hot(c, P, cx):
    tagc = {'爆': P['accent'], '热': '#E07A2E', '新': '#3E7C8C', '沸': P['accent2']}
    rows = ''
    for i, it in enumerate(c['items'], 1):
        title, heat, tag = (list(it) + ['', ''])[:3]
        num = f'<b style="color:{P["accent"] if i <= 3 else "#9a9488"}">{i}</b>'
        t = f'<span class="tg" style="background:{tagc.get(tag, P["sub"])}">{cx["esc"](tag)}</span>' if tag else ''
        rows += f'<div class="hr">{num}<div class="hn">{cx["marked"](title)}</div><span class="hv">{cx["esc"](heat)}</span>{t}</div>'
    return f'''<style>
.hh{{display:flex;align-items:center;gap:20px;padding:40px 56px 26px;font:60px H9;border-bottom:4px solid var(--ink)}} .hh small{{font:32px H5;color:var(--sub);margin-left:auto}}
.hr{{display:flex;align-items:center;gap:26px;padding:0 56px;height:118px;border-bottom:2px solid #ddd8cc}} .hr b{{font:56px NUM;width:56px;text-align:center}}
.hn{{flex:1;font:46px H7;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}} .hv{{font:32px H5;color:#9a9488}}
.tg{{font:30px H8;color:#fff;padding:2px 10px;border-radius:8px}} #card{{padding-bottom:40px}}
</style><div class="hh">{cx["PAW"].format(s=58, c=P["accent"])}{cx["esc"](c.get("title", "喵博热搜"))}<small>{cx["esc"](c.get("sub", "实时"))}</small></div>{rows}'''


TYPES = {'scene': scene, 'chat': chat, 'moments': moments, 'memo': memo, 'diary': diary, 'hot': hot}
