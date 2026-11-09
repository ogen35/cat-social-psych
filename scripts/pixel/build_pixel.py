#!/usr/bin/env python3
"""像素喵剧团出片：film.py（口播 + 镜头函数）→ 豆包配音 → 时间轴 → 逐帧画像素动画 → 配乐音效混音 → 成片＋字幕＋封面＋发布文案。

  python3 $S/scripts/pixel/build_pixel.py <集目录>/film.py --check          # 只检查脚本（费曼结构、钩子、用词、角度、时长）
  python3 $S/scripts/pixel/build_pixel.py <集目录>/film.py --preview        # 不渲视频，出每句一帧的总览图 output/预览.jpg
  python3 $S/scripts/pixel/build_pixel.py <集目录>/film.py [--still 12.5,30] [--no-voice] [--no-bgm] [--platform 抖音|视频号|小红书]
  python3 $S/scripts/pixel/build_pixel.py <集目录>/film.py --publish-only --platform 小红书   # 不重渲，只换平台的封面和发布文案

film.py 里要有：
  LINES  = [dict(id='hook', who='旁白'|'大比'…, say='口播（【】= 字幕高亮）', mood='悬疑', part='钩子', gap=0.25, tone=None), …]
  SCENES = [('hook', 函数), ('pain1', 函数), …]      # 从哪一句开始用哪个镜头函数；函数签名 fn(fr, t, T)
  SFX(T) -> [(秒, 音效名, 音量), …]                   # 画面动作对应的音效（举牌 pop、翻牌 whoosh、揭晓 hit…）
  WIPES  = [('def', '这叫什么'), …]                   # 可选：在这一句开始时扫一次黄色转场
  ANGLES = {'hook': '过肩', 'truth': '俯视', …}       # 每个镜头用的角度（自检要求至少 4 种）
  BGM    = '轻松'                                      # 全片铺底的配乐情绪（只铺一段，不切换）
  META   = dict(title=, sources=[], cover=dict(line1=, line2=, hi=, who=, expr=, emote=, bg=, tag=)  # 爆款封面模板，三个尺寸各排一版
                douyin=dict(keyword, titles, hook, points, ask, next, source, tags, pinned),   # 抖音标题＋爆款简介
                publish=dict(titles=[], desc=, tags=[], pinned=), platforms={'小红书': dict(…)})
封面：封面_9x16.png、封面_竖屏_3x4.png（抖音竖封面 / 小红书 / 主页九宫格）、封面_横屏_4x3.png（抖音横封面）。
PACE = 'fast'：完播优先（快语速、短停顿、重点词推镜、大字幕）。背景照片用 fr.photo(...)。
STYLE = 'line'：线条画风（kit_line.py，film.py 里 `from kit_line import *`）；不写就是像素画风（kit.py）。线条画风要 uv 加 --with skia-python。
T 是时间轴：T['hook'].start / .end / .dur / .at('关键词') 返回这个词念到的时刻（秒，整片时间）。

配音用豆包（seed_voice.say，固定音色 + 按 mood 的语气）；没 Key 或 --no-voice 时按 4.5 字/秒估时长出无声片。
配乐：全片一段浅浅的铺底（不按情绪切段、不抽空），节奏交给 SFX 里的音效。
画面在 270×480 逻辑像素上画，放大 4 倍；单进程逐帧渲，CPU 占用低。
"""
import argparse, hashlib, importlib.util, json, re, subprocess, sys, wave
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(SKILL / 'scripts'))
import kit
import seed_voice
from cards_story import find_cast

FPS = 30
MOODS = {   # 与 build_episode.py 一致：语速偏移、旁白语气、角色情绪
    '平叙': (0, '自然聊天的口吻，清楚、有条理，不要播音腔', ''),
    '悬疑': (-12, '压低声音、放慢语速，神秘、带着悬念，像在讲一个秘密，关键处停顿一下', '压着嗓子、紧张兮兮'),
    '紧张': (10, '语速加快，紧张、急促，一句比一句紧', '很着急'),
    '揭晓': (-12, '先停半拍，再郑重、有力地宣布答案，带着一点震惊', '很震惊'),
    '反转': (8, '语气突然一转，惊讶里带着调侃，语调上扬', '很意外'),
    '轻松': (6, '轻松调侃、带着笑意，像在跟朋友八卦', '很开心'),
    '温暖': (-8, '温柔、真诚，放慢一点，带着微笑', '很真诚'),
}
PLATFORMS = {
    '抖音': dict(cover='封面_竖屏_3x4.png（竖封面）＋ 封面_横屏_4x3.png（横封面）；手机 App 发布用 封面_9x16.png',
                 note='抖音：电脑端上传页要同时设竖封面 3:4 和横封面 4:3；标题 ≤ 30 字放钩子和搜索词；简介首句就是钩子；话题 3–5 个；置顶评论抛问题。'),
    '视频号': dict(cover='封面_9x16.png', note='视频号：标题稳重一点，少用网络梗；描述里写清出处，适合转发给朋友。'),
    '小红书': dict(cover='封面_竖屏_3x4.png', note='小红书：标题 ≤ 20 字、带一个表情；正文分点写干货，结尾带 #话题；封面用 3:4。'),
}


