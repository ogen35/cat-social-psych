"""像素喵剧团 v4 画面工具包。两层：
  像素层：270×480 逻辑像素，画场景、道具、角色（chibi.py 的单色简约猫），最近邻放大 4 倍；
  涂鸦层：1080×1920 高清，画所有文字和标注（doodle.py：手写粗体字 + 白描边、贴纸、气泡、箭头、取景框）。
所有坐标都用逻辑像素（0–270 × 0–480），涂鸦的字号用成片像素。

  fr = Frame(bg)                                   # 竖屏 270×480；横封面用 Frame(size=HCOVER)，即 360×270
  fr.cat('大比', x, 脚底y, s=3, view='front'|'back'|'side'|'top', expr=..., talk=True, flip=True)
  fr.paws('大宝', y)                              # 第一人称：画面下方两只爪子
  fr.text / title / bubble / sticker / arrow / wiggle / viewfinder / motion   # 涂鸦层
  fr.spot(cx, cy, r, a) · fr.wipe(t, t0, '段落名')
  fr.photo('素材/图/xxx.jpg', dark=0.7, fx=0.8)       # 真实照片当背景：自动像素化、减色、调明暗
  img = fr.render()                                # 1080×1920
安全区（逻辑像素）：标题放 y 30–100，角色和情境放 100–340，字幕固定在 355（成片 1420），最下面 380 以下留给平台按钮；
右侧 x>230、y 225–400 是点赞评论按钮，主角的脸别放进去。
"""
import math
import random
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
import chibi as cb
import doodle as dd

W, H, S = 270, 480, 4
HCOVER = (360, 270)          # 横封面 4:3 的逻辑画布（成片 1440×1080）
PAPER, INK, CARD = (242, 236, 223), (36, 32, 44), (255, 252, 244)
YOU, TOMATO, TEAL, GREY, LIGHT, MINT, NIGHT = (245, 194, 71), (229, 83, 60), (44, 150, 132), (204, 196, 180), (250, 226, 160), (206, 232, 226), (64, 72, 104)
DIM = (120, 112, 100)
COLOR = {n: v['body'] for n, v in cb.CAST.items()}
_GRAIN = {}
def _grain(w, h):
    if (w, h) not in _GRAIN: _GRAIN[(w, h)] = np.random.default_rng(3).random((h, w)) < 0.03
    return _GRAIN[(w, h)]


def clamp(x, a=0., b=1.): return a if x < a else b if x > b else x
def ease(u): u = clamp(u); return u * u * (3 - 2 * u)
def eout(u): u = clamp(u); return 1 - (1 - u) ** 3
def lerp(a, b, u): return a + (b - a) * u
def pop(t, t0, h=6):
    """弹入：从上方落下、回弹一下。返回 (是否显示, y 偏移)。"""
    if t < t0: return False, 0
    u = (t - t0) / 0.22
    return True, (0 if u >= 1 else int(round(-h * (1 - u) * math.cos(u * math.pi * 1.5))))
def blink(t, seed=0): return ((t + seed * 0.71) % (2.6 + (seed % 5) * 0.37)) < 0.12
def talking(t, t0, t1): return t0 <= t < t1 and int((t - t0) / 0.13) % 2 == 0
def bob(t, seed=0): return 1 if ((t + seed * 0.3) % 0.8) < 0.4 else 0
def step(t, t0, t1): return int((t - t0) / 0.11) % 4 if t0 <= t < t1 else 0
def walk_x(t, t0, t1, x0, x1): return lerp(x0, x1, ease((t - t0) / max(1e-6, t1 - t0)))
def shake(t, t0, dur=0.3, amp=2): return int(round(amp * math.sin(t * 90))) if t0 <= t < t0 + dur else 0


_PHOTO = {}


