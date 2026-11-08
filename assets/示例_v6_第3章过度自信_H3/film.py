"""第3章 · 过度自信（平涂版 · 海螺 H3 多参情境版）。
故事（同一个客厅里演完）：一向冷静的大宝说「胜利会怎么选，我闭着眼都知道」。胜利拿出 20 张题卡，让大宝猜、再报把握——大宝说八成。
大比押它能对八成，胜利押没那么多。翻牌对答案：只对 14 道。胜利笑翻：把握八成，实际七成。
书：Dunning 等（1990）斯坦福学生猜室友的回答，命中 68%、自认为 78%；人们把过去错误的判断回忆为基本正确（Tetlock）；
自信和能力之间没有必然一致的关系；设想自己可能出错的原因、即时反馈能降低过度自信（Koriat 等, 1980）。20 道对 14 道是演示设定。
画面：13 个镜头都是海螺 H3 多参（客厅场景图＋三只猫设定图＋问答卡道具图），代码只画字幕、小贴纸、一次数字揭晓和金句卡。"""
from kit_flat import *

flat_init(__file__)

PACE = 'fast'
FORMAT = '实验'
GAP = 0.25
TAIL = 1.8
AUTOZOOM = False
TOPBAR = '你有八成把握，就能对八成吗？'
GREEN = (60, 170, 110)

LINES = [
    dict(id='hook', who='大宝', say='胜利会怎么选？我闭着眼都知道。', mood='轻松', part='钩子', tone='冷静又笃定，有点得意'),
    dict(id='quiz', who='胜利', say='那就猜20道：我选哪个。', mood='轻松', part='实验', tone='坏笑，挑衅'),
    dict(id='rule', who='胜利', say='每道再说说，你有几成把握。', mood='平叙', part='实验', tone='坏笑'),
    dict(id='conf', who='大宝', say='八成。稳了。', mood='轻松', part='实验', tone='淡定，很有把握', gap=0.5),
    dict(id='betD', who='大比', say='大宝那么聪明，肯定能对八成！', mood='温暖', part='下注', tone='崇拜'),
    dict(id='betS', who='胜利', say='我猜，没那么多。', mood='轻松', part='下注', tone='憋着笑', gap=0.5),
    dict(id='play', say='20道猜完，对答案——', mood='悬疑', part='结果', gap=1.4),
    dict(id='result', who='大宝', say='……才对了14道？', mood='反转', part='结果', tone='愣住，不敢相信', gap=0.4),
    dict(id='laugh', who='胜利', say='把握八成，实际七成！', mood='轻松', part='结果', tone='笑得前仰后合'),
    dict(id='book', say='斯坦福的学生猜室友的回答：只猜对68%，却觉得有78%的把握。', mood='揭晓', part='为什么', gap=0.4),
    dict(id='why', who='大宝', say='猜错的那几道，我都记成了差不多对。', mood='揭晓', part='为什么', tone='有点不好意思，承认'),
    dict(id='term', say='这就是【过度自信】。', mood='揭晓', part='点名', gap=0.35),
    dict(id='point', who='大宝', say='自信，不等于能力。', mood='揭晓', part='点名', tone='一字一句'),
    dict(id='ask', who='大比', say='那怎么才能不那么自信？', mood='温暖', part='办法', tone='认真地问', gap=0.4),
    dict(id='tip1', who='大宝', say='下判断前，先问自己：我可能错在哪？', mood='平叙', part='办法', tone='认真'),
    dict(id='tip2', who='大宝', say='再找个能马上告诉你对错的人。', mood='平叙', part='办法', tone='认真'),
    dict(id='punch', who='胜利', say='那我问问自己……嗯，我不可能错。', mood='轻松', part='收尾', tone='一本正经地吹牛', gap=0.6),
    dict(id='gold1', say='越有把握的时候，', mood='温暖', part='金句', rate=-32, tone='稍微放慢，真诚，自然连贯', gap=0.4, cap=False),
    dict(id='gold2', say='越要问：我可能错在哪？', mood='温暖', part='金句', rate=-32, tone='加重语气，连贯地说完，留一点余味', cap=False),
]
BGM = '轻松'
WIPES = []
SPEAKS = {'大宝': ['hook', 'conf', 'result', 'why', 'point', 'tip1', 'tip2'], '胜利': ['quiz', 'rule', 'betS', 'laugh', 'punch'],
          '大比': ['betD', 'ask']}


