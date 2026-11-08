"""线条萌猫（B 画风）原型：skia 矢量绘制，深棕粗描边、头身一体、豆豆眼，线条每 3 帧轻微抖动（line boil）。
坐标：猫的脚底中心 (x, y)，s = 猫的高度（像素）。猫内部用单位坐标：脚底 y=0，头顶 y=-1。
"""
import math
import random
import skia

LINE = (58, 38, 28)
WHITE = (255, 255, 255)
PINK = (255, 150, 150)
MOUTH = (150, 52, 52)
TONGUE = (238, 120, 120)
TEAR = (120, 190, 240)
GOLD = (255, 210, 70)

CAST = {
    '大比': dict(body=(252, 246, 234), accent=(104, 72, 56), eye=(38, 56, 110), hw=0.43, bw=0.45, k=1.0, tail='fluff', ear=0.17, sig='normal', aw=0.13),
    '胜利': dict(body=(248, 192, 76), accent=(222, 146, 40), eye=LINE, hw=0.39, bw=0.37, k=1.03, tail='big', ear=0.2, sig='smug', aw=0.11, leg=0.07),
    '大宝': dict(body=(150, 160, 180), accent=(98, 106, 128), eye=LINE, hw=0.45, bw=0.48, k=1.15, tail='norm', ear=0.19, sig='flat', aw=0.13),
}
# 模拟实验里的「实验猫」：不是主角，没有招牌特征，只靠颜色区分策略（名字就是策略名）
CAST.update({
    '好人猫': dict(body=(252, 196, 208), accent=(232, 150, 168), eye=LINE, hw=0.43, bw=0.45, k=1.0, tail='fluff', ear=0.18, sig='happy', aw=0.12),
    '坑人猫': dict(body=(156, 132, 180), accent=(120, 98, 146), eye=LINE, hw=0.42, bw=0.43, k=1.0, tail='norm', ear=0.2, sig='sideeye', aw=0.12),
    '互惠猫': dict(body=(150, 204, 236), accent=(104, 164, 206), eye=LINE, hw=0.43, bw=0.45, k=1.0, tail='norm', ear=0.18, sig='normal', aw=0.12),
})
POSES = ('stand', 'cheer', 'jump', 'headhold', 'akimbo', 'point', 'think', 'shrug', 'flop', 'slump')
EXPRS = ('normal', 'happy', 'smug', 'flat', 'shock', 'blank', 'star', 'love', 'xx', 'dizzy', 'sob', 'cry', 'rage', 'grin', 'gloom', 'sad', 'sideeye')


def col(rgb, a=255): return skia.Color(int(rgb[0]), int(rgb[1]), int(rgb[2]), int(a))


def paint(rgb, a=255, stroke=None, cap='round'):
    p = skia.Paint(AntiAlias=True, Color=col(rgb, a))
    if stroke is not None:
        p.setStyle(skia.Paint.kStroke_Style); p.setStrokeWidth(stroke)
        p.setStrokeCap(skia.Paint.kRound_Cap if cap == 'round' else skia.Paint.kButt_Cap); p.setStrokeJoin(skia.Paint.kRound_Join)
    return p


def spline(pts, closed=True, t=1.0):
    n = len(pts); p = skia.Path(); p.moveTo(*pts[0])
    for i in (range(n) if closed else range(n - 1)):
        p0 = pts[(i - 1) % n] if (closed or i > 0) else pts[i]
        p1, p2 = pts[i], pts[(i + 1) % n]
        p3 = pts[(i + 2) % n] if (closed or i + 2 < n) else p2
        c1 = (p1[0] + (p2[0] - p0[0]) / 6 * t, p1[1] + (p2[1] - p0[1]) / 6 * t)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6 * t, p2[1] - (p3[1] - p1[1]) / 6 * t)
        p.cubicTo(*c1, *c2, *p2)
    if closed: p.close()
    return p


def jit(pts, key, boil, amp=0.006):
    if amp <= 0: return list(pts)
    r = random.Random(f'{key}|{boil}')
    return [(x + r.uniform(-amp, amp), y + r.uniform(-amp, amp)) for x, y in pts]


def ellipse_pts(cx, cy, rx, ry, n=12, a0=0.0):
    return [(cx + rx * math.cos(a0 + 2 * math.pi * i / n), cy + ry * math.sin(a0 + 2 * math.pi * i / n)) for i in range(n)]


def arc_pts(cx, cy, rx, ry, a0, a1, n=8):
    return [(cx + rx * math.cos(a0 + (a1 - a0) * i / (n - 1)), cy + ry * math.sin(a0 + (a1 - a0) * i / (n - 1))) for i in range(n)]


