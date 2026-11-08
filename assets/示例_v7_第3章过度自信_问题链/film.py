"""第3章 · 过度自信（问题链版 · 海螺 H3 多参情境 · LibTV Seed Audio 配音）。

一个剧情：客厅里的「九成八把握挑战」。胜利当主持人，大比当选手，大宝在沙发上当裁判。
一个知识点：心里的把握，比真知道的多。
核心问题：为什么明明老翻车，下一次还是觉得「稳了」？

问题链：
- 开场：观众和大比一起答新德里那道题。
- 层1 是什么：大比中招 → 三成套不住 → 过度自信。
  - 追问「那是我这题不熟！」
- 层2 为什么：带猫字的词，看不见自己漏掉的；得分最低的最高估自己。
  - 追问「那我多输几次，总能学乖吧？」
- 层3 为什么学不乖：胜利把错的天气预测记成「基本对」；专家也一样。
  - 追问「那怎么办？」
- 层4 办法：先问「我可能错在哪」。大比最后一题答对了。
- 结尾：回到观众。

画面：全部是海螺 H3 多参镜头，在 v3 客厅里演。代码只画字幕和名牌（用户：不用图标分析知识，全部情境演绎）。
"""
from kit_flat import *

flat_init(__file__)

FLAT = True
FORMAT = '问题链'
PACE = 'fast'
VOICE = 'libtv'
VOICE_TEMPO = 1.25          # Seed Audio 念得慢：整体加速 1.25 倍（只变快不变调）
VOICE_MAX_GAP = 0.4         # 句中停顿最长 0.4 秒
GAP = 0.2
TAIL = 1.8
AUTOZOOM = False
TOPBAR = '为什么老翻车，下次还觉得稳了？'