class Line:
    def __init__(self, d, start, dur, words):
        self.id, self.who, self.say, self.d = d['id'], d.get('who', '旁白'), d['say'], d
        self.start, self.dur, self.end, self.words = start, dur, start + dur, words
        self.plain = re.sub(r'[【】]', '', self.say)
        self.voiced = [(start, start + dur)]                         # 真实出声的区间（整片秒）；有配音时按波形算，嘴只在这些区间里动

    def talk(self, t):
        """这一刻嘴是不是张开：只在真实出声的区间里一张一合（0.13 秒一下），句中停顿和句尾余音时闭嘴。"""
        for a, b in self.voiced:
            if a <= t < b: return int((t - a) / 0.13) % 2 == 0
        return False

    def at(self, word, frac=0.0):
        """这个词开始念的整片时刻；找不到就按字数比例估。"""
        i = self.plain.find(word)
        if i < 0: return self.start + self.dur * frac
        n = max(1, len(self.plain)); t = self.dur * i / n
        k = 0
        for w in self.words:
            j = self.plain.find(w['text'], k)
            if j < 0: continue
            if j >= i: t = w['t']; break
            k = j + len(w['text'])
        return self.start + t


PARTS = ['钩子', '痛点', '承诺', '正文', '收尾']
FORMATS = ['小品', '实验', '寓言', '排比', '问题链']
MUST = {'术语翻译': '术语一出现就翻成大白话', '生活类比': '至少一个生活类比', '纠正误解': '主动指出并纠正一个常见误解'}
ABSOLUTE = ['一定会', '所有人', '100%', '百分之百', '科学证明', '绝对', '永远不会', '必然']
BANNED = ['震惊', '必看', '全网', '私信', '加微信', '加V', '领取', '点击链接']        # 抖音限流、引流词


def douyin_desc(dy):
    """抖音爆款简介：首句钩子 → 干货 → 互动问题 → 收藏/下期 → 出处行 → 话题。返回 (正文, 话题行)。"""
    body = [dy.get('hook', ''), *dy.get('points', []), dy.get('ask', ''), dy.get('next', '')]
    body = '\n'.join(x for x in body if x)
    src = dy.get('source', '猫咪为拟人演绎，知识来自迈尔斯《社会心理学》')
    tags = ' '.join('#' + t.lstrip('#') for t in dy.get('tags', []))
    return body, src, tags


def check_douyin(meta):
    """抖音标题和爆款简介的自检，只给黄灯。"""
    dy = meta.get('douyin')
    if not dy: return ["META 里没有 douyin（抖音标题＋爆款简介），见 references/抖音发布.md"]
    Wn = []
    kw = dy.get('keyword', '')
    titles = dy.get('titles', [])
    if len(titles) < 3: Wn.append(f'抖音标题只有 {len(titles)} 个：给 3 个备选')
    for x in titles:
        if len(x) > 30: Wn.append(f'抖音标题超过 30 字：{x}')
    if not dy.get('hook'): Wn.append('抖音简介缺首句钩子 hook')
    elif len(dy['hook']) > 20: Wn.append(f'抖音简介首句 {len(dy["hook"])} 字：折叠前只露一行，压到 20 字内')
    body, _, _ = douyin_desc(dy)
    if not kw: Wn.append('douyin 里没写 keyword（观众会搜的词，一般是概念名或场景词）')
    else:
        if not any(kw in x for x in titles): Wn.append(f'没有一个抖音标题带搜索词「{kw}」')
        if kw not in body: Wn.append(f'抖音简介里没出现搜索词「{kw}」')
    if len(body) > 150: Wn.append(f'抖音简介 {len(body)} 字：压到 150 字内（不含出处和话题）')
    if not any(q in dy.get('ask', '') for q in '？?'): Wn.append('抖音简介缺互动问题 ask（要以问句结尾，好回答）')
    n = len(dy.get('tags', []))
    if not meta.get('_flat') and not 3 <= n <= 5: Wn.append(f'抖音话题 {n} 个：3–5 个最好（概念词＋场景词＋领域词＋系列词）')
    for w in ABSOLUTE + BANNED:
        if w in body or any(w in x for x in titles): Wn.append(f'抖音标题/简介用了「{w}」')
    return Wn


def fast(film):
    """完播优先的快节奏模式：film.py 里写 PACE = 'fast'。"""
    return getattr(film, 'PACE', '') == 'fast'


def check_pages(film):
    """平涂版：画面和抖音文案里都不能出现页码（用户 2026-11-07 要求）。"""
    E = []
    src = Path(film.__file__).read_text()
    for k, ln in enumerate(src.splitlines(), 1):
        if re.search(r'(fr\.(text|sticker)|sticker|text)\(.*(书页|第\s*\d+\s*页|页\s*\d)', ln): E.append(f'film.py 第 {k} 行：画面上写了页码，删掉')
    dy = getattr(film, 'META', {}).get('douyin', {})
    for key in ('titles', 'hook', 'points', 'ask', 'next', 'source', 'pinned'):
        v = dy.get(key, '')
        for x in (v if isinstance(v, list) else [v]):
            if re.search(r'书页|\d\s*页|页\s*\d', str(x)): E.append(f'抖音文案 {key} 里有页码：{x}')
    for L in film.LINES:
        if re.search(r'书页|第\s*\d+\s*页', L['say']): E.append(f'{L["id"]} 的口播念了页码')
    return E


