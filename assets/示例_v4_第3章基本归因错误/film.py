"""第3章 · 基本归因错误（像素喵剧团 v4 · 费曼版）。
故事：大宝已读不回，大比脑补一整晚；真相是大宝的手机掉进了猫砂盆。"""
import random
from kit import *
import props as P

LINES = [
    dict(id='hook', say='朋友已读不回，你第一反应是什么？', mood='悬疑', part='钩子'),
    dict(id='pain', say='它是不是生气了？是不是早就嫌我烦？脑补了一整晚。', mood='紧张', part='痛点'),
    dict(id='promise', say='一分钟，看懂你为什么总把别人往坏处想，再教你一招：换个镜头看。', mood='平叙', part='承诺'),
    dict(id='truth', say='其实，大宝的手机，掉进了猫砂盆。', mood='反转', part='正文·真相', gap=0.15),
    dict(id='truth2', who='大宝', say='我的手机！', mood='紧张', part='正文·真相', tone='慌张，但还压着嗓子，有点崩溃'),
    dict(id='term', say='这叫【基本归因错误】。说白了：把处境的锅，算在人头上。', mood='平叙', part='正文·术语翻译'),
    dict(id='why', say='为什么？看别人时，人站在画面中间，背景是糊的；', mood='悬疑', part='正文·为什么', gap=0.15),
    dict(id='why2', say='轮到自己，看到的全是【处境】。', mood='揭晓', part='正文·为什么'),
    dict(id='ana', say='就像有人超你的车，你骂他路怒。', mood='轻松', part='正文·生活类比', gap=0.15),
    dict(id='ana2', say='可他也许是开会，快要迟到了。', mood='反转', part='正文·生活类比'),
    dict(id='myth', say='你以为聪明人不会这样？', mood='悬疑', part='正文·纠正误解', gap=0.15),
    dict(id='myth2', say='书里说，聪明、会社交的人，反而【更容易犯】。', mood='揭晓', part='正文·纠正误解'),
    dict(id='fix', say='下次先问一句：如果我在它的处境，会不会也这样？', mood='温暖', part='正文·办法'),
    dict(id='cta1', who='大宝', say='刚捞出来，回你了。', mood='平叙', part='收尾', tone='平淡、慢半拍，有点委屈'),
    dict(id='cta', say='你被谁冤枉过？评论区说说。关注我，下期聊：为什么一旦认定，就很难改。', mood='温暖', part='收尾'),
]
BGM = '轻松'
WIPES = [('term', '这叫什么'), ('fix', '怎么办')]
SPEAKS = {'大宝': ['truth2', 'cta1']}        # 角色台词：actor() 在这些句子里自动张嘴



# ---------------------------------------------------------------- 1 钩子 · 过肩：从大比背后看它的手机
def sc_hook(fr, t, T):
    L = T['hook']
    fr.d.rectangle([0, 300, W, H], fill=(52, 58, 86)); P.window(fr, 14, 92, 70, 150, night=True)
    fr.d.ellipse([60, 90, 260, 360], fill=(84, 92, 128))
    msgs = [('me', '周末一起吃饭吗？', '已读 · 20:13' if t >= L.at('已读') else '20:13')]
    P.phone(fr, 102, 112, 232, 322, '大宝', msgs)
    if t >= L.at('不回'): fr.text('（3小时没回）', 167, 230, 34, (190, 80, 70), stroke=0)
    actor(fr, '大比', 80, 430, 6, t, T, view='back', seed=3)
    v, dy = pop(t, L.start + 0.05)
    if v: fr.title('已读不回', 40 + dy, 140, col=(255, 255, 255), scol=INK, rot=-3, shadow=TOMATO)
    if t >= L.at('第一反应'): fr.title('你第一反应是？', 86, 72, col=(255, 255, 255), scol=INK, stroke=10)
    v, dy = pop(t, L.at('第一反应') + 0.2)
    if v: fr.bubble('它是不是\n讨厌我……', 62, 248 + dy, 50, think=True, tail=(75, 280), seed=3)
    for k, (s, col, y, r) in enumerate((('A  它讨厌我', TOMATO, 303, -4), ('B  它在忙吧', TEAL, 330, 3))):
        v, dy = pop(t, L.end - 0.2 + 0.25 * k)
        if v: fr.sticker(s, 207, y + dy, 56, col, (255, 255, 255), r, seed=k + 1)