LINES = [
    dict(id='hook', who='胜利', say='先别划走！北京飞新德里有多远？', mood='轻松', part='开场', tone='像综艺主持人凑到镜头前出题，热情、带点挑衅'),
    dict(id='hook2', who='胜利', say='报个你九成八有把握的范围。', mood='轻松', part='开场', tone='挑眉，一字一句，带着笑', gap=0.9),
    dict(id='ans', who='大比', say='三千到三千五，稳了！', mood='轻松', part='层1·是什么', tone='难得拍着胸脯，很有把握'),
    dict(id='reveal', who='胜利', say='答案：大约四千公里。', mood='反转', part='层1·是什么', tone='拖长音宣布，憋着笑', gap=0.45),
    dict(id='book1', say='别笑它。心理学家问过很多人：说好九成八把握，三成都没套中。', mood='揭晓', part='层1·是什么',
         tone='先轻轻一笑说别笑它，后半句放慢，把数字说清楚'),
    dict(id='term', who='大宝', say='这叫【过度自信】：心里的把握，比真知道的多。', mood='揭晓', part='层1·是什么', tone='懒洋洋，一本正经'),
    dict(id='ask1', who='大比', say='那是我这题不熟！换一题！', mood='反转', part='追问', tone='不服气，有点急'),
    dict(id='game', who='胜利', say='行！十秒钟，说出所有带猫字的词！', mood='轻松', part='层2·为什么', tone='兴奋，像综艺主持人宣布新一轮'),
    dict(id='list', who='大比', say='猫粮、猫砂、熊猫、招财猫……全了！', mood='紧张', part='层2·为什么', tone='飞快地数，最后很得意', gap=0.4),
    dict(id='more', who='大宝', say='夜猫子。猫头鹰。躲猫猫。', mood='平叙', part='层2·为什么', tone='慢悠悠，一个一个往外补'),
    dict(id='why', who='大宝', say='你没想到的，在你脑子里根本不存在。', mood='揭晓', part='层2·为什么', tone='平静地解释'),
    dict(id='why2', who='大宝', say='所以你会觉得：我全想到了。', mood='揭晓', part='层2·为什么', tone='平静，最后半句学大比的口气'),
    dict(id='book2', say='越不会的人，越看不见自己漏了：测验得分最低的，反而最高估自己。', mood='揭晓', part='层2·为什么',
         tone='清楚、有一点意味深长'),
    dict(id='ask2', who='大比', say='那我多输几次，总能学乖吧？', mood='温暖', part='追问', tone='蔫蔫的，带一点希望', gap=0.35),
    dict(id='brag', who='胜利', say='我就不一样！我昨天说今天肯定不下雨——', mood='轻松', part='层3·为什么学不乖', tone='得意洋洋地炫耀'),
    dict(id='rain', who='大宝', say='下了一下午。', mood='平叙', part='层3·为什么学不乖', tone='面无表情，淡淡一句'),
    dict(id='brag2', who='胜利', say='那也基本对！', mood='轻松', part='层3·为什么学不乖', tone='理直气壮，嘴硬', gap=0.4),
    dict(id='book3', say='心理学家查过专家的预测：自认八成把握，对了不到四成。', mood='揭晓', part='层3·为什么学不乖', tone='清楚，把数字说清楚'),
    dict(id='book3b', say='可事后，错了的人还是说——', mood='轻松', part='层3·为什么学不乖', tone='忍着笑，留个悬念', gap=0.1),
    dict(id='basic', who='胜利', say='我基本上是对的！', mood='轻松', part='层3·为什么学不乖', tone='大声、得意、嘴硬'),
    dict(id='see', who='大宝', say='错了也记成基本对，当然学不乖。', mood='平叙', part='层3·为什么学不乖', tone='淡淡地吐槽'),
    dict(id='ask3', who='大比', say='那怎么办？我又看不见自己漏了啥。', mood='温暖', part='追问', tone='着急又认真', gap=0.35),
    dict(id='tip', who='大宝', say='越想我为什么对，就越觉得自己对。', mood='揭晓', part='层4·办法', tone='难得坐直了，认真'),
    dict(id='tip2', who='大宝', say='所以说稳了之前，先问一句：我可能错在哪？', mood='揭晓', part='层4·办法', tone='认真，最后半句放慢'),
    dict(id='last', who='胜利', say='最后一题！你今晚几点能睡着？', mood='轻松', part='层4·办法', tone='主持人口气，大声'),
    dict(id='win', who='大比', say='……我可能错在哪？那，一点到三点吧。', mood='温暖', part='层4·办法', tone='先停住小声问自己，再老老实实改口', gap=0.5),
    dict(id='end', say='如果你刚才一直在想：我是不是也这样——', mood='温暖', part='结尾', tone='温和，像在跟朋友说悄悄话'),
    dict(id='end2', say='那你已经在用这个办法了。', mood='温暖', part='结尾', tone='温暖，带一点笑意，稍微放慢'),
]
BGM = '轻松'
WIPES = []
SPEAKS = {'胜利': ['hook', 'hook2', 'reveal', 'game', 'brag', 'brag2', 'basic', 'last'],
          '大比': ['ans', 'ask1', 'list', 'ask2', 'ask3', 'win'],
          '大宝': ['term', 'more', 'why', 'why2', 'rain', 'see', 'tip', 'tip2']}


