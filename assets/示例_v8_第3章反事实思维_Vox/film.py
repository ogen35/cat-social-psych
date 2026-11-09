"""第3章 · 反事实思维（问题链版 · Vox 拼贴桌面 · 真实猫照片＋网络实拍素材）。

一个剧情：喵喵跳高赛。大宝金牌，胜利银牌（不甘心），大比铜牌（乐坏了）。
一个知识点：反事实思维——在脑子里演一遍「本来可能会怎样」。
核心问题：为什么「差一点」最难受？

问题链：
- 开场：观众和胜利一起猜：银牌和铜牌谁更开心？→ 铜牌。
- 层1 是什么：猫的跳高赛重演一遍 → 反事实思维：银牌往上想到金牌，铜牌往下想到没牌。
  - 追问「差得远我早认了，就差一点才气人！」
- 层2 为什么差一点最难受：差得越少，越容易想出另一个结局（赶车、B+）。
  - 追问「那以后不想『要是』，不就不难受了？」
- 层3 往哪想：往下想好受，往上想＋想下次怎么做，下次更容易做好。
- 层4 办法：别光问「要是」，问「下次我改哪一步」。胜利改口。
- 结尾：回到观众。

画面：cat_vox 语法（Vox 调查桌：网点冲印件、剪报、索引卡、红线、印章、黑卡纸；猫是真实照片剪纸、拼贴式张嘴）。
镜头、封面都写在 镜头表.json，由 vox_shots.py 渲成片段帧；字幕、名牌、顶部标题也由 cat_vox 画（OVERLAY = False），
build_pixel 按 SHOTS 播片段、混音、出封面和文案。
"""
from kit_flat import *

flat_init(__file__)

FLAT = True
FORMAT = '问题链'
PACE = 'fast'
VOICE = 'libtv'              # LibTV Seed Audio 1.0（references/配音_SeedAudio.md）；build_pixel 只读 libtv_voice.py fetch 写的缓存
VOICE_TEMPO = 1.35
VOICE_MIN_RATE = 4.6
VOICE_MAX_GAP = 0.4
GAP = 0.2
TAIL = 1.8
AUTOZOOM = False
TOPBAR = '为什么「差一点」最难受？'
OVERLAY = False             # Vox 版：顶部标题、字幕、名牌由 cat_vox 片段画成黑底撕边标签（vox_shots.py），build_pixel 不再叠

