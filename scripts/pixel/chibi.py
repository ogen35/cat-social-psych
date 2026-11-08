"""喵喵剧团 v4 角色：三只单色的简约像素猫（外加路人猫），一眼能认出来、记得住。

  大比  奶白色 · 布偶的深色耳尖 · 蓝眼睛 · 八字眉、常冒汗 —— 乖巧、怂、在乎别人怎么看
  胜利  金黄色 · 头顶小王冠 · 竖起的大尾巴 · 眯眼得意 —— 自信过头、爱吹牛、常翻车
  大宝  灰蓝色 · 猞猁耳尖簇毛 · 额头三道纹 · 半睁眼的死鱼脸，个子大一号 —— 冷静、嘴硬、爱唱反调
  路人  米灰色，没有记忆点，衬托主角

角度 view：front 正面 / back 背面 / side 侧面（朝右，flip 后朝左）/ top 俯视
表情 expr：normal happy sad shock smug flat angry cry（不写就用这只猫的招牌表情）
       夸张表情：dizzy 转圈晕 / star 星星眼 / blank 白眼（吓傻）/ xx 眯成 >< / love 爱心眼 / rage 暴怒咬牙 / grin 咧嘴笑 / sob 嚎啕大哭 / gloom 脸发黑
姿势 pose：stand 站 / cheer 双手举高 / jump 跳起（配 kit.hop 抬高）/ headhold 抱头 / akimbo 叉腰 / point 伸手指（朝右，flip 朝左）/ flop 瘫成一摊 / slump 垂头耷耳
  cat(name, view='front', expr=None, talk=False, bob=0, step=0, pose='stand') -> RGBA ndarray（逻辑像素，约 24×25，大宝 27×28；非 stand 时四周多留空白放手臂）
"""
import numpy as np

INK = (36, 32, 44)
CAST = {
    '大比': dict(body=(245, 239, 228), line=(150, 132, 118), accent=(108, 76, 60), eye=(58, 132, 222), k=1.0, sig='normal'),
    '胜利': dict(body=(245, 184, 64), line=(168, 108, 22), accent=(229, 83, 60), eye=INK, k=1.0, sig='smug'),
    '大宝': dict(body=(126, 136, 154), line=(70, 78, 98), accent=(70, 78, 98), eye=INK, k=1.15, sig='flat'),
    '路人': dict(body=(217, 208, 193), line=(152, 142, 128), accent=(152, 142, 128), eye=(110, 100, 90), k=0.95, sig='normal'),
}
PINK = (240, 150, 160)
WHITE = (255, 255, 255)
RED = (214, 72, 70)
BLUE = (120, 180, 240)


def _se(X, Y, cx, cy, rx, ry, p=2.8): return (np.abs((X - cx) / rx) ** p + np.abs((Y - cy) / ry) ** p) <= 1
def _tri(X, Y, a, b, c):
    def s(p1, p2, p3): return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
    P = (X, Y); d1, d2, d3 = s(P, a, b), s(P, b, c), s(P, c, a)
    return ~(((d1 < 0) | (d2 < 0) | (d3 < 0)) & ((d1 > 0) | (d2 > 0) | (d3 > 0)))
def _seg(X, Y, pts, r):
    m = np.zeros(X.shape, bool)
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        dx, dy = x1 - x0, y1 - y0; L = dx * dx + dy * dy or 1
        t = np.clip(((X - x0) * dx + (Y - y0) * dy) / L, 0, 1)
        m |= (X - (x0 + t * dx)) ** 2 + (Y - (y0 + t * dy)) ** 2 <= r * r
    return m


POSES = ('stand', 'cheer', 'jump', 'headhold', 'akimbo', 'point', 'flop', 'slump')
EXPRS = ('normal', 'happy', 'sad', 'shock', 'smug', 'flat', 'angry', 'cry', 'dizzy', 'star', 'blank', 'xx', 'love', 'rage', 'grin', 'sob', 'gloom')
GLOOM = (120, 112, 170)