class Pen:
    """在单位坐标里画：lw 是描边宽度（单位）。"""
    def __init__(self, cv, lw, boil, key):
        self.cv, self.lw, self.boil, self.key, self.n = cv, lw, boil, key, 0

    def _k(self): self.n += 1; return f'{self.key}{self.n}'

    def line(self, pts, rgb=LINE, w=None, a=255, amp=0.004, smooth=True):
        pts = jit(pts, self._k(), self.boil, amp)
        path = spline(pts, closed=False) if (smooth and len(pts) > 2) else _poly(pts, False)
        self.cv.drawPath(path, paint(rgb, a, stroke=w or self.lw))

    def blob(self, pts, fill, outline=True, amp=0.004, w=None, a=255):
        pts = jit(pts, self._k(), self.boil, amp); path = spline(pts)
        if fill is not None: self.cv.drawPath(path, paint(fill, a))
        if outline: self.cv.drawPath(path, paint(LINE, a, stroke=w or self.lw))
        return path

    def dot(self, x, y, r, rgb=LINE, a=255):
        self.cv.drawCircle(x, y, r, paint(rgb, a))

    def tube(self, pts, w, fill, amp=0.004):
        """有描边的粗管子（尾巴、手臂）。"""
        pts = jit(pts, self._k(), self.boil, amp); path = spline(pts, closed=False) if len(pts) > 2 else _poly(pts, False)
        self.cv.drawPath(path, paint(LINE, stroke=w + 2 * self.lw)); self.cv.drawPath(path, paint(fill, stroke=w))
        return pts


def _poly(pts, closed=True):
    p = skia.Path(); p.moveTo(*pts[0])
    for q in pts[1:]: p.lineTo(*q)
    if closed: p.close()
    return p


def _ear(c, side, droop, P):
    hw = c['hw']; e = c['ear']
    if droop:
        bi, bo, tip, inside = (hw * 0.42, -0.955), (hw * 0.96, -0.80), (hw * 1.10, -0.68), (hw * 0.6, -0.80)
    else:
        bi, bo, tip, inside = (hw * 0.20, -0.985), (hw * 0.97, -0.82), (hw * 0.72, -1.0 - e), (hw * 0.55, -0.84)
    pts = [bi, tip, bo, inside]
    return [P(side * x, y) for x, y in pts]


def _ear_path(q, r=0.035):
    bi, tip, bo, ins = q
    def toward(a, b, d):
        L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1; return (a[0] + (b[0] - a[0]) * d / L, a[1] + (b[1] - a[1]) * d / L)
    p = skia.Path(); p.moveTo(*ins); p.lineTo(*bi); p.lineTo(*toward(tip, bi, r)); p.quadTo(*tip, *toward(tip, bo, r)); p.lineTo(*bo); p.close()
    return p


def _arms(pose, c):
    """返回 [(肩, 肘, 爪), ...]，右手在前（x>0），单位坐标。"""
    b, h = c['bw'], c['hw']
    R = {
        'stand':    ((b * .62, -.50), (b * .80, -.40), (b * .64, -.29)),
        'cheer':    ((b * .66, -.55), (b + .10, -.74), (b + .14, -.98)),
        'jump':     ((b * .66, -.55), (b + .14, -.70), (b + .22, -.90)),
        'headhold': ((b * .66, -.52), (h + .10, -.60), (h * .80, -.84)),
        'akimbo':   ((b * .66, -.52), (b + .20, -.42), (b * .86, -.27)),
        'point':    ((b * .66, -.55), (b + .18, -.58), (b + .42, -.66)),
        'think':    ((b * .62, -.48), (b * .62, -.34), (h * .22, -.60)),
        'shrug':    ((b * .66, -.50), (b + .14, -.42), (b + .30, -.56)),
        'flop':     ((b * .70, -.30), (b + .10, -.18), (b + .20, -.07)),
        'slump':    ((b * .62, -.46), (b * .78, -.30), (b * .66, -.12)),
    }
    L = {'point': ((b * .62, -.50), (b * .80, -.40), (b * .64, -.29)), 'think': ((b * .62, -.50), (b * .82, -.40), (b * .60, -.28))}
    r = R[pose]; l = L.get(pose, r)
    return [r, tuple((-x, y) for x, y in l)]


