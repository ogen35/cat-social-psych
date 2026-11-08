"""第3章 · 启动效应 · 照片背景版（完播优先 + 像素化真实照片背景）。
故事：大宝深夜看完恐怖片，厨房「哐」一声；答案留到最后——灯一开，是大比在偷吃小鱼干。"""
import random
from pathlib import Path
from kit import *
import props as P

PACE = 'fast'
IMG = Path(__file__).parent / '素材' / '图'
LR, HALLP, TOWER, KIT = (IMG / f for f in ('living_room_night_c02.jpg', 'dark_hallway_c01.jpg', 'apartment_building_night_c02.jpg', 'kitchen_interior_o02.jpg'))
NIGHTTINT = (36, 46, 96)
LINES = [
    dict(id='hook', say='看完恐怖片，厨房突然一响。', mood='悬疑', part='钩子'),
    dict(id='pain1', who='大宝', say='谁？！', mood='紧张', part='痛点', tone='压着嗓子，吓了一跳'),
    dict(id='pain2', say='你是不是也秒脑补：进贼了？', mood='紧张', part='痛点'),
    dict(id='promise', say='30秒看懂你怎么被带偏。', mood='平叙', part='承诺'),
    dict(id='term', say='这叫【启动效应】：刚看过的东西，会给接下来的想法定调。', mood='平叙', part='正文·术语翻译'),
    dict(id='why', say='恐怖片一碰，连着害怕的念头，【全亮了】。', mood='悬疑', part='正文·为什么'),
    dict(id='ana', say='就像输入法：刚打过的词，【第一个】跳出来。', mood='轻松', part='正文·生活类比'),
    dict(id='myth', say='以为没注意就没事？一闪而过的词，也能【启动你】。', mood='揭晓', part='正文·纠正误解'),
    dict(id='fix', say='心里一慌，先问：我刚看了什么？然后，开灯。', mood='温暖', part='正文·办法'),
    dict(id='truth', say='是大比，在偷吃小鱼干。', mood='反转', part='正文·真相'),
    dict(id='truth2', who='大比', say='我就拿一条……', mood='紧张', part='正文·真相', tone='心虚，小声'),
    dict(id='cta1', who='大宝', say='下次偷吃，开灯。', mood='平叙', part='收尾', tone='面无表情地吐槽'),
]
BGM = '轻松'
WIPES = []
SPEAKS = {'大宝': ['pain1', 'cta1'], '大比': ['truth2']}

WHITE = (255, 255, 255)
DARK, HALL, WARM, KITCHEN = (36, 40, 58), (48, 52, 72), (250, 226, 160), (250, 240, 214)


def fish(fr, x, y, k=1):
    """小鱼干：x, y 是鱼身中心。"""
    d = fr.d
    d.ellipse([x - 9 * k, y - 4 * k, x + 7 * k, y + 4 * k], fill=(150, 176, 196), outline=INK)
    d.polygon([(x + 6 * k, y), (x + 13 * k, y - 5 * k), (x + 13 * k, y + 5 * k)], fill=(150, 176, 196), outline=INK)
    d.point((x - 5 * k, y - 1), fill=INK)


def silhouette(fr, name, x, by, s, view='side', flip=False, col=(18, 20, 30)):
    """墙上的影子：角色的剪影。"""
    spr = cb.cat(name, view).copy()
    if flip: spr = spr[:, ::-1]
    spr[..., :3] = col
    im = Image.fromarray(spr.repeat(s, 0).repeat(s, 1)); fr.art.paste(im, (int(x - im.width / 2), int(by - im.height)), im)