LINES = [
    dict(id='hook', who='胜利', say='先别划走！奥运领奖台上，银牌和铜牌，你猜谁更开心？', mood='轻松', part='开场',
         tone='像综艺主持人凑到镜头前出题，热情，带点挑衅'),
    dict(id='hook2', who='胜利', say='肯定是银牌啊，名次更高！', mood='轻松', part='开场', tone='抢着自问自答，理所当然', gap=0.5),
    dict(id='reveal', say='心理学家看过奥运选手的表情：铜牌的，反而比银牌的开心。', mood='反转', part='层1·是什么',
         tone='先平静，说到「反而」时放慢一点，像揭晓答案'),
    dict(id='rank', who='大宝', say='领奖台上的开心排名，据说是一、三、二。', mood='揭晓', part='层1·是什么', tone='懒洋洋，慢悠悠地报数'),
    dict(id='dare', who='胜利', say='不可能！咱们比一场跳高就知道！', mood='轻松', part='层1·是什么', tone='不服气，嗓门很大'),
    dict(id='result', say='结果：大宝金牌，胜利银牌，大比铜牌。', mood='轻松', part='层1·是什么', tone='像体育解说宣布成绩，轻快', gap=0.35),
    dict(id='silver', who='胜利', say='就差一点点！金牌本来是我的！', mood='紧张', part='层1·是什么', tone='又急又气，捶胸顿足'),
    dict(id='bronze', who='大比', say='我差一点就没牌了！我有牌！', mood='温暖', part='层1·是什么', tone='又惊又喜，开心得声音发颤'),
    dict(id='term', who='大宝', say='这叫【反事实思维】：在脑子里演一遍，本来可能会怎样。', mood='揭晓', part='层1·是什么',
         tone='慵懒，一本正经地解释'),
    dict(id='term2', who='大宝', say='银牌往上想，想到金牌；铜牌往下想，想到没牌。', mood='揭晓', part='层1·是什么', tone='慢条斯理，前后两半对比着说'),
    dict(id='ask1', who='胜利', say='要是差得远，我早认了！就差一点才气人！', mood='反转', part='追问', tone='委屈又不服，越说越激动', gap=0.35),
    dict(id='why', who='大宝', say='对，差得越少，越容易想出另一个结局。', mood='揭晓', part='层2·为什么', tone='平静地点头，说中要害'),
    dict(id='bus', say='赶车也一样：差两分钟没赶上，你会想：要是早点出门就好了；', mood='平叙', part='层2·为什么',
         tone='像跟朋友聊天，后半句学人懊恼的口气'),
    dict(id='bus2', say='差半小时，反倒没那么难受。', mood='平叙', part='层2·为什么', tone='轻轻一笑，放松'),
    dict(id='grade', say='考试也是：同样八十几分，考八十九的比考八十的更难受。', mood='平叙', part='层2·为什么',
         tone='清楚，把两种情况对比着说'),
    dict(id='ask2', who='大比', say='那以后不想「要是」，不就不难受了？', mood='温暖', part='追问', tone='小心翼翼地提议，带点希望', gap=0.35),
    dict(id='deep', who='大宝', say='停不了，也不用停，关键是往哪想。', mood='揭晓', part='层3·往哪想', tone='淡淡地，难得认真'),
    dict(id='down', who='大宝', say='往下想，本来可能更糟，你会好受点；', mood='揭晓', part='层3·往哪想', tone='平静，语速稍慢'),
    dict(id='up', who='大宝', say='往上想，再想想下次怎么做，下次就更容易做好。', mood='揭晓', part='层3·往哪想', tone='平静，最后半句加重'),
    dict(id='tip', who='大宝', say='所以难受的时候，别光问「要是」，问一句：下次我改哪一步？', mood='揭晓', part='层4·办法',
         tone='认真，最后一问放慢', gap=0.4),
    dict(id='win', who='胜利', say='……下次起跳，我早半拍！', mood='温暖', part='层4·办法', tone='先憋了一下，然后认真又带点不服气', gap=0.5),
    dict(id='end', say='你最近一次「差一点」，是哪件事？', mood='温暖', part='结尾', tone='温和，像在问朋友'),
    dict(id='end2', say='差一点，说明另一个结局离你很近。下次，去够它。', mood='温暖', part='结尾', tone='温暖，带一点笑意，最后四个字放慢'),
]
BGM = '轻松'
WIPES = []
SPEAKS = {'胜利': ['hook', 'hook2', 'dare', 'silver', 'ask1', 'win'],
          '大比': ['bronze', 'ask2'],
          '大宝': ['rank', 'term', 'term2', 'why', 'deep', 'down', 'up', 'tip']}


# ================================================================ 镜头（vox_shots.py 渲好的片段帧：build/clips/<镜头>/%04d.jpg，从这一镜第一句开口前 PRE 秒起播）
PRE = 0.25
SHOTS = [  # (镜头, 从哪句开始)
    ('A', 'hook'), ('B', 'hook2'), ('C', 'reveal'), ('D', 'rank'), ('E', 'dare'), ('F', 'result'), ('G', 'silver'),
    ('H', 'bronze'), ('I', 'term'), ('J', 'term2'), ('K', 'ask1'), ('L', 'why'), ('M', 'bus'), ('M2', 'bus2'), ('N', 'grade'),
    ('O', 'ask2'), ('P', 'deep'), ('Q', 'up'), ('R', 'tip'), ('S', 'win'), ('T', 'end'), ('U', 'end2'),
]


def _mk(name, lid):
    def sc(fr, t, T): clip(fr, name, t, T[lid].start - PRE, offset=0.0)
    return sc


SCENES = [(lid, _mk(name, lid)) for name, lid in SHOTS]
ANGLES = {'hook': '实拍满幅推近', 'hook2': '照片横移', 'reveal': '实拍对切', 'rank': '桌面拉远', 'dare': '照片快推',
          'result': '三张照片竖排横移', 'silver': '特写红圈', 'bronze': '特写荧光', 'term': '索引卡推近', 'term2': '红线上下连',
          'ask1': '照片快推', 'why': '照片缓推', 'bus': '实拍满幅', 'grade': '实拍对切', 'ask2': '照片横移',
          'deep': '桌面拉远', 'up': '实拍满幅', 'tip': '照片推近', 'win': '照片砸入', 'end': '实拍呼应开场', 'end2': '照片定格'}


