"""线条画风（film.py 里写 STYLE = 'line'）的画面工具包。film.py 开头改成 `from kit_line import *`。

和 kit.py（像素版）接口一样、坐标一样（逻辑 270×480，成片 ×4），区别是：
  - 背景、猫、道具、特效都用 skia 在 1080×1920 上直接画成矢量线条（深棕粗描边、平涂、线条每 3 帧轻微抖动），不再像素化；
  - 猫来自 linecat.py（头身一体的线条萌猫），道具来自 assets/道具库_线条（LibTV 出图，import_sheet.py --style line 导入）；
  - 照片背景 fr.photo() 保持高清，只做轻微虚化、提亮、降饱和，让线条猫跳出来；
  - 没有 fr.d（像素画笔）：自己画东西用 fr.rect / ellipse / circle / poly / lines / draw(fn)。
文字、贴纸、气泡、箭头、字幕、转场（涂鸦层）和像素版完全一样。

  fr = Frame(bg)                                             # 纯色底
  fr.scene('room' | 'road' | 'sky' | 'cabin' | 'street', bg=…) # 纯色底 + 同色系简笔场景
  fr.photo('素材/图/x.jpg', dark=0.8, blur=1.5)               # 高清照片背景
  actor(fr, '大比', x, 脚底y, s, t, T, expr=…, pose=…)         # s 和像素版同一量级：猫高 ≈ 25·s 逻辑像素
  fr.prop('墓碑', x, 底y, h=26)                                # 线条道具，h = 目标高度（逻辑像素）
  fr.focus / burst / bolt / gloom / soul / sparkles / puff / spot / emote / paws / shock
"""
import math
import random
from pathlib import Path
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageDraw
import skia
import kit
from kit import (W, H, S, HCOVER, PAPER, INK, CARD, YOU, TOMATO, TEAL, GREY, LIGHT, MINT, NIGHT, DIM, SERIES, SPEAKS,
                 clamp, ease, eout, lerp, pop, blink, talking, bob, step, walk_x, shake, hop, caption_chunks, draw_topbar, draw_caption)
import doodle as dd
import linecat as lc
from linecat import LINE, paint

STYLE = 'line'
WHITE = (255, 255, 255)
TEAR = lc.TEAR
PROPS_DIR = Path(__file__).resolve().parents[2] / 'assets' / '道具库_线条'
COLOR = {n: v['body'] for n, v in lc.CAST.items()}
CAT_H = 21          # 线条猫身高（不含耳朵）= 21·s 逻辑像素，和像素猫同一个 s 时大小相当


def darker(rgb, k=0.78): return tuple(int(c * k) for c in rgb)


def _skimg(arr):
    return skia.Image.fromarray(np.ascontiguousarray(arr), colorType=skia.kRGBA_8888_ColorType)


_PHOTO, _PROP = {}, {}


def photo_img(path, size, fx=0.5, fy=0.5, zoom=1.0, dark=1.0, sat=0.85, tint=None, blur=0, wash=0.10, soft=0.6):
    """高清照片背景：按画幅裁切，虚化 blur(+soft) 逻辑像素，降饱和、调明暗、叠色调，再往纸色洗一点（wash），线条角色压在上面更清楚。"""
    key = (str(path), tuple(size), fx, fy, zoom, dark, sat, tint, blur, wash, soft)
    if key not in _PHOTO:
        im = Image.open(path).convert('RGB'); w, h = size; r = w / h
        cw, ch = (im.height * r, im.height) if im.width / im.height > r else (im.width, im.width / r)
        cw, ch = cw / zoom, ch / zoom
        x0, y0 = (im.width - cw) * fx, (im.height - ch) * fy
        im = im.crop((int(x0), int(y0), int(x0 + cw), int(y0 + ch))).resize((int(w * S), int(h * S)), Image.LANCZOS)
        if blur + soft > 0: im = im.filter(ImageFilter.GaussianBlur((blur + soft) * S * 0.8))
        im = ImageEnhance.Color(im).enhance(sat); im = ImageEnhance.Brightness(im).enhance(dark)
        if tint: im = Image.blend(im, Image.new('RGB', im.size, tint), 0.18)
        if wash: im = Image.blend(im, Image.new('RGB', im.size, PAPER), wash)
        _PHOTO[key] = _skimg(np.array(im.convert('RGBA')))
    return _PHOTO[key]