# ================================================================ 镜头（片段按口型对齐：锚点＝(台词出声时刻, 片段里第几段说话)）
# 锚点按 素材/片段/<镜头>.json 的说话区间填（fetch 时打印）
def sc_A(fr, t, T): clip_sync(fr, 'A', t, [(T['hook'].start, 0), (T['hook'].at('北京'), 1), (T['hook2'].start, 2)])
def sc_B(fr, t, T): clip_sync(fr, 'B', t, [(T['ans'].start, 1), (T['ans'].at('稳了'), 2)])
def sc_C(fr, t, T): clip_sync(fr, 'C', t, [(T['reveal'].start, 0), (T['reveal'].at('大约'), 1)])
def sc_D(fr, t, T): clip(fr, 'D', t, T['book1'].start - 0.3, offset=0.0)
def sc_E(fr, t, T): clip_sync(fr, 'E', t, [(T['term'].start, 0), (T['term'].at('心里'), 2)])
def sc_F(fr, t, T): clip_sync(fr, 'F', t, [(T['ask1'].start, 0), (T['ask1'].at('换'), 1), (T['game'].start, 2)])
def sc_G(fr, t, T): clip_sync(fr, 'G', t, [(T['list'].start, 0), (T['list'].at('全了'), 4)])
def sc_H(fr, t, T): clip_sync(fr, 'H', t, [(T['more'].start, 0), (T['why'].start, 3), (T['why2'].start, 5)])
def sc_I(fr, t, T): clip(fr, 'I', t, T['book2'].start - 0.2, offset=0.0)
def sc_J(fr, t, T): clip_sync(fr, 'J', t, [(T['ask2'].start, 0), (T['brag'].start, 1), (T['brag'].at('我昨天'), 2)])
def sc_K(fr, t, T): clip_sync(fr, 'K', t, [(T['rain'].start, 0), (T['brag2'].start, 2)])
def sc_L(fr, t, T): clip(fr, 'L', t, T['book3'].start - 0.2, offset=0.0)
def sc_R(fr, t, T): clip_sync(fr, 'R', t, [(T['basic'].start, 0)])
def sc_M(fr, t, T): clip_sync(fr, 'M', t, [(T['see'].start, 0), (T['ask3'].start, 2)])
def sc_N(fr, t, T): clip_sync(fr, 'N', t, [(T['tip'].start, 0), (T['tip2'].start, 2), (T['tip2'].at('我可能'), 4)])
def sc_O(fr, t, T): clip_sync(fr, 'O', t, [(T['last'].start, 0), (T['last'].at('你今晚'), 1)])
def sc_P(fr, t, T): clip_sync(fr, 'P', t, [(T['win'].start, 0), (T['win'].at('一点'), 2)])
def sc_Q(fr, t, T): clip(fr, 'Q', t, T['end'].start - 0.2, offset=0.0)


SCENES = [('hook', sc_A), ('ans', sc_B), ('reveal', sc_C), ('book1', sc_D), ('term', sc_E), ('ask1', sc_F), ('list', sc_G),
          ('more', sc_H), ('book2', sc_I), ('ask2', sc_J), ('rain', sc_K), ('book3', sc_L), ('basic', sc_R), ('see', sc_M),
          ('tip', sc_N), ('last', sc_O), ('win', sc_P), ('end', sc_Q)]
ANGLES = {'hook': '低机位特写推近', 'ans': '仰拍中景', 'reveal': '侧面双人', 'book1': '远景拉远', 'term': '特写', 'ask1': '双人横移',
          'list': '俯拍', 'more': '过肩推近', 'book2': '脸部特写慢推', 'ask2': '仰拍双人', 'rain': '仰拍', 'book3': '倾斜广角环绕',
          'basic': '仰拍特写', 'see': '沙发双人', 'tip': '正面中近景', 'last': '过肩', 'win': '双人推特写', 'end': '远景拉远'}


def SFX(T):
    return [(T['hook'].start, 'pop', 0.4), (T['ans'].at('稳了'), 'ding', 0.45), (T['reveal'].at('四千'), 'scratch', 0.5),
            (T['term'].at('过度自信'), 'hit', 0.7), (T['ask1'].start, 'pop', 0.35), (T['game'].at('十秒'), 'riser', 0.3),
            *[(T['game'].end + 0.2 + i * 0.4, 'tick', 0.2) for i in range(6)],
            (T['list'].at('全了'), 'ding', 0.45), (T['more'].start, 'pop', 0.3), (T['more'].at('猫头鹰'), 'pop', 0.3),
            (T['more'].at('躲猫猫'), 'pop', 0.3), (T['why'].start, 'whoosh', 0.3), (T['ask2'].start, 'pop', 0.3),
            (T['rain'].start, 'scratch', 0.45), (T['basic'].start, 'hit', 0.5), (T['ask3'].start, 'pop', 0.3),
            (T['tip2'].at('我可能'), 'ding', 0.5), (T['last'].start, 'whoosh', 0.35), (T['win'].at('一点'), 'ding', 0.5),
            (T['end'].start, 'whoosh', 0.4)]