# ================================================================ 镜头（片段按口型对齐：锚点＝(台词出声时刻, 片段里第几段说话)）
def sc_A(fr, t, T): clip_sync(fr, 'A', t, [(T['hook'].start, 0), (T['hook'].at('我闭'), 1)])


def sc_B(fr, t, T):
    Q, R = T['quiz'], T['rule']
    clip_sync(fr, 'B', t, [(Q.start, 0), (Q.at('我选'), 1), (R.start, 2), (R.at('你有'), 3)])


def sc_C(fr, t, T):
    L = T['conf']
    clip_sync(fr, 'C', t, [(L.start, 0), (L.at('稳了'), 1)])
    v, dy = pop(t, L.start + 0.1, 10)
    if v: fr.sticker('八成！', 200, 116 + dy, 96, COBALT, WHITE, 6, seed=5)


def sc_D(fr, t, T):
    D, S = T['betD'], T['betS']
    clip_sync(fr, 'D', t, [(D.start, 0), (D.at('肯定'), 1), (S.start, 3), (S.at('没那么多'), 4)])
    v, dy = pop(t, D.at('八成'), 8)
    if v: fr.sticker('押：对八成', 76, 116 + dy, 64, ROSE, INK, -4, seed=2)
    v, dy = pop(t, S.at('没那么多'), 8)
    if v: fr.sticker('押：没那么多', 196, 150 + dy, 64, SUN, INK, 4, seed=5)


def sc_E(fr, t, T):
    L = T['play']
    clip(fr, 'E', t, L.start, offset=0.0)


def sc_F(fr, t, T): clip_sync(fr, 'F', t, [(T['result'].start, 0)])


def sc_G(fr, t, T):
    L = T['laugh']
    clip_sync(fr, 'G', t, [(L.start, 0), (L.at('实际'), 1)])
    v, dy = pop(t, L.at('把握'), 8)
    if v: fr.sticker('把握：八成', 82, 104 + dy, 70, COBALT, WHITE, -4, seed=3)
    v, dy = pop(t, L.at('实际'), 8)
    if v: fr.sticker('实际：七成', 190, 150 + dy, 70, TOMATO, WHITE, 4, seed=6)


def bars(fr, x0, y, rows, u):
    for j, (lab, v, col) in enumerate(rows):
        yy = y + j * 44
        fr.text(lab, x0, yy - 14, 64, INK, stroke=0, align='l')
        bar(fr, x0 + 76, yy - 10, x0 + 76 + 140, yy + 12, v / 100 * u, col)
        if u >= 1: fr.text(f'{v}%', x0 + 76 + 140 * v / 100 + 4, yy - 14, 64, col, stroke=0, align='l')


def sc_H(fr, t, T):
    """书里的数字：大宝一个人坐在夜里的沙发上，镜头拉远；上方弹出唯一一张数字卡。"""
    L = T['book']
    clip(fr, 'H', t, L.start, offset=1.0)
    t1 = L.at('只猜对')
    if t >= t1 - 0.1:
        g = eout((t - t1 + 0.1) / 0.25)
        panel(fr, 22, 84 - (1 - g) * 10, 248, 186 - (1 - g) * 10, WHITE)
        fr.text('猜室友的回答', W / 2, 92 - (1 - g) * 10, 66, INK, stroke=0)
        bars(fr, 34, 134 - (1 - g) * 10, [('猜对', 68, GREEN), ('自认为', 78, COBALT)], eout((t - t1) / 0.6))