def check(film, cast_names):
    E, Wn = [], []
    ids = [d['id'] for d in film.LINES]
    if len(set(ids)) != len(ids): E.append('LINES 里有重复的 id')
    fmt = getattr(film, 'FORMAT', '')
    if fmt == '问题链':                                         # 2026-11-07 默认：一个剧情、一个知识点，用问题链一层层铺开（references/费曼脚本.md 第 0 节）
        parts = [d.get('part', '') for d in film.LINES]
        layers = []
        for x in parts:
            if x.startswith('层') and x.split('·')[0] not in layers: layers.append(x.split('·')[0])
        asks = [d for d in film.LINES if d.get('part', '').startswith('追问')]
        if not parts or not parts[0].startswith('开场'): E.append('问题链：第一句要标 part=\'开场\'（让观众中招、抛出核心问题）')
        if len(layers) < 3: E.append(f'问题链：只有 {len(layers)} 层（part 写 层1·是什么、层2·为什么……），至少 3 层才算铺开')
        if len(asks) < 2: E.append(f'问题链：只有 {len(asks)} 句「追问」：每层结尾让角色说出观众心里的反驳或追问（part=\'追问\'）')
        for d in asks:
            if d.get('who', '旁白') == '旁白': Wn.append(f'{d["id"]}：追问要由角色说（替观众问），不要旁白')
        if not any('办法' in x for x in parts): E.append('问题链：最后一层要是「办法」（part 写 层N·办法），对准前面的「为什么」')
        if '你' not in ''.join(d['say'] for d in film.LINES if d.get('part', '').startswith('开场')): Wn.append('问题链：开场没有对观众说话（没有「你」）：开场要让观众本人中招')
        n_all = sum(len(d['say']) for d in film.LINES) or 1
        n_nar = sum(len(d['say']) for d in film.LINES if d.get('who', '旁白') == '旁白')
        if n_nar / n_all > 0.4: Wn.append(f'问题链：旁白占 {n_nar * 100 // n_all}% 的字：剧情让角色演，旁白只带书里的证据')
        src = Path(getattr(film, '__file__', '')).read_text() if getattr(film, '__file__', '') else ''
        if re.search(r'\b(bar|panel|grow|crowd)\(|\.sticker\(', src):
            Wn.append('问题链：film.py 里还在画图表/贴纸/卡片（bar、panel、grow、crowd、sticker）：用户要求不用图标分析知识，全部情境演绎')
    elif fmt:                                                  # 短视频格式（小品/实验/寓言/排比）：一条线讲到底，不套费曼五段
        if fmt not in FORMATS: E.append(f'FORMAT「{fmt}」不认识（可用：{"、".join(FORMATS)}）')
        term = [i for i, d in enumerate(film.LINES) if '【' in d['say']]
        if term and term[0] < len(film.LINES) * 0.6: Wn.append(f'{fmt}：术语在第 {term[0] + 1}/{len(film.LINES)} 句就出现了，先让观众看懂，放到后 40%')
        n_all = sum(len(d['say']) for d in film.LINES) or 1
        n_nar = sum(len(d['say']) for d in film.LINES if d.get('who', '旁白') == '旁白')
        if fmt in ('小品', '实验') and n_nar / n_all > 0.35: Wn.append(f'{fmt}：旁白占 {n_nar * 100 // n_all}% 的字，让角色自己说，旁白只用来点名')
        if not getattr(film, 'TOPBAR', ''): Wn.append(f'{fmt}：没写 TOPBAR（顶部全程不变的一句标题）')
    else:
        parts = [d.get('part', '').split('·')[0] for d in film.LINES]
        order = [p for p in parts if p]
        for need in PARTS:
            if need not in order: E.append(f'缺少「{need}」段（费曼结构：钩子 → 痛点 → 承诺 → 正文 → 收尾）')
        seen = [PARTS.index(p) for p in order if p in PARTS]
        if seen != sorted(seen): E.append('段落顺序不对：必须按 钩子 → 痛点 → 承诺 → 正文 → 收尾')
        tags = ' '.join(d.get('part', '') for d in film.LINES)
        for k, why in MUST.items():
            if k not in tags: E.append(f'正文里没有标「{k}」的句子：{why}')
    hook = [d for d in film.LINES if d.get('part', '').startswith('钩子')]
    if hook and len(re.sub(r'[【】]', '', hook[0]['say'])) > 20: Wn.append('钩子超过 20 字（约 4 秒）：前三秒要直接、有冲击力')
    for d in film.LINES:
        for w in ABSOLUTE:
            if w in d['say']: Wn.append(f'{d["id"]} 用了「{w}」：换成有出处的具体说法')
        if d.get('who', '旁白') not in cast_names and d.get('who', '旁白') != '旁白': E.append(f'{d["id"]} 的 who「{d["who"]}」不在角色库')
        if d.get('mood', '平叙') not in MOODS: E.append(f'{d["id"]} 的 mood「{d.get("mood")}」不认识（可用：{"、".join(MOODS)}）')
        n = len(re.sub(r'[【】]', '', d['say']))
        if n > 34: Wn.append(f'{d["id"]} 一句 {n} 字，太长不好演：拆成两句')
        who = d.get('who')
        if who and who != '旁白' and d['id'] not in getattr(film, 'SPEAKS', {}).get(who, []):
            Wn.append(f'{d["id"]} 是{who}的台词，但没登记到 SPEAKS[\'{who}\']：说话时不会张嘴')
    for who, ks in getattr(film, 'SPEAKS', {}).items():
        for k in ks:
            if k not in ids: E.append(f'SPEAKS[\'{who}\'] 里的「{k}」不是 LINES 的 id')
    for k, _ in film.SCENES:
        if k not in ids: E.append(f'SCENES 里的「{k}」不是 LINES 的 id')
    for k, _ in getattr(film, 'WIPES', []):
        if k not in ids: E.append(f'WIPES 里的「{k}」不是 LINES 的 id')
    if fast(film):
        plain = lambda d: re.sub(r'[【】]', '', d['say'])
        if hook and len(plain(hook[0])) > 14: Wn.append('快节奏：钩子压到 14 字内（2.5 秒）')
        pr = sum(len(plain(d)) for d in film.LINES if d.get('part', '').startswith('承诺'))
        if pr > 12: Wn.append(f'快节奏：承诺 {pr} 字，压到 12 字内，或只放字幕')
        tail = sum(len(plain(d)) for d in film.LINES if d.get('part', '').startswith('收尾'))
        if tail > 16 and not getattr(film, 'FLAT', False): Wn.append(f'快节奏：收尾 {tail} 字，结尾一拖观众就走；互动问题放字幕和置顶评论')
    angles = set(getattr(film, 'ANGLES', {}).values())
    if len(angles) < 4: Wn.append(f'镜头角度只有 {len(angles)} 种（{"、".join(angles) or "没写 ANGLES"}）：至少用 4 种（远景/特写/过肩/俯视/侧面/背面/主观/分屏/取景器）')
    if getattr(film, 'FLAT', False):
        film.META['_flat'] = True
        E += check_pages(film)
        for k_ in ('cover_v', 'cover_h'):
            if not callable(film.META.get(k_)): E.append(f"平涂版要在 META 里写 {k_}（竖封面 3:4 / 横封面 4:3），用 kit_flat 的 flat_cover_v / flat_cover_h")
    Wn += check_douyin(getattr(film, 'META', {}))
    cv = getattr(film, 'META', {}).get('cover')
    if isinstance(cv, dict):
        if len(cv.get('line1', '')) > 8: Wn.append(f"封面上行「{cv['line1']}」超过 8 字：字会变小")
        if len(cv.get('line2', '')) > 7: Wn.append(f"封面大字「{cv['line2']}」超过 7 字：压短，字才够大")
        if cv.get('hi') and cv['hi'] not in cv.get('line2', ''): Wn.append('封面的 hi 要是大字那一行里的词')
        if cv.get('who') and cv['who'] not in cast_names: E.append(f"封面的 who「{cv['who']}」不在角色库")
    elif callable(cv) and not getattr(film, 'FLAT', False): Wn.append("META['cover'] 还是函数：改成爆款封面模板 dict(line1=, line2=, hi=, who=, expr=, bg=, tag=)，见 references/抖音发布.md")
    if not isinstance(getattr(film, 'META', {}).get('cover'), dict) and not getattr(film, 'META', {}).get('cover_h'): Wn.append("META 里没有 cover_h（抖音横封面 4:3）：会用竖封面自动拼一张，最好单独画")
    # Seed Audio 原速每秒约 3.5 字（第 29 期实测 416 字、tempo 1.25 念了 94.8 秒），按 VOICE_TEMPO 折算；其他配音按每秒 5.2 字
    rate = 3.5 * getattr(film, 'VOICE_TEMPO', 1.0) if getattr(film, 'VOICE', '') == 'libtv' else 5.2
    if fast(film): est = sum(len(re.sub(r'[【】，。！？：；、…—]', '', d['say'])) / rate + d.get('gap', getattr(film, 'GAP', 0.12)) for d in film.LINES) + getattr(film, 'TAIL', 1)
    else: est = sum(len(re.sub(r'[【】]', '', d['say'])) / 4.5 + d.get('gap', 0.28) for d in film.LINES) + 2
    if fast(film):
        lim = 92 if getattr(film, 'FORMAT', '') == '问题链' else 62 if getattr(film, 'FLAT', False) else 50   # 问题链 3–4 层约 70–90 秒（估时已按 Seed Audio 实际语速校准）
        if est > lim: Wn.append(f'快节奏：估计 {est:.0f} 秒，{"问题链压到 90 秒左右（全片约 380 字）" if lim == 92 else "平涂实验格式压到 60 秒内" if lim > 50 else "完播优先要压到 30–45 秒"}')
        shot = est / max(1, len(film.SCENES))
        if shot > (5.5 if getattr(film, 'FLAT', False) else 3.5): Wn.append(f'快节奏：平均 {shot:.1f} 秒才换一个镜头，抖音要 1.5–3 秒一换：多拆几个镜头')
    elif est > 118: Wn.append(f'估计 {est:.0f} 秒，可能超过 120 秒')
    return E, Wn, est