def _arms(pose, view, k):
    """手臂：每条是 (折线点, 粗细, 爪子圆心)；模板坐标，左右镜像。"""
    def mirror(a): return ([(26 - x, y) for x, y in a[0]], a[1], (26 - a[2][0], a[2][1]))
    if view == 'side':
        if pose in ('cheer', 'jump'): return [([(12, 19.5), (12.6, 13), (13.4, 7.6)], 1.25, (13.6, 7.0))]
        if pose == 'point': return [([(14, 19.5), (20.5, 17.4), (25.6, 16.6)], 1.25, (26.4, 16.4))]
        return []
    L = {'cheer': ([(7.6, 19.6), (4.4, 14.2), (3.2, 8.6)], 1.25, (3.2, 7.8)),
         'jump': ([(7.6, 19.6), (3.6, 15.2), (1.8, 10.4)], 1.25, (1.6, 9.6)),
         'headhold': ([(7.6, 19.6), (3.8, 15.4), (4.8, 8.6)], 1.25, (5.6, 7.6)),
         'akimbo': ([(8.0, 19.2), (3.6, 20.4), (7.4, 22.8)], 1.15, (7.6, 22.8)),
         'slump': ([(8.0, 19.6), (7.0, 23.8)], 1.15, (7.0, 24.2)),
         'flop': ([(4.0, 25.0)], 0.1, (3.0, 25.2))}
    if pose == 'point':
        return [([(18.0, 19.4), (23.4, 16.6), (27.4, 15.6)], 1.25, (28.2, 15.4)), ([(8.0, 19.6), (7.0, 23.6)], 1.15, (7.0, 24.0))]
    if pose not in L: return []
    return [L[pose], mirror(L[pose])]