def _prop(name, dark=1.0):
    key = (name, dark)
    if key not in _PROP:
        p = PROPS_DIR / f'{name}.png'
        if not p.exists():
            have = sorted(x.stem for x in PROPS_DIR.glob('*.png'))
            raise FileNotFoundError(f'线条道具库里没有「{name}」。现有：{"、".join(have)}')
        a = np.array(Image.open(p).convert('RGBA'))
        if dark != 1.0: a = a.copy(); a[:, :, :3] = (a[:, :, :3] * dark).astype(np.uint8)
        _PROP[key] = (_skimg(a), a.shape[1], a.shape[0])
    return _PROP[key]


def props_list(): return sorted(x.stem for x in PROPS_DIR.glob('*.png'))


_MINI = {}


def _mini_img(name, expr, hpx, var, pose='stand'):
    key = (name, expr, int(round(hpx)), var, pose)
    if key not in _MINI:
        hh = int(round(hpx)); w_ = int(hh * 1.9) + 12; h_ = int(hh * 1.45) + 12
        surf = skia.Surface(w_, h_); cv = surf.getCanvas(); cv.clear(skia.ColorTRANSPARENT)
        lc.draw_cat(cv, name, w_ / 2, h_ - 6, hh, expr=expr, pose=pose, boil=var, lw_px=max(2.0, hh * 0.05))
        _MINI[key] = (surf.makeImageSnapshot(), w_, h_)
    return _MINI[key]


LIN = skia.SamplingOptions(skia.FilterMode.kLinear, skia.MipmapMode.kLinear)