def SFX(T):
    return [(T['hook'].start, 'pop', 0.4), (T['hook2'].start, 'ding', 0.35), (T['reveal'].at('反而'), 'scratch', 0.5),
            (T['rank'].at('一、三、二'), 'hit', 0.5), (T['dare'].start, 'whoosh', 0.35), (T['result'].at('大宝'), 'ding', 0.3),
            (T['result'].at('胜利'), 'ding', 0.3), (T['result'].at('大比'), 'ding', 0.3), (T['silver'].start, 'hit', 0.45),
            (T['bronze'].start, 'pop', 0.4), (T['term'].at('反事实'), 'hit', 0.6), (T['ask1'].start, 'pop', 0.35),
            (T['bus'].start, 'whoosh', 0.35), (T['grade'].start, 'whoosh', 0.3), (T['ask2'].start, 'pop', 0.3),
            (T['up'].start, 'whoosh', 0.3), (T['tip'].at('下次'), 'ding', 0.5), (T['win'].at('早半拍'), 'hit', 0.45),
            (T['end'].start, 'whoosh', 0.4)]


def cover_v(fr):
    """竖封面 3:4：cat_vox 语法渲的 Vox 拼贴封面（build/vox/cover_v.json → 素材/vox封面_竖.png）。"""
    backdrop(fr, 'vox封面_竖.png', x=0, y=0, w=W, h=360)


def cover_h(fr):
    """横封面 4:3：同上（素材/vox封面_横.png）。"""
    backdrop(fr, 'vox封面_横.png', x=0, y=0, w=360, h=270)


META = dict(
    title='第3章 · 反事实思维（问题链 · Vox 版）',
    cover_v=cover_v, cover_h=cover_h,
    sources=['戴维·迈尔斯《社会心理学》（第11版），侯玉波等译，人民邮电出版社，第3章 社会信念和判断·反事实思维，p95–96：'
             '反事实思维＝对可能发生事情的心理模拟；以一分之差输掉更容易想象另一种结果；'
             '铜牌获得者比银牌获得者显得更快乐，领奖台上据说快乐排名是 1-3-2（Medvec 等, 1995；McGraw 等, 2005）；'
             '同一评分等级内得分越高感觉越糟（Medvec & Savitsky, 1997）——本片化用为「同样八十几分」；'
             '刚刚错过车会想「要是按平常时间出发、路上不聊天」，误了半个钟头则较难设想、挫败感较小（Kahneman & Miller, 1986 等）；'
             '设想更坏的可能让人好受，设想更好的可能并考虑下次怎样做得更好，有助于未来的表现（Epstude & Roese, 2008）',
             '跳高比赛、名次为演绎情节',
             '猫：角色库真实照片；实拍素材见 素材/网络素材/来源.md；画面：huashu-art-motion 引擎＋cat_vox 拼贴语法；配音：LibTV Seed Audio 1.0（复刻角色声音样本）'],
    douyin=dict(
        keyword='反事实思维',
        titles=['银牌为什么没铜牌开心？反事实思维', '为什么「差一点」最难受？', '差两分钟没赶上车，比差半小时更气人'],
        hook='银牌和铜牌，你猜谁更开心？',
        points=['反事实思维：在脑子里演一遍「本来可能会怎样」。',
                '银牌往上想到金牌，铜牌往下想到没牌。',
                '差得越少，越容易想出另一个结局，「差一点」最难受。',
                '办法：往下想让自己好受；往上想时问一句：下次我改哪一步？'],
        ask='你最近一次「差一点」，是哪件事？',
        next='下期：为什么你总觉得「这事有规律」',
        source='（猫咪为拟人演绎，知识来自迈尔斯《社会心理学》第3章；跳高比赛为演绎情节；部分画面为网络实拍素材）',
        tags=[],
        pinned='开头那题你猜对了吗？说说你最近一次「差一点」👇'),
)