# ---------------------------------------------------------------- 2 痛点 · 俯视：大比在床上翻来覆去
def sc_pain(fr, t, T):
    L = T['pain']
    fr.d.rectangle([0, 0, W, H], fill=(70, 78, 110))
    fr.d.rounded_rectangle([50, 140, 220, 340], radius=8, fill=(196, 212, 238), outline=INK)         # 床（浅蓝床单）
    fr.d.rounded_rectangle([74, 150, 196, 184], radius=8, fill=(255, 255, 255), outline=(150, 164, 196))   # 枕头
    flip = int((t - L.start) / 0.45) % 2 == 1
    actor(fr, '大比', 135 + (6 if flip else -6), 262, 4, t, T, view='top', flip=flip)
    fr.d.rectangle([52, 236, 218, 338], fill=(232, 120, 104))                                       # 被子盖住身子
    for y in range(244, 336, 10): fr.d.line([(54, y), (216, y)], fill=(214, 100, 88))
    fr.motion(214, 196, 3, 10, vertical=True, seed=int(t * 3)); fr.motion(40, 196, 3, 10, vertical=True, seed=int(t * 3) + 5)
    for k, (w, s, x, y) in enumerate((('生气', '生气了？', 60, 96), ('嫌我烦', '嫌我烦？', 210, 108), ('一整晚', '我说错话了？', 82, 124))):
        v, dy = pop(t, L.at(w) - 0.1)
        if v: fr.bubble(s, x, y + dy, 46, think=True, seed=k)
    v, dy = pop(t, L.at('脑补'))
    if v: fr.sticker('脑补 ×100', 196, 214 + dy, 60, YOU, INK, -5, seed=4)


# ---------------------------------------------------------------- 3 承诺 · 远景：胜利举起相机
def sc_promise(fr, t, T):
    L = T['promise']
    P.floor(fr, 300)
    x = walk_x(t, L.start, L.start + 0.8, 300, 182)
    actor(fr, '大比', 72, 300, 4, t, T, view='side', expr='sad' if t < L.at('换个') else 'normal', seed=3)
    actor(fr, '胜利', x, 300, 4, t, T, view='front', expr='smug', seed=1, walk=(L.start, L.start + 0.8))
    if t >= L.at('换个'):
        fr.d.rounded_rectangle([x + 14, 214, x + 46, 236], radius=3, fill=INK); fr.d.ellipse([x + 22, 217, x + 38, 233], fill=(150, 210, 240), outline=GREY)
        v, dy = pop(t, L.at('换个'))
        if v: fr.bubble('换个镜头看！', 182, 160 + dy, 52, tail=(184, 196), seed=2)
    v, dy = pop(t, L.at('看懂') - 0.1)
    if v:
        fr.box(30, 104 + dy, 240, 146 + dy, INK, CARD, seed=5)
        fr.text('① 为什么总往坏处想', 40, 110 + dy, 46, align='l', stroke=0)
        if t >= L.at('再教你'): fr.text('② 一招：换个镜头', 40, 128 + dy, 46, TEAL, align='l', stroke=0)


# ---------------------------------------------------------------- 4 真相 · 俯视：大宝在猫砂盆里刨手机
SAND = [(random.Random(i).randint(60, 210), random.Random(i * 7).randint(140, 250)) for i in range(40)]