def cover_v(fr):
    """竖封面 3:4：大比僵住的那一帧铺满，上方两行大字。"""
    fr.fill(COBALT)
    backdrop(fr, '封面图.jpg', x=0, y=96, w=W, h=264, fy=0.62)
    fr.text('九成八的把握', W / 2, 14, 104, WHITE, scol=INK, stroke=14, rot=-2, maxw=1000)
    fr.text('三成都错了', W / 2, 50, 168, WHITE, hi='三成', hcol=SUN, scol=INK, stroke=22, rot=-3, shadow=TOMATO, maxw=1030)


def cover_h(fr):
    """横封面 4:3：左边两行大字，右边大比。"""
    fr.fill(COBALT)
    backdrop(fr, '封面图.jpg', x=160, y=0, w=200, h=270, fx=0.45, fy=0.62)
    fr.text('九成八的把握', 84, 56, 92, WHITE, scol=INK, stroke=14, rot=-2, maxw=620)
    fr.text('三成都错了', 84, 104, 128, WHITE, hi='三成', hcol=SUN, scol=INK, stroke=18, rot=-3, shadow=TOMATO, maxw=620)


META = dict(
    title='第3章 · 过度自信（问题链版）',
    cover_v=cover_v, cover_h=cover_h,
    sources=['戴维·迈尔斯《社会心理学》（第11版），侯玉波等译，人民邮电出版社，第3章 社会信念和判断·过度自信现象，p89–92：'
             '98% 把握区间约 30% 套不住、新德里到北京约 4000 公里（Kahneman & Tversky, 1979，书页边栏）；'
             '能力不足促进过度自信，语法、幽默、逻辑测验得分最低者最高估自己（Kruger & Dunning, 1999）；'
             '用 psychology 的字母拼单词、被提醒漏了一个（Caputo & Dunning, 2005）——本片化用为「带猫字的词」；'
             '专家预测自认 80% 把握、实际不足 40%，事后仍说「我基本上是正确的」（Tetlock, 1998–2005）；'
             '思考一个观点为什么正确会让它显得更正确，设想自己可能出错的原因能降低过度自信（Koehler, 1991；Koriat 等, 1980）',
             '下雨、几点能睡着为演绎情节',
             '角色、场景：LibTV Style Image V8.2 生成；动画：LibTV 海螺 H3 多参考生视频；配音：LibTV Seed Audio 1.0（复刻自设计的角色声音样本）'],
    douyin=dict(
        keyword='过度自信',
        titles=['九成八的把握，三成都错了：过度自信', '为什么你老翻车，下次还觉得稳了？', '越不会的人越自信？心理学说是真的'],
        hook='北京飞新德里多远？报个九成八把握的范围',
        points=['过度自信：说好九成八把握，三成都套不住。',
                '你没想到的，在脑子里根本不存在，所以越不会越看不见自己漏了。',
                '错了还记成「基本对」，吃亏也学不乖。',
                '办法：说「稳了」之前，先问一句：我可能错在哪？'],
        ask='开头那道题，你报的范围套中了吗？',
        next='下期：为什么你只看得见支持你的证据',
        source='（猫咪为拟人演绎，知识来自迈尔斯《社会心理学》第3章；下雨、几点睡为演绎情节）',
        tags=[],
        pinned='开头那道题，你报的范围套中了吗？答案约4000公里👇'),
)