def sc_I(fr, t, T):
    W_, M = T['why'], T['term']
    clip_sync(fr, 'I', t, [(W_.start, 0), (W_.at('我都'), 1)], tail_rate=0.7)
    v, dy = pop(t, M.at('过度自信'), 10)
    if v: fr.sticker('过度自信', W / 2, 150 + dy, 124, TOMATO, WHITE, -4, seed=6)


def sc_J(fr, t, T):
    L = T['point']
    clip_sync(fr, 'J', t, [(L.start, 0), (L.at('不等于'), 1)])


def sc_K(fr, t, T): clip_sync(fr, 'K', t, [(T['ask'].start, 0)])


def sc_L(fr, t, T):
    A_, B_ = T['tip1'], T['tip2']
    clip_sync(fr, 'L', t, [(A_.start, 0), (A_.at('先问'), 1), (A_.at('我可能'), 2), (B_.start, 3)])
    v, dy = pop(t, A_.at('我可能'), 8)
    if v and t < B_.start: fr.sticker('我可能错在哪？', W / 2, 108 + dy, 80, WHITE, INK, -3, seed=4)
    v, dy = pop(t, B_.at('马上'), 8)
    if v: fr.sticker('马上知道对错', W / 2, 108 + dy, 80, SUN, INK, 3, seed=7)


def sc_M(fr, t, T):
    L = T['punch']
    clip_sync(fr, 'M', t, [(L.start, 0), (L.at('嗯'), 1), (L.at('我不'), 2)])


def gold_bg(fr, t):
    """金句卡：v3 客厅铺底，压一层深钴蓝，让大字跳出来。"""
    backdrop(fr, '场景/客厅_v3.png', fy=0.6)
    fr.rect(0, 0, W, H, (16, 30, 90), None, a=150)


def sc_gold1(fr, t, T):
    gold_bg(fr, t)
    v, dy = pop(t, T['gold1'].start, 10)
    if v: fr.text('越有把握的时候，', W / 2, 136 + dy, 104, WHITE, stroke=12, scol=INK, maxw=1030)


def sc_gold2(fr, t, T):
    L = T['gold2']; gold_bg(fr, t)
    fr.text('越有把握的时候，', W / 2, 136, 104, WHITE, stroke=12, scol=INK, maxw=1030)
    v, dy = pop(t, L.start, 14)
    if v: fr.text('越要问：我可能错在哪？', W / 2, 200 + dy, 100, SUN, stroke=16, scol=INK, maxw=1000)
    if t >= L.end: fr.sticker('过度自信', W / 2, 286, 48, TEAL, WHITE, -2, seed=8)


SCENES = [('hook', sc_A), ('quiz', sc_B), ('conf', sc_C), ('betD', sc_D), ('play', sc_E), ('result', sc_F), ('laugh', sc_G),
          ('book', sc_H), ('why', sc_I), ('point', sc_J), ('ask', sc_K), ('tip1', sc_L), ('punch', sc_M),
          ('gold1', sc_gold1), ('gold2', sc_gold2)]
ANGLES = {'hook': '远景推近', 'quiz': '过肩', 'conf': '中近景', 'betD': '双人中景', 'play': '俯拍', 'result': '特写推近',
          'laugh': '倾斜广角', 'book': '拉远', 'why': '侧面横移', 'point': '正面直视', 'ask': '反打过肩', 'tip1': '双人中景',
          'punch': '仰拍', 'gold1': '金句卡'}