def sc_truth(fr, t, T):
    L, Q = T['truth'], T['truth2']
    P.floor(fr, 0, top=True)
    P.litter_top(fr, 34, 118, 236, 262, seed=4)
    fr.d.ellipse([112, 160, 168, 228], fill=(196, 172, 122)); fr.d.ellipse([118, 166, 162, 222], fill=(214, 194, 146))
    fr.d.rectangle([126, 176, 154, 216], fill=(26, 26, 34)); fr.d.rectangle([129, 179, 151, 207], fill=(150, 210, 240))
    j = int(t * 12)
    for k, (x, y) in enumerate(SAND):
        dx = ((j + k) % 5 - 2) * 3; dy = -((j * 3 + k * 7) % 14)
        fr.d.rectangle([x + dx, y + dy, x + dx + 1, y + dy + 1], fill=(196, 172, 120))
    dig = 2 if j % 2 else 0
    actor(fr, '大宝', 140, 240 + dig, 4, t, T, view='top')
    for k in range(3): fr.wiggle([(70 + k * 60, 200 - k * 20), (60 + k * 60, 170 - k * 20)], INK, 6, seed=j + k)
    if t >= L.at('其实'): fr.sticker('真相', 50, 76, 56, YOU, INK, -4, seed=5)
    fr.text('深夜 23:41', 228, 78, 56, stroke=8, kind='smiley')
    v, dy = pop(t, L.at('猫砂盆'))
    if v:
        fr.sticker('这才是原因', 75, 308 + dy, 56, TEAL, (255, 255, 255), 4, seed=8); fr.arrow((88, 296), (126, 210), seed=9)
    v, dy = pop(t, Q.start)
    if v: fr.bubble('我的手机！！', 196, 288 + dy, 56, tail=(160, 270), seed=7)


# ---------------------------------------------------------------- 5 术语翻译 · 分屏：你眼里的大宝 vs 大宝眼里的
def split_frames(fr, t, T, seed=2):
    rng = random.Random(seed)
    fr.d.rectangle([18, 120, 252, 224], fill=(196, 202, 214))
    for _ in range(400): fr.d.point((rng.randint(18, 252), rng.randint(120, 224)), fill=(178, 184, 198))
    actor(fr, '大宝', 135, 222, 4, t, T, view='front', expr='flat')
    fr.d.rectangle([18, 232, 252, 336], fill=(230, 210, 164))
    for _ in range(600): fr.d.point((rng.randint(18, 252), rng.randint(232, 336)), fill=(206, 184, 136))
    fr.d.rectangle([120, 262, 150, 300], fill=(26, 26, 34)); fr.d.rectangle([123, 265, 147, 292], fill=(150, 210, 240))
    fr.paws('大宝', 300, dig=2 if int(t * 8) % 2 else 0)
    fr.d.line([(18, 228), (252, 228)], fill=INK, width=2)


def sc_term(fr, t, T):
    L = T['term']
    split_frames(fr, t, T)
    fr.viewfinder(24, 122, 246, 220)
    fr.sticker('你眼里的大宝', 60, 120, 44, (255, 255, 255), INK, -3, seed=11)
    fr.sticker('大宝眼里的', 54, 238, 44, (255, 255, 255), INK, 3, seed=13)
    v, dy = pop(t, L.at('基本归因错误'), 8)
    if v: fr.title('这叫基本归因错误', 30 + dy, 92, hi='基本归因错误', mark='基本归因错误')
    if t >= L.at('说白了'): fr.text('说白了：把处境的锅，算在人头上', W / 2, 74, 52, (90, 80, 90), hi='处境', hcol=TEAL, stroke=8)
    if t >= L.at('处境的锅'): fr.text('只看到「人」', 70, 200, 52, TOMATO, stroke=8, rot=-3)
    if t >= L.at('人头上'): fr.text('看到的全是「处境」', 168, 314, 52, TEAL, stroke=8, rot=2)


