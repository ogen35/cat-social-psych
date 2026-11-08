"""平涂海报风（v6，IP 造型 v2）的画布工具：在 kit_line 的基础上加贴图、Hailuo 片段播放、主角头像和平涂小件。

film.py 里这样用：

    from kit_flat import *
    flat_init(__file__)          # 告诉工具这一集的目录（片段帧在 build/clips/，本集素材在 素材/）

画法分两类：
- 角色表演镜头 = LibTV 关键帧 + Hailuo 2.3 图生视频，用 clip() 播放（见 references/平涂画风.md）。
- 卡片、实验过程、图表 = 代码画：panel() 面板、body()/head() 主角贴图、crowd() 路人猫、fish() 等平涂小件。
逻辑坐标 270×480（和 kit_line 一样），渲染是 1080×1920。
"""
import json as _json
from pathlib import Path

import numpy as np
import skia
from PIL import Image as _Image

from kit_line import *            # noqa: F401,F403  画布、文字、贴纸、pop/ease/eout/clamp、W/H、INK/TOMATO/TEAL
from kit_line import LIN
from kit import hop               # noqa: F401

STYLE = 'line'                    # build_pixel 按 line 模式渲（skia 全分辨率）
FLAT = True

# ---------------------------------------------------------------- 配色（只用这几种）
WHITE = (255, 255, 255)
CREAMBG = (250, 241, 224)         # 奶白底
FLOOR = (238, 226, 204)           # 奶白底配的地面
COBALT = (20, 88, 200)            # 钴蓝（大宝的底色）
HOTPINK = (244, 74, 140)          # 玫粉（大比的底色）
ROSE = (250, 196, 210)            # 浅玫粉
SUN = (252, 214, 48)              # 明黄（胜利的底色）
LEMON = (255, 238, 150)           # 浅黄
SKYB = (206, 228, 248)            # 浅蓝
LILAC = (226, 214, 240)           # 浅紫
BROWN = (92, 58, 40)              # 深棕
FISH = (110, 170, 226)
CAT_BG = {'大比': HOTPINK, '胜利': SUN, '大宝': COBALT}
CAT_LIGHT = {'大比': ROSE, '胜利': LEMON, '大宝': SKYB}
GROUND = 334                      # 地面线：猫的脚踩在 y≤334，字幕带从 338 开始

# 主角头像：表情名 → 设定图里的第几个表情
EXPR = {
    '大比': {'微笑': 1, '担心': 2, '震惊': 3, '哭': 4},
    '胜利': {'得意': 1, '大笑': 2, '震惊': 3, '生闷气': 4},
    '大宝': {'面无表情': 1, '斜眼': 2, '吃惊': 3, '不爽': 4},
}
CROWD = ('粉猫', '紫猫', '蓝猫')   # 路人猫三种颜色，表情 normal / happy / sad

SKILL = Path(__file__).resolve().parents[2]
LIB = SKILL / 'assets' / '平涂'
EP = None                          # 本集目录（flat_init 设置）
_ANCHOR = {}
_SPR = {}
_CLIP = {}


def flat_init(film_file):
    """film.py 开头调用一次：flat_init(__file__)。"""
    global EP
    EP = Path(film_file).resolve().parent
    for f in (LIB / '锚点.json', EP / '素材' / '锚点.json'):
        if f.exists():
            _ANCHOR.update({k.replace('\\', '/'): v[0] for k, v in _json.loads(f.read_text()).items()})


def _find(rel):
    for base in ((EP / '素材') if EP else None, LIB):
        if base and (base / rel).exists(): return base / rel
    raise FileNotFoundError(f'找不到素材 {rel}（本集 素材/ 和 assets/平涂/ 里都没有）')


def _skimg_file(p):
    p = str(p)
    if p not in _SPR:
        a = np.array(_Image.open(p).convert('RGBA'))
        _SPR[p] = (skia.Image.fromarray(np.ascontiguousarray(a), colorType=skia.kRGBA_8888_ColorType), a.shape[1], a.shape[0])
    return _SPR[p]