class Frame(kit.Frame):
    """线条版画布。坐标、文字层和 kit.Frame 一样；画面层先记成一串绘制函数，render() 时按镜头推近（fr.zoom）一起画。"""
    def __init__(self, bg=PAPER, grain=False, size=(W, H)):
        self.w, self.h = size; self.ops = []; self.top = []; self.zoom = None; self.t = 0.0; self.draws = []; self.cats = []; self.scene_ops = None
        self.fill(bg)

    @property
    def d(self): raise AttributeError('线条画风没有 fr.d（像素画笔）：用 fr.rect / ellipse / circle / poly / lines / draw(fn)')

    @property
    def boil(self): return int(self.t * 30) // 3

    def draw(self, fn): self.draws.append(fn)

    # ---------------- 基本形状（逻辑坐标；lw 是描边粗细，逻辑像素）
    def fill(self, rgb): self.draws.append(lambda cv: cv.drawRect(skia.Rect.MakeWH(self.w, self.h), paint(rgb)))

    def rect(self, x0, y0, x1, y1, fill=None, line=LINE, r=0, lw=1.8, a=255):
        R = skia.Rect.MakeLTRB(x0, y0, x1, y1)
        def fn(cv):
            if fill is not None: cv.drawRoundRect(R, r, r, paint(fill, a))
            if line is not None and lw: cv.drawRoundRect(R, r, r, paint(line, a, stroke=lw))
        self.draws.append(fn)

    def ellipse(self, x0, y0, x1, y1, fill=None, line=LINE, lw=1.8, a=255):
        R = skia.Rect.MakeLTRB(x0, y0, x1, y1)
        def fn(cv):
            if fill is not None: cv.drawOval(R, paint(fill, a))
            if line is not None and lw: cv.drawOval(R, paint(line, a, stroke=lw))
        self.draws.append(fn)

    def circle(self, cx, cy, r, fill=None, line=LINE, lw=1.8, a=255): self.ellipse(cx - r, cy - r, cx + r, cy + r, fill, line, lw, a)

    def poly(self, pts, fill=None, line=LINE, lw=1.8, smooth=False, wobble=0.35, a=255, key='poly'):
        boil = self.boil
        def fn(cv):
            q = lc.jit(pts, key + str(len(pts)), boil, wobble)
            p = lc.spline(q) if smooth else lc._poly(q)
            if fill is not None: cv.drawPath(p, paint(fill, a))
            if line is not None and lw: cv.drawPath(p, paint(line, a, stroke=lw))
        self.draws.append(fn)

    def lines(self, pts, col=LINE, w=1.8, smooth=True, wobble=0.35, a=255, key='ln'):
        boil = self.boil
        def fn(cv):
            q = lc.jit(pts, key + str(len(pts)), boil, wobble)
            p = lc.spline(q, closed=False) if (smooth and len(q) > 2) else lc._poly(q, False)
            cv.drawPath(p, paint(col, a, stroke=w))
        self.draws.append(fn)

    # ---------------- 背景
    def photo(self, path, x=0, y=0, size=None, **kw):
        kw.pop('colors', None)
        w, h = size or (self.w, self.h); img = photo_img(path, (w, h), **kw)
        self.draws.append(lambda cv: cv.drawImageRect(img, skia.Rect.MakeXYWH(x, y, w, h), LIN))

    def scene(self, kind='room', bg=(253, 236, 186), ink=None, ground=None, deco=None, horizon=0.62, seed=0):
        """纯色底 + 同色系简笔场景（不抢角色）。
        kind：room 室内 / road 公路 / sky 天空 / cabin 机舱 / street 街道 / blank 只有底色。
        ground：地面线的 y（逻辑像素），要和角色的脚底对齐（脚踩在线上或略低于线）；不写就是 horizon × 画面高。
        deco：室内窗户放哪边，'l' / 'r' / None（不放）。挑角色和贴纸都不在的那一边。"""
        ink = ink or darker(bg, 0.80); self.fill(bg); w, h = self.w, self.h
        y0 = ground if ground is not None else h * horizon
        L = lambda pts, **k: self.lines(pts, ink, 1.5, **k)
        if kind == 'room':
            L([(-4, y0), (w + 4, y0 + 1)], key='fl')
            if deco in ('l', 'r'):
                x0 = w * (.06 if deco == 'l' else .66); x1 = x0 + w * .28; ya, yb = h * .21, h * .35
                self.rect(x0, ya, x1, yb, None, ink, r=3, lw=1.5)
                L([((x0 + x1) / 2, ya), ((x0 + x1) / 2, yb)], smooth=False, key='w1'); L([(x0, (ya + yb) / 2), (x1, (ya + yb) / 2)], smooth=False, key='w2')
        elif kind == 'road':
            hz = y0 - h * .07
            L([(-4, hz + 3), (w * .5, hz - 2), (w + 4, hz - 5)], key='hz')
            for i in range(5): L([(w * (.06 + i * .21), y0 + 6), (w * (.13 + i * .21), y0 + 6)], smooth=False, key=f'd{i}')
            for (cx, cy, k) in ((w * .14, hz - 26, 1.0), (w * .80, hz - 52, 1.2)): self._cloud_line(cx, cy, k, ink)
        elif kind == 'sky':
            for (cx, cy, k) in ((w * .2, h * .3, 1.2), (w * .75, h * .22, 1.0), (w * .6, h * .55, 1.4)): self._cloud_line(cx, cy, k, ink)
        elif kind == 'cabin':
            for i in range(3):
                cx = w * (.2 + i * .3); self.rect(cx - 22, h * .22, cx + 22, h * .36, darker(bg, .93), ink, r=18, lw=1.5)
            L([(-4, y0), (w + 4, y0)], key='cab')
        elif kind == 'street':
            L([(-4, y0), (w + 4, y0)], key='st')
            for i in range(3):
                bx = w * (.05 + i * .33); self.rect(bx, y0 - h * (.18 + .05 * (i % 2)), bx + w * .24, y0, None, ink, r=2, lw=1.5)

    def wheel(self, cx, cy, r, col=(92, 96, 110)):
        """方向盘（画在角色前面）：粗圆环 + 三根辐条。"""
        def fn(cv):
            for w_, c_ in ((r * .26 + 3.6, LINE), (r * .26, col)):
                cv.drawCircle(cx, cy, r, paint(c_, stroke=w_))
            for ang in (200, 340, 90):
                a = math.radians(ang); x1, y1 = cx + math.cos(a) * r, cy + math.sin(a) * r
                cv.drawLine(cx, cy, x1, y1, paint(LINE, stroke=r * .2 + 3.6)); cv.drawLine(cx, cy, x1, y1, paint(col, stroke=r * .2))
            cv.drawCircle(cx, cy, r * .24, paint(col)); cv.drawCircle(cx, cy, r * .24, paint(LINE, stroke=1.8))
        self.draws.append(fn)

    def _cloud_line(self, cx, cy, k, ink):
        pts = lc.arc_pts(cx, cy, 9 * k, 8 * k, math.pi, math.pi * 2, 6) + lc.arc_pts(cx + 13 * k, cy + 1.5 * k, 7 * k, 6 * k, math.pi * 1.1, math.pi * 2, 5)
        self.lines(pts, ink, 1.5, key=f'cl{int(cx)}')

    # ---------------- 角色
    def cat(self, name, x, by, s=3, view='front', expr=None, talk=False, bob=0, step=0, flip=False, shadow=True, rot=0, pose='stand', lift=0,
            look=None, wag=0.0, blush=None, blinking=False):
        c = lc.CAST[name]; hh = CAT_H * s; k = c['k']
        if look is None: look = 0.9 if view == 'side' else 0.0
        deg = rot * 90 if isinstance(rot, int) and abs(rot) <= 3 else rot
        if step: deg += (3 if step % 2 else -3)
        sy = 1 + 0.018 * bob; lw = clamp(0.024 * hh, 1.6, 4.2); boil = self.boil
        v = 'back' if view == 'back' else 'front'
        def fn(cv):
            if shadow and view != 'top':
                sw = hh * k * c['bw'] * (1.5 if pose == 'flop' else 1.15) * (0.75 if lift else 1)
                cv.drawOval(skia.Rect.MakeLTRB(x - sw, by - hh * .035, x + sw, by + hh * .035), paint(LINE, 38))
            lc.draw_cat(cv, name, x, by - lift - (step % 2) * hh * .01, hh, expr=expr, pose=pose, talk=talk, look=look, boil=boil, flip=flip, rot=deg,
                        sy=sy, wag=wag, blink=blinking, blush=blush, lw_px=lw, view=v)
        self.draws.append(fn)
        top = int(by - lift - hh * k * (1 + c['ear']) * (0.6 if pose == 'flop' else 1))
        hw = hh * k * c['bw'] * 1.2
        self.cats.append((name, x - hw, top, x + hw, by - lift))
        return top

    def mini(self, name, x, by, h, expr=None, a=255, var=None, pose='stand', flip=False):
        """成群的小猫（模拟实验里的上百只）：先把这只猫按 (表情, 大小) 画成小图缓存起来，每帧直接贴，100 只也不卡。
        h = 身高（逻辑像素，不含耳朵）；a = 透明度；var 不写就跟着线条抖动换两版。"""
        v = (self.boil % 2) if var is None else var
        img, w_, h_ = _mini_img(name, expr or lc.CAST[name]['sig'], h * S, v, pose)
        k = 1 / S
        def fn(cv):
            p = skia.Paint(AntiAlias=True); p.setAlphaf(a / 255)
            cv.save(); cv.translate(x, by)
            if flip: cv.scale(-1, 1)
            cv.drawImageRect(img, skia.Rect.MakeXYWH(-w_ * k / 2, -(h_ - 6) * k, w_ * k, h_ * k), LIN, p); cv.restore()
        self.draws.append(fn)

    # ---------------- 漫画特效
    def focus(self, cx, cy, r, t=0, n=44, col=INK, seed=0, a=200):
        """集中线：从画面四周射向 (cx, cy)，r 以内留空，每 1/12 秒抖一下。"""
        rnd = random.Random(seed * 997 + int(t * 12)); R = math.hypot(max(cx, self.w - cx), max(cy, self.h - cy)) + 6
        segs = []
        for i in range(n):
            ang = 2 * math.pi * (i + rnd.uniform(-.3, .3)) / n; r0 = r * rnd.uniform(1.0, 1.5); da = rnd.uniform(.006, .02)
            segs.append([(cx + math.cos(ang) * r0, cy + math.sin(ang) * r0), (cx + math.cos(ang - da) * R, cy + math.sin(ang - da) * R), (cx + math.cos(ang + da) * R, cy + math.sin(ang + da) * R)])
        def fn(cv):
            for q in segs: cv.drawPath(lc._poly(q), paint(col, a))
        self.draws.append(fn)

    def burst(self, cx, cy, r, col=None, line=INK, spikes=11, seed=0, t=0):
        rnd = random.Random(seed * 31 + int(t * 8)); col = col or YOU; pts = []
        for i in range(spikes * 2):
            a = math.pi * i / spikes; rr = r * (rnd.uniform(.95, 1.08) if i % 2 == 0 else rnd.uniform(.58, .7))
            pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
        self.poly(pts, col, LINE, 2.0, wobble=0)

    def bolt(self, x, y, h=56, col=None, seed=0):
        col = col or YOU; w = h * .28; rnd = random.Random(seed)
        pts = [(x, y), (x + w, y), (x + w * .45, y + h * .42), (x + w * .95, y + h * .42), (x - w * .1, y + h), (x + w * .18, y + h * .55), (x - w * .3, y + h * .55)]
        self.poly([(px + rnd.uniform(-.6, .6), py) for px, py in pts], col, LINE, 1.8, wobble=0)

    def gloom(self, x, y, w=60, t=0, seed=0):
        """头顶一朵小乌云在下雨。"""
        pts = lc.ellipse_pts(x - w * .22, y + 2, w * .22, w * .16, 7, math.pi) [:5] + lc.ellipse_pts(x + w * .05, y - 3, w * .26, w * .2, 9, math.pi)[:6] + lc.ellipse_pts(x + w * .3, y + 3, w * .18, w * .14, 7, math.pi * 1.3)[:5]
        pts = [(px, min(py, y + w * .14)) for px, py in pts]
        self.poly(pts, (150, 156, 178), LINE, 1.6, smooth=True, key='gloom')
        for i in range(5):
            px = x - w * .3 + i * w * .15; py = y + w * .2 + ((t * 60 + i * 9 + seed) % 18)
            self.lines([(px, py), (px - 1, py + 5)], TEAR, 1.6, smooth=False, wobble=0)

    def soul(self, name, x, y, t, t0, s=3):
        """灵魂出窍：白色小幽灵从头顶飘出来。"""
        if t < t0: return
        u = min(1.0, (t - t0) / 0.9); boil = self.boil
        self.draws.append(lambda cv: lc.soul(cv, x, y, s * 9, ease(u), boil))

    def sparkles(self, cx, cy, r, t, n=6, seed=0, col=None):
        self.draws.append(lambda cv: lc.sparkles(cv, cx, cy, r, t, n=n, seed=seed, rgb=col or lc.GOLD))

    def puff(self, x, y, t, t0, n=3, col=(240, 240, 244)):
        if not (t0 <= t < t0 + 0.5): return
        u = (t - t0) / 0.5
        for i in range(n):
            dx = (-1 if i % 2 else 1) * (8 + u * 18) * (1 + i * .4); r = 5 * (1 - u) + 2
            self.circle(x + dx, y - r - i * 2, r, col, LINE, 1.2)

    def shock(self, x, y, r=30):
        """头顶三道惊吓线。"""
        boil = self.boil; self.draws.append(lambda cv: lc.shock_lines(cv, x, y, r, boil=boil))

    def emote(self, kind, x, y, s=3):
        if kind == 'sweat': self.draws.append(lambda cv: lc.sweat(cv, x, y + s * 3, s * 4))
        elif kind == 'anger': self.draws.append(lambda cv: lc.vein(cv, x, y + s * 3, s * 4))
        elif kind == 'heart':
            def fn(cv):
                r = s * 3; p = skia.Path(); p.moveTo(x, y + r * 1.6); p.cubicTo(x - r * 2.4, y, x - r, y - r * 1.4, x, y - r * .2); p.cubicTo(x + r, y - r * 1.4, x + r * 2.4, y, x, y + r * 1.6); p.close()
                cv.drawPath(p, paint((240, 80, 100))); cv.drawPath(p, paint(LINE, stroke=1.4))
            self.draws.append(fn)
        elif kind == 'spark': self.sparkles(x, y, s * 4, 0.3, n=3)
        elif kind in ('!', '?'): self.text('！' if kind == '!' else '？', x, y, 30 * s, TOMATO, stroke=10)

    def paws(self, name, y, s=1, dx=0, dig=0):
        """第一人称：画面下方的两只爪子。"""
        body = lc.CAST[name]['body']
        for k_, px in enumerate((80 + dx, 190 + dx)):
            py = y + (dig if k_ == 0 else -dig)
            self.ellipse(px - 24 * s, py - 16 * s, px + 24 * s, py + 60 * s, body, LINE, 2.0)
            for j in (-11, 0, 11): self.ellipse(px + j * s - 4, py - 9 * s, px + j * s + 4, py - s, (240, 150, 160), None)

    def spot(self, cx, cy, r, a=1.0):
        if a <= 0: return
        def fn(cv):
            p = skia.Path(); p.addRect(skia.Rect.MakeWH(self.w, self.h)); p.addOval(skia.Rect.MakeLTRB(cx - r, cy - r / .8, cx + r, cy + r / .8))
            p.setFillType(skia.PathFillType.kEvenOdd); cv.drawPath(p, paint((0, 0, 0), int(150 * a)))
        self.draws.append(fn)

    def prop(self, name, x, by, s=1, flip=False, rot=0, dark=1.0, h=None):
        """线条道具（assets/道具库_线条/名字.png）。(x, by) 底边中点；默认最长边 56·s 逻辑像素，h = 目标高度。返回顶部 y。"""
        img, pw, ph = _prop(name, dark)
        k = (h / ph) if h else (56 * s / max(pw, ph)); wl, hl = pw * k, ph * k
        deg = rot * 90 if isinstance(rot, int) and abs(rot) <= 3 else rot
        def fn(cv):
            cv.save(); cv.translate(x, by - hl / 2)
            if deg: cv.rotate(deg)
            if flip: cv.scale(-1, 1)
            cv.drawImageRect(img, skia.Rect.MakeXYWH(-wl / 2, -hl / 2, wl, hl), LIN); cv.restore()
        self.draws.append(fn)
        return int(by - hl)

    # ---------------- 出图
    def render(self):
        surf = skia.Surface(int(self.w * S), int(self.h * S)); cv = surf.getCanvas()
        cv.save(); cv.scale(S, S)
        if self.zoom and self.zoom[0] > 1.001:
            f, cx, cy = self.zoom; cw, ch = self.w / f, self.h / f
            x0 = clamp(cx - cw / 2, 0, self.w - cw); y0 = clamp(cy - ch / 2, 0, self.h - ch)
            cv.scale(f, f); cv.translate(-x0, -y0)
        for fn in self.draws: fn(cv)
        cv.restore()
        img = lc.to_pil(surf)
        for kind, args, kw in self.zoomed_ops(): getattr(dd, kind)(img, *args, **kw)
        for x0, title in self.top:
            X = x0 * S; d = ImageDraw.Draw(img)
            d.rectangle([X, 0, X + self.w * S, self.h * S], fill=YOU); d.polygon([(X - 60, 0), (X, 0), (X, self.h * S), (X - 170, self.h * S)], fill=TOMATO)
            if title: dd.text(img, title, X + self.w * S / 2, self.h * S / 2 - 90, 130, stroke=12, rot=-3)
        return img.convert('RGB')


