"""涂鸦层：画在 1080×1920 的高清层上（像素画放大之后），手写粗体字 + 白描边、马克笔高亮、手抖的线、箭头、贴纸、云朵气泡、取景框。
像素负责角色和场景，涂鸦负责文字和标注：字清楚，又有手账感。坐标一律是成片像素（1080×1920）。"""
import math, random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

FONTS = Path(__file__).resolve().parent / 'fonts'
INK, WHITE = (36, 32, 44), (255, 255, 255)
TOMATO, TEAL, YOU = (229, 83, 60), (44, 150, 132), (245, 194, 71)
_cache = {}


def font(size, kind='kuaile'):
    key = (size, kind)
    if key not in _cache:
        f = {'kuaile': 'ZCOOLKuaiLe-Regular.ttf', 'smiley': 'SmileySans-Oblique.ttf'}[kind]
        _cache[key] = ImageFont.truetype(str(FONTS / f), size)
    return _cache[key]


_NOTDEF = {}


def _has(f, ch):
    """字体里有没有这个字（缺字时 Pillow 会画出 .notdef 方块）。"""
    if ch.isspace(): return True
    k = (f.path, f.size)
    if k not in _NOTDEF: _NOTDEF[k] = (bytes(f.getmask('\ue000')), {})
    nd, memo = _NOTDEF[k]
    if ch not in memo: memo[ch] = bytes(f.getmask(ch)) != nd
    return memo[ch]


def _runs(s, f):
    """按字体覆盖把字符串切段：站酷快乐体缺的字（≠ ★ → ① ② 等）换成得意黑，反之亦然。
    快乐体的阿拉伯数字太花（「0」像方框，「100」读成「1口口」），数字一律用得意黑。"""
    fb = font(f.size, 'smiley' if 'KuaiLe' in f.path else 'kuaile')
    out = []
    for ch in s:
        ff = fb if ('KuaiLe' in f.path and ch.isdigit()) else (f if _has(f, ch) or not _has(fb, ch) else fb)
        if out and out[-1][1] is ff: out[-1][0] += ch
        else: out.append([ch, ff])
    return out


def tlen(d, s, f):
    """带缺字回退的字宽。"""
    return sum(d.textlength(r, font=ff) for r, ff in _runs(s, f))


def tdraw(d, xy, s, f, **kw):
    """带缺字回退的写字：各段按主字体的基线对齐。"""
    x, y = xy; base = y + f.getmetrics()[0]
    for r, ff in _runs(s, f):
        d.text((x, base), r, font=ff, anchor='ls', **kw); x += d.textlength(r, font=ff)


def _jit(rng, a): return rng.uniform(-a, a)


def wobble_line(img, pts, col=INK, width=6, seed=0, amp=2.5, step=26):
    """手抖的线：沿途每 step 像素加一点随机偏移。"""
    rng = random.Random(seed); d = ImageDraw.Draw(img); out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        for i in range(n): u = i / n; out.append((x0 + (x1 - x0) * u + _jit(rng, amp), y0 + (y1 - y0) * u + _jit(rng, amp)))
    out.append(pts[-1]); d.line(out, fill=col, width=width, joint='curve')
    for x, y in (out[0], out[-1]): d.ellipse([x - width / 2, y - width / 2, x + width / 2, y + width / 2], fill=col)


def wobble_box(img, x0, y0, x1, y1, col=INK, width=6, fill=None, seed=0, shadow=None):
    rng = random.Random(seed); d = ImageDraw.Draw(img)
    c = [(x0 + _jit(rng, 4), y0 + _jit(rng, 4)), (x1 + _jit(rng, 4), y0 + _jit(rng, 4)), (x1 + _jit(rng, 4), y1 + _jit(rng, 4)), (x0 + _jit(rng, 4), y1 + _jit(rng, 4))]
    if shadow: d.polygon([(x + 10, y + 10) for x, y in c], fill=shadow)
    if fill: d.polygon(c, fill=fill)
    wobble_line(img, c + [c[0]], col, width, seed + 1)