def _toes(pen, elbow, paw, w):
    dx, dy = paw[0] - elbow[0], paw[1] - elbow[1]; L = math.hypot(dx, dy) or 1; dx, dy = dx / L, dy / L; nx, ny = -dy, dx
    for k in (-1, 1):
        x0, y0 = paw[0] + nx * k * w * 0.18 + dx * w * 0.42, paw[1] + ny * k * w * 0.18 + dy * w * 0.42
        pen.line([(x0, y0), (x0 - dx * w * 0.32, y0 - dy * w * 0.32)], w=pen.lw * 0.7, amp=0.002, smooth=False)


def draw_cat(cv, name, x, y, s, expr=None, pose='stand', talk=False, look=0.0, boil=0, flip=False, rot=0.0,
             sx=1.0, sy=1.0, wag=0.0, blink=False, blush=None, lw_px=None, view='front'):
    """view：front 正面（look -1…1 让脸转向一侧，当侧脸用）/ back 背面（没有脸，尾巴在前）。"""
    c = CAST[name]; S = s * c['k']; lw = (lw_px or max(3.0, s * 0.024)) / S
    back = view == 'back'
    if back: look = 0
    E = expr or c['sig']
    if pose == 'flop': sx, sy = sx * 1.32, sy * 0.58
    if pose == 'slump': sy *= 0.9
    if pose == 'jump': sy *= 1.04
    P = lambda px, py: (px * sx, py * sy)
    cv.save(); cv.translate(x, y); cv.rotate(rot)
    cv.scale(-S if flip else S, S)
    pen = Pen(cv, lw, boil, name)
    hw, bw = c['hw'], c['bw']; leg = c.get('leg', 0)

    # ---- 尾巴（在身体后面）
    T = {'fluff': ([(bw * .55, -.12), (bw * 1.05, -.10), (bw * 1.30, -.22), (bw * 1.22, -.36)], .15),
         'big':   ([(bw * .60, -.16), (bw * 1.25, -.20), (bw * 1.50, -.42), (bw * 1.38, -.66), (bw * 1.50, -.82)], .12),
         'norm':  ([(bw * .60, -.10), (bw * 1.20, -.12), (bw * 1.42, -.30), (bw * 1.36, -.50)], .12)}[c['tail']]
    tp, tw = T
    if pose == 'flop': tp = [(bw * .6, -.08), (bw * .95, -.07), (bw * 1.18, -.10), (bw * 1.32, -.06)]
    if wag:
        r0 = tp[0]; ca, sa = math.cos(wag), math.sin(wag)
        tp = [r0] + [(r0[0] + (px - r0[0]) * ca - (py - r0[1]) * sa, r0[1] + (px - r0[0]) * sa + (py - r0[1]) * ca) for px, py in tp[1:]]
    if not back: pen.tube([P(*q) for q in tp], tw, c['body'])

    # ---- 身体轮廓（头身一体 + 两只耳朵）
    R = [(0, -1.0), (hw * .62, -.975), (hw * .95, -.87), (hw, -.74), (hw * .93, -.62), (bw * .95, -.47), (bw, -.28), (bw * .93, -.10),
         (bw * .72, -.005), (bw * .40, 0.0), (bw * .14, -.02 - leg)]
    pts = R + [(0, -.055 - leg * 1.6)] + [(-px, py) for px, py in reversed(R[1:])]
    pts = jit([P(*q) for q in pts], name + 'body', boil, 0.005)
    sil = spline(pts)
    droop = pose in ('flop', 'slump') or E in ('gloom', 'sob')
    ears = []
    flaps = []
    for side in (1, -1):
        q = jit(_ear(c, side, False, P), f'{name}ear{side}', boil, 0.005)
        if droop:   # 耷拉耳朵：单独画成盖在头侧的耳片（完整描边），不并进轮廓
            fp = [P(side * hw * .50, -.965), P(side * hw * 1.0, -.80), P(side * hw * 1.24, -.60)]
            flaps.append(jit(fp, f'{name}flap{side}', boil, .004)); continue
        ears.append(q)
        sil = skia.Op(sil, _ear_path(q), skia.PathOp.kUnion_PathOp)
    cv.drawPath(sil, paint(c['body']))
    cv.save(); cv.clipPath(sil, doAntiAlias=True)
    if name == '大比':
        for q in ears:
            bi, tip, bo, _ = q
            cv.drawPath(_poly([(bi[0] + (tip[0] - bi[0]) * .42, bi[1] + (tip[1] - bi[1]) * .42), (tip[0] + (tip[0] - bi[0]) * .3, tip[1] - .08),
                               (bo[0] + (tip[0] - bo[0]) * .42, bo[1] + (tip[1] - bo[1]) * .42)]), paint(c['accent']))
    if name == '大宝' and back:
        for dy_ in (-.62, -.50, -.38): pen.line([P(-.12, dy_), P(0, dy_ + .03), P(.12, dy_)], rgb=c['accent'], w=lw * 1.2)
    if name == '大宝' and not back:
        for dxs in (-.075, 0, .075):
            pen.line([P(dxs + look * .05, -.985), P(dxs * 1.1 + look * .05, -.905)], rgb=c['accent'], w=lw * 1.2, smooth=False)
    if E == 'gloom':
        g = skia.Paint(AntiAlias=True); g.setShader(skia.GradientShader.MakeLinear([skia.Point(0, -1.15 * sy), skia.Point(0, -0.70 * sy)], [col((70, 70, 130), 120), col((70, 70, 130), 0)]))
        cv.drawRect(skia.Rect.MakeLTRB(-1, -1.3, 1, -0.6 * sy), g)
    cv.restore()
    cv.drawPath(sil, paint(LINE, stroke=lw))
    for a, b2, tip in flaps:
        fpth = _ear_path((a, tip, b2, ((a[0] + b2[0]) / 2, (a[1] + b2[1]) / 2 + .02)), r=.05)
        cv.drawPath(fpth, paint(c['body']))
        if name == '大比':
            cv.save(); cv.clipPath(fpth, doAntiAlias=True); cv.drawCircle(*tip, .13, paint(c['accent'])); cv.restore()
        cv.drawPath(fpth, paint(LINE, stroke=lw))
    if pose != 'flop' and leg < 0.05 and not back:
        pen.line([P(0, -.06), P(0, -.13)], w=lw * .8, smooth=False)
    if name == '大宝':
        for q in ears:
            bi, tip, bo, _ = q
            pen.line([tip, (tip[0] + (.02 if tip[0] > 0 else -.02), tip[1] - .07)], w=lw * .9, smooth=False)

    # ---- 脸（背面不画）；背面时尾巴画在身体前面
    hc = P(look * hw * 0.30, -.735 + (.04 if pose == 'slump' else 0))
    if back:
        pen.tube([P(-px, py) for px, py in tp], tw, c['body'])
    else:
        face(pen, c, name, E, hc, talk, blink, look, blush)

    # ---- 手臂（在身体前面）
    interior = None
    for (sh, el, pw) in ([] if back else _arms(pose, c)):
        sh, el, pw = P(*sh), P(*el), P(*pw)
        q = pen.tube([sh, el, pw], c['aw'], c['body'])
        if interior is None:
            ring = skia.Path(); paint(LINE, stroke=lw * 1.05).getFillPath(sil, ring)
            interior = skia.Op(sil, ring, skia.PathOp.kDifference_PathOp)
        cv.save(); cv.clipPath(interior, doAntiAlias=True); cv.drawCircle(q[0][0], q[0][1], c['aw'] / 2 + lw * 1.1, paint(c['body'])); cv.restore()
        _toes(pen, q[1], q[2], c['aw'])

    # ---- 王冠
    if name == '胜利':
        cx0, cy0 = P(look * hw * .3 + .06, -.985)
        cv.save(); cv.translate(cx0, cy0); cv.rotate(12)
        cr = [(-.12, 0), (-.15, -.17), (-.07, -.08), (0, -.20), (.07, -.08), (.15, -.17), (.12, 0)]
        cr = jit(cr, 'crown', boil, .004)
        cv.drawPath(_poly(cr), paint(GOLD)); cv.drawPath(_poly(cr), paint(LINE, stroke=lw * .85))
        for tx, ty in (cr[1], cr[3], cr[5]): cv.drawCircle(tx, ty, .022, paint(GOLD)); cv.drawCircle(tx, ty, .022, paint(LINE, stroke=lw * .7))
        cv.drawCircle(0, -.05, .022, paint((230, 70, 70)))
        cv.restore()
    cv.restore()
    return dict(top=y - S * (1.0 + c['ear']) * sy, head=(x + (-1 if flip else 1) * hc[0] * S, y + hc[1] * S), S=S)