LFrame = Frame


def actor(fr, name, x, by, s, t, T, view='front', expr=None, flip=False, seed=0, walk=None, rot=0, pose='stand', lift=0, look=None):
    """会动的角色：说自己台词时张嘴、自动眨眼、呼吸、尾巴慢慢摇；walk=(t0, t1) 期间左右晃着走。返回头顶 y。"""
    talk = any((T[k].talk(t) if hasattr(T[k], "talk") else talking(t, T[k].start, T[k].end)) for k in SPEAKS.get(name, []) if k in T)   # 嘴跟着真实声音动
    bl = view in ('front', 'side') and blink(t, seed)
    st = step(t, *walk) if walk else 0
    return fr.cat(name, x, by, s, view, expr, talk, 0 if st or lift else bob(t, seed), st, flip, rot=rot, pose=pose, lift=lift,
                  look=look, wag=math.sin(t * 3.2 + seed) * 0.18, blinking=bl)


def douyin_cover(fr, c):
    """抖音爆款封面（线条版）：和 kit.douyin_cover 同一个模板 dict。"""
    w, h = fr.w, fr.h; land = w > h
    bg = c.get('bg', (253, 228, 128))
    if isinstance(bg, tuple): fr.scene(c.get('scene', 'blank'), bg=bg)
    else: fr.photo(bg, **{'dark': 0.7, 'blur': 1.2, 'sat': 0.8, **c.get('bg_kw', {})})
    name = c.get('who', '大比'); k = lc.CAST[name]['k']
    if land: s, cx = 8, w * 0.74
    else: s, cx = (9 if h <= 380 else 11), w * 0.56
    sh = CAT_H * k * s * 1.18
    by = h + int(sh * (0.30 if land else 0.26))
    fr.spot(cx, by - sh * 0.62, sh * 0.62, 0.45)
    if c.get('prop'): c['prop'](fr, dict(w=w, h=h, land=land, cx=cx, by=by, sh=sh))
    top = fr.cat(name, cx, by, s, 'front', c.get('expr', 'shock'), shadow=False, pose=c.get('pose', 'stand'))
    em = c.get('emote')
    if em in ('!', '?'): fr.text('！' if em == '!' else '？', min(w - 26, cx + sh * 0.36), top - 30, 230 if land else 260, TOMATO, scol=WHITE, stroke=14, rot=10)
    elif em: fr.emote(em, min(w - 24, cx + sh * 0.34), top - 4, 8)
    l1, l2, hi = c.get('line1', ''), c.get('line2', ''), c.get('hi')
    if land:
        tx, y1, mw = w * 0.34, h * 0.14, 900
        if l1: fr.text(l1, tx, y1, 110, WHITE, scol=INK, stroke=14, rot=-2, maxw=mw)
        fr.text(l2, tx, y1 + 36, 160, WHITE, hi=hi, hcol=YOU, scol=INK, stroke=20, rot=-3, shadow=TOMATO, maxw=mw)
        if c.get('tag'): fr.sticker(c['tag'], tx, y1 + 112, 64, TEAL, WHITE, -3, seed=2)
    else:
        y1 = h * (0.10 if h <= 380 else 0.15)
        if l1: fr.text(l1, w / 2, y1, 124, WHITE, scol=INK, stroke=14, rot=-2, maxw=1000)
        fr.text(l2, w / 2, y1 + 40, 186, WHITE, hi=hi, hcol=YOU, scol=INK, stroke=22, rot=-3, shadow=TOMATO, maxw=1030)
        if c.get('tag'): fr.sticker(c['tag'], w * 0.27, y1 + 118, 66, TEAL, WHITE, -4, seed=2)
    if c.get('no') is not None: fr.sticker(f"{SERIES} · {c['no']}", w - 56, 16, 36, INK, WHITE, 0, seed=9)