# ---------------------------------------------------------------- 6 为什么 · 特写 → 拉远
def sc_why(fr, t, T):
    L, M = T['why'], T['why2']
    if t < M.start:                                                     # 特写：画面里只有大宝的脸，背景糊成一片
        rng = random.Random(5); fr.d.rectangle([0, 100, W, 340], fill=(190, 196, 210))
        for _ in range(900): fr.d.point((rng.randint(0, W), rng.randint(100, 340)), fill=(172, 178, 196))
        actor(fr, '大宝', 135, 360, 8, t, T, view='front', expr='flat')
        if t >= L.at('人站在'): fr.sticker('人：清清楚楚', 70, 118, 52, (255, 255, 255), INK, -3, seed=3)
        if t >= L.at('背景是糊的'): fr.sticker('背景：糊的', 200, 150, 52, GREY, INK, 4, seed=4)
    else:                                                               # 拉远：整个处境都露出来
        fr.d.rectangle([0, 0, W, 300], fill=(232, 222, 202)); P.floor(fr, 300)
        P.window(fr, 26, 120, 86, 176, night=True)
        fr.d.ellipse([196, 124, 230, 158], fill=CARD, outline=INK); fr.d.line([(213, 141), (213, 130)], fill=INK, width=2); fr.d.line([(213, 141), (222, 145)], fill=INK, width=2)
        fr.d.rounded_rectangle([96, 262, 196, 306], radius=6, fill=(92, 150, 172)); fr.d.rectangle([104, 268, 188, 290], fill=(230, 210, 164))
        fr.d.rectangle([136, 272, 150, 286], fill=(26, 26, 34))
        actor(fr, '大宝', 150, 300, 3, t, T, view='side', expr='shock', flip=True)
        fr.emote('sweat', 128, 214)
        for k, (w, s, x, y, col) in enumerate((('轮到', '猫砂盆', 60, 250, TEAL), ('自己', '深夜', 213, 168, YOU), ('处境', '手机掉了', 214, 230, TOMATO))):
            v, dy = pop(t, M.at(w) + 0.1 * k)
            if v: fr.sticker(s, x, y + dy, 48, col, INK if col == YOU else (255, 255, 255), (-1) ** k * 4, seed=k)


# ---------------------------------------------------------------- 7 生活类比 · 侧面：路上被超车 → 车内特写
def sc_car(fr, t, T):
    A, B = T['ana'], T['ana2']
    if t < B.start:
        fr.d.rectangle([0, 110, W, 290], fill=(186, 214, 232)); fr.d.rectangle([0, 290, W, 340], fill=(90, 92, 104))
        for x in range(-30, W, 40): fr.d.rectangle([x + int(t * 90) % 40, 312, x + int(t * 90) % 40 + 18, 315], fill=(240, 240, 240))
        for x in (30, 120, 220): fr.d.rectangle([x - int(t * 20) % 270, 250, x - int(t * 20) % 270 + 6, 290], fill=(110, 160, 110))
        tp = A.at('超你'); xo = walk_x(t, tp - 0.3, tp + 0.6, -90, 380)
        fr.cat('胜利', 140, 270, 2, 'side', 'angry' if t >= A.at('路怒') else 'smug'); P.car(fr, 140, 302, (245, 184, 64), k=2)
        if tp - 0.3 <= t < tp + 0.7:
            fr.cat('路人', xo, 270, 2, 'side', 'shock'); P.car(fr, xo, 302, (160, 160, 170), k=2); fr.motion(xo - 110, 250, 3, 22, seed=int(t * 10))
        if t >= A.at('路怒'):
            v, dy = pop(t, A.at('路怒'))
            fr.bubble('路怒！', 150, 150 + dy, 72, tail=(150, 196), seed=1); fr.emote('anger', 176, 212, 4)
    else:
        fr.d.rectangle([0, 110, W, 340], fill=(70, 78, 104))
        fr.d.rounded_rectangle([20, 130, 250, 330], radius=10, fill=(96, 104, 132)); fr.d.rectangle([34, 150, 236, 250], fill=(186, 214, 232))
        for x in range(34, 236, 40): fr.d.rectangle([x + int(t * 200) % 40, 210, x + int(t * 200) % 40 + 18, 214], fill=(240, 240, 240))
        actor(fr, '路人', 120, 330, 5, t, T, view='side', expr='shock')
        fr.emote('sweat', 92, 184)
        fr.d.ellipse([196, 270, 232, 306], fill=CARD, outline=INK)
        v, dy = pop(t, B.at('开会'))
        if v: fr.sticker('08:59 开会', 200, 254 + dy, 48, TOMATO, (255, 255, 255), 4, seed=6)
        v, dy = pop(t, B.at('迟到'))
        if v: fr.bubble('要迟到了！', 168, 126 + dy, 56, tail=(140, 170), seed=3)