def sprite(fr, rel, x, by, h, a=255, flip=False, sy=1.0, rot=0):
    """透明贴图。rel：素材相对路径（先找本集 素材/，再找 assets/平涂/）；(x, by) 脚底中点；h 高度（逻辑像素）。返回顶边 y。"""
    p = _find(rel)
    img, w_, h_ = _skimg_file(p)
    k = h / h_; ax = _ANCHOR.get(rel, 0.5)
    hw = h * sy

    def fn(cv):
        pt = skia.Paint(AntiAlias=True); pt.setAlphaf(a / 255)
        cv.save(); cv.translate(x, by)
        if rot: cv.rotate(rot)
        if flip: cv.scale(-1, 1)
        cv.drawImageRect(img, skia.Rect.MakeXYWH(-w_ * k * ax, -hw, w_ * k, hw), LIN, pt); cv.restore()
    fr.draw(fn)
    return by - hw


def head(fr, name, expr, x, by, h, talk=False, a=255):
    """主角大头（反应镜头、封面）。expr 用表情名（见 EXPR）或 1–4。说话时一伸一缩。"""
    n = EXPR[name].get(expr, expr) if isinstance(expr, str) else expr
    top = sprite(fr, f'角色/{name}_表情{n}.png', x, by, h, sy=1.05 if talk else 1.0, a=a)
    fr.cats.append((name, x - h * .5, top, x + h * .5, by))
    return top


def body(fr, name, x, by, h, view='正面', flip=False, talk=False, bob=0.0, a=255):
    """主角全身贴图（正面 / 侧面 / 背面）。说话时轻轻一伸一缩；bob 是向上弹起的像素。"""
    top = sprite(fr, f'角色/{name}_{view}.png', x, by - bob, h, flip=flip, sy=1.04 if talk else 1.0, a=a)
    fr.cats.append((name, x - h * .35, top, x + h * .35, by))
    return top


_CROWD_EXPR = {None: 'normal', 'normal': 'normal', 'happy': 'happy', 'grin': 'happy', 'sad': 'sad', 'sob': 'sad', 'xx': 'sad'}


def crowd(fr, color, x, by, h, expr=None, a=255, flip=False):
    """路人猫（实验被试、人群）。color：粉猫 / 紫猫 / 蓝猫；expr：normal / happy / sad，xx = 半透明的 sad（出局）。"""
    e = _CROWD_EXPR.get(expr, 'normal')
    if expr == 'xx': a = int(a * 0.55)
    return sprite(fr, f'路人猫/{color}_{e}.png', x, by, h, a=a, flip=flip)


def clip_speech(name):
    """片段自带音轨里说话的区间（flat_clips.py fetch 量好存在 素材/片段/<镜头>.json）。"""
    f = EP / '素材' / '片段' / f'{name}.json'
    return _json.loads(f.read_text()).get('speech', []) if f.exists() else []


def clip(fr, name, t, t0, offset=None, rate=1.0, run=0, lead=0.03):
    """播放片段（build/clips/<name>/%04d.jpg，30fps）：镜头从 t0 开始。
    offset＝从片段的第几秒播起；不写就自动对口型：片段里第 run 段说话的开头，对准 t0（台词出声的时刻）。"""
    if offset is None:
        sp = clip_speech(name)
        offset = max(0.0, sp[min(run, len(sp) - 1)][0] - lead) if sp else 0.0
    d = EP / 'build' / 'clips' / name
    n = _CLIP.setdefault(name, len(list(d.glob('*.jpg'))))
    if not n: raise FileNotFoundError(f'{d} 里没有帧：先跑 scripts/flat_clips.py frames')
    i = int(clamp(((t - t0) * rate + offset) * 30, 0, n - 1)) + 1
    p = str(d / f'{i:04d}.jpg')
    img = _skimg_file(p)[0]
    _SPR.pop(p, None)                                   # 视频帧不缓存
    fr.draw(lambda cv: cv.drawImageRect(img, skia.Rect.MakeWH(W, H), LIN))


