"""常用像素道具（逻辑像素坐标），搭情境用。字一律走涂鸦层（fr.text），这里只画形状。
  phone(fr, x0, y0, x1, y1, header, msgs)   聊天界面：msgs = [('me'|'them', '文字', 小注), …]
  table(fr, y)                               会议桌（猫站在桌后，桌子挡住下半身）
  window(fr, x0, y0, x1, y1, night)          窗户（白天云 / 夜里月亮）
  floor(fr, y0, y1, top=False)               地板（侧视木纹 / 俯视方砖）
  door(fr, x0, y0, x1, y1) · car(fr, x, y, body, flip) · litter_top(fr, x0, y0, x1, y1, seed) · desk(fr, x0, x1, y)
"""
import random
from kit import INK, CARD, YOU, TOMATO, TEAL, GREY, W, H


def phone(fr, x0, y0, x1, y1, header='', msgs=(), status='23:41', size=34):
    d = fr.d
    d.rounded_rectangle([x0, y0, x1, y1], radius=10, fill=(26, 26, 34)); d.rectangle([x0 + 6, y0 + 12, x1 - 6, y1 - 10], fill=(246, 243, 236))
    d.rectangle([x0 + 6, y0 + 12, x1 - 6, y0 + 30], fill=(230, 224, 214))
    if status: fr.text(status, x0 + 10, y0 + 14, 26, (90, 90, 100), stroke=0, kind='smiley', align='l')
    if header: fr.text(header, (x0 + x1) / 2, y0 + 15, 36, stroke=0)
    y = y0 + 42
    for who, s, note in msgs:
        from doodle import font
        from PIL import ImageDraw, Image
        from doodle import tlen
        tw = tlen(ImageDraw.Draw(Image.new('RGB', (1, 1))), s, font(size)) / 4 + 10
        if who == 'me': bx1 = x1 - 12; bx0 = bx1 - tw; col = (250, 214, 110)
        else: bx0 = x0 + 12; bx1 = bx0 + tw; col = (255, 255, 255)
        d.rounded_rectangle([bx0, y, bx1, y + 16], radius=4, fill=col, outline=(214, 208, 196))
        fr.text(s, (bx0 + bx1) / 2, y + 2, size, stroke=0)
        if note: fr.text(note, bx1 if who == 'me' else bx0, y + 18, 26, (140, 136, 130), stroke=0, align='r' if who == 'me' else 'l')
        y += 32


def table(fr, y=290, x0=4, x1=266):
    d = fr.d
    d.rectangle([x0 + 2, y + 2, x1 + 2, y + 12], fill=GREY); d.rectangle([x0, y, x1, y + 10], fill=(166, 120, 78), outline=INK)
    for x in (x0 + 12, x1 - 16): d.rectangle([x, y + 10, x + 4, y + 44], fill=(120, 84, 52))


def window(fr, x0, y0, x1, y1, night=False):
    d = fr.d
    d.rectangle([x0, y0, x1, y1], fill=(96, 70, 52)); d.rectangle([x0 + 4, y0 + 4, x1 - 4, y1 - 4], fill=(30, 36, 60) if night else (166, 214, 236))
    mx = (x0 + x1) // 2; d.line([(mx, y0 + 4), (mx, y1 - 4)], fill=(96, 70, 52), width=2)
    if night:
        d.ellipse([mx + 6, y0 + 10, mx + 20, y0 + 24], fill=(250, 232, 170)); d.ellipse([mx + 10, y0 + 9, mx + 23, y0 + 21], fill=(30, 36, 60))
        for k in range(4): d.point((x0 + 8 + k * 11, y0 + 14 + (k % 2) * 12), fill=(230, 230, 200))
    else:
        d.rectangle([x0 + 10, y0 + 12, x0 + 22, y0 + 15], fill=(255, 255, 255)); d.rectangle([x0 + 13, y0 + 9, x0 + 19, y0 + 12], fill=(255, 255, 255))


def floor(fr, y0, y1=None, top=False, c1=(222, 210, 190), c2=(212, 198, 176)):
    d = fr.d; y1 = fr.h if y1 is None else y1; W = fr.w
    if top:
        for y in range(y0, y1, 16):
            for x in range(0, W, 16):
                d.rectangle([x, y, x + 15, y + 15], fill=c2 if (x // 16 + y // 16) % 2 else c1)
    else:
        d.rectangle([0, y0, W, y1], fill=(184, 138, 95))
        for y in range(y0 + 6, y1, 8): d.line([(0, y), (W, y)], fill=(160, 118, 82))


def door(fr, x0, y0, x1, y1, col=(150, 104, 66)):
    d = fr.d; d.rectangle([x0, y0, x1, y1], fill=col, outline=INK); d.ellipse([x1 - 9, (y0 + y1) // 2, x1 - 5, (y0 + y1) // 2 + 4], fill=YOU)


def car(fr, x, y, body=(229, 83, 60), flip=False, k=1):
    """侧视小汽车（敞篷）：x 是车中心，y 是轮子底，k 是放大倍数。"""
    d = fr.d; s = -1 if flip else 1; q = lambda a, b: (x + a * k * s, y + b * k)
    d.rounded_rectangle([x - 34 * k, y - 22 * k, x + 34 * k, y - 6 * k], radius=5 * k, fill=body, outline=INK, width=k)
    d.polygon([q(-22, -22), q(-14, -30), q(-6, -30), q(-2, -22)], fill=(180, 220, 240), outline=INK)
    for wx in (-20, 20):
        cx, cy = q(wx, -6); d.ellipse([cx - 7 * k, cy - 7 * k, cx + 7 * k, cy + 7 * k], fill=INK); d.ellipse([cx - 3 * k, cy - 3 * k, cx + 3 * k, cy + 3 * k], fill=GREY)
    hx, hy = q(30, -18); d.rectangle([hx - 2 * k, hy, hx + 1 * k, hy + 4 * k], fill=(255, 238, 160))


def litter_top(fr, x0, y0, x1, y1, seed=0):
    """俯视猫砂盆。"""
    d = fr.d; rng = random.Random(seed)
    d.rounded_rectangle([x0, y0, x1, y1], radius=10, fill=(92, 150, 172)); d.rounded_rectangle([x0 + 12, y0 + 10, x1 - 12, y1 - 10], radius=6, fill=(230, 210, 164))
    for _ in range((x1 - x0) * (y1 - y0) // 30):
        d.point((rng.randint(x0 + 14, x1 - 14), rng.randint(y0 + 12, y1 - 12)), fill=(206, 184, 136) if rng.random() < .7 else (244, 230, 196))


def desk(fr, x0, x1, y, monitor=True):
    d = fr.d
    d.rectangle([x0, y, x1, y + 7], fill=(140, 98, 57)); d.rectangle([x0 + 4, y + 7, x0 + 8, y + 50], fill=(110, 76, 44)); d.rectangle([x1 - 8, y + 7, x1 - 4, y + 50], fill=(110, 76, 44))
    if monitor:
        cx = (x0 + x1) // 2; d.rectangle([cx - 26, y - 36, cx + 26, y - 4], fill=(40, 44, 58)); d.rectangle([cx - 23, y - 33, cx + 23, y - 8], fill=(120, 206, 190)); d.rectangle([cx - 4, y - 4, cx + 4, y], fill=(40, 44, 58))