# ---------------------------------------------------------------- 8 纠正误解 · 正面：自以为聪明的胜利
def sc_myth(fr, t, T):
    A, B = T['myth'], T['myth2']
    P.floor(fr, 310)
    hit = t >= B.at('更容易犯')
    top = actor(fr, '胜利', 135 + shake(t, B.at('更容易犯')), 310, 6, t, T, view='front', expr='shock' if hit else 'smug')
    fr.d.polygon([(105, top + 22), (135, top + 8), (165, top + 22), (135, top + 34)], fill=INK); fr.d.rectangle([122, top + 26, 148, top + 36], fill=INK)
    fr.d.line([(162, top + 22), (166, top + 40)], fill=YOU, width=2)
    v, dy = pop(t, A.at('聪明人'))
    if v and not hit: fr.bubble('我这么聪明，\n才不会！', 135, 110 + dy, 56, tail=(140, 150), seed=4)
    if hit:
        v, dy = pop(t, B.at('更容易犯'), 10)
        fr.sticker('聪明人反而更容易犯', 135, 120 + dy, 64, TOMATO, (255, 255, 255), -5, seed=7)
        fr.text('书页 105', 210, 150, 40, (110, 100, 100), stroke=6, kind='smiley')
        fr.emote('!', 186, top - 6)


# ---------------------------------------------------------------- 9 办法 · 取景器：换个镜头看
def sc_fix(fr, t, T):
    L = T['fix']
    wide = t >= L.at('它的处境')
    if not wide:
        rng = random.Random(5); fr.d.rectangle([0, 100, W, 340], fill=(190, 196, 210))
        for _ in range(900): fr.d.point((rng.randint(0, W), rng.randint(100, 340)), fill=(172, 178, 196))
        actor(fr, '大宝', 135, 330, 6, t, T, view='front', expr='flat')
        fr.viewfinder(40, 130, 230, 320)
    else:
        fr.d.rectangle([0, 0, W, 300], fill=(232, 222, 202)); P.floor(fr, 300)
        P.window(fr, 26, 120, 86, 176, night=True)
        fr.d.rounded_rectangle([110, 262, 210, 306], radius=6, fill=(92, 150, 172)); fr.d.rectangle([118, 268, 202, 290], fill=(230, 210, 164))
        actor(fr, '大宝', 160, 300, 3, t, T, view='side', expr='sad', flip=True)
        fr.viewfinder(14, 104, 256, 324)
        v, dy = pop(t, L.at('它的处境'))
        if v: fr.sticker('它的处境', 200, 140 + dy, 56, TEAL, (255, 255, 255), 4, seed=2)
    v, dy = pop(t, L.at('会不会'))
    if v: fr.bubble('如果我是它，\n会不会也这样？', 135, 70 + dy, 52, think=True, seed=6)


# ---------------------------------------------------------------- 10 收尾 · 主观：大比捧着手机，大宝回消息了
def sc_cta(fr, t, T):
    A, B = T['cta1'], T['cta']
    fr.d.rectangle([0, 0, W, H], fill=(64, 72, 104))
    msgs = [('me', '周末一起吃饭吗？', '已读 · 20:13')]
    if t >= A.start: msgs.append(('them', '刚捞出来，回你了。', ''))
    if t >= A.start + 0.6: msgs.append(('them', '周末可以。', ''))
    P.phone(fr, 60, 104, 210, 330, '大宝', msgs, status='23:58')
    fr.paws('大比', 316)
    if t >= A.start + 0.3: fr.emote('heart', 228, 150)
    if t >= B.start:
        v, dy = pop(t, B.start)
        fr.title('你被谁冤枉过？', 40 + dy, 88, col=(255, 255, 255), scol=INK)
    v, dy = pop(t, B.at('评论区'))
    if v: fr.sticker('评论区说说', 68, 268 + dy, 52, YOU, INK, -4, seed=3)
    v, dy = pop(t, B.at('下期'))
    if v: fr.sticker('下期：为什么一认定就很难改', 150, 302 + dy, 44, (255, 255, 255), INK, 3, seed=5)