def clip_sync(fr, name, t, anchors, tail_rate=1.0):
    """一段片段里有好几句台词时用：anchors＝[(台词出声时刻, 片段里第几段说话), …]。
    在锚点之间按比例微调播放速度，让每句台词的出声都对上片段里的张嘴，画面连续不跳。"""
    sp = clip_speech(name)
    pts = [(ta, sp[min(r, len(sp) - 1)][0] - 0.03) for ta, r in anchors] if sp else [(anchors[0][0], 0.0)]
    t0, c0 = pts[0]
    if t <= t0: ct = max(0.0, c0 - (t0 - t))
    else:
        ct = None
        for (ta, ca), (tb, cb) in zip(pts, pts[1:]):
            if ta <= t < tb: ct = ca + (t - ta) * (cb - ca) / max(1e-3, tb - ta); break
        if ct is None: ct = pts[-1][1] + (t - pts[-1][0]) * tail_rate
    clip(fr, name, ct, 0.0, offset=0.0)


def clip_len(name):
    d = EP / 'build' / 'clips' / name
    return _CLIP.setdefault(name, len(list(d.glob('*.jpg')))) / 30


def backdrop(fr, rel, fx=0.5, fy=0.5, scale=1.0, x=None, y=None, w=None, h=None, a=255):
    """整张图铺底（cover 方式裁切）：rel 是素材相对路径（场景图、v3 角色图）。给 x,y,w,h 就只铺在这个框里。"""
    img, iw, ih = _skimg_file(_find(rel))
    X, Y = (0, 0) if x is None else (x, y)
    cw, ch = (fr.w, fr.h) if w is None else (w, h)          # fr.w / fr.h 是逻辑尺寸（270×480、270×360、360×270）
    k = max(cw / iw, ch / ih) * scale
    dw, dh = iw * k, ih * k
    dx = X + (cw - dw) * fx; dy = Y + (ch - dh) * fy

    def fn(cv):
        pt = skia.Paint(AntiAlias=True); pt.setAlphaf(a / 255)
        cv.save(); cv.clipRect(skia.Rect.MakeXYWH(X, Y, cw, ch))
        cv.drawImageRect(img, skia.Rect.MakeXYWH(dx, dy, dw, dh), LIN, pt); cv.restore()
    fr.draw(fn)


def panel(fr, x0, y0, x1, y1, col=WHITE, r=12, shadow=True):
    """平涂面板：纯色圆角块 + 一点下投影，没有描边。"""
    if shadow: fr.rect(x0 + 2, y0 + 3, x1 + 2, y1 + 3, (0, 0, 0), None, r=r, a=28)
    fr.rect(x0, y0, x1, y1, col, None, r=r)


def stage(fr, bg=CREAMBG, floor=None, ground=GROUND):
    """代码画镜头的底：一块纯色墙 + 一块地面色（地面线 = ground）。"""
    fr.fill(bg)
    if floor: fr.rect(0, ground, W, H, floor, None)


def fish(fr, x, y, s=1.0, col=FISH):
    """平涂小鱼：椭圆身子 + 三角尾巴。"""
    fr.ellipse(x - 9 * s, y - 5 * s, x + 7 * s, y + 5 * s, col, None)
    fr.poly([(x + 5 * s, y), (x + 13 * s, y - 6 * s), (x + 13 * s, y + 6 * s)], col, None, wobble=0)
    fr.circle(x - 4 * s, y - 1 * s, 1.4 * s, (30, 40, 70), None)


def bar(fr, x0, y0, x1, y1, frac, col, bg=(232, 226, 214), r=6):
    """平涂进度条 / 横向柱：frac 0–1。"""
    fr.rect(x0, y0, x1, y1, bg, None, r=r)
    if frac > 0: fr.rect(x0, y0, x0 + (x1 - x0) * clamp(frac), y1, col, None, r=r)


def grow(name, t, T, ids, base, big, dur=0.22):
    """连续镜头里谁说话谁变大：ids 是这一段的台词 id，返回 (当前大小, 当前台词 id)。"""
    cur = None
    for k in ids:
        if t >= T[k].start - 0.05: cur = k
    if cur is None: return base, None
    L = T[cur]
    if L.who == name: return base + (big - base) * ease((t - L.start + 0.05) / dur), cur
    j = ids.index(cur)
    if j > 0 and T[ids[j - 1]].who == name: return big - (big - base) * ease((t - L.start + 0.05) / dur), cur
    return base, cur


def talking(name, t, T):
    """这只猫此刻是否正在出声（按真实波形）。"""
    return any(L.who == name and hasattr(L, 'talk') and L.talk(t) for L in T.values())