def face(pen, c, name, E, hc, talk, blink, look, blush):
    hx, hy = hc; hw = c['hw']; ex = hw * .40; lw = pen.lw; cv = pen.cv
    L, Rr = (hx - ex, hy - .01), (hx + ex, hy - .01)
    my = hy + .125
    eye = c['eye']
    # 胡须小短线
    if E not in ('gloom',):
        for sd in (-1, 1):
            bx = hx + sd * hw * .80
            for j, dy in enumerate((-.02, .035)):
                pen.line([(bx, hy + dy), (bx + sd * .07, hy + dy + (.012 if j else -.006))], w=lw * .7, smooth=False, amp=.002)
    mouth = None
    if blink and E in ('normal', 'flat', 'sad', 'cry', 'rage', 'sideeye'):
        for (ox, oy) in (L, Rr): pen.line([(ox - .04, oy), (ox + .04, oy)], w=lw * 1.1, smooth=False)
        E2 = 'blinked'
    else:
        E2 = E
    if E2 == 'normal' or E2 == 'cry' or E2 == 'sad' or E2 == 'rage':
        for (ox, oy) in (L, Rr):
            cv.drawOval(skia.Rect.MakeXYWH(ox - .036, oy - .047, .072, .094), paint(eye))
            cv.drawCircle(ox + .012, oy - .02, .014, paint(WHITE))
        if name == '大比' or E2 == 'sad':
            for sd, (ox, oy) in ((-1, L), (1, Rr)): pen.line([(ox - sd * .01, oy - .085), (ox + sd * .055, oy - .065)], w=lw * .85, smooth=False)
        if E2 == 'rage':
            for sd, (ox, oy) in ((-1, L), (1, Rr)): pen.line([(ox - sd * .05, oy - .10), (ox + sd * .03, oy - .065)], w=lw * 1.2, smooth=False)
        if E2 == 'cry':
            pen.blob([(Rr[0] + .02, Rr[1] + .05), (Rr[0] + .045, Rr[1] + .11), (Rr[0] + .02, Rr[1] + .135), (Rr[0] - .005, Rr[1] + .11)], TEAR, w=lw * .7)
        mouth = 'frown' if E2 in ('sad', 'cry') else ('teeth' if E2 == 'rage' else 'w')
    elif E2 == 'smug':
        for sd, (ox, oy) in ((-1, L), (1, Rr)):
            pen.line(arc_pts(ox, oy - .02, .045, .028, math.pi * .05, math.pi * .95, 6), w=lw * 1.1)
        mouth = 'w'; blush = True if blush is None else blush
    elif E2 == 'flat':
        for (ox, oy) in (L, Rr):
            p = skia.Path(); p.moveTo(ox - .04, oy); p.lineTo(ox + .04, oy); p.arcTo(skia.Rect.MakeXYWH(ox - .04, oy - .04, .08, .08), 0, 180, False); p.close()
            cv.drawPath(p, paint(eye)); pen.line([(ox - .055, oy - .002), (ox + .055, oy + .004)], w=lw * 1.1, smooth=False)
        mouth = 'flat'
    elif E2 == 'sideeye':
        for (ox, oy) in (L, Rr):
            cv.drawOval(skia.Rect.MakeXYWH(ox - .05, oy - .035, .10, .07), paint(WHITE)); cv.drawOval(skia.Rect.MakeXYWH(ox - .05, oy - .035, .10, .07), paint(LINE, stroke=lw * .8))
            cv.drawCircle(ox + .03 * (1 if look >= 0 else -1), oy, .022, paint(LINE))
            pen.line([(ox - .06, oy - .03), (ox + .06, oy - .045)], w=lw * 1.1, smooth=False)
        mouth = 'flat'
    elif E2 == 'happy' or E2 == 'grin':
        for (ox, oy) in (L, Rr): pen.line(arc_pts(ox, oy + .02, .045, .04, math.pi * 1.1, math.pi * 1.9, 6), w=lw * 1.1)
        mouth = 'smile' if E2 == 'grin' else 'w'; blush = True if blush is None else blush
    elif E2 in ('shock', 'blank'):
        r = .068 if E2 == 'blank' else .058
        for (ox, oy) in (L, Rr):
            cv.drawCircle(ox, oy, r, paint(WHITE)); cv.drawCircle(ox, oy, r, paint(LINE, stroke=lw * .9))
            cv.drawCircle(ox, oy, .014 if E2 == 'blank' else .024, paint(LINE))
        mouth = 'scream' if E2 == 'blank' else 'open'
    elif E2 == 'star':
        for (ox, oy) in (L, Rr):
            st = [(ox + (.07 if i % 2 == 0 else .03) * math.cos(-math.pi / 2 + i * math.pi / 5), oy + (.07 if i % 2 == 0 else .03) * math.sin(-math.pi / 2 + i * math.pi / 5)) for i in range(10)]
            cv.drawPath(_poly(st), paint(GOLD)); cv.drawPath(_poly(st), paint(LINE, stroke=lw * .7))
        mouth = 'smile'; blush = True if blush is None else blush
    elif E2 == 'love':
        for (ox, oy) in (L, Rr):
            p = skia.Path(); r = .032
            p.moveTo(ox, oy + .05); p.cubicTo(ox - .09, oy - .01, ox - .04, oy - .07, ox, oy - .025); p.cubicTo(ox + .04, oy - .07, ox + .09, oy - .01, ox, oy + .05); p.close()
            cv.drawPath(p, paint((240, 80, 100))); cv.drawPath(p, paint(LINE, stroke=lw * .7))
        mouth = 'smile'; blush = True if blush is None else blush
    elif E2 == 'xx':
        for (ox, oy) in (L, Rr):
            pen.line([(ox - .04, oy - .04), (ox + .04, oy + .04)], w=lw * 1.1, smooth=False); pen.line([(ox + .04, oy - .04), (ox - .04, oy + .04)], w=lw * 1.1, smooth=False)
        mouth = 'wavy'
    elif E2 == 'dizzy':
        for (ox, oy) in (L, Rr):
            sp = [(ox + .005 * i * math.cos(i * .9), oy + .005 * i * math.sin(i * .9)) for i in range(2, 13)]
            pen.line(sp, w=lw * .9, amp=0)
        mouth = 'wavy'
    elif E2 == 'sob':
        for (ox, oy) in (L, Rr):
            pen.line(arc_pts(ox, oy + .025, .045, .035, math.pi * 1.1, math.pi * 1.9, 6), w=lw * 1.1)
            pen.tube([(ox, oy + .04), (ox - .005, oy + .14), (ox + .005, oy + .24)], .03, TEAR, amp=.003)
        for sd, (ox, oy) in ((-1, L), (1, Rr)): pen.line([(ox - sd * .01, oy - .085), (ox + sd * .055, oy - .06)], w=lw * .85, smooth=False)
        mouth = 'scream'
    elif E2 == 'gloom':
        for (ox, oy) in (L, Rr): cv.drawOval(skia.Rect.MakeXYWH(ox - .026, oy - .02, .052, .06), paint(eye))
        for i in range(4): pen.line([(hx - .14 + i * .09, hy - .26), (hx - .14 + i * .09, hy - .15)], rgb=(90, 90, 150), w=lw * .8, smooth=False)
        mouth = 'frown'
    elif E2 == 'blinked':
        mouth = 'w' if E != 'flat' else 'flat'
    # 鼻子
    cv.drawOval(skia.Rect.MakeXYWH(hx - .02, my - .05, .04, .026), paint((236, 140, 140)))
    if blush:
        for sd in (-1, 1): cv.drawOval(skia.Rect.MakeXYWH(hx + sd * hw * .52 - .05, hy + .06, .10, .045), paint(PINK, 150))
    if talk and mouth in ('w', 'flat', 'frown'): mouth = 'talk'
    _mouth(pen, mouth or 'w', hx, my)