def load_film(path):
    spec = importlib.util.spec_from_file_location('film', path); m = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(Path(path).parent)); spec.loader.exec_module(m); return m


def voice_lines(film, base, build, no_voice):
    if getattr(film, 'VOICE', '') == 'libtv' and not no_voice:     # LibTV Seed Audio：只读 libtv_voice.py fetch 写好的缓存
        import libtv_voice
        out, missing = libtv_voice.for_build(base, build, getattr(film, 'VOICE_TEMPO', 1.0), getattr(film, 'VOICE_MAX_GAP', None),
                                             getattr(film, 'VOICE_MIN_RATE', None))
        if missing:
            sys.exit(f'🔴 还有 {len(missing)} 句没配音：{", ".join(missing)}\n'
                     f'   先跑 python3 $S/scripts/libtv_voice.py plan {base}，用 LibTV 生成后 fetch 进缓存（见 references/平涂画风.md 第 5 节）')
        return out
    cast, cast_dir = find_cast(base)
    use = (not no_voice) and seed_voice.api_key() and cast_dir
    out = []
    for d in film.LINES:
        plain = re.sub(r'[【】]', '', d['say'])
        if not use:
            out.append((None, [], len(plain) / (5.2 if fast(film) else 4.5))); continue
        who = d.get('who', '旁白'); key = who if who in cast else '_旁白'
        rate, tone_n, emo = MOODS[d.get('mood', '平叙')]
        style = ((cast.get(key) or {}).get('seed') or {}).get('style', '')
        tone = d.get('tone') or (tone_n if key == '_旁白' else '，'.join(x for x in (style, emo and f'这一句{emo}') if x))
        if fast(film) and key == '_旁白' and not d.get('tone'):                # 快节奏：去掉放慢、停顿的说法，整体轻快
            tone = re.sub(r'放慢语速，|放慢一点，|先停半拍，|，关键处停顿一下|，像在讲一个秘密', '', tone) + '，语速偏快、紧凑，不拖音，不刻意停顿'
        sr = (55 + rate // 4) if fast(film) else (20 + rate // 2)          # 快节奏：每秒 5 个多字
        mp3, words, dur, heard = seed_voice.say(plain, seed_voice.sample_path(cast_dir, key), tone, build / 'tts', sr + d.get('rate', 0))
        if heard: print(f'🟡 {d["id"]} 念出来和稿子不一样：「{heard}」')
        print(f'  {d["id"]:<8} {dur:5.2f}s [{d.get("mood", "平叙")}] {who}：{plain[:26]}')
        out.append((mp3, words, dur))
    return out


def pcm(mp3):
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(mp3), '-f', 's16le', '-ac', '1', '-ar', '48000', '-'])
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def write_wav(path, x):
    x = np.clip(x, -1, 1); y = (x * 32767).astype(np.int16)
    with wave.open(str(path), 'wb') as w: w.setnchannels(1); w.setsampwidth(2); w.setframerate(48000); w.writeframes(y.tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('film'); ap.add_argument('--still', help='只出这几个时刻的样帧，如 1.5,30')
    ap.add_argument('--no-voice', action='store_true'); ap.add_argument('--no-bgm', action='store_true')
    ap.add_argument('--platform', default='抖音', choices=list(PLATFORMS))
    ap.add_argument('--check', action='store_true'); ap.add_argument('--preview', action='store_true')
    ap.add_argument('--publish-only', action='store_true', help='不渲画面：用缓存的配音时间轴，只重出字幕、封面和这个平台的发布文案')
    a = ap.parse_args()
    sys.stdout.reconfigure(line_buffering=True)
    fp = Path(a.film).resolve(); base = fp.parent; build, out = base / 'build', base / 'output'
    for p in (build / 'tts', build / 'audio', out): p.mkdir(parents=True, exist_ok=True)
    film = load_film(fp)
    if getattr(film, 'STYLE', 'pixel') == 'line':
        import kit_line as K
    else:
        K = kit
    kit.SPEAKS.clear(); kit.SPEAKS.update(getattr(film, 'SPEAKS', {}))
    cast, _ = find_cast(base)
    E, Wn, est = check(film, set(cast))
    for w in Wn: print('🟡', w)
    for e in E: print('🔴', e)
    if E: sys.exit(f'有 {len(E)} 条红灯，先改 film.py。')
    print(f'✅ 检查通过：{len(film.LINES)} 句，估计 {est:.0f} 秒，角度 {len(set(getattr(film, "ANGLES", {}).values()))} 种')
    if a.check: return

    # 1 配音 → 时间轴
    print('配音…')
    vo = voice_lines(film, base, build, a.no_voice)
    F = fast(film)
    T, t = {}, (0.1 if F else 0.4)
    for d, (mp3, words, dur) in zip(film.LINES, vo):
        T[d['id']] = L_ = Line(d, t, dur, words); t += dur + d.get('gap', film.__dict__.get('GAP', 0.12 if F else 0.28))   # GAP：整集默认句间停顿（小品对话用 0.25）
        if mp3 is not None: L_.voiced = [(L_.start + a_, L_.start + b_) for a_, b_ in seed_voice.voiced(seed_voice.envelope(pcm(mp3)), merge=0.12)]
    total = round((t + film.__dict__.get('TAIL', 0.8 if F else 1.6)) * FPS) / FPS
    lines = [T[d['id']] for d in film.LINES]
    print(f'时间轴：{len(lines)} 句，{total:.1f} 秒')
    if total > 120: print(f'🟡 全片 {total:.1f} 秒，超过 120 秒：删一两句')
    scenes = sorted(((T[k].start, fn) for k, fn in film.SCENES), key=lambda x: x[0])
    wipes = [(T[k].start - 0.18, title) for k, title in getattr(film, 'WIPES', [])]
    caps = []
    for L in lines:
        for c0, c1, txt, hi in kit.caption_chunks(L.say, L.words, L.dur):
            caps.append((L.start + c0, L.start + c1 + (0.25 if c1 >= L.dur - 1e-6 else 0), txt, hi, None if L.who == '旁白' else L.who))

    nocap = [(L.start, L.end + L.d.get('gap', 0.3)) for L in lines if L.d.get('cap') is False]   # cap=False：这句的字已经大字上屏（金句卡），不再压底部字幕
    if lines and lines[-1].d.get('cap') is False: nocap[-1] = (lines[-1].start, 1e9)
    punches = []                                                       # 快节奏：念到【重点词】时镜头推近一下，到下一句复原
    if F and getattr(film, 'AUTOZOOM', True):
        for L in lines:
            for h in re.findall(r'【(.+?)】', L.say): punches.append((L.at(h), L.end + L.d.get('gap', film.__dict__.get('GAP', 0.12))))
    cap_size = 76 if F else 64

    def frame(t):
        fr = K.Frame(); fr.t = t
        fn = [f for s, f in scenes if s <= t + 1e-6]; fn = fn[-1] if fn else scenes[0][1]
        fn(fr, t, T)
        fr.scene_ops = len(fr.ops)                                     # 到这里为止的字和贴纸属于镜头，跟着推近；下面的标题栏、字幕不动
        if fr.zoom is None:
            for p0, p1 in punches:
                if p0 <= t < p1: fr.zoom = (1 + 0.1 * kit.eout((t - p0) / 0.15), kit.W / 2, 220); break
        for w0, title in wipes: fr.wipe(t, w0, title)
        overlay = getattr(film, 'OVERLAY', True)                       # Vox 版：顶部标题、字幕、名牌由片段自己画（vox_shots.py），这里不再叠
        if overlay and getattr(film, 'TOPBAR', ''): kit.draw_topbar(fr, film.TOPBAR)
        shown = None
        for c0, c1, txt, hi, who in (caps if overlay else []):
            if any(a <= t < b for a, b in nocap): break
            if c0 <= t < c1: kit.draw_caption(fr, txt, hi, who, cap_size); shown = txt; break
        if shown and qa is not None:                                    # 自检：字幕（含名牌）压在猫身上
            for name, x0, y0, x1, y1 in getattr(fr, 'cats', []):
                if fr.zoom and fr.zoom[0] > 1.001:                         # 推近时换算成画面上的位置
                    f_, cx_, cy_ = fr.zoom; x0_ = kit.clamp(cx_ - kit.W / f_ / 2, 0, kit.W - kit.W / f_); y0_ = kit.clamp(cy_ - kit.H / f_ / 2, 0, kit.H - kit.H / f_)
                    x0, x1, y1 = (x0 - x0_) * f_, (x1 - x0_) * f_, (y1 - y0_) * f_
                if y1 > CAP_TOP and x1 > 40 and x0 < kit.W - 40:
                    qa['overlap'].setdefault(cur_line(t), set()).add(name)
        return fr.render()

    def cur_line(t):
        k = [L.id for L in lines if L.start <= t + 1e-6]
        return k[-1] if k else lines[0].id
    CAP_TOP = 338                                                       # 字幕带（名牌 + 字）从逻辑 y≈338 开始；角色的脚要踩在它上面
    qa = None

    if a.preview:
        from PIL import Image
        thumbs = [frame(L.start + L.dur * 0.6).resize((270, 480), Image.LANCZOS) for L in lines]
        cols = 6; rows = (len(thumbs) + cols - 1) // cols
        sheet = Image.new('RGB', (cols * 270, rows * 480), (30, 30, 40))
        for k, im in enumerate(thumbs): sheet.paste(im, ((k % cols) * 270, (k // cols) * 480))
        sheet.save(out / '预览.jpg', quality=85); print('预览 →', out / '预览.jpg'); return
    if a.still:
        for s in a.still.split(','):
            p = build / f'still_{float(s):06.2f}.png'; frame(float(s)).save(p); print('样帧 →', p)
        return

    CUT_DIFF = 10                                                       # 相邻两帧（缩到 54×96 灰度）平均差超过它，算一次切镜

    def rhythm_report(cuts):
        """自检视听节奏：切镜切在话中间、一闪而过的镜头、字幕压在猫身上。写进 build/qa/节奏.txt，同时打印。"""
        msgs = []
        for c in cuts:
            for L in lines:
                for a_, b_ in L.voiced:
                    if a_ + 0.12 < c < b_ - 0.12:
                        msgs.append(f'{c:5.2f}s 切镜时 {L.id} 还在说话（{L.who}：{L.plain[:14]}…）：镜头留到这句说完，或者改成同一镜头里的动作')
        edges = [0.0] + cuts + [total]
        for a_, b_ in zip(edges, edges[1:]):
            if b_ - a_ < 0.7 and a_ > 0: msgs.append(f'{a_:5.2f}s 这个镜头只有 {b_ - a_:.2f} 秒，一闪而过：并到前后镜头，或者给这句加 gap 让它停够 1 秒')
        for lid, names in qa['overlap'].items():
            msgs.append(f'{lid} 字幕压在{"、".join(sorted(names))}身上：角色脚底放到 y≤{CAP_TOP}（scene(ground=…) 一起改），字幕带留给地面')
        for L in lines:
            if L.voiced and L.words and abs((L.start + L.words[0]['t']) - L.voiced[0][0]) > 0.15:
                msgs.append(f'{L.id} 字幕比声音早/晚 {(L.start + L.words[0]["t"]) - L.voiced[0][0]:+.2f} 秒')
        (build / 'qa').mkdir(exist_ok=True)
        (build / 'qa' / '节奏.txt').write_text('\n'.join([f'切镜 {len(cuts)} 次：' + ' '.join(f'{c:.2f}' for c in cuts)] + msgs) + '\n')
        if msgs: print(f'🟡 视听节奏自检有 {len(msgs)} 条（build/qa/节奏.txt）：'); [print('   ', m) for m in msgs[:20]]
        else: print(f'✅ 视听节奏自检通过：切镜 {len(cuts)} 次，没有切在话中间，没有一闪而过的镜头，字幕没压到猫')

    def render_and_mix():
        # 2 画面
        video = build / '画面.mp4'; n = int(total * FPS)
        print(f'渲染 {n} 帧…')
        ff = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{kit.W * kit.S}x{kit.H * kit.S}', '-r', str(FPS), '-i', '-',
                               '-c:v', 'libx264', '-preset', 'medium', '-crf', '18', '-pix_fmt', 'yuv420p', '-threads', '2', str(video)], stdin=subprocess.PIPE)
        nonlocal qa
        qa = {'overlap': {}}; prev = None; cuts = []
        for i in range(n):
            img = frame(i / FPS); ff.stdin.write(img.tobytes())
            small = np.asarray(img.resize((54, 96)).convert('L'), np.float32)
            if prev is not None and np.abs(small - prev).mean() > CUT_DIFF: cuts.append(i / FPS)
            prev = small
            if i % (FPS * 10) == 0: print(f'  {i / FPS:5.1f}s')
        ff.stdin.close(); ff.wait()
        rhythm_report(cuts)

        # 3 声音：配音轨 + 情绪配乐 + 音效
        N = int((total + 1) * 48000); voice = np.zeros(N, np.float32)
        for L, (mp3, _, _) in zip(lines, vo):
            if mp3 is None: continue
            x = pcm(mp3); i0 = int(L.start * 48000); voice[i0:i0 + len(x)] += x[:N - i0]
        write_wav(build / '口播.wav', voice[:int(total * 48000)])
        # 配乐：全片一段浅浅的铺底（不按情绪切段、不抽空），节奏交给音效
        beds = [{'start': 0.0, 'end': total, 'mood': getattr(film, 'BGM', '轻松')}]
        sfx = [{'t': t0, 'name': nm, 'gain': g} for t0, nm, g in film.SFX(T)] + [{'t': w0, 'name': 'whoosh', 'gain': 0.5} for w0, _ in wipes]
        drops = []
        plan = {'total': total, 'beds': beds, 'drops': drops, 'sfx': sfx}
        (build / '音频计划.json').write_text(json.dumps(plan, ensure_ascii=False, indent=1))
        r = subprocess.run(['uv', 'run', '--quiet', '--with', 'numpy', '--with', 'scipy', '--with', 'soundfile', 'python', str(SKILL / 'scripts' / 'audio_fx.py'),
                            '--plan', str(build / '音频计划.json'), '--out', str(build / 'audio')], capture_output=True, text=True)
        if r.returncode: sys.exit('配乐/音效合成失败：\n' + r.stderr[-1500:])
        af = 'aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo'
        bv = 0 if a.no_bgm else 0.6                                # 铺底再压低一点，人声和音效在前
        fc = (f'[1:a]{af},asplit=2[vo][key];[2:a]{af},volume={bv}[bg0];[bg0][key]sidechaincompress=threshold=0.025:ratio=6:attack=15:release=400,{af}[bg];'
              f'[3:a]{af}[fx];[vo][bg][fx]amix=inputs=3:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11[a]')
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(video), '-i', str(build / '口播.wav'), '-i', str(build / 'audio' / 'bgm.wav'), '-i', str(build / 'audio' / 'sfx.wav'),
                        '-filter_complex', fc, '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000', '-t', f'{total:.3f}', '-movflags', '+faststart', str(final)], check=True)

    final = out / '成片.mp4'
    if not a.publish_only: render_and_mix()
    elif not final.exists(): print('🟡 还没有成片：--publish-only 只重出字幕、封面和发布文案')

    # 4 字幕、口播稿、抽帧、封面、发布文案
    st = lambda x: f'{int(x // 3600):02d}:{int(x % 3600 // 60):02d}:{int(x % 60):02d},{int(round(x % 1 * 1000)) % 1000:03d}'
    FL = getattr(film, 'FLAT', False)                                  # 平涂版：output/ 只放成片、两张封面、抖音文案.txt，其余放 build/qa
    qa = build / 'qa' if FL else out; qa.mkdir(parents=True, exist_ok=True)
    (qa / '字幕.srt').write_text(''.join(f'{k}\n{st(c0)} --> {st(c1)}\n{(who + "：") if who else ""}{txt}\n\n' for k, (c0, c1, txt, _, who) in enumerate(caps, 1)))
    (qa / '口播稿.txt').write_text('\n'.join(f'[{L.start:5.1f}s] [{L.d.get("part", "")}] {L.who}：{L.plain}' for L in lines) + '\n')
    times = [L.start + L.dur * 0.6 for L in lines]
    from PIL import Image
    thumbs = [frame(x).resize((270, 480), Image.LANCZOS) for x in times]
    cols = 6; rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * 270, rows * 480), (30, 30, 40))
    for k, im in enumerate(thumbs): sheet.paste(im, ((k % cols) * 270, (k // cols) * 480))
    sheet.save(qa / '抽帧.jpg', quality=85)
    meta = film.META
    if isinstance(meta.get('cover'), dict):                             # 爆款封面模板：三个尺寸各自排版
        cv = dict(meta['cover'])
        if 'no' not in cv:
            m = re.match(r'(\d+)', base.name); cv['no'] = int(m.group(1)) if m else None
        if isinstance(cv.get('bg'), str) and not Path(cv['bg']).is_absolute(): cv['bg'] = str(base / cv['bg'])
        for name, size in (('封面_9x16.png', (kit.W, kit.H)), ('封面_竖屏_3x4.png', (270, 360)), ('封面_横屏_4x3.png', kit.HCOVER)):
            fr = K.Frame(size=size); K.douyin_cover(fr, cv); fr.render().save(out / name)
    elif FL and meta.get('cover_v'):                                   # 平涂版：竖 3:4、横 4:3 各自构图
        fr = K.Frame(size=(270, 360)); meta['cover_v'](fr); fr.render().save(out / '封面_竖屏_3x4.png')
        fh = K.Frame(size=kit.HCOVER); meta['cover_h'](fh); fh.render().save(out / '封面_横屏_4x3.png')
    elif meta.get('cover'):
        fr = K.Frame(); meta['cover'](fr); img = fr.render()
        img.save((qa if FL else out) / '封面_9x16.png')
        # 竖封面 3:4（1080×1440）：窗口对准封面上的字和贴纸（标题优先）
        ys = [(a_[2] - a_[3], a_[2] + a_[3] * 1.5) for k_, a_, _ in fr.ops if k_ in ('text', 'sticker', 'bubble')]
        lo, hi = (min(y for y, _ in ys), max(y for _, y in ys)) if ys else (240, 1680)
        top = (lo + hi) / 2 - 720 if hi - lo <= 1440 else lo
        top = int(kit.clamp(top, 0, 480))
        v34 = img.crop((0, top, 1080, top + 1440)); v34.save(out / '封面_竖屏_3x4.png')
        # 横封面 4:3（1440×1080）：film.py 的 META['cover_h'] 在 360×270 的横画布上单独构图；没写就用竖封面拼一张
        if meta.get('cover_h'):
            fh = K.Frame(size=kit.HCOVER); meta['cover_h'](fh); fh.render().save(out / '封面_横屏_4x3.png')
        else:
            from PIL import ImageFilter
            bg = img.resize((1440, 2560), Image.LANCZOS).crop((0, 740, 1440, 1820)).filter(ImageFilter.GaussianBlur(28))
            bg = Image.blend(bg, Image.new('RGB', bg.size, (0, 0, 0)), 0.3)
            bg.paste(v34.resize((810, 1080), Image.LANCZOS), (315, 0)); bg.save(out / '封面_横屏_4x3.png')
            print('🟡 横封面是用竖封面拼的（模糊背景＋居中）；在 META 里写 cover_h 单独构图会更好')
    if FL and meta.get('douyin'):                                      # 平涂版：抖音爆款文案 txt（不带话题、不带页码）
        dy = meta['douyin']; body, src, _ = douyin_desc(dy)
        txt = ['【标题】（三选一）', *[f'{k}. {x}' for k, x in enumerate(dy.get('titles', []), 1)], '', '【作品简介】', body, src, '']
        if dy.get('pinned'): txt += ['【置顶评论】', dy['pinned'], '']
        txt += ['【发布提醒】作品声明里勾选「内容由AI生成」。']
        (out / '抖音文案.txt').write_text('\n'.join(txt) + '\n')
        print(f'\n🎬 成片 → {final}（{total:.1f}s）\n   output/ 里：成片.mp4、封面_竖屏_3x4.png、封面_横屏_4x3.png、抖音文案.txt；自检材料在 build/qa/')
        return
    pf = PLATFORMS[a.platform]; pub = dict(meta.get('publish', {})); pub.update(meta.get('platforms', {}).get(a.platform, {}))
    md = [f'# 发布文案 · {meta.get("title", base.name)}（{a.platform}）', '', f'时长 {total:.1f} 秒 · 封面：{pf["cover"]}', '', f'> {pf["note"]}', '']
    dy = meta.get('douyin') if a.platform == '抖音' else None
    if dy:
        body, src, tags = douyin_desc(dy)
        if dy.get('titles'): md += ['## 作品标题（三选一，≤ 30 字）', *[f'{k}. {x}' for k, x in enumerate(dy['titles'], 1)], '']
        md += ['## 爆款简介（整段复制到「作品简介」）', '', '```', body, src, tags, '```', '',
               f'搜索词：{dy.get("keyword", "")} · 简介 {len(body)} 字（不含出处和话题）', '']
        if dy.get('pinned') or pub.get('pinned'): md += ['## 置顶评论', dy.get('pinned') or pub['pinned'], '']
    else:
        if pub.get('titles'): md += ['## 标题（三选一）', *[f'{k}. {x}' for k, x in enumerate(pub['titles'], 1)], '']
        md += ['## 简介', pub.get('desc', ''), '本系列猫咪均为拟人演绎，故事纯属虚构；心理学实验和数据来自真实的人类研究，出处见下。', '']
        if pub.get('tags'): md += ['## 话题', ' '.join('#' + x.lstrip('#') for x in pub['tags']), '']
        if pub.get('pinned'): md += ['## 置顶评论', pub['pinned'], '']
    md += ['## 出处', *[f'- {x}' for x in meta.get('sources', [])], '']
    md += ['## 配乐、音效与配音', '配乐和音效为代码合成的原创作品。配音：豆包音频生成 seed-audio-1.0 的设计音色，AI 合成；发布时在「作品声明」里勾选「内容由AI生成」。', '']
    pubf = out / ('发布文案.md' if a.platform == '抖音' else f'发布文案_{a.platform}.md')   # 各平台各一份，不互相覆盖
    pubf.write_text('\n'.join(md))
    print(f'\n🎬 成片 → {final}（{total:.1f}s）\n   字幕/口播稿/抽帧/封面 → {out}/ · 发布文案 → {pubf.name}')


if __name__ == '__main__':
    main()