def crew(fr, t, T, ids, faces, y=GROUND, xs=(52, 135, 218), base=58, big=78):
    """三只主角并排看（连续镜头的观众席）：说话的那只变大、一伸一缩。faces：{台词id: (大比表情, 胜利表情, 大宝表情)}，'_' 是默认。"""
    cur = None
    for k in ids:
        if t >= T[k].start - 0.05: cur = k
    f = faces.get(cur, faces.get('_', ('微笑', '得意', '面无表情')))
    for (name, x), e in zip(zip(('大比', '胜利', '大宝'), xs), f):
        h, _ = grow(name, t, T, ids, base, big)
        head(fr, name, e, x, y, h, talk=talking(name, t, T))


def flat_cover(fr, who, expr, line1, line2, hi=None, bg=None, tag=None, emote='！', crowd_col=None, crowd_expr='happy'):
    """抖音竖封面 9:16 的平涂模板：底色 = 主角的颜色，上面两行大字（hi 标黄），主角大头在中下，可选一排路人猫。"""
    bg = bg or CAT_BG[who]
    fr.fill(bg)
    if crowd_col:
        for i in range(12):
            crowd(fr, crowd_col[i % len(crowd_col)], 20 + (i % 6) * 46, 420 + (i // 6) * 40, 34, crowd_expr)
    head(fr, who, expr, 140, 436, 236)
    if emote: fr.text(emote, 246, 168, 220, TOMATO, scol=WHITE, stroke=14, rot=10)
    txt = WHITE if bg in (COBALT, HOTPINK) else INK
    sc = INK if txt == WHITE else WHITE
    fr.text(line1, W / 2, 52, 124, txt, scol=sc, stroke=14, rot=-2, maxw=1000)
    fr.text(line2, W / 2, 92, 186, WHITE, hi=hi, hcol=SUN if bg != SUN else TOMATO, scol=INK, stroke=22, rot=-3, shadow=TOMATO, maxw=1030)
    if tag: fr.sticker(tag, W * 0.25, 176, 62, TEAL, WHITE, -4, seed=2)


def flat_cover_v(fr, who, expr, line1, line2, hi=None, bg=None, tag=None, emote='！', crowd_col=None, crowd_expr='happy'):
    """抖音竖封面 3:4（270×360 的画布）：上面两行大字，主角大头在下半，可选一排路人猫。"""
    bg = bg or CAT_BG[who]
    fr.fill(bg)
    head(fr, who, expr, 132, 372, 200)
    if crowd_col:
        for i in range(6): crowd(fr, crowd_col[i % len(crowd_col)], 22 + i * 45, 362, 34, crowd_expr)
    if emote: fr.text(emote, 236, 150, 200, TOMATO, scol=WHITE, stroke=14, rot=10)
    txt = WHITE if bg in (COBALT, HOTPINK) else INK
    fr.text(line1, W / 2, 30, 118, txt, scol=INK if txt == WHITE else WHITE, stroke=14, rot=-2, maxw=1000)
    fr.text(line2, W / 2, 68, 176, WHITE, hi=hi, hcol=SUN if bg != SUN else TOMATO, scol=INK, stroke=22, rot=-3, shadow=TOMATO, maxw=1030)
    if tag: fr.sticker(tag, W * 0.25, 150, 60, TEAL, WHITE, -4, seed=2)


def flat_cover_h(fr, who, expr, line1, line2, hi=None, bg=None, tag=None):
    """横封面 4:3（360×270）。"""
    bg = bg or CAT_BG[who]
    fr.fill(bg)
    head(fr, who, expr, 268, 262, 200)
    txt = WHITE if bg in (COBALT, HOTPINK) else INK
    fr.text(line1, 122, 40, 110, txt, scol=INK if txt == WHITE else WHITE, stroke=14, rot=-2, maxw=900)
    fr.text(line2, 122, 76, 160, WHITE, hi=hi, hcol=SUN if bg != SUN else TOMATO, scol=INK, stroke=20, rot=-3, shadow=TOMATO, maxw=900)
    if tag: fr.sticker(tag, 122, 170, 64, TEAL, WHITE, -3, seed=2)