def photo_bg(path, size=(W, H), fx=0.5, fy=0.5, zoom=1.0, dark=1.0, sat=0.85, colors=32, tint=None, blur=0):
    """真实照片 → 像素背景：按画幅裁切（fx/fy 是裁切窗口的位置 0–1，zoom 越大裁得越近），缩到逻辑像素网格，
    降一点饱和、调明暗（dark<1 压暗）、可叠一层色调 tint，再减到 colors 种颜色（不抖动），和像素猫的颗粒一致。结果会缓存。"""
    from PIL import ImageEnhance, ImageFilter
    key = (str(path), tuple(size), fx, fy, zoom, dark, sat, colors, tint, blur)
    if key not in _PHOTO:
        im = Image.open(path).convert('RGB'); w, h = size; r = w / h
        cw, ch = (im.height * r, im.height) if im.width / im.height > r else (im.width, im.width / r)
        cw, ch = cw / zoom, ch / zoom
        x0, y0 = (im.width - cw) * fx, (im.height - ch) * fy
        im = im.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch)))
        if blur: im = im.filter(ImageFilter.GaussianBlur(blur * im.width / w))
        im = im.resize((w, h), Image.BOX)
        im = ImageEnhance.Color(im).enhance(sat); im = ImageEnhance.Brightness(im).enhance(dark)
        if tint: im = Image.blend(im, Image.new('RGB', im.size, tint), 0.18)
        _PHOTO[key] = im.quantize(colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert('RGB')
    return _PHOTO[key]


PROPS_DIR = Path(__file__).resolve().parents[2] / 'assets' / '道具库'
_PROP = {}


def _prop(name):
    if name not in _PROP:
        p = PROPS_DIR / f'{name}.png'
        if not p.exists():
            have = sorted(x.stem for x in PROPS_DIR.glob('*.png'))
            raise FileNotFoundError(f'道具库里没有「{name}」。现有：{"、".join(have)}')
        _PROP[name] = np.array(Image.open(p).convert('RGBA'))
    return _PROP[name]


def props_list():
    """道具库里所有道具的名字。"""
    return sorted(x.stem for x in PROPS_DIR.glob('*.png'))


SPEAKS = {}          # 角色 → 它的台词 id 列表（build_pixel.py 从 film.SPEAKS 填进来），actor() 据此自动张嘴


def hop(t, t0, h=18, dur=0.42):
    """从 t0 起跳一次：返回离地高度（逻辑像素），传给 actor(lift=…)；影子留在地上。"""
    if not (t0 <= t < t0 + dur): return 0
    u = (t - t0) / dur
    return int(round(h * 4 * u * (1 - u)))


def actor(fr, name, x, by, s, t, T, view='front', expr=None, flip=False, seed=0, walk=None, rot=0, pose='stand', lift=0):
    """画一个会动的角色：说自己台词时张嘴、自动眨眼和呼吸、walk=(t0, t1) 期间换脚。返回头顶 y。
    pose：stand cheer jump headhold akimbo point flop slump；lift：离地高度（配 hop）。表情和姿势见 chibi.py 开头。"""
    talk = any((T[k].talk(t) if hasattr(T[k], "talk") else talking(t, T[k].start, T[k].end)) for k in SPEAKS.get(name, []) if k in T)   # 嘴跟着真实声音动
    e = expr
    if view in ('front', 'side') and blink(t, seed) and (expr or cb.CAST[name]['sig']) in ('normal', 'sad', 'smug'): e = 'flat'
    st = step(t, *walk) if walk else 0
    return fr.cat(name, x, by, s, view, e, talk, 0 if st or view == 'top' or lift else bob(t, seed), st, flip, rot=rot, pose=pose, lift=lift)


def zoom_op(op, f, X0, Y0):
    """把一个涂鸦层操作（成片像素坐标）按镜头推近换算：位置 (X−X0)·f，字号和线宽 ×f。"""
    kind, args, kw = op; P = lambda x, y: ((x - X0) * f, (y - Y0) * f); kw = dict(kw); a = list(args)
    if kind in ('text', 'bubble'):
        a[1], a[2] = P(a[1], a[2]); a[3] = int(a[3] * f)
        if kw.get('maxw'): kw['maxw'] = kw['maxw'] * f
        if kw.get('tail'): kw['tail'] = P(*kw['tail'])
    elif kind == 'sticker': a[1], a[2] = P(a[1], a[2]); a[3] = int(a[3] * f)
    elif kind == 'arrow': a[0], a[1] = P(*a[0]), P(*a[1])
    elif kind == 'wobble_line': a[0] = [P(x, y) for x, y in a[0]]
    elif kind in ('viewfinder', 'wobble_box'): (a[0], a[1]), (a[2], a[3]) = P(a[0], a[1]), P(a[2], a[3])
    elif kind == 'motion': a[0], a[1] = P(a[0], a[1]); a[3] = a[3] * f
    return (kind, tuple(a), kw)


class Frame:
    def __init__(self, bg=PAPER, grain=True, size=(W, H)):
        """size：逻辑像素画布。成片和竖封面用默认 270×480；横封面（4:3）用 size=HCOVER（360×270）。"""
        self.w, self.h = size
        a = np.zeros((self.h, self.w, 3), np.uint8); a[:] = bg
        if grain: a[_grain(self.w, self.h)] = tuple(max(0, c - 12) for c in bg)
        self.art = Image.fromarray(a); self.d = ImageDraw.Draw(self.art); self.ops = []; self.top = []
        self.zoom = None          # (倍数, cx, cy)：镜头推近；镜头函数里写的字和贴纸跟着一起推近，标题栏和字幕不动
        self.cats = []            # 这一帧画了哪些猫（名字, x0, y0, x1, y1），出片自检用：字幕不能压在猫身上
        self.scene_ops = None     # build_pixel 在镜头函数画完后记下 len(ops)：在这之前的字跟着推近

    # ---------------- 像素层
    def cat(self, name, x, by, s=3, view='front', expr=None, talk=False, bob=0, step=0, flip=False, shadow=True, rot=0, pose='stand', lift=0):
        spr = cb.cat(name, view, expr, talk, bob, step, pose)
        if flip: spr = spr[:, ::-1]
        if rot: spr = np.rot90(spr, rot)
        if shadow and view != 'top':
            if pose and pose != 'stand':                            # 有手臂时按脚的宽度算影子
                cols = np.where(spr[-3:, :, 3].any(0))[0]; w = (cols[-1] - cols[0] + 1) * s * 1.1 if len(cols) else spr.shape[1] * s
            else: w = spr.shape[1] * s
            self.d.ellipse([x - w * .32, by - 2, x + w * .32, by + 2], fill=tuple(max(0, c - 22) for c in self.art.getpixel((int(clamp(x, 0, self.w - 1)), int(clamp(by + 3, 0, self.h - 1))))))
        t = Image.fromarray(spr.repeat(s, 0).repeat(s, 1))
        self.art.paste(t, (int(x - t.width / 2), int(by - lift - t.height)), t)
        rows = np.where(spr[:, :, 3].any(1))[0]
        top = int(by - lift - (spr.shape[0] - (rows[0] if len(rows) else 0)) * s)
        self.cats.append((name, x - t.width / 2, top, x + t.width / 2, by - lift))
        return top   # 头顶的 y

    # ---------------- 漫画特效（像素层，逻辑坐标）：让表演更夸张
    def focus(self, cx, cy, r, t=0, n=44, col=INK, seed=0):
        """集中线：从画面四周射向 (cx, cy)，r 以内留空。每 1/12 秒抖一下。"""
        rnd = random.Random(seed * 997 + int(t * 12)); R = math.hypot(max(cx, self.w - cx), max(cy, self.h - cy)) + 4
        for i in range(n):
            a = 2 * math.pi * (i + rnd.uniform(-.3, .3)) / n; r0 = r * rnd.uniform(1.0, 1.5); da = rnd.uniform(.006, .02)
            self.d.polygon([(cx + math.cos(a) * r0, cy + math.sin(a) * r0), (cx + math.cos(a - da) * R, cy + math.sin(a - da) * R),
                            (cx + math.cos(a + da) * R, cy + math.sin(a + da) * R)], fill=col)

    def burst(self, cx, cy, r, col=None, line=INK, spikes=11, seed=0, t=0):
        """爆炸星：放在角色身后，喊话、震惊、得意时用。"""
        rnd = random.Random(seed * 31 + int(t * 8)); col = col or YOU; pts = []
        for i in range(spikes * 2):
            a = math.pi * i / spikes; rr = r * (rnd.uniform(.95, 1.08) if i % 2 == 0 else rnd.uniform(.55, .68))
            pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
        self.d.polygon(pts, fill=col, outline=line)

    def bolt(self, x, y, h=56, col=None, seed=0):
        """闪电：被雷劈到一样的震惊。"""
        rnd = random.Random(seed); col = col or YOU; w = h * .28
        pts = [(x, y), (x + w, y), (x + w * .45, y + h * .42), (x + w * .95, y + h * .42), (x - w * .1, y + h), (x + w * .18, y + h * .55), (x - w * .3, y + h * .55)]
        self.d.polygon([(px + rnd.uniform(-1, 1), py) for px, py in pts], fill=col, outline=INK)

    def gloom(self, x, y, w=60, t=0, seed=0):
        """头顶一朵小乌云在下雨：沮丧、绝望。"""
        c = (96, 100, 120)
        for dx, dy, r in ((-w * .3, 4, w * .2), (0, 0, w * .26), (w * .3, 4, w * .2)): self.d.ellipse([x + dx - r, y + dy - r * .8, x + dx + r, y + dy + r * .8], fill=c, outline=INK)
        for i in range(5):
            px = x - w * .36 + i * w * .18; py = y + 14 + ((t * 60 + i * 9 + seed) % 22)
            self.d.line([(px, py), (px - 1, py + 5)], fill=(120, 180, 240), width=2)

    def soul(self, name, x, y, t, t0, s=3):
        """灵魂出窍：一只半透明的白色小猫从角色头顶飘出来。"""
        if t < t0: return
        u = min(1.0, (t - t0) / 0.9)
        spr = np.pad(cb.cat(name, 'front', 'blank', pose='cheer'), ((1, 1), (1, 1), (0, 0))).copy(); m = spr[:, :, 3] > 0
        ring = (np.pad(m, 1)[:-2, 1:-1] | np.pad(m, 1)[2:, 1:-1] | np.pad(m, 1)[1:-1, :-2] | np.pad(m, 1)[1:-1, 2:]) & ~m
        spr[m, :3] = (250, 250, 255); spr[m, 3] = 190; spr[ring, :3] = (90, 96, 130); spr[ring, 3] = 220
        img = Image.fromarray(spr.repeat(s, 0).repeat(s, 1))
        sx = x + math.sin((t - t0) * 7) * 4; sy = y - u * 46
        self.d.polygon([(sx - 6, sy + img.height - 6), (sx + 6, sy + img.height - 6), (sx + math.sin(t * 9) * 5, sy + img.height + 14)], fill=(236, 236, 246))
        self.art.paste(img, (int(sx - img.width / 2), int(sy)), img)

    def sparkles(self, cx, cy, r, t, n=6, seed=0, col=None):
        """身边一闪一闪的小星星：得意、开心、灵光一现。"""
        rnd = random.Random(seed); col = col or YOU
        for i in range(n):
            a = rnd.uniform(0, 2 * math.pi); rr = r * rnd.uniform(.7, 1.1); ph = rnd.uniform(0, 1)
            k = 1 + int(2.5 * (0.5 + 0.5 * math.sin((t + ph) * 9)))
            px, py = cx + math.cos(a) * rr, cy + math.sin(a) * rr
            self.d.polygon([(px, py - 2 * k), (px + k * .6, py - k * .6), (px + 2 * k, py), (px + k * .6, py + k * .6), (px, py + 2 * k),
                            (px - k * .6, py + k * .6), (px - 2 * k, py), (px - k * .6, py - k * .6)], fill=col, outline=INK)

    def puff(self, x, y, t, t0, n=3, col=(230, 230, 236)):
        """落地 / 急刹时扬起的小烟团。"""
        if not (t0 <= t < t0 + 0.5): return
        u = (t - t0) / 0.5
        for i in range(n):
            dx = (-1 if i % 2 else 1) * (8 + u * 18) * (1 + i * .4); r = 5 * (1 - u) + 2
            self.d.ellipse([x + dx - r, y - r - i * 2, x + dx + r, y + r - i * 2], fill=col, outline=INK)

    def prop(self, name, x, by, s=1, flip=False, rot=0, dark=1.0, h=None):
        """道具库里的像素道具（assets/道具库/名字.png，LibTV 出图后用 scripts/props_import 导入）。
        (x, by) 是底边中点，s 是整数放大倍数；h 是目标高度（逻辑像素，可以比原图小）；dark<1 压暗（放在夜景里）。返回顶部 y。"""
        spr = _prop(name)
        if dark != 1.0: spr = spr.copy(); spr[:, :, :3] = (spr[:, :, :3] * dark).astype(np.uint8)
        if flip: spr = spr[:, ::-1]
        if rot: spr = np.rot90(spr, rot)
        if h: t = Image.fromarray(spr).resize((max(1, round(spr.shape[1] * h / spr.shape[0])), int(h)), Image.NEAREST)
        else: t = Image.fromarray(spr.repeat(s, 0).repeat(s, 1))
        self.art.paste(t, (int(x - t.width / 2), int(by - t.height)), t)
        return int(by - t.height)

    def photo(self, path, x=0, y=0, size=None, **kw):
        """把一张真实照片处理成像素背景贴上（size 不写就铺满画面；分屏时给格子大小）。参数见 photo_bg。"""
        im = photo_bg(path, size or (self.w, self.h), **kw); self.art.paste(im, (int(x), int(y))); self.d = ImageDraw.Draw(self.art)

    def emote(self, kind, x, y, s=3):
        t = Image.fromarray(cb.emote(kind).repeat(s, 0).repeat(s, 1)); self.art.paste(t, (int(x - t.width / 2), int(y)), t)

    def paws(self, name, y, s=1, dx=0, dig=0):
        """第一人称：画面下方的两只爪子（看到的是「我」的手）。dig：刨的动作偏移。"""
        C = cb.CAST[name]
        for k, px in enumerate((80 + dx, 190 + dx)):
            py = y + (dig if k == 0 else -dig)
            self.d.ellipse([px - 24 * s, py - 16 * s, px + 24 * s, py + 46 * s], fill=C['body'], outline=C['line'], width=2)
            for j in (-11, 0, 11): self.d.ellipse([px + j * s - 4, py - 9 * s, px + j * s + 4, py - s], fill=(240, 150, 160))

    def spot(self, cx, cy, r, a=1.0):
        """聚光灯：圆外压暗。"""
        if a <= 0: return
        Y, X = np.mgrid[0:self.h, 0:self.w]; out = (X - cx) ** 2 + ((Y - cy) * 0.8) ** 2 > r * r
        arr = np.array(self.art); arr[out] = (arr[out] * (1 - 0.6 * a)).astype(np.uint8)
        self.art = Image.fromarray(arr); self.d = ImageDraw.Draw(self.art)

    # ---------------- 涂鸦层（坐标逻辑像素，字号成片像素）
    def text(self, s, x, y, size=64, col=None, **kw):
        if col is not None: kw['col'] = col
        self.ops.append(('text', (s, x * S, y * S, size), kw))
    def title(self, s, y=86, size=110, **kw):
        kw.setdefault('stroke', 12); self.ops.append(('text', (s, self.w / 2 * S, y * S, size), kw))
    def bubble(self, s, x, y, size=52, think=False, tail=None, **kw):
        self.ops.append(('bubble', (s, x * S, y * S, size), dict(think=think, tail=(tail[0] * S, tail[1] * S) if tail else None, **kw)))
    def sticker(self, s, x, y, size=56, bg=YOU, fg=INK, rot=-3, seed=0): self.ops.append(('sticker', (s, x * S, y * S, size, bg, fg, rot, seed), {}))
    def arrow(self, p0, p1, col=INK, seed=0, bend=0.25): self.ops.append(('arrow', ((p0[0] * S, p0[1] * S), (p1[0] * S, p1[1] * S), col, 8, seed, bend), {}))
    def wiggle(self, pts, col=INK, width=6, seed=0): self.ops.append(('wobble_line', ([(x * S, y * S) for x, y in pts], col, width, seed), {}))
    def viewfinder(self, x0, y0, x1, y1, col=(255, 255, 255)): self.ops.append(('viewfinder', (x0 * S, y0 * S, x1 * S, y1 * S, col), {}))
    def motion(self, x, y, n=3, length=14, vertical=False, col=INK, seed=0): self.ops.append(('motion', (x * S, y * S, n, length * S, col, seed, vertical), {}))
    def box(self, x0, y0, x1, y1, col=INK, fill=None, seed=0): self.ops.append(('wobble_box', (x0 * S, y0 * S, x1 * S, y1 * S, col, 6, fill, seed), {}))

    def wipe(self, t, t0, title, dur=0.6):
        """转场：黄色面板从右往左扫过，中间停一下写段落名（画在最上层）。"""
        u = (t - t0) / dur
        if not (0 <= u < 1): return
        x0 = lerp(self.w, 0, eout(u / 0.3)) if u < 0.3 else (0 if u < 0.7 else lerp(0, -self.w, ease((u - 0.7) / 0.3)))
        self.top.append((x0, title if 0.2 < u < 0.8 else None))

    def zoomed_ops(self):
        """镜头推近时，镜头函数里写的字、贴纸、箭头跟着画面一起放大、挪位（不然标签和它标的东西会错开）；标题栏、字幕原样。"""
        if not (self.zoom and self.zoom[0] > 1.001): return self.ops
        f, cx, cy = self.zoom; W2, H2 = self.w * S, self.h * S; cw, ch = W2 / f, H2 / f
        X0 = clamp(cx * S - cw / 2, 0, W2 - cw); Y0 = clamp(cy * S - ch / 2, 0, H2 - ch)
        n = len(self.ops) if self.scene_ops is None else self.scene_ops
        return [zoom_op(o, f, X0, Y0) for o in self.ops[:n]] + self.ops[n:]

    def render(self):
        img = self.art.resize((self.w * S, self.h * S), Image.NEAREST)
        if self.zoom and self.zoom[0] > 1.001:
            f, cx, cy = self.zoom; W2, H2 = img.size; cw, ch = W2 / f, H2 / f
            x0 = clamp(cx * S - cw / 2, 0, W2 - cw); y0 = clamp(cy * S - ch / 2, 0, H2 - ch)
            img = img.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((W2, H2), Image.NEAREST)
        img = img.convert('RGBA')
        for kind, args, kw in self.zoomed_ops(): getattr(dd, kind)(img, *args, **kw)
        for x0, title in self.top:
            X = x0 * S; d = ImageDraw.Draw(img)
            d.rectangle([X, 0, X + self.w * S, self.h * S], fill=YOU); d.polygon([(X - 60, 0), (X, 0), (X, self.h * S), (X - 170, self.h * S)], fill=TOMATO)
            if title: dd.text(img, title, X + self.w * S / 2, self.h * S / 2 - 90, 130, stroke=12, rot=-3)
        return img.convert('RGB')


SERIES = '猫说心理学'


def douyin_cover(fr, c):
    """抖音爆款封面模板（竖 9:16、竖 3:4、横 4:3 都按 fr 的画布自己排版，不截静帧）。
    c = dict(line1='看完恐怖片', line2='厨房一响就进贼？', hi='进贼',     # 两行大字：上行 ≤ 8 字，下行 ≤ 7 字，hi 是下行里要标黄的词
             who='大宝', expr='shock', emote='!',                          # 主角大头特写，表情要夸张
             bg='素材/图/xxx.jpg' 或 (r, g, b), bg_kw=dict(fx=…, dark=…),  # 背景：照片（自动像素化、压暗、虚化）或纯色
             tag='启动效应', no=19, prop=函数(fr, 布局))                    # 概念标签、期数、可选的小道具
    版式：标题在上方三分之一；主角大头压在下方、身子出画；左上角留给「置顶」标签，左下角留给播放量，都不放字。"""
    w, h = fr.w, fr.h; land = w > h
    bg = c.get('bg', NIGHT)
    if isinstance(bg, tuple): fr.d.rectangle([0, 0, w, h], fill=bg)
    else: fr.photo(bg, **{'dark': 0.62, 'blur': 0.8, 'sat': 0.8, **c.get('bg_kw', {})})
    name = c.get('who', '大比'); k = cb.CAST[name].get('k', 1.0)
    if land: s, cx = 8, w * 0.74
    else: s, cx = (9 if h <= 380 else 11), w * 0.56
    sh = int(27 * k * s)
    by = h + int(sh * (0.30 if land else 0.26))
    fr.spot(cx, by - sh * 0.62, sh * 0.62, 0.55)
    if c.get('prop'): c['prop'](fr, dict(w=w, h=h, land=land, cx=cx, by=by, sh=sh))
    top = fr.cat(name, cx, by, s, 'front', c.get('expr', 'shock'), shadow=False)
    em = c.get('emote')
    if em in ('!', '?'): fr.text('！' if em == '!' else '？', min(w - 26, cx + sh * 0.36), top - 30, 230 if land else 260, TOMATO, scol=(255, 255, 255), stroke=14, rot=10)
    elif em: fr.emote(em, min(w - 24, cx + sh * 0.34), top - 4, 8)
    l1, l2, hi = c.get('line1', ''), c.get('line2', ''), c.get('hi')
    if land:
        tx, y1, mw = w * 0.34, h * 0.14, 900
        if l1: fr.text(l1, tx, y1, 110, (255, 255, 255), scol=INK, stroke=14, rot=-2, maxw=mw)
        fr.text(l2, tx, y1 + 36, 160, (255, 255, 255), hi=hi, hcol=YOU, scol=INK, stroke=20, rot=-3, shadow=TOMATO, maxw=mw)
        if c.get('tag'): fr.sticker(c['tag'], tx, y1 + 112, 64, TEAL, (255, 255, 255), -3, seed=2)
    else:
        y1 = h * (0.10 if h <= 380 else 0.15)
        if l1: fr.text(l1, w / 2, y1, 124, (255, 255, 255), scol=INK, stroke=14, rot=-2, maxw=1000)
        fr.text(l2, w / 2, y1 + 40, 186, (255, 255, 255), hi=hi, hcol=YOU, scol=INK, stroke=22, rot=-3, shadow=TOMATO, maxw=1030)
        if c.get('tag'): fr.sticker(c['tag'], w * 0.27, y1 + 118, 66, TEAL, (255, 255, 255), -4, seed=2)
    if c.get('no') is not None: fr.sticker(f"{SERIES} · {c['no']}", w - 56, 16, 36, INK, (255, 255, 255), 0, seed=9)


def caption_chunks(say, words, dur, maxc=14):
    """把一句口播切成字幕块（每块 ≤ maxc 字，优先在标点处断），按逐字时间给出起止。"""
    import re
    plain = re.sub(r'[【】]', '', say)
    pieces, cur = [], ''
    for ch in plain:
        if not cur and pieces and ch in '，。！？；：、—':           # 标点不放在一块的开头，并回上一块
            pieces[-1] += ch; continue
        cur += ch
        if ch in '，。！？；：、—' and len(cur) >= 4: pieces.append(cur); cur = ''
        elif len(cur) >= maxc: pieces.append(cur); cur = ''
    if cur.strip():
        if pieces and not cur.strip('，。！？；：、— '): pieces[-1] += cur
        else: pieces.append(cur)
    hl = re.findall(r'【(.+?)】', say)
    n = max(1, len(plain)); times = [dur * i / n for i in range(n + 1)]
    if words:
        k = 0
        for w in words:
            j = plain.find(w['text'], k)
            if j < 0: continue
            for q in range(j, j + len(w['text'])): times[q] = w['t']
            k = j + len(w['text'])
    out, i = [], 0
    for p in pieces:
        t0 = times[min(i, n - 1)]; i += len(p)
        out.append([t0, dur, p.rstrip('，。、；：— '), [h for h in hl if h in p]])
    for j in range(len(out) - 1): out[j][1] = out[j + 1][0]
    return [tuple(x) for x in out]


def draw_topbar(fr, text, size=64):
    """顶部全程不变的一句标题（FORMAT 短视频用）：白底黑字，成片 y≈250，抖音顶栏下方。场景里的贴纸放在 y ≥ 95。"""
    fr.sticker(text, W / 2, 62, size, (255, 255, 255), INK, rot=0, seed=11)


def draw_caption(fr, text, hi, who=None, size=64):
    """字幕：成片 y≈1420，平台底部按钮之上；角色台词在上方挂一个角色色的名牌。快节奏（PACE='fast'）用大一号的字。"""
    if who:
        bg = COLOR.get(who, YOU); fg = (255, 255, 255) if who == '大宝' else INK
        fr.sticker(who, W / 2, 346, 40, bg, fg, rot=-2)
        fr.text(text, W / 2, 360, size, hi=hi or None, stroke=10, maxw=1000)
    else:
        fr.text(text, W / 2, 352, size, hi=hi or None, stroke=11, maxw=1000)