def _mouth(pen, m, hx, my):
    cv, lw = pen.cv, pen.lw
    if m == 'w':
        pen.line(arc_pts(hx - .03, my - .012, .03, .028, 0, math.pi, 6), w=lw * .9); pen.line(arc_pts(hx + .03, my - .012, .03, .028, 0, math.pi, 6), w=lw * .9)
    elif m == 'flat':
        pen.line([(hx - .035, my + .01), (hx + .035, my + .01)], w=lw * .9, smooth=False)
    elif m == 'frown':
        pen.line(arc_pts(hx, my + .045, .045, .03, math.pi * 1.15, math.pi * 1.85, 6), w=lw * .9)
    elif m == 'wavy':
        pen.line([(hx - .06 + i * .02, my + .01 + (.012 if i % 2 else -.012)) for i in range(7)], w=lw * .85, smooth=False)
    elif m in ('talk', 'open', 'scream', 'smile'):
        w, h = {'talk': (.075, .07), 'open': (.09, .10), 'scream': (.12, .17), 'smile': (.13, .09)}[m]
        if m == 'smile':
            p = skia.Path(); p.moveTo(hx - w / 2, my - .01); p.lineTo(hx + w / 2, my - .01); p.cubicTo(hx + w / 2, my + h, hx - w / 2, my + h, hx - w / 2, my - .01); p.close()
        elif m == 'scream':
            p = spline([(hx - w * .35, my - .01), (hx + w * .35, my - .01), (hx + w * .5, my + h * .8), (hx, my + h), (hx - w * .5, my + h * .8)])
        else:
            p = spline(ellipse_pts(hx, my + h * .4, w / 2, h / 2, 10))
        cv.drawPath(p, paint(MOUTH)); cv.save(); cv.clipPath(p, doAntiAlias=True)
        cv.drawOval(skia.Rect.MakeXYWH(hx - w * .4, my + h * .55, w * .8, h * .7), paint(TONGUE)); cv.restore()
        cv.drawPath(p, paint(LINE, stroke=lw * .9))
    elif m == 'teeth':
        r = skia.Rect.MakeXYWH(hx - .06, my - .01, .12, .06)
        cv.drawRoundRect(r, .02, .02, paint(WHITE)); cv.drawRoundRect(r, .02, .02, paint(LINE, stroke=lw * .8))
        pen.line([(hx - .06, my + .02), (hx + .06, my + .02)], w=lw * .6, smooth=False)
        for i in (-1, 0, 1): pen.line([(hx + i * .03, my - .01), (hx + i * .03, my + .05)], w=lw * .6, smooth=False)