SCENES = [('hook', sc_hook), ('pain', sc_pain), ('promise', sc_promise), ('truth', sc_truth), ('term', sc_term), ('why', sc_why),
          ('ana', sc_car), ('myth', sc_myth), ('fix', sc_fix), ('cta1', sc_cta)]
ANGLES = {'hook': '过肩', 'pain': '俯视', 'promise': '远景', 'truth': '俯视', 'term': '分屏', 'why': '特写→拉远', 'ana': '侧面', 'myth': '正面特写', 'fix': '取景器', 'cta1': '主观'}


def SFX(T):
    L = T['hook']
    out = [(L.start + 0.05, 'pop', 0.6), (L.at('已读'), 'tick', 0.6), (L.at('第一反应') + 0.2, 'pop', 0.5), (L.end - 0.2, 'pop', 0.5), (L.end + 0.05, 'pop', 0.5)]
    P_ = T['pain']; out += [(P_.at(w) - 0.1, 'pop', 0.45) for w in ('生气', '嫌我烦', '一整晚')] + [(P_.at('脑补'), 'hit', 0.6)]
    out += [(T['promise'].start, 'whoosh', 0.4), (T['promise'].at('换个'), 'ding', 0.5)]
    out += [(T['truth'].start, 'scratch', 0.6), (T['truth'].at('猫砂盆'), 'ding', 0.6), (T['truth2'].start, 'pop', 0.5)]
    out += [(T['term'].at('基本归因错误'), 'hit', 0.8), (T['term'].at('处境的锅'), 'pop', 0.4), (T['term'].at('人头上'), 'pop', 0.4)]
    out += [(T['why'].at('人站在'), 'pop', 0.4), (T['why2'].start, 'whoosh', 0.5)] + [(T['why2'].at(w) + 0.1 * k, 'pop', 0.4) for k, w in enumerate(('轮到', '自己', '处境'))]
    out += [(T['ana'].at('超你') - 0.3, 'whoosh', 0.8), (T['ana'].at('路怒'), 'hit', 0.6), (T['ana2'].at('开会'), 'tick', 0.6), (T['ana2'].at('迟到'), 'pop', 0.5)]
    out += [(T['myth'].at('聪明人'), 'pop', 0.5), (T['myth2'].at('更容易犯'), 'hit', 1.0)]
    out += [(T['fix'].at('它的处境'), 'whoosh', 0.5), (T['fix'].at('会不会'), 'pop', 0.4)]
    out += [(T['cta1'].start, 'ding', 0.6), (T['cta'].start, 'pop', 0.5), (T['cta'].at('评论区'), 'pop', 0.4), (T['cta'].at('下期'), 'whoosh', 0.4)]
    return out


def cover(fr):
    fr.d.rectangle([0, 0, W, H], fill=(64, 72, 104)); fr.d.rectangle([0, 300, W, H], fill=(52, 58, 86))
    P.window(fr, 14, 160, 70, 218, night=True); fr.d.ellipse([60, 120, 260, 380], fill=(84, 92, 128))
    P.phone(fr, 102, 150, 232, 330, '大宝', [('me', '周末一起吃饭吗？', '已读 · 20:13')])
    fr.cat('大比', 80, 440, 6, 'back')
    fr.title('已读不回', 44, 150, col=(255, 255, 255), scol=INK, rot=-3, shadow=TOMATO)
    fr.title('是它讨厌你吗？', 92, 84, col=(255, 255, 255), scol=INK, hi='讨厌你', hcol=YOU)
    fr.sticker('基本归因错误', 200, 352, 52, TEAL, (255, 255, 255), 4, seed=2)