def tv(fr, x0, y0, x1, y1, t, ghost=True):
    d = fr.d; d.rectangle([x0, y0, x1, y1], fill=(24, 24, 30)); d.rectangle([x0 + 5, y0 + 5, x1 - 5, y1 - 5], fill=(30, 36, 44))
    rng = random.Random(int(t * 12))
    for _ in range((x1 - x0) * (y1 - y0) // 40): d.point((rng.randint(x0 + 5, x1 - 5), rng.randint(y0 + 5, y1 - 5)), fill=(70, 76, 86))
    if ghost and int(t * 7) % 4:
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2 + 4
        d.ellipse([cx - 14, cy - 24, cx + 14, cy + 4], fill=(214, 220, 226)); d.rectangle([cx - 14, cy - 10, cx + 14, cy + 18], fill=(214, 220, 226))
        for k in range(4): d.polygon([(cx - 14 + k * 7, cy + 18), (cx - 7 + k * 7, cy + 18), (cx - 10 + k * 7, cy + 24)], fill=(214, 220, 226))
        d.rectangle([cx - 8, cy - 14, cx - 5, cy - 11], fill=TOMATO); d.rectangle([cx + 5, cy - 14, cx + 8, cy - 11], fill=TOMATO)


def hallway(fr, t, shadow=True, x_door=196):
    """深夜走廊（照片）：墙上一个巨大的黑影。"""
    fr.photo(HALLP, dark=0.85, tint=NIGHTTINT)
    if shadow: silhouette(fr, '大比', x_door - 50 + bob(t, 2), 300, 7, flip=True, col=(8, 8, 14))


def kitchen(fr):
    fr.photo(KIT, fx=0.35, dark=1.0, sat=0.9)


NODES = {'恐怖片': (160, 124), '黑影': (98, 180), '小偷': (222, 178), '危险': (160, 236), '小鱼干': (226, 292), '大比': (150, 300)}
EDGES = [('恐怖片', '黑影'), ('恐怖片', '小偷'), ('黑影', '危险'), ('小偷', '危险'), ('大比', '小鱼干'), ('危险', '大比')]




# ---------------------------------------------------------------- 1 钩子 · 过肩：大宝看恐怖片，厨房「哐」
def sc_hook(fr, t, T):
    L = T['hook']; hit = L.at('一响')
    fr.photo(LR, fx=0.85, dark=0.55, tint=NIGHTTINT)
    tv(fr, 120, 150, 250, 250, t); fr.spot(185, 200, 120, 0.35)
    fr.cat('大宝', 80 + shake(t, hit, 0.4, 3), 450, 7, 'back', shadow=False)
    fr.title('看完恐怖片', 36, 120, col=WHITE, scol=INK, rot=-3, shadow=TOMATO)
    if t >= hit:
        fr.zoom = (1.12, 200, 260)
        v, dy = pop(t, hit, 12)
        fr.sticker('哐！', 214, 268 + dy, 96, TOMATO, WHITE, 8, seed=1); fr.emote('!', 90, 262, 5)


# ---------------------------------------------------------------- 2 痛点 · 大特写：大宝「谁？！」
def sc_who(fr, t, T):
    L = T['pain1']
    fr.photo(LR, fx=0.85, dark=0.4 if int(t * 9) % 3 else 0.55, tint=NIGHTTINT, blur=2)
    top = actor(fr, '大宝', 135 + shake(t, L.start, 0.5, 2), 380, 9, t, T, view='front', expr='shock', seed=3)
    fr.emote('sweat', 214, top + 30, 5)
    v, dy = pop(t, L.start)
    if v: fr.bubble('谁？！', 135, 112 + dy, 110, seed=1)


# ---------------------------------------------------------------- 3 痛点 · 侧面：黑走廊，墙上巨大的影子
def sc_hall(fr, t, T):
    L = T['pain2']
    hallway(fr, t)
    x = walk_x(t, L.start, L.end, 30, 90)
    actor(fr, '大宝', x, 304, 4, t, T, view='side', expr='shock', seed=3, walk=(L.start, L.end))
    fr.zoom = (1 + 0.15 * ease((t - L.start) / max(0.1, L.dur)), 160, 230)
    v, dy = pop(t, L.at('进贼'))
    if v: fr.bubble('进贼了？', 120, 130 + dy, 80, think=True, seed=3)


# ---------------------------------------------------------------- 4 承诺 · 远景：整个家的剖面
def sc_promise(fr, t, T):
    L = T['promise']
    fr.photo(TOWER, fy=0.35, dark=0.8)
    v, dy = pop(t, L.start + 0.05, 10)
    if v: fr.sticker('30 秒看懂', 135, 120 + dy, 84, YOU, INK, -4, seed=2)
    fr.text('厨房里到底是谁？最后揭晓', W / 2, 160, 52, WHITE, stroke=9, scol=INK)


# ---------------------------------------------------------------- 5 术语翻译 · 分屏
def sc_term(fr, t, T):
    L = T['term']
    fr.d.rectangle([0, 0, W, H], fill=PAPER)
    fr.photo(LR, 18, 116, (234, 106), fx=0.85, dark=0.5, tint=NIGHTTINT); tv(fr, 36, 126, 136, 210, t)
    fr.cat('大宝', 196, 220, 3, 'side', 'shock', flip=True, shadow=False)
    fr.photo(HALLP, 18, 232, (234, 106), dark=0.85, tint=NIGHTTINT)
    fr.d.line([(18, 227), (252, 227)], fill=INK, width=2)
    v, dy = pop(t, L.at('接下来'))
    if v: fr.bubble('贼！', 96, 282 + dy, 72, think=True, seed=3); fr.arrow((100, 210), (96, 256), TOMATO, seed=4, bend=0.3)
    fr.title('启动效应', 30, 120, hi='启动效应', mark='启动效应')
    if t >= L.at('刚看过'): fr.text('刚看过的，给后面的想法定调', W / 2, 76, 52, (90, 80, 90), hi='定调', hcol=TOMATO, stroke=8)


# ---------------------------------------------------------------- 6 为什么 · 特写：念头网一碰就亮
def sc_why(fr, t, T):
    L = T['why']
    fr.d.rectangle([0, 0, W, H], fill=(52, 58, 86))
    actor(fr, '大宝', 46, 344, 4, t, T, view='front', expr='shock' if t >= L.at('全亮') else 'flat', seed=3)
    lit = {}
    if t >= L.at('恐怖片'): lit['恐怖片'] = 1
    for k, n in enumerate(('黑影', '小偷', '危险')):
        if t >= L.at('全亮') + 0.1 * k: lit[n] = 1
    for a, b in EDGES:
        on = a in lit and b in lit
        fr.wiggle([NODES[a], NODES[b]], TOMATO if on else (120, 126, 150), 6 if on else 4, seed=len(a + b))
    for k, (n, (x, y)) in enumerate(NODES.items()):
        fr.sticker(n, x, y - 12, 50, TOMATO if n in lit else (170, 176, 196), WHITE if n in lit else INK, (-1) ** k * 3, seed=k)


# ---------------------------------------------------------------- 7 生活类比 · 主观：输入法
def sc_ana(fr, t, T):
    L = T['ana']
    fr.photo(LR, fx=0.6, dark=0.4, tint=NIGHTTINT, blur=2)
    P.phone(fr, 40, 100, 230, 332, '和大比的聊天', [('them', '你睡了吗？', '')], status='00:12')
    fr.d.rectangle([50, 214, 220, 236], fill=WHITE, outline=GREY); fr.text('小', 58, 216, 48, align='l', stroke=0)
    fr.d.rectangle([50, 240, 220, 322], fill=(214, 218, 226))
    for j in range(3):
        for i in range(7): fr.d.rectangle([54 + i * 23, 262 + j * 20, 73 + i * 23, 278 + j * 20], fill=WHITE)
    first = t >= L.at('第一个')
    for k, c in enumerate(['小偷', '小鱼干', '小心']):
        x = 56 + k * 56
        if k == 0 and first: fr.d.rectangle([x - 4, 242, x + 44, 258], fill=TOMATO)
        fr.text(c, x + 20, 243, 42, WHITE if (k == 0 and first) else INK, stroke=0)
    fr.paws('大宝', 326)
    if first: fr.zoom = (1.25, 90, 250)


# ---------------------------------------------------------------- 8 纠正误解 · 特写：一闪而过的词
def sc_myth(fr, t, T):
    L = T['myth']; flash = L.at('一闪')
    fr.photo(LR, fx=0.85, dark=0.3, tint=NIGHTTINT)
    fr.d.rectangle([40, 100, 230, 196], fill=(24, 24, 30)); fr.d.rectangle([46, 106, 224, 190], fill=(40, 46, 60))
    if flash <= t < flash + 0.12: fr.text('害怕', 135, 120, 130, WHITE, stroke=0)
    top = actor(fr, '大宝', 135, 350, 6, t, T, view='front', expr='flat', seed=3)
    v, dy = pop(t, L.at('没注意'))
    if v and t < flash: fr.bubble('没看见啊', 200, 210 + dy, 52, tail=(170, top + 20), seed=1)
    v, dy = pop(t, L.at('启动你'), 12)
    if v: fr.sticker('也能启动你', 135, 70 + dy, 84, TOMATO, WHITE, -4, seed=3)


# ---------------------------------------------------------------- 9 办法 · 正面：问一句，伸爪开灯
def sc_fix(fr, t, T):
    L = T['fix']
    hallway(fr, t)
    fr.d.rectangle([60, 196, 78, 222], fill=CARD, outline=INK); fr.d.rectangle([66, 210, 72, 218], fill=INK)
    top = actor(fr, '大宝', 110, 306, 5, t, T, view='front', expr='flat', seed=3)
    v, dy = pop(t, L.at('先问'))
    if v: fr.bubble('我刚才\n看了什么？', 150, 110 + dy, 60, think=True, seed=2)
    if t >= L.at('开灯') - 0.2: fr.d.line([(80, top + 80), (70, 212)], fill=cb.CAST['大宝']['body'], width=7)


# ---------------------------------------------------------------- 10 真相 · 正面：灯一开，大比叼着小鱼干
def sc_truth(fr, t, T):
    L = T['truth']
    kitchen(fr)
    top = actor(fr, '大比', 135, 306, 6, t, T, view='front', expr='shock', seed=2)
    fish(fr, 150, top + 120, 2); fr.emote('sweat', 186, top + 6)
    if L.start <= t < L.start + 0.1: fr.d.rectangle([0, 0, W, H], fill=WHITE)
    v, dy = pop(t, L.start + 0.1, 10)
    if v: fr.sticker('原来是它！', 135, 96 + dy, 84, YOU, INK, -4, seed=3)


# ---------------------------------------------------------------- 11 真相 · 大特写：大比心虚
def sc_caught(fr, t, T):
    L = T['truth2']
    fr.photo(KIT, fx=0.35, zoom=1.6, fy=0.6, sat=0.9, blur=1.5)
    top = actor(fr, '大比', 135, 380, 9, t, T, view='front', expr='shock', seed=2)
    fish(fr, 160, top + 190, 4); fr.emote('sweat', 226, top + 20, 5)
    v, dy = pop(t, L.start)
    if v: fr.bubble('就一条……', 135, 104 + dy, 80, seed=2)


# ---------------------------------------------------------------- 12 收尾 · 远景：大宝吐槽，问题放字幕
def sc_end(fr, t, T):
    L = T['cta1']
    kitchen(fr)
    t1 = actor(fr, '大比', 196, 306, 4, t, T, view='front', expr='shock', seed=2)
    fish(fr, 206, t1 + 80, 2); fr.emote('sweat', 226, t1)
    t2 = actor(fr, '大宝', 80, 306, 4, t, T, view='side', expr='flat', seed=3)
    v, dy = pop(t, L.start)
    if v: fr.bubble('下次偷吃，\n开灯。', 92, 150 + dy, 60, tail=(90, t2), seed=2)
    v, dy = pop(t, L.start + 0.3)
    if v: fr.title('你被什么带偏过？', 40 + dy, 84, col=WHITE, scol=INK)


SCENES = [('hook', sc_hook), ('pain1', sc_who), ('pain2', sc_hall), ('promise', sc_promise), ('term', sc_term), ('why', sc_why),
          ('ana', sc_ana), ('myth', sc_myth), ('fix', sc_fix), ('truth', sc_truth), ('truth2', sc_caught), ('cta1', sc_end)]
ANGLES = {'hook': '过肩', 'pain1': '大特写', 'pain2': '侧面', 'promise': '远景', 'term': '分屏', 'why': '特写', 'ana': '主观',
          'myth': '特写', 'fix': '正面', 'truth': '正面', 'truth2': '大特写', 'cta1': '远景'}


def SFX(T):
    out = [(T['hook'].start, 'sting', 0.4), (T['hook'].at('一响'), 'hit', 1.0), (T['pain1'].start, 'scratch', 0.5)]
    out += [(T['pain2'].start, 'heartbeat', 0.6), (T['pain2'].at('进贼'), 'pop', 0.5), (T['promise'].start, 'whoosh', 0.5)]
    out += [(T['term'].start, 'whoosh', 0.4), (T['term'].at('启动效应'), 'hit', 0.7), (T['term'].at('接下来'), 'pop', 0.45)]
    out += [(T['why'].start, 'whoosh', 0.4), (T['why'].at('恐怖片'), 'ding', 0.5)] + [(T['why'].at('全亮') + 0.1 * k, 'pop', 0.45) for k in range(3)]
    out += [(T['ana'].start, 'whoosh', 0.4), (T['ana'].at('第一个'), 'ding', 0.5)]
    out += [(T['myth'].start, 'whoosh', 0.4), (T['myth'].at('一闪'), 'glitch', 0.7), (T['myth'].at('启动你'), 'hit', 0.9)]
    out += [(T['fix'].start, 'whoosh', 0.4), (T['fix'].at('先问'), 'pop', 0.4), (T['fix'].at('开灯'), 'tick', 0.6)]
    out += [(T['truth'].start, 'scratch', 0.8), (T['truth'].start + 0.1, 'ding', 0.6), (T['truth2'].start, 'pop', 0.5), (T['cta1'].start, 'pop', 0.5)]
    return out


def cover_prop(fr, L):
    """封面小道具：角落里放着恐怖片的电视。"""
    x0 = 16 if L['land'] else 12; y0 = int(L['h'] * (0.64 if L['land'] else 0.6))
    tv(fr, x0, y0, x0 + 72, y0 + 56, 0.5)


COVER = dict(line1='看完恐怖片', line2='一响就是贼？', hi='贼', who='大宝', expr='shock', emote='!',
             bg='素材/图/living_room_night_c02.jpg', bg_kw=dict(fx=0.85, tint=NIGHTTINT), tag='启动效应', prop=cover_prop)


META = dict(
    title='第3章 · 启动效应（照片背景版）',
    cover=COVER,                                   # 爆款封面模板：竖 9:16、竖 3:4、横 4:3 各自排版
    sources=['戴维·迈尔斯《社会心理学》（第11版），侯玉波等译，人民邮电出版社，第3章 社会信念和判断：「启动」（书页 78–79）',
             '背景照片（均做像素化处理）：「Filipijnen 248 Living room at night」larsjuh，CC BY 2.0；「Window at the of the dark hallway at the old abandoned building」Shixart1985，CC BY 2.0；「An apartment building at night」waferboard，CC BY 2.0（以上来自 Wikimedia Commons）；「Free modern kitchen interior image」rawpixel，CC0'],
    publish=dict(titles=['看完恐怖片，厨房一响就以为进贼？｜社会心理学'], desc='《社会心理学》第3章：刚看过的东西，会给接下来的想法定调——这叫启动效应。',
                 tags=['社会心理学', '心理学', '启动效应', '猫咪'], pinned='书里说：在家看完恐怖片，人会把炉子的声响听成有人闯入。你被什么带偏过？下期聊：为什么一旦认定，就很难改。'),
    douyin=dict(
        keyword='启动效应',
        titles=['看完恐怖片厨房一响就以为进贼？启动效应', '30秒看懂启动效应：你的想法被刚看过的东西定了调', '一闪而过的词也能带偏你？启动效应'],
        hook='看完恐怖片，厨房一响就以为进贼？',
        points=['心理学管这叫启动效应：刚看过的东西，会给接下来的想法定调。',
                '书里说，连一闪而过、根本看不清的词，也能启动你。',
                '一招：心里一慌，先问一句，我刚看了什么？'],
        ask='你被什么带偏过？',
        next='下期：为什么一旦认定，就很难改👀',
        source='（猫咪为拟人演绎，知识来自迈尔斯《社会心理学》第3章；背景照片：larsjuh、Shixart1985、waferboard，CC BY 2.0，Wikimedia Commons）',
        tags=['启动效应', '恐怖片', '心理学', '猫说社会心理学', '涨知识'],
        pinned='书里说：在家看完恐怖片，人会把炉子的声响听成有人闯入。你被什么带偏过？'),
)