# ================= 特效（像素坐标）
def shock_lines(cv, x, y, s, boil=0, n=3):
    r = random.Random(boil)
    for i in range(n):
        a = math.radians(-90 + (i - (n - 1) / 2) * 28)
        x0, y0 = x + math.cos(a) * s * .55, y + math.sin(a) * s * .55
        x1, y1 = x + math.cos(a) * s * (.95 + r.uniform(-.05, .05)), y + math.sin(a) * s * (.95 + r.uniform(-.05, .05))
        cv.drawLine(x0, y0, x1, y1, paint(LINE, stroke=s * .07))


def sweat(cv, x, y, s, rgb=TEAR):
    p = skia.Path(); p.moveTo(x, y - s * .5); p.cubicTo(x + s * .45, y + s * .05, x + s * .3, y + s * .5, x, y + s * .5)
    p.cubicTo(x - s * .3, y + s * .5, x - s * .45, y + s * .05, x, y - s * .5); p.close()
    cv.drawPath(p, paint(rgb)); cv.drawPath(p, paint(LINE, stroke=s * .09)); cv.drawCircle(x - s * .1, y + s * .15, s * .07, paint(WHITE))


def soul(cv, x, y, s, t, boil=0):
    """小灵魂从头顶飘出：t 0→1 上升。"""
    yy = y - s * 1.2 * t; sway = math.sin(t * 9) * s * .12
    body = [(x + sway, yy - s * .5), (x + s * .38 + sway, yy - s * .2), (x + s * .3 + sway, yy + s * .25), (x + s * .1, yy + s * .6),
            (x - s * .05 - sway * .5, yy + s * .95), (x - s * .25, yy + s * .45), (x - s * .38 + sway, yy - s * .05)]
    body = jit(body, 'soul', boil, s * .02); p = spline(body)
    cv.drawPath(p, paint(WHITE, 235)); cv.drawPath(p, paint(LINE, stroke=s * .07))
    cv.drawCircle(x - s * .1 + sway, yy - s * .12, s * .05, paint(LINE)); cv.drawCircle(x + s * .1 + sway, yy - s * .12, s * .05, paint(LINE))
    cv.drawOval(skia.Rect.MakeXYWH(x - s * .04 + sway, yy + s * .02, s * .08, s * .1), paint(LINE))