def SFX(T):
    out = [(T['hook'].start, 'pop', 0.4), (T['quiz'].start, 'whoosh', 0.35), (T['conf'].start + 0.1, 'ding', 0.5),
           (T['betD'].at('八成'), 'pop', 0.45), (T['betS'].at('没那么多'), 'pop', 0.45), (T['play'].start, 'riser', 0.35)]
    out += [(T['play'].start + 0.5 + i * 0.35, 'tick', 0.22) for i in range(8)]
    out += [(T['result'].start, 'scratch', 0.5), (T['laugh'].at('把握'), 'pop', 0.4), (T['laugh'].at('实际'), 'pop', 0.4),
            (T['book'].at('只猜对'), 'ding', 0.45), (T['term'].at('过度自信'), 'hit', 0.8), (T['point'].at('不等于'), 'hit', 0.45),
            (T['ask'].start, 'pop', 0.35), (T['tip1'].at('我可能'), 'ding', 0.45), (T['tip2'].at('马上'), 'pop', 0.35),
            (T['punch'].at('我不'), 'ding', 0.45), (T['gold1'].start, 'whoosh', 0.5), (T['gold2'].start, 'ding', 0.6)]
    return out


def cover_v(fr):
    """竖封面 3:4：大宝定稿图铺满，上方压两行大字。"""
    fr.fill(COBALT)
    backdrop(fr, '角色v3/大宝.png', x=0, y=108, w=W, h=252, fy=0.05)
    fr.text('八成把握？', W / 2, 14, 112, WHITE, scol=INK, stroke=14, rot=-2, maxw=1000)
    fr.text('只对了七成', W / 2, 48, 170, WHITE, hi='七成', hcol=SUN, scol=INK, stroke=22, rot=-3, shadow=TOMATO, maxw=1030)
    fr.sticker('过度自信', 62, 332, 60, TEAL, WHITE, -4, seed=2)


def cover_h(fr):
    """横封面 4:3：左边两行大字，右边大宝定稿图。"""
    fr.fill(COBALT)
    backdrop(fr, '角色v3/大宝.png', x=170, y=0, w=190, h=270, fy=0.15)
    fr.text('八成把握？', 88, 50, 100, WHITE, scol=INK, stroke=14, rot=-2, maxw=640)
    fr.text('只对了七成', 88, 100, 132, WHITE, hi='七成', hcol=SUN, scol=INK, stroke=18, rot=-3, shadow=TOMATO, maxw=640)
    fr.sticker('过度自信', 88, 200, 62, TEAL, WHITE, -3, seed=2)


META = dict(
    title='第3章 · 过度自信（平涂版 · 海螺 H3 多参情境版）',
    cover_v=cover_v, cover_h=cover_h,
    sources=['戴维·迈尔斯《社会心理学》（第11版），侯玉波等译，人民邮电出版社，第3章 社会信念和判断：过度自信现象（Dunning 等, 1990：猜室友的回答命中 68%、自认为 78%）；'
             '把过去错误的判断回忆为基本正确（Tetlock）；对过度自信的矫正：即时反馈、设想自己可能出错的原因（Koriat 等, 1980）',
             '20 道题对 14 道为演示设定',
             '角色、场景、道具：LibTV（Lib Image 2.5 Pro）AI 生成，角色参考作者自家三只猫的照片；动画：LibTV 海螺 H3 多参考生视频'],
    douyin=dict(
        keyword='过度自信',
        titles=['八成把握，只对了七成：过度自信', '最自信的猫，翻车最狠：过度自信', '你说有八成把握，真能对八成吗？'],
        hook='你说有八成把握，真能对八成吗？',
        points=['过度自信：斯坦福的学生猜室友的回答，只猜对68%，却觉得有78%的把握。',
                '猜错的，常被我们记成「差不多对」，所以越错越自信。',
                '下判断前问一句：我可能错在哪？再找个能马上告诉你对错的人。'],
        ask='你最近一次百分百确定、结果错了，是什么事？',
        next='下期：为什么你只看得见支持你的证据👀',
        source='（猫咪为拟人演绎，知识来自迈尔斯《社会心理学》第3章；20道对14道为演示设定）',
        tags=[],
        pinned='你最近一次「我百分百确定」结果错了，是什么事？'),
)