def cover_h(fr):
    """抖音横封面 4:3：横画布 fr.w×fr.h = 360×270（成片 1440×1080）。左边标题＋大比背影，右边手机。"""
    w, h = fr.w, fr.h
    fr.d.rectangle([0, 0, w, h], fill=(64, 72, 104)); fr.d.rectangle([0, 200, w, h], fill=(52, 58, 86))
    fr.d.ellipse([168, 6, 362, 292], fill=(84, 92, 128))                         # 手机屏幕的光
    P.window(fr, 10, 100, 66, 152, night=True)
    P.phone(fr, 206, 28, 338, 252, '大宝', [('me', '周末一起吃饭吗？', '已读 · 20:13')])
    fr.cat('大比', 128, 300, 6, 'back')                                          # 背影压在左下，看着手机
    fr.text('已读不回', 100, 22, 150, (255, 255, 255), scol=INK, stroke=12, rot=-3, shadow=TOMATO)
    fr.text('是它讨厌你吗？', 100, 72, 80, (255, 255, 255), scol=INK, stroke=10, hi='讨厌你', hcol=YOU)
    fr.sticker('基本归因错误', 286, 228, 52, TEAL, (255, 255, 255), 4, seed=2)


META = dict(
    title='第3章 · 基本归因错误',
    cover=cover,                                   # 竖封面（出 9:16 和 3:4）
    cover_h=cover_h,                               # 抖音横封面 4:3
    sources=['戴维·迈尔斯《社会心理学》（第11版），侯玉波等译，人民邮电出版社，第3章 社会信念和判断：「基本归因错误」——定义与例子（书页 104）、聪明和有社交能力的人更容易犯（书页 105）、视角与情境意识（书页 106）',
             'Ross, L. (1977). The intuitive psychologist and his shortcomings；Jones, E. E., & Harris, V. A. (1967)（转引自上书）'],
    publish=dict(
        titles=['朋友已读不回，你第一反应是什么？｜社会心理学', '把处境的锅，算在人头上：基本归因错误', '越聪明的人，越容易冤枉别人？'],
        desc='《社会心理学》第3章：解释别人的行为时，我们会低估处境的影响、高估性格——这叫基本归因错误。看别人时，人站在画面中间，背景是模糊的；轮到自己，看到的全是处境。书里还说，聪明、会社交的人反而更容易犯。下次先问一句：如果我在它的处境，会不会也这样？',
        tags=['社会心理学', '心理学', '基本归因错误', '人际关系', '已读不回', '猫咪', '涨知识'],
        pinned='书里的例子：有人在高速上飞驰而过，我们觉得他好斗，却没想到他也许正赶着开会、快迟到了。你最近冤枉过谁？'),
    douyin=dict(                                   # 抖音：标题＋爆款简介（写法见 references/抖音发布.md）
        keyword='基本归因错误',
        titles=['朋友已读不回，你第一反应是什么？基本归因错误', '已读不回就是讨厌你？基本归因错误了解一下', '聪明人反而更容易冤枉别人？基本归因错误'],
        hook='已读不回≠讨厌你，别再脑补一整晚了',
        points=['心理学管这叫基本归因错误：把处境的锅，算在人头上。',
                '看别人只看到「人」，看自己才看到「处境」。书里说，聪明、会社交的人反而更容易犯。',
                '一招破解：先问一句，如果我在它的处境，会不会也这样？'],
        ask='你被谁冤枉过？还是冤枉过谁？',
        next='收藏这期，下次脑补之前先看一眼👀',
        source='（猫咪为拟人演绎，知识来自迈尔斯《社会心理学》第3章）',
        tags=['基本归因错误', '已读不回', '心理学', '猫说社会心理学', '涨知识'],
        pinned='书里的例子：有人在高速上飞驰而过，我们觉得他好斗，却没想到他也许正赶着开会、快迟到了。你最近冤枉过谁？'),
    platforms={'小红书': dict(titles=['已读不回≠讨厌你😿', '把处境的锅算在人头上？', '聪明人更容易冤枉别人？'],
                              desc='💡 基本归因错误：看别人只看到「人」，看自己才看到「处境」\n📖 出自《社会心理学》第3章\n✅ 自救一招：如果我在它的处境，会不会也这样？')},
)