def vein(cv, x, y, s, rgb=(230, 70, 60)):
    for a in (45, 135, 225, 315):
        r = math.radians(a); cx, cy = x + math.cos(r) * s * .3, y + math.sin(r) * s * .3
        cv.drawArc(skia.Rect.MakeXYWH(cx - s * .25, cy - s * .25, s * .5, s * .5), a + 90, 180, False, paint(rgb, stroke=s * .14))


def sparkles(cv, cx, cy, r, t, n=5, seed=0, rgb=GOLD):
    rr = random.Random(seed)
    for i in range(n):
        a = rr.uniform(0, 6.28); d = r * rr.uniform(.6, 1.1); ph = (t * 3 + rr.random()) % 1
        k = math.sin(ph * math.pi) * r * .22
        if k < r * .02: continue
        x, y = cx + math.cos(a) * d, cy + math.sin(a) * d
        st = [(x, y - k), (x + k * .25, y - k * .25), (x + k, y), (x + k * .25, y + k * .25), (x, y + k), (x - k * .25, y + k * .25), (x - k, y), (x - k * .25, y - k * .25)]
        cv.drawPath(_poly(st), paint(rgb)); cv.drawPath(_poly(st), paint(LINE, stroke=max(2, k * .12)))


def focus(cv, w, h, cx, cy, boil=0, n=60, rgb=LINE, a=150, inner=0.42):
    r = random.Random(boil); R = math.hypot(w, h)
    for i in range(n):
        ang = 2 * math.pi * i / n + r.uniform(-.03, .03); r0 = min(w, h) * inner * r.uniform(.9, 1.25)
        x0, y0 = cx + math.cos(ang) * r0, cy + math.sin(ang) * r0; x1, y1 = cx + math.cos(ang) * R, cy + math.sin(ang) * R
        p = skia.Path(); nx, ny = -math.sin(ang), math.cos(ang); ww = r.uniform(4, 12)
        p.moveTo(x0, y0); p.lineTo(x1 + nx * ww, y1 + ny * ww); p.lineTo(x1 - nx * ww, y1 - ny * ww); p.close()
        cv.drawPath(p, paint(rgb, a))