def cat(name, view='front', expr=None, talk=False, bob=0, step=0, pose='stand'):
    C = CAST[name]; k = C['k']; expr = expr or C['sig']
    pose = pose or 'stand'
    padT, padX = (0, 0) if pose == 'stand' else (7, 6)
    W, H = int(round(26 * k)) + 2 * padX, int(round(27 * k)) + padT
    Y, X = np.mgrid[0:H, 0:W] + 0.5
    f = lambda x, y: (W / 2 + (x - 13) * k, H - 1 + (y - 26) * k)    # 26×27 模板坐标 → 本猫
    hb = -bob; lift = [(0, 0), (1, 0), (0, 0), (0, 1)][step % 4]
    if pose == 'flop': hb = 7                       # 头趴到地上
    elif pose == 'slump': hb = 2
    img = np.zeros((H, W, 4), np.uint8)
    def put(m, col):
        img[m, :3] = col; img[m, 3] = 255
    def px(x, y, col):
        x, y = int(x), int(y)
        if 0 <= x < W and 0 <= y < H: img[y, x, :3] = col; img[y, x, 3] = 255

    side = view == 'side'
    if view == 'top':
        head = _se(X, Y, *f(13, 8), 7.4 * k, 6.0 * k, 2.2)
        earL = _tri(X, Y, f(6, 6.5), f(6.5, 0.5), f(10.5, 3)); earR = _tri(X, Y, f(15.5, 3), f(19.5, 0.5), f(20, 6.5))
        body = _se(X, Y, *f(13, 18.5), 5.0 * k, 5.8 * k, 2.2)
        tail = _seg(X, Y, [f(13, 23.5), f(16, 25.4), f(20.5, 24.5), f(22, 21.5)], (2.0 if name == '胜利' else 1.2) * k)
        feet = _se(X, Y, *f(8.6, 14.6), 1.6 * k, 1.4 * k, 2) | _se(X, Y, *f(17.4, 14.6), 1.6 * k, 1.4 * k, 2)
        sil = head | earL | earR | body | tail | feet
    else:
        hx = 14 if side else 13
        head = _se(X, Y - hb, *f(hx, 11.5), 9.2 * k, 6.6 * k)
        if side:
            earL = _tri(X, Y - hb, f(7.5, 7), f(9.5, 1.5), f(12.5, 5.6)); earR = _tri(X, Y - hb, f(13.5, 5.4), f(17, 0.8), f(20, 6.4))
            snout = _se(X, Y - hb, *f(22.4, 13.2), 1.6 * k, 1.4 * k, 2); head |= snout
        elif pose in ('flop', 'slump'):            # 飞机耳：耳朵往两边耷拉
            earL = _tri(X, Y - hb, f(4.2, 9.0), f(0.8, 4.6), f(9.4, 6.0)); earR = _tri(X, Y - hb, f(16.6, 6.0), f(25.2, 4.6), f(21.8, 9.0))
        else:
            earL = _tri(X, Y - hb, f(4.5, 8.5), f(6.5, 1), f(10.8, 5.8)); earR = _tri(X, Y - hb, f(15.2, 5.8), f(19.5, 1), f(21.5, 8.5))
        if name == '大宝':
            tips = ((9.5, 1.5), (17, 0.8)) if side else (((0.8, 4.6), (25.2, 4.6)) if pose in ('flop', 'slump') else ((6.5, 1), (19.5, 1)))
            for (ex, ey) in tips:
                earL |= _seg(X, Y - hb, [f(ex, ey), f(ex + (0.3 if ex > 13 else -0.3), ey - 1.6)], 0.55)
        bx = 11 if side else 13
        body = _se(X, Y, *f(bx, 21), 6.4 * k, 4.8 * k, 2.4)
        fdx = 2 if pose == 'jump' else 3
        feet = _se(X, Y + lift[0], *f(bx - fdx, 25.2), 1.8 * k, 1.1 * k, 2) | _se(X, Y + lift[1], *f(bx + fdx, 25.2), 1.8 * k, 1.1 * k, 2)
        if pose == 'flop':                          # 瘫成一摊：身体压扁、摊开
            body = _se(X, Y, *f(13, 24.4), 11.6 * k, 2.4 * k, 2.4); feet = _se(X, Y, *f(2.2, 25.2), 1.9 * k, 1.1 * k, 2) | _se(X, Y, *f(23.8, 25.2), 1.9 * k, 1.1 * k, 2)
        if side:
            tail = _seg(X, Y, [f(5.5, 22), f(2.5, 19), f(2.2, 14)], (1.9 if name == '胜利' else 1.2) * k)
        elif view == 'back':
            tail = _seg(X, Y, [f(13, 24), f(13, 27)], 0) | _seg(X, Y, [f(16, 23.5), f(20.5, 21), f(21.5, 15.5)], (1.9 if name == '胜利' else 1.2) * k)
        else:
            tail = _seg(X, Y, [f(18.5, 23), f(22, 20.5), f(22.5, 15)], (1.9 if name == '胜利' else 1.2) * k)
        if pose == 'flop': tail = _seg(X, Y, [f(23, 25), f(27.5, 25.2), f(29.5, 24.0)], 1.1 * k)
        sil = head | earL | earR | body | feet | tail
    arms = np.zeros(X.shape, bool)
    if view != 'top':
        for pts, r, paw in _arms(pose, view, k):
            arms |= _seg(X, Y, [f(*p) for p in pts], r * k) | _se(X, Y, *f(*paw), 1.6 * k, 1.5 * k, 2)
        sil = sil | arms
    put(sil, C['body'])
    # ---- 招牌标记
    if name == '大比':                                     # 布偶的深色耳尖和尾巴
        put((earL | earR) & (Y < f(0, 4.6)[1] + (0 if view == 'top' else hb)), C['accent'])
        put(tail & ~body, C['accent'])
    if name == '大宝' and view in ('front', 'top', 'back'):  # 额头 / 背上三道纹
        for dx in (-2, 0, 2):
            x0, y0 = f(13 + dx, 5.4 if view != 'top' else 6.5)
            for dy in range(2): px(x0, y0 + dy + (hb if view != 'top' else 0), C['accent'])
        if view == 'top':
            for yy in (15, 17.5, 20):
                a, b = f(9.5, yy), f(16.5, yy); put(_seg(X, Y, [a, b], 0.5) & body, C['accent'])
    # ---- 描边：用同色系的深色，不用纯黑，整体更像「单色贴纸」
    S = np.pad(sil, 1); near = S[:-2, 1:-1] | S[2:, 1:-1] | S[1:-1, :-2] | S[1:-1, 2:]
    put(near & ~sil, C['line'])
    hS = np.pad(head, 1); put((body | feet) & ~head & ~arms & (hS[:-2, 1:-1]), C['line'])   # 头和身体之间一道线（俯视时是脖子）
    if arms.any():                                   # 手臂压在头和身体前面：沿手臂描一圈
        aS = np.pad(arms, 1); put((aS[:-2, 1:-1] | aS[2:, 1:-1] | aS[1:-1, :-2] | aS[1:-1, 2:]) & ~arms & (head | body | feet), C['line'])
    # ---- 王冠（胜利）
    if name == '胜利':
        cx, cy = f(14 if side else 13, 3.6 if view != 'top' else 4.4); cy += hb if view != 'top' else 0
        crown = [(-3, 1), (-3, 0), (-3, -1), (-2, 0), (-1, 0), (0, -1), (0, -2), (0, 0), (1, 0), (2, 0), (3, -1), (3, 0), (3, 1),
                 (-2, 1), (-1, 1), (0, 1), (1, 1), (2, 1)]
        for dx, dy in crown: px(cx + dx, cy + dy, (250, 214, 70))
        for dx, dy in ((-4, 0), (-4, 1), (4, 0), (4, 1), (-3, 2), (-2, 2), (-1, 2), (0, 2), (1, 2), (2, 2), (3, 2), (-3, -2), (0, -3), (3, -2)): px(cx + dx, cy + dy, C['line'])
        px(cx, cy, C['accent'])
    if view in ('back', 'top'): return img
    # ---- 五官
    ey = int(f(0, 11.8)[1] + hb)
    eyes = [int(f(9.2, 0)[0]), int(f(16.8, 0)[0])] if not side else [int(f(18.6, 0)[0])]
    E = expr
    def eye(x, kind):
        if kind == 'normal':
            px(x, ey - 1, C['eye']); px(x, ey, C['eye']); px(x + 1, ey - 1, WHITE if C['eye'] != INK else INK); px(x + 1, ey, C['eye'])
            if C['eye'] != INK: px(x, ey + 1, INK); px(x + 1, ey + 1, INK)
        elif kind == 'happy': px(x - 1, ey, INK); px(x, ey - 1, INK); px(x + 1, ey - 1, INK); px(x + 2, ey, INK)
        elif kind == 'flat': px(x - 1, ey, INK); px(x, ey, INK); px(x + 1, ey, INK); px(x + 2, ey, INK)
        elif kind == 'smug':
            px(x - 1, ey - 1, INK); px(x, ey - 1, INK); px(x + 1, ey - 1, INK); px(x + 2, ey - 1, INK); px(x, ey, INK); px(x + 1, ey, INK)
        elif kind == 'shock':
            for dx, dy in ((0, -2), (1, -2), (-1, -1), (2, -1), (-1, 0), (2, 0), (0, 1), (1, 1)): px(x + dx, ey + dy, INK)
            px(x, ey - 1, WHITE); px(x + 1, ey - 1, WHITE); px(x, ey, WHITE); px(x + 1, ey, INK)
        elif kind == 'angry': px(x - 1, ey - 1, INK); px(x, ey, INK); px(x + 1, ey, INK); px(x + 2, ey - 1, INK)
        elif kind == 'dizzy':                        # @ 转圈眼
            for dx, dy in ((0, -2), (1, -2), (2, -1), (2, 0), (1, 1), (0, 1), (-1, 0), (-1, -1), (1, -1)): px(x + dx, ey + dy, INK)
        elif kind == 'star':                         # ✦ 星星眼
            for dx, dy in ((0, -3), (0, -2), (0, 0), (0, 1), (-2, -1), (-1, -1), (1, -1), (2, -1)): px(x + dx, ey + dy, INK)
            px(x, ey - 1, (250, 210, 70))
        elif kind == 'blank':                        # 吓傻的白眼：只有一圈，没有眼珠
            for dx, dy in ((0, -2), (1, -2), (-1, -1), (2, -1), (-1, 0), (2, 0), (0, 1), (1, 1)): px(x + dx, ey + dy, INK)
            for dx, dy in ((0, -1), (1, -1), (0, 0), (1, 0)): px(x + dx, ey + dy, WHITE)
        elif kind == 'xl': px(x - 1, ey - 2, INK); px(x, ey - 1, INK); px(x + 1, ey - 1, INK); px(x - 1, ey, INK)          # >
        elif kind == 'xr': px(x + 2, ey - 2, INK); px(x + 1, ey - 1, INK); px(x, ey - 1, INK); px(x + 2, ey, INK)          # <
        elif kind == 'love':
            for dx, dy in ((-1, -2), (2, -2), (-1, -1), (0, -1), (1, -1), (2, -1), (0, 0), (1, 0)): px(x + dx, ey + dy, RED)
    kinds = {'normal': 'normal', 'happy': 'happy', 'sad': 'normal', 'shock': 'shock', 'smug': 'smug', 'flat': 'flat', 'angry': 'normal', 'cry': 'happy',
             'dizzy': 'dizzy', 'star': 'star', 'blank': 'blank', 'xx': 'xx', 'love': 'love', 'rage': 'normal', 'grin': 'happy', 'sob': 'xx', 'gloom': 'flat'}
    for i, x in enumerate(eyes):
        kd = kinds[E]
        if kd == 'xx': kd = 'xr' if (side or i == 1) else 'xl'
        eye(x, kd)
    if E == 'gloom' and not side:                            # 脸发黑：额头几道竖线
        for gx in range(int(f(8, 0)[0]), int(f(19, 0)[0]), 2):
            for gy in range(int(f(0, 6.2)[1] + hb), int(f(0, 9.4)[1] + hb)): px(gx, gy, GLOOM)
    for x in eyes:                                           # 眉毛
        if E in ('sad', 'cry', 'sob', 'gloom') or (name == '大比' and E in ('normal', 'shock')):
            px(x - 1, ey - 3, INK); px(x, ey - 3, INK) if x > W / 2 else None; px(x + 1, ey - 3, INK) if x < W / 2 else None
            px(x + (2 if x < W / 2 else -1), ey - 4, INK)
        if E in ('angry', 'rage'):
            px(x - 1 if x < W / 2 else x + 2, ey - 3, INK); px(x, ey - 2, INK) if x < W / 2 else px(x + 1, ey - 2, INK)
    mx = int(f(13, 0)[0]) if not side else int(f(21.4, 0)[0]); my = int(f(0, 14.6)[1] + hb)
    if talk or E in ('shock', 'sob', 'grin'):
        px(mx - 1, my, INK); px(mx, my, INK); px(mx - 1, my + 1, RED); px(mx, my + 1, RED); px(mx - 2, my + 1, INK); px(mx + 1, my + 1, INK); px(mx - 1, my + 2, INK); px(mx, my + 2, INK)
    elif E in ('happy', 'star', 'love'):
        px(mx - 2, my, INK); px(mx - 1, my + 1, INK); px(mx, my + 1, INK); px(mx + 1, my, INK)
    elif E == 'rage':                                         # 咬牙
        for dx in (-2, -1, 0, 1): px(mx + dx, my, INK); px(mx + dx, my + 2, INK)
        px(mx - 2, my + 1, INK); px(mx - 1, my + 1, WHITE); px(mx, my + 1, WHITE); px(mx + 1, my + 1, INK)
    elif E in ('dizzy', 'xx'):                                # 波浪嘴
        px(mx - 2, my + 1, INK); px(mx - 1, my, INK); px(mx, my + 1, INK); px(mx + 1, my, INK)
    elif E == 'blank':
        px(mx - 1, my + 1, INK)
    elif E in ('sad', 'cry', 'angry', 'gloom'):
        px(mx - 2, my + 1, INK); px(mx - 1, my, INK); px(mx, my, INK); px(mx + 1, my + 1, INK)
    elif E == 'smug':
        px(mx - 2, my + 1, INK); px(mx - 1, my + 1, INK); px(mx, my + 1, INK); px(mx + 1, my, INK)
    elif E == 'flat':
        px(mx - 1, my + 1, INK); px(mx, my + 1, INK)
    else:
        px(mx - 2, my, INK); px(mx - 1, my + 1, INK); px(mx, my, INK); px(mx + 1, my + 1, INK); px(mx + 2, my, INK) if not side else None
    if E in ('happy', 'normal', 'sad', 'cry', 'star', 'love', 'grin') and not side:   # 腮红
        for x in (eyes[0] - 2, eyes[1] + 3): px(x, my, PINK)
    if E == 'rage' and not side:                              # 气红了脸
        for x in (eyes[0] - 3, eyes[0] - 2, eyes[1] + 3, eyes[1] + 4): px(x, my - 1, RED); px(x, my, RED)
    if E == 'sob':                                            # 两道眼泪流到下巴
        for x in ((eyes[0], eyes[1] + 1) if not side else (eyes[0],)):
            for dy in range(1, 8): px(x, ey + dy, BLUE)
    if E == 'cry':
        for x in (eyes[0], eyes[1] + 1):
            for dy in (2, 3): px(x, ey + dy, BLUE)
    return img


EMOTES = {
    'sweat': ["..k..", ".kbk.", "kbbbk", "kbwbk", ".kkk."],
    '!': [".kk.", ".kk.", ".kk.", "....", ".kk."],
    '?': [".kkk.", "k...k", "...k.", "..k..", ".....", "..k.."],
    'anger': ["r.r", ".r.", "r.r"],
    'heart': [".rr.rr.", "rrrrrrr", ".rrrrr.", "..rrr..", "...r..."],
    'spark': ["..y..", ".yyy.", "yyyyy", ".yyy.", "..y.."],
    '...': ["k.k.k"],
}


def emote(kind):
    g = EMOTES[kind]; h, w = len(g), len(g[0])
    cols = {'k': INK, 'b': BLUE, 'w': WHITE, 'r': RED, 'y': (250, 210, 70)}
    img = np.zeros((h, w, 4), np.uint8)
    for r, row in enumerate(g):
        for c, ch in enumerate(row):
            if ch != '.': img[r, c, :3] = cols[ch]; img[r, c, 3] = 255
    return img