def marker(img, x0, y0, x1, y1, col=(250, 214, 70), seed=0):
    """马克笔高亮：一道歪一点、两头毛糙的粗色块，画在字底下。"""
    rng = random.Random(seed); d = ImageDraw.Draw(img, 'RGBA'); h = y1 - y0
    pts = [(x0 - 8, y0 + h * .25 + _jit(rng, 4)), (x1 + 10, y0 + h * .15 + _jit(rng, 4)), (x1 + 6, y1 - h * .1 + _jit(rng, 4)), (x0 - 12, y1 + _jit(rng, 4))]
    d.polygon(pts, fill=col + (200,))


def text(img, s, x, y, size=72, col=INK, hi=None, hcol=TOMATO, stroke=9, scol=WHITE, align='c', kind='kuaile', mark=None, rot=0.0, shadow=None, maxw=None):
    """手写粗体字（白色描边，压在任何背景上都清楚）。hi：要标红的词（可多个）；mark：要画马克笔底的词；maxw：太长就缩字号。"""
    d0 = ImageDraw.Draw(img)
    while maxw and size > 28 and tlen(d0, s, font(size, kind)) > maxw: size -= 2
    f = font(size, kind)
    parts = [(s, col)]
    if hi:
        parts = []; rest = s
        for h in ([hi] if isinstance(hi, str) else hi):
            if h in rest: a, rest = rest.split(h, 1); parts += [(a, col), (h, hcol)]
        parts += [(rest, col)]
    tw = sum(tlen(d0, p, f) for p, _ in parts); pad = stroke + 30
    layer = Image.new('RGBA', (int(tw) + pad * 2, int(size * 1.4) + pad * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    xx = pad
    if mark:
        for p, _ in parts:
            w = tlen(d, p, f)
            if p == mark or (isinstance(mark, (list, tuple)) and p in mark): marker(layer, xx, pad + size * .55, xx + w, pad + size * 1.15, seed=len(p))
            xx += w
        xx = pad
    if shadow:
        sx = pad
        for p, c in parts: tdraw(d, (sx + 6, pad + 6), p, f, fill=shadow, stroke_width=stroke, stroke_fill=shadow); sx += tlen(d, p, f)
    for p, c in parts: tdraw(d, (xx, pad), p, f, fill=c, stroke_width=stroke, stroke_fill=scol); xx += tlen(d, p, f)
    if rot: layer = layer.rotate(rot, resample=Image.BICUBIC, expand=True)
    x0 = x - layer.width / 2 if align == 'c' else (x - pad if align == 'l' else x - layer.width + pad)
    img.paste(layer, (int(x0), int(y - pad)), layer)
    return tw


def sticker(img, s, x, y, size=56, bg=YOU, fg=INK, rot=-3, seed=0):
    """贴纸标签：歪一点的色块 + 手抖描边 + 字。"""
    f = font(size); tw = tlen(ImageDraw.Draw(img), s, f)
    layer = Image.new('RGBA', (int(tw) + 80, size + 70), (0, 0, 0, 0))
    wobble_box(layer, 20, 18, tw + 56, size + 44, INK, 5, bg, seed, shadow=(0, 0, 0, 60))
    tdraw(ImageDraw.Draw(layer), (38, 24), s, f, fill=fg)
    layer = layer.rotate(rot, resample=Image.BICUBIC, expand=True)
    img.paste(layer, (int(x - layer.width / 2), int(y - layer.height / 2)), layer)


def arrow(img, p0, p1, col=INK, width=7, seed=0, bend=0.25):
    """手画箭头：微弯的线 + 两笔箭头。"""
    (x0, y0), (x1, y1) = p0, p1; mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    nx, ny = -(y1 - y0), (x1 - x0); L = math.hypot(nx, ny) or 1
    cx, cy = mx + nx / L * bend * math.hypot(x1 - x0, y1 - y0), my + ny / L * bend * math.hypot(x1 - x0, y1 - y0)
    pts = [((1 - u) ** 2 * x0 + 2 * (1 - u) * u * cx + u * u * x1, (1 - u) ** 2 * y0 + 2 * (1 - u) * u * cy + u * u * y1) for u in [i / 12 for i in range(13)]]
    wobble_line(img, pts, col, width, seed, amp=1.5, step=40)
    ang = math.atan2(y1 - pts[-3][1], x1 - pts[-3][0])
    for s in (-1, 1):
        a = ang + math.pi + s * 0.5; wobble_line(img, [(x1, y1), (x1 + 38 * math.cos(a), y1 + 38 * math.sin(a))], col, width, seed + s, amp=1)


def bubble(img, s, x, y, size=52, think=False, tail=None, fill=WHITE, seed=0, maxw=None):
    """对白气泡（圆角、手抖描边）/ 想法气泡（云朵 + 小圆点尾巴）。(x, y) 是气泡中心。"""
    f = font(size); d = ImageDraw.Draw(img); lines = s.split('\n')
    tw = max(tlen(d, l, f) for l in lines); th = size * 1.2 * len(lines)
    w, h = tw + size * 1.2, th + size * 0.9; x0, y0 = x - w / 2, y - h / 2
    if think:
        rng = random.Random(seed)
        for i in range(14):
            a = i / 14 * 2 * math.pi; rx, ry = w / 2 * 0.95, h / 2 * 0.9
            cx, cy = x + rx * math.cos(a), y + ry * math.sin(a); r = size * (0.55 + rng.random() * 0.2)
            d.ellipse([cx - r - 5, cy - r - 5, cx + r + 5, cy + r + 5], fill=INK)
        for i in range(14):
            a = i / 14 * 2 * math.pi; rx, ry = w / 2 * 0.95, h / 2 * 0.9
            cx, cy = x + rx * math.cos(a), y + ry * math.sin(a); r = size * (0.55 + random.Random(seed).random() * 0.0 + 0.1)
            d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
        d.ellipse([x0, y0, x0 + w, y0 + h], fill=fill)
        if tail:
            for k, r in ((1, 16), (2, 10)):
                tx, ty = x + (tail[0] - x) * (0.55 + 0.25 * k), y + h / 2 + (tail[1] - y - h / 2) * (0.35 * k)
                d.ellipse([tx - r - 5, ty - r - 5, tx + r + 5, ty + r + 5], fill=INK); d.ellipse([tx - r, ty - r, tx + r, ty + r], fill=fill)
    else:
        if tail:
            bx = max(x0 + 40, min(x0 + w - 40, tail[0]))
            d.polygon([(bx - 24, y0 + h - 6), (bx + 24, y0 + h - 6), tail], fill=INK)
            d.polygon([(bx - 15, y0 + h - 12), (bx + 15, y0 + h - 12), (tail[0] + (bx - tail[0]) * 0.15, tail[1] - 12)], fill=fill)
        d.rounded_rectangle([x0 - 6, y0 - 6, x0 + w + 6, y0 + h + 6], radius=size * 0.7, fill=INK)
        d.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=size * 0.6, fill=fill)
    for i, l in enumerate(lines):
        lw = tlen(d, l, f); tdraw(d, (x - lw / 2, y0 + size * 0.42 + i * size * 1.2), l, f, fill=INK)


def viewfinder(img, x0, y0, x1, y1, col=WHITE, label='REC'):
    """取景框：四个角 + 红点 REC。"""
    d = ImageDraw.Draw(img); L = 60
    for (cx, cy, sx, sy) in ((x0, y0, 1, 1), (x1, y0, -1, 1), (x0, y1, 1, -1), (x1, y1, -1, -1)):
        d.line([(cx, cy), (cx + sx * L, cy)], fill=col, width=8); d.line([(cx, cy), (cx, cy + sy * L)], fill=col, width=8)
    d.ellipse([x0 + 34, y0 + 30, x0 + 58, y0 + 54], fill=TOMATO); tdraw(d, (x0 + 70, y0 + 22), label, font(40, 'smiley'), fill=col)


def motion(img, x, y, n=3, length=60, col=INK, seed=0, vertical=False):
    for i in range(n):
        o = (i - (n - 1) / 2) * 26
        if vertical: wobble_line(img, [(x + o, y), (x + o, y + length)], col, 6, seed + i, amp=1.5)
        else: wobble_line(img, [(x, y + o), (x + length, y + o)], col, 6, seed + i, amp=1.5)