def doodle_bg(cv, w, h, bg, ink, boil=0, kind='road', horizon=0.56):
    """纯色底 + 同色系简笔场景。"""
    cv.clear(col(bg)); lw = w * 0.0065; pen = Pen(cv, lw, boil, 'bg' + kind)
    y0 = h * horizon
    if kind == 'road':
        pen.line([(-20, y0 + 30), (w * .3, y0 - 10), (w * .7, y0 - 34), (w + 20, y0 - 50)], rgb=ink, amp=3)
        for i in range(5):
            xx = w * (.08 + i * .21); pen.line([(xx, y0 + 70 - i * 10), (xx + w * .07, y0 + 64 - i * 10)], rgb=ink, amp=2, smooth=False)
        for (cx, cy, s) in ((w * .12, y0 - 60, 1.0), (w * .86, y0 - 130, 1.2)):
            pts = arc_pts(cx, cy, 34 * s, 30 * s, math.pi, math.pi * 2, 6) + arc_pts(cx + 50 * s, cy + 6 * s, 26 * s, 22 * s, math.pi * 1.1, math.pi * 2, 5)
            pen.line(pts, rgb=ink, amp=2)
    elif kind == 'room':
        pen.line([(-20, y0), (w + 20, y0 + 6)], rgb=ink, amp=3)
        pen.line([(w * .08, y0 - h * .22), (w * .30, y0 - h * .22), (w * .30, y0 - h * .06), (w * .08, y0 - h * .06), (w * .08, y0 - h * .22)], rgb=ink, amp=2, smooth=False)
        pen.line([(w * .19, y0 - h * .22), (w * .19, y0 - h * .06)], rgb=ink, amp=2, smooth=False)
        pen.line([(w * .70, y0), (w * .70, y0 - h * .10), (w * .95, y0 - h * .10), (w * .95, y0)], rgb=ink, amp=2, smooth=False)


def car(cv, x, y, s, body=(250, 120, 90), boil=0):
    pen = Pen(cv, s * .05, boil, 'car')
    pts = [(x - s, y - s * .25), (x - s * .95, y - s * .55), (x - s * .5, y - s * .6), (x - s * .3, y - s * .95), (x + s * .35, y - s * .95),
           (x + s * .6, y - s * .6), (x + s * .98, y - s * .5), (x + s, y - s * .2)]
    p = _poly(jit(pts, 'car', boil, s * .015)); cv.drawPath(p, paint(body)); cv.drawPath(p, paint(LINE, stroke=s * .06))
    win = _poly([(x - s * .22, y - s * .85), (x + s * .05, y - s * .85), (x + s * .05, y - s * .6), (x - s * .38, y - s * .6)])
    cv.drawPath(win, paint((200, 230, 250))); cv.drawPath(win, paint(LINE, stroke=s * .04))
    for wx in (x - s * .55, x + s * .55):
        cv.drawCircle(wx, y - s * .2, s * .2, paint((70, 60, 60))); cv.drawCircle(wx, y - s * .2, s * .2, paint(LINE, stroke=s * .05)); cv.drawCircle(wx, y - s * .2, s * .07, paint((220, 220, 220)))


def tomb(cv, x, y, s, boil=0):
    pts = jit([(x - s * .5, y), (x - s * .5, y - s * .7), (x - s * .3, y - s), (x + s * .3, y - s), (x + s * .5, y - s * .7), (x + s * .5, y)], 'tomb%d' % x, boil, s * .02)
    p = spline(pts, closed=False); p.close()
    cv.drawPath(p, paint((196, 196, 204))); cv.drawPath(p, paint(LINE, stroke=s * .07))
    cv.drawLine(x, y - s * .78, x, y - s * .38, paint(LINE, stroke=s * .07)); cv.drawLine(x - s * .17, y - s * .63, x + s * .17, y - s * .63, paint(LINE, stroke=s * .07))


def to_pil(surface):
    from PIL import Image
    return Image.fromarray(surface.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType)).convert('RGBA')
