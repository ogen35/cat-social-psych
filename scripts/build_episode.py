#!/usr/bin/env python3
"""一集猫咪社会心理学抖音视频：分镜.json → 检查 → 配音 → 逐镜渲 Vox 竖屏片段 → 拼接混音 → 成片＋字幕＋封面＋发布文案。

  S=<skill 目录>
  uv run --with playwright --with edge-tts python $S/scripts/build_episode.py <集目录>/分镜.json --check      # 只检查，不渲
  uv run --with playwright --with edge-tts python $S/scripts/build_episode.py <集目录>/分镜.json            # 出片
     [--tts auto|seed|edge] [--voice zh-CN-YunxiNeural | --no-voice] [--rate +20%] [--bgm 音乐.mp3] [--bgm-vol 1.0] [--no-bgm] [--no-sfx] [--jobs 1] [--only 3,4]

分镜.json 的写法见 references/分镜规范.md。产物在 <集目录>/output/：
  成片.mp4（1080×1920@30，带配音时有声）· 字幕.srt · 口播稿.txt · 封面.png · 发布文案.md · 抽帧.jpg（每镜中段一帧，审片用）
中间文件在 <集目录>/build/（按内容哈希缓存：只改了一镜，只重渲那一镜）。

情绪（mood）：每镜一个，决定配音的语速音高、配乐、画面的压暗和推近；重音（accent cue）配音效、白闪、震屏、大字砸入。
配乐和音效由 audio_fx.py 纯代码合成（原创，没有版权问题），配乐在人声下自动避让，整片响度对齐 -14 LUFS。

配音：有豆包语音的 API Key、而且每个出场角色都有声音样本（seed_voice.py design 生成）时，用豆包音频生成 seed-audio-1.0：
每个角色固定一个设计好的声音，每句按 mood（或单镜的 tone）带情绪念，要联网、按时长计费（会把口播稿发给火山引擎）。
否则用 edge-tts（微软在线语音，免费、要联网；会把口播稿发给微软的服务）。--tts edge|seed 强制选一个。
--no-voice 出无声片，时长按 4.5 字/秒估，之后用剪映配音即可（字幕.srt 的时间就是按这个估的）。
"""
import argparse, asyncio, concurrent.futures as cf, hashlib, json, math, re, shutil, subprocess, sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL / 'scripts'))
from cards_story import find_cast   # 角色表：谁用什么配音
import seed_voice                   # 豆包音频生成配音（固定音色＋情绪）
ENGINE = SKILL / 'scripts' / 'engine'
W, H, FPS = 1080, 1920, 30
SAFE_TOP, SAFE_BOTTOM = 360, 560          # 顶部标题栏 / 底部字幕带（抖音底部 UI 约占最下 420px，字幕落在它上面）
CPS = 4.5                                  # 配音前估时长用的语速（字/秒，含标点）：豆包实测约 4.5、edge-tts +20% 约 4.8，按慢的估，免得出片前才发现超 8 秒
MAX_LABEL = 14                             # 上屏文字（标签、索引卡、标题条）上限
PALETTE_INK = {'vox': '#171716', 'paper': '#1B1A17', 'poster': '#111111', 'ink': '#0B0C0E', 'navy': '#081320', 'bauhaus': '#111111', 'snow': '#1F2A30', 'wood': '#2B2622', 'chalk': '#18211D'}
# 情绪 → 配音（相对基础语速的增减、音高）、画面（压暗、整镜推近）。配乐见 audio_fx.py 的 BEDS
MOODS = {
    '平叙': {'rate': 0,   'pitch': 0,  'vignette': 0.2,  'creep': 0.0, 'tone': '自然聊天的口吻，清楚、有条理，不要播音腔', 'emo': ''},
    '悬疑': {'rate': -12, 'pitch': -5, 'vignette': 0.55, 'creep': 0.05, 'tone': '压低声音、放慢语速，神秘、带着悬念，像在讲一个秘密，关键处停顿一下', 'emo': '压着嗓子、紧张兮兮'},
    '紧张': {'rate': 10,  'pitch': 2,  'vignette': 0.4,  'creep': 0.07, 'tone': '语速加快，紧张、急促，一句比一句紧', 'emo': '很着急'},
    '揭晓': {'rate': -12, 'pitch': -3, 'vignette': 0.35, 'creep': 0.0, 'tone': '先停半拍，再郑重、有力地宣布答案，带着一点震惊', 'emo': '很震惊'},
    '反转': {'rate': 8,   'pitch': 6,  'vignette': 0.1,  'creep': 0.0, 'tone': '语气突然一转，惊讶里带着调侃，语调上扬', 'emo': '很意外'},
    '轻松': {'rate': 6,   'pitch': 3,  'vignette': 0.1,  'creep': 0.0, 'tone': '轻松调侃、带着笑意，像在跟朋友八卦', 'emo': '很开心'},
    '温暖': {'rate': -8,  'pitch': 0,  'vignette': 0.1,  'creep': 0.0, 'tone': '温柔、真诚，放慢一点，带着微笑', 'emo': '很真诚'},
}
SFX_NAMES = ['whoosh', 'hit', 'boom', 'riser', 'ding', 'pop', 'tick', 'heartbeat', 'glitch', 'scratch', 'sting']
RISKY = ['科学证明', '100%', '一定会', '绝对', '所有猫', '所有人', '治愈', '治疗']

# ---------------------------------------------------------------- 文本工具
def plain(s):
    return re.sub(r'[【】]', '', s or '')


def segs(s):
    out, hi = [], False
    for ch in s or '':
        if ch == '【': hi = True; continue
        if ch == '】': hi = False; continue
        out.append((ch, hi))
    return out


def join_segs(ss):
    out, hi = '', False
    for ch, h in ss:
        if h and not hi: out += '【'
        if not h and hi: out += '】'
        out += ch; hi = h
    return out + ('】' if hi else '')


PUNCT = '，。！？；：、…,.!?;:'
def sub_chunks(say, maxc=16):
    """口播一句 → 字幕若干条（在标点处断，单条 ≤maxc 字；去掉句尾的逗号句号，保留问号叹号）。返回 [(seg列表, 起始字下标, 结束字下标)]。"""
    ss = segs(say); parts, cur, start = [], [], 0
    for i, (ch, h) in enumerate(ss):
        cur.append((ch, h))
        if ch in PUNCT or i == len(ss) - 1:
            parts.append((cur, start, i + 1)); cur, start = [], i + 1
    # 只有标点的片段（「睡觉？？」的第二个问号）并回前一段，不单独成一条字幕
    glued = []
    for p in parts:
        if glued and all(c in PUNCT or c.isspace() for c, _ in p[0]):
            glued[-1] = (glued[-1][0] + p[0], glued[-1][1], p[2])
        else:
            glued.append(p)
    parts = glued
    merged = []
    for p in parts:
        if merged and len(merged[-1][0]) + len(p[0]) <= maxc and merged[-1][0][-1][0] not in '。！？!?':
            merged[-1] = (merged[-1][0] + p[0], merged[-1][1], p[2])
        else:
            merged.append(p)
    out = []
    for body, a, b in merged:                       # 超长的硬切
        while len(body) > maxc:
            out.append((body[:maxc - 2], a, a + maxc - 2)); body, a = body[maxc - 2:], a + maxc - 2
        out.append((body, a, b))
    clean = []
    for body, a, b in out:
        while body and body[-1][0] in '，。、,.;；：:': body = body[:-1]
        if any(not c.isspace() for c, _ in body): clean.append((body, a, b))
    return clean


def sha(*xs):
    return hashlib.sha1(json.dumps(xs, ensure_ascii=False, sort_keys=True).encode()).hexdigest()[:12]


def lum(hexc):
    h = hexc.lstrip('#'); r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    f = lambda x: x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def probe_dur(f):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(f)]).decode().strip())

# ---------------------------------------------------------------- 配音（edge-tts，逐词时间）
async def _tts(text, voice, rate, pitch, mp3):
    import edge_tts
    com = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, boundary='WordBoundary')
    words = []
    with open(mp3, 'wb') as f:
        async for ch in com.stream():
            if ch['type'] == 'audio': f.write(ch['data'])
            elif ch['type'] == 'WordBoundary': words.append({'t': ch['offset'] / 1e7, 'd': ch['duration'] / 1e7, 'text': ch['text']})
    return words


def tts(text, voice, rate, cache, pitch='+0Hz'):
    key = sha(text, voice, rate, pitch); mp3, js = cache / f'{key}.mp3', cache / f'{key}.json'
    if not (mp3.exists() and js.exists()):
        for attempt in range(3):
            try:
                words = asyncio.run(_tts(text, voice, rate, pitch, mp3)); break
            except Exception as e:
                if attempt == 2: raise SystemExit(f'配音失败（edge-tts 要联网）：{e}\n可以先加 --no-voice 出无声片。')
        js.write_text(json.dumps(words, ensure_ascii=False))
    return mp3, json.loads(js.read_text()), probe_dur(mp3)


def char_clock(say_plain, words, total):
    """第 i 个字什么时候念到：有逐词时间就按词对齐，没有就按字数均分。返回 f(i)->秒。"""
    n = max(1, len(say_plain))
    if not words:
        return lambda i: total * min(i, n) / n
    pts, cur = [(0, words[0]['t'])], 0
    for w in words:
        k = say_plain.find(w['text'], cur)
        if k < 0: continue
        pts.append((k, w['t'])); pts.append((k + len(w['text']), w['t'] + w['d'])); cur = k + len(w['text'])
    pts.append((n, total)); pts.sort()
    def f(i):
        for (a, ta), (b, tb) in zip(pts, pts[1:]):
            if a <= i <= b: return ta if b == a else ta + (tb - ta) * (i - a) / (b - a)
        return total
    return f

# ---------------------------------------------------------------- 检查
def check(ep, base, durs=None, soft_dur=False):
    E, Wn = [], []
    cast, _ = find_cast(base)
    shots = ep.get('shots') or []
    if not shots: E.append('没有 shots')
    if not ep.get('sources'): E.append('sources 为空：至少写书的章节和经典研究出处（科普号的底线，也是评论区被质疑时的依据）')
    if not ep.get('title'): Wn.append('没写 title（顶部标题栏）')
    elif '【' not in ep['title']: Wn.append('顶部标题没有【】高亮词：抖音标题栏要有一个抓眼的词')
    total = 0
    text_only, hl_shots = 0, 0
    prev_img = None
    prev_hl, mood, moods, sections, hl_say, n_accent = False, '平叙', set(), 1, 0, 0
    for i, s in enumerate(shots, 1):
        tag = f'镜{i:02d}'
        say = s.get('say', '')
        if not plain(say).strip(): E.append(f'{tag} 没有 say（口播）'); continue
        if s.get('who') and s['who'] not in cast: Wn.append(f'{tag} who「{s["who"]}」不在角色库/角色.json 里：会用旁白的声音')
        if s.get('who') and len(re.sub(r'[，。！？、…,.!?\s]', '', plain(say))) > 12: Wn.append(f'{tag} 角色台词超过 12 字：台词要短，长的交给旁白')
        d = durs[i - 1] if durs else len(plain(say)) / CPS + s.get('pause', 0.15)
        total += d
        if d > 8:
            msg = f'{tag} 约 {d:.1f}s，超过 8 秒：拆成两镜（单个 Vox 片段撑太久就成了 PPT）'
            # 没配音时按语速估的时长只是估计：出片时会先配音、再按真实时长卡 8 秒，所以估计超了只亮黄灯
            (Wn if soft_dur else E).append(msg + ('（按语速估计；配音后按真实时长再查）' if soft_dur else ''))
        for w in RISKY:
            if w in plain(say): Wn.append(f'{tag} 口播里有「{w}」：抖音科普容易被判夸大，换成有出处的具体说法')
        cues = s.get('cues') or []
        if not cues: E.append(f'{tag} 没有 cues'); continue
        imgs = [q for q in cues if q.get('kind') in ('image', 'clip')]
        if not imgs: text_only += 1
        has_hl = any(q.get('kind') == 'highlight' for q in cues)
        if has_hl: hl_shots += 1
        if has_hl and prev_hl: Wn.append(f'{tag} 和上一镜都画了红圈：红圈只给每段的重点，其余用音效（accent）')
        prev_hl = has_hl
        if s.get('mood') and s['mood'] not in MOODS: E.append(f'{tag} 不认识的情绪「{s["mood"]}」（可用：{" ".join(MOODS)}）')
        mood = s.get('mood') or mood; moods.add(mood)
        if s.get('title'): sections += 1
        if '【' in say: hl_say += 1
        cur_img = None
        for q in cues:
            k = q.get('kind')
            if k not in ('image', 'clip', 'title', 'point', 'highlight', 'accent', 'sfx'): E.append(f'{tag} 不认识的 kind「{k}」（image/title/point/highlight/accent/sfx）')
            if k == 'sfx' and q.get('name') not in SFX_NAMES: E.append(f'{tag} 音效「{q.get("name")}」不存在（可用：{" ".join(SFX_NAMES)}）')
            if k == 'accent' and q.get('sfx', 'hit') not in SFX_NAMES: E.append(f'{tag} 重音的音效「{q.get("sfx")}」不存在（可用：{" ".join(SFX_NAMES)}）')
            if k == 'accent': n_accent += 1
            if k in ('image', 'clip'):
                f = base / q.get('image', '')
                if not q.get('image') or not f.is_file(): E.append(f'{tag} 图片不存在：{q.get("image")}')
                cur_img = f
            if k in ('title', 'point') and not plain(q.get('text', '')).strip(): E.append(f'{tag} {k} 没有 text')
            t = plain(q.get('text', ''))
            if len(t) > MAX_LABEL: E.append(f'{tag} 上屏文字「{t}」{len(t)} 字，超过 {MAX_LABEL}：口播交给字幕，屏上只留关键词')
            if k == 'highlight':
                if cur_img is None: E.append(f'{tag} highlight 前面没有图：荧光笔要画在本镜的某张图上')
                elif 'mark' in q:
                    sc = cur_img.with_suffix('.json')
                    if not sc.exists(): E.append(f'{tag} highlight 写了 mark，但 {cur_img.name} 没有 make_card.py 生成的坐标文件')
                    else:
                        mk = json.loads(sc.read_text()).get('marks', [])
                        if not (0 <= int(q['mark']) < len(mk)): E.append(f'{tag} mark={q["mark"]} 超出范围（{cur_img.name} 只有 {len(mk)} 个【】重点）')
                elif not (q.get('rect') or (q.get('data') or {}).get('rect')): E.append(f'{tag} highlight 要写 mark（证据卡）或 rect（照片，[x,y,w,h] 0..1）')
            if q.get('on') and q['on'] not in plain(say): E.append(f'{tag} on「{q["on"]}」不在这一镜的口播里')
        if imgs and prev_img and imgs[0].get('image') == prev_img: Wn.append(f'{tag} 和上一镜开头是同一张图：相邻两镜换构图')
        prev_img = imgs[-1].get('image') if imgs else prev_img
        if i == 1:
            if d > 4.2: Wn.append(f'镜01 约 {d:.1f}s：钩子镜头最好 ≤4 秒，一句话把悬念抛出去')
            if cues[0].get('kind') not in ('image', 'clip'): Wn.append('镜01 第一个 cue 不是图：开场第一帧要是猫（画面事件），不是字卡')
    if shots:
        if text_only / len(shots) > 0.3: Wn.append(f'没有图的镜头占 {text_only}/{len(shots)}：超过三成就像翻 PPT')
        if hl_shots > max(4, sections + 1): Wn.append(f'红圈（highlight）用了 {hl_shots} 次：每一段只圈一个最重要的地方（这一集约 {sections + 1} 处），其余的重点交给音效和重音（accent）')
        if hl_say / len(shots) > 0.4: Wn.append(f'{hl_say}/{len(shots)} 镜的口播有【】高亮：字幕到处是黄字就等于没有重点，只留每段的关键词')
        if len(moods) < 3: Wn.append(f'全片只有 {len(moods)} 种情绪（{"、".join(moods)}）：没有起伏。按「悬疑开场 → 轻松故事 → 紧张实验 → 揭晓 → 反转/温暖收尾」排一条情绪线')
        if n_accent == 0: Wn.append('全片没有重音（accent）：揭晓数字、反转的那一下要砸出来（音效＋白闪＋震屏，可配大字）')
        elif n_accent > 5: Wn.append(f'重音用了 {n_accent} 次：重音多了就不重了，留 2–4 个最要紧的')
        last = shots[-1].get('cues') or []
        if last and all(q.get('kind') in ('title', 'point') for q in last): Wn.append('最后一镜只有字卡：结尾落在猫的画面上（字可以作为标签贴在图上）')
    if total > 125: E.append(f'全片约 {total:.0f}s，超过 120 秒：删掉重复的旁白或次要的情节，不要硬塞')
    elif total > 120: Wn.append(f'全片约 {total:.0f}s，略超 120 秒：再精简一两句')
    elif total and total < 45: Wn.append(f'全片约 {total:.0f}s：太短观众可能看不明白，按「讲透」的标准补实验细节或原因（目标 60–120 秒）')
    return E, Wn, total

# ---------------------------------------------------------------- 组 spec
def build_spec(ep, s, i, dur, clock, base, prev_title, section):
    say = s['say']; sp = plain(say)
    cues, cur_img = [], None
    raw = [q for q in s['cues'] if q['kind'] not in ('accent', 'sfx')]   # 重音和音效不是画面元素，交给张力层和音频
    n = len(raw)
    for j, q in enumerate(raw):
        k = q['kind']
        if 'at' in q: at = float(q['at'])
        elif q.get('on'):
            at = clock(sp.find(q['on'])) - (0.15 if k in ('image', 'clip') else 0.0)
        else:
            at = 0.0 if j == 0 else dur * j / n
        at = round(max(0.0, min(at, dur - 0.5)), 3)
        c = {'at': at, 'kind': k}
        if k in ('image', 'clip'):
            cur_img = (base / q['image']).resolve(); c['image'] = str(cur_img)
            if q.get('text'): c['text'] = plain(q['text'])
            data = {kk: q[kk] for kk in ('halftone', 'fit', 'focus', 'aspect') if kk in q}
            # Vox：照片一律灰度网点（证据卡是 make_card 生成的纸件，旁边有坐标 json，保持原样）；个别照片要原色写 "halftone": false
            if 'halftone' not in data and not cur_img.with_suffix('.json').exists(): data['halftone'] = True
            if data: c['data'] = data
        elif k in ('title', 'point'):
            c['text'] = plain(q['text'])
        elif k == 'highlight':
            if 'mark' in q:
                rect = json.loads(cur_img.with_suffix('.json').read_text())['marks'][int(q['mark'])]['rect']
            else:
                rect = q.get('rect') or q['data']['rect']
            c['data'] = {'rect': rect, 'marker': q.get('marker', 'mark' in q)}   # 证据卡上的字用荧光笔；照片上默认只画红圈（荧光黄盖在猫脸上很难看）
        cues.append(c)
    # 顶部标题：title 是段落标题，一直保持到下一个 title；title_once 只管这一镜（比如揭晓数字）
    title = s.get('title_once') or section or ep.get('title', '')
    # 字幕：按口播断句，时间跟着配音走
    subs = []
    chunks = sub_chunks(say)
    for ci, (body, a, b) in enumerate(chunks):
        t0 = clock(a) if ci else 0.0
        t1 = clock(chunks[ci + 1][1]) if ci + 1 < len(chunks) else dur
        txt = join_segs(body)
        if s.get('who') and ci == 0: txt = f'【{s["who"]}】：' + txt   # 角色台词：字幕前面标出是谁在说
        subs.append({'from': round(t0, 3), 'to': round(max(t1, t0 + 0.3), 3), 'text': txt})
    theme = ep.get('theme', 'vox')
    spec = {'grammar': 'y2_vox', 'duration': round(dur, 3), 'fps': FPS, 'width': W, 'height': H, 'theme': theme,
            'safe': {'top': SAFE_TOP, 'bottom': SAFE_BOTTOM, 'fill': ep.get('band', PALETTE_INK.get(theme, '#1B1A17'))},
            'finish': ep.get('finish', 'soft'),
            'overlay': {'title': title, 'titleIn': title != prev_title, 'subs': subs},   # 不放章节标签：片子里只留钩子标题
            'cues': cues}
    if s.get('camera') == 'snap': spec['data'] = {'camera': 'snap'}
    spec['fx'] = shot_fx(s, sp, dur, clock)
    return spec, subs, title


def cue_time(q, sp, dur, clock):
    if 'at' in q: return max(0.0, min(float(q['at']), dur - 0.2))
    if q.get('on'): return max(0.0, min(clock(sp.find(q['on'])), dur - 0.2))
    return 0.0


def shot_fx(s, sp, dur, clock):
    """情绪 → 压暗和推近；重音 → 白闪、震屏、冲一下、大字砸入、红色脉冲、黑场；反转 → 开头故障撕裂。"""
    m = MOODS[s['_mood']]; ev = []
    if s['_mood'] == '反转' and s.get('_mood_changed'): ev.append({'t': 0.0, 'type': 'glitch', 'dur': 0.3})
    for q in s['cues']:
        if q['kind'] != 'accent': continue
        t = cue_time(q, sp, dur, clock)
        if q.get('blackout'): ev.append({'t': max(0, t - 0.35), 'type': 'blackout', 'dur': 0.35})
        if q.get('flash', True): ev.append({'t': t, 'type': 'flash', 'dur': 0.18})
        if q.get('shake', True): ev.append({'t': t, 'type': 'shake', 'dur': 0.35, 'amp': q.get('amp', 16)})
        if q.get('slam'): ev.append({'t': t, 'type': 'slam', 'text': q['slam'], 'sub': q.get('sub', ''), 'dur': 99})
        elif q.get('punch', True): ev.append({'t': t, 'type': 'punch', 'dur': 0.35, 'amp': 0.05})
        if q.get('pulse'): ev.append({'t': t, 'type': 'pulse', 'dur': 0.8})
    return {'vignette': s.get('vignette', m['vignette']), 'creep': s.get('creep', m['creep']), 'events': ev}


def shot_sfx(s, i, sp, dur, clock, t0):
    """这一镜的音效（绝对时间）和配乐的「抽空」窗口。显式的 sfx cue ＋ 自动规则。"""
    out, drops = [], []
    mood = s['_mood']
    if i == 1 and mood in ('悬疑', '紧张'): out.append({'t': t0 + 0.02, 'name': 'boom', 'gain': 0.8})
    if i > 1 and s.get('title'): out.append({'t': t0 - 0.12, 'name': 'whoosh', 'gain': 0.55})      # 换段落：嗖
    if s.get('who') and mood not in ('悬疑', '紧张'): out.append({'t': t0 + 0.02, 'name': 'pop', 'gain': 0.45})
    if mood == '反转' and s.get('_mood_changed'): out.append({'t': t0, 'name': 'scratch', 'gain': 0.7})
    for q in s['cues']:
        t = t0 + cue_time(q, sp, dur, clock)
        if q['kind'] == 'sfx': out.append({'t': t, 'name': q['name'], 'gain': q.get('gain', 0.8), **({'dur': q['dur']} if q.get('dur') else {})})
        elif q['kind'] == 'highlight': out.append({'t': t + 0.15, 'name': 'ding', 'gain': 0.28})
        elif q['kind'] == 'accent':
            out.append({'t': t, 'name': q.get('sfx', 'hit'), 'gain': q.get('gain', 1.0)})
            if q.get('drop', mood == '揭晓'):                       # 停—悬—砸：先把音乐抽空，riser 蓄力，再砸
                lead = q.get('lead', 0.9)
                drops.append({'t': t, 'dur': lead}); out.append({'t': t, 'name': 'riser', 'dur': lead, 'gain': 0.6})
    return out, drops


def video_ok(f, dur=None):
    """完整的 mp4（有 moov、能读出时长、时长对得上）才算渲好：中断留下的半截文件不能当缓存用。"""
    try:
        d = probe_dur(f)
    except Exception:
        return False
    return dur is None or abs(d - dur) < 0.1


def render_shot(spec_f, out, dur):
    part = Path(out).with_name(Path(out).stem + '.part.mp4')   # 先写临时文件，验过再改名：中途被打断不会留下「看起来渲好了」的坏文件
    part.unlink(missing_ok=True)
    cmd = ['uv', 'run', '--quiet', '--with', 'playwright', 'python', str(ENGINE / 'render.py'), '--spec', str(spec_f), '--out', str(part), '--crf', '16']
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode or not part.exists() or not video_ok(part, dur):
        part.unlink(missing_ok=True)
        raise RuntimeError(f'{spec_f.name} 渲染失败：\n{r.stdout[-1500:]}\n{r.stderr[-1500:]}')
    part.replace(out)
    return out


def srt_time(t):
    ms = int(round(t * 1000)); return f'{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('plan')
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--voice', default=None, help='旁白音色，默认取分镜里的 voice，再取角色库 _旁白 的 voice，再默认 zh-CN-YunxiNeural')
    ap.add_argument('--no-voice', action='store_true')
    ap.add_argument('--tts', choices=['auto', 'seed', 'edge'], default='auto', help='配音引擎：auto＝有豆包语音 Key 和声音样本就用 seed，否则 edge')
    ap.add_argument('--rate', default=None, help='语速，默认 +20%%（约 5.5 字/秒）')
    ap.add_argument('--bgm', help='用自己的配乐文件替换合成的配乐（整片循环）')
    ap.add_argument('--bgm-vol', type=float, default=1.0, help='配乐音量倍数（默认 1.0）')
    ap.add_argument('--no-bgm', action='store_true', help='不加配乐（打算在抖音里用平台音乐时）')
    ap.add_argument('--no-sfx', action='store_true', help='不加音效')
    ap.add_argument('--jobs', type=int, default=1, help='同时渲几镜；机器配置低就用 1')
    ap.add_argument('--only', help='只重渲这些镜（逐号，如 3,4），其余用缓存')
    a = ap.parse_args()
    sys.stdout.reconfigure(line_buffering=True)               # 后台跑、输出进日志时也能逐行看到进度
    plan = Path(a.plan).resolve(); base = plan.parent
    ep = json.loads(plan.read_text())
    shots = ep.get('shots') or []

    E, Wn, est = check(ep, base, soft_dur=not a.no_voice)
    for w in Wn: print('🟡', w)
    for e in E: print('🔴', e)
    if E: sys.exit(f'\n有 {len(E)} 条红灯，先改分镜.json。')
    print(f'✅ 检查通过：{len(shots)} 镜，估计 {est:.0f} 秒')
    if a.check: return

    build, out = base / 'build', base / 'output'
    for d in (build / 'tts', build / 'specs', build / 'shots', build / 'audio', out): d.mkdir(parents=True, exist_ok=True)
    cast, cast_dir = find_cast(base)
    voice = None if a.no_voice else (a.voice or ep.get('voice') or (cast.get('_旁白') or {}).get('voice') or 'zh-CN-YunxiNeural')
    voice_of = lambda s: voice if not (voice and s.get('who')) else ((cast.get(s['who']) or {}).get('voice') or voice)   # 角色台词用角色自己的声音
    used_voices = {}
    rate = a.rate or ep.get('rate', '+20%')
    base_rate = int(re.sub(r'[^0-9+-]', '', rate) or 0)
    speaker = lambda s: s['who'] if s.get('who') in cast else '_旁白'
    engine = 'edge' if voice else None
    if voice and a.tts != 'edge':
        need = sorted({speaker(s) for s in shots})
        missing = [w.lstrip('_') for w in need if not (cast_dir and seed_voice.sample_path(cast_dir, w).exists())]
        why = '没有豆包语音的 API Key' if not seed_voice.api_key() else (f'{"、".join(missing)} 还没有声音样本（先跑 seed_voice.py design）' if missing else '')
        if not why: engine = 'seed'
        elif a.tts == 'seed': sys.exit(f'🔴 不能用豆包配音：{why}')
        else: print(f'🟡 配音用 edge-tts：{why}')
    prev = None                                              # 情绪：没写就沿用上一镜
    for s in shots:
        s['_mood'] = s.get('mood') or (prev or ep.get('mood', '平叙')); s['_mood_changed'] = s['_mood'] != prev; prev = s['_mood']

    # 1 配音 → 每镜时长
    seed_res = {}
    if engine == 'seed':
        def seed_job(s, extra=0):
            who, mm = speaker(s), MOODS[s['_mood']]
            style = ((cast.get(who) or {}).get('seed') or {}).get('style', '')
            tone = s.get('tone') or (mm['tone'] if who == '_旁白' else '，'.join(x for x in (style, mm['emo'] and f'这一句{mm["emo"]}') if x))
            r = base_rate + mm['rate'] // 2 + s.get('rate', 0) + extra
            return who, seed_voice.say(plain(s['say']), seed_voice.sample_path(cast_dir, who), tone, build / 'tts', r), r
        print(f'豆包配音 {len(shots)} 句（同一句有缓存；新句子每句约半分钟到一分钟，3 句一起配）…')
        try:
            with cf.ThreadPoolExecutor(3) as ex:             # 等的是网络，不占本机 CPU；豆包默认允许 5 并发
                futs = {i: ex.submit(seed_job, s) for i, s in enumerate(shots, 1)}
                seed_res = {i: f.result() for i, f in futs.items()}
            for i, s in enumerate(shots, 1):                 # 一句超过 8 秒：自动加快语速重配一次（只多花这一句的钱）
                _, (_, _, ad, _), r = seed_res[i]; room = 7.9 - s.get('pause', 0.15)
                if ad > room:
                    nr = min(60, math.ceil(((1 + r / 100) * ad / room - 1) * 100) + 3)
                    print(f'🟡 镜{i:02d} 配音 {ad:.1f}s 超过 8 秒：自动加快（speech_rate {r:+d} → {nr:+d}）重配；还超就得拆镜')
                    seed_res[i] = seed_job(s, nr - r)
        except seed_voice.SeedError as e:
            sys.exit(f'🔴 豆包配音失败：{e}\n可以加 --tts edge 先用 edge-tts 出片。')
    durs, clocks, mp3s = [], [], []
    for i, s in enumerate(shots, 1):
        sp = plain(s['say']); pause = s.get('pause', 0.15)
        if engine == 'seed':
            who, (mp3, words, ad, heard), _ = seed_res[i]
            if heard: print(f'🟡 镜{i:02d} 念出来和稿子不一样：「{heard}」（改一下 say 的写法或加 tone 重跑；字幕仍按稿子）')
            used_voices[who.lstrip('_')] = '豆包音频生成（设计音色）'
            d = max(1.6, ad + pause); clocks.append(char_clock(sp, words, ad)); mp3s.append(mp3)
        elif voice:
            v = voice_of(s); used_voices[s.get('who') or '旁白'] = v
            mm = MOODS[s['_mood']]
            mp3, words, ad = tts(sp, v, f"{base_rate + mm['rate'] + s.get('rate', 0):+d}%", build / 'tts', f"{mm['pitch'] + s.get('pitch', 0):+d}Hz")
            d = max(1.6, ad + pause); clocks.append(char_clock(sp, words, ad)); mp3s.append(mp3)
        else:
            ad = len(sp) / CPS; d = max(1.6, ad + pause); clocks.append(char_clock(sp, [], ad)); mp3s.append(None)
        durs.append(round(d * FPS) / FPS)
        print(f'镜{i:02d}  {durs[-1]:.2f}s  [{s["_mood"]}] {(s["who"] + "：") if s.get("who") else ""}{sp[:24]}')
    E2, _, total = check(ep, base, durs)
    if E2:
        for e in E2: print('🔴', e)
        sys.exit('按真实配音时长检查有红灯（多半是某镜超过 8 秒），拆镜后重跑。')

    # 2 spec + 渲染（按内容哈希缓存）
    only = {int(x) for x in a.only.split(',')} if a.only else None
    jobs, prev_title, all_subs, t_acc, timeline, section = [], None, [], 0.0, [], None
    sfx_events, drops = [], []
    for i, s in enumerate(shots, 1):
        if s.get('title'): section = s['title']
        spec, subs, prev_title = build_spec(ep, s, i, durs[i - 1], clocks[i - 1], base, prev_title, section)
        key = sha(spec, [Path(q['image']).stat().st_mtime for q in spec['cues'] if q.get('image')], (ENGINE / 'clips' / 'y2_vox.js').stat().st_mtime, (ENGINE / 'lib' / 'douyin.js').stat().st_mtime, (ENGINE / 'lib' / 'fx.js').stat().st_mtime)
        spec_f = build / 'specs' / f'镜{i:02d}.json'; spec_f.write_text(json.dumps(spec, ensure_ascii=False, indent=1))
        mp4 = build / 'shots' / f'镜{i:02d}_{key}.mp4'
        for old in (build / 'shots').glob(f'镜{i:02d}_*.mp4'):
            if old != mp4 or not video_ok(old): old.unlink()
        if not video_ok(mp4, durs[i - 1]) or (only and i in only): jobs.append((spec_f, mp4, durs[i - 1]))
        timeline.append({'shot': i, 'start': round(t_acc, 3), 'dur': durs[i - 1], 'mp4': str(mp4), 'mood': s['_mood']})
        ev, dr = shot_sfx(s, i, plain(s['say']), durs[i - 1], clocks[i - 1], t_acc); sfx_events += ev; drops += dr
        all_subs += [{**x, 'from': x['from'] + t_acc, 'to': x['to'] + t_acc} for x in subs]
        t_acc += durs[i - 1]
    print(f'渲染 {len(jobs)} 镜（其余 {len(shots) - len(jobs)} 镜用缓存）…')
    with cf.ThreadPoolExecutor(a.jobs) as ex:
        futs = {ex.submit(render_shot, sf, mp, d): sf for sf, mp, d in jobs}
        for f in cf.as_completed(futs):
            f.result(); print('  ✓', futs[f].stem)

    # 3 拼画面
    lst = build / '镜头列表.txt'
    lst.write_text(''.join(f"file '{t['mp4']}'\n" for t in timeline))
    video = build / '画面.mp4'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(lst), '-r', str(FPS), '-c:v', 'libx264', '-crf', '17', '-preset', 'medium',
                    '-pix_fmt', 'yuv420p', '-an', str(video)], check=True)
    final = out / '成片.mp4'
    # 4 拼声音：配音 ＋ 配乐（人声下自动避让）＋ 音效，整片对齐 -14 LUFS
    parts = []
    for i, (mp3, d) in enumerate(zip(mp3s, durs), 1):
        w = build / 'audio' / f'镜{i:02d}.wav'
        src = ['-i', str(mp3)] if mp3 else ['-f', 'lavfi', '-i', 'anullsrc=r=48000:cl=mono']
        subprocess.run(['ffmpeg', '-y', '-v', 'error', *src, '-af', 'apad', '-t', f'{d:.3f}', '-ar', '48000', '-ac', '1', str(w)], check=True)
        parts.append(w)
    (build / '音频列表.txt').write_text(''.join(f"file '{p}'\n" for p in parts))
    voice_wav = build / '口播.wav'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-f', 'concat', '-safe', '0', '-i', str(build / '音频列表.txt'), '-c', 'copy', str(voice_wav)], check=True)
    beds = []                                                # 相邻同情绪的镜头合成一段配乐
    for t in timeline:
        if beds and beds[-1]['mood'] == t['mood']: beds[-1]['end'] = t['start'] + t['dur']
        else: beds.append({'start': t['start'], 'end': t['start'] + t['dur'], 'mood': t['mood']})
    aplan = {'total': total, 'beds': beds, 'drops': drops, 'sfx': [] if a.no_sfx else sfx_events}
    (build / '音频计划.json').write_text(json.dumps(aplan, ensure_ascii=False, indent=1))
    r = subprocess.run(['uv', 'run', '--quiet', '--with', 'numpy', '--with', 'scipy', '--with', 'soundfile', 'python', str(SKILL / 'scripts' / 'audio_fx.py'),
                        '--plan', str(build / '音频计划.json'), '--out', str(build / 'audio')], capture_output=True, text=True)
    if r.returncode: raise SystemExit('配乐/音效合成失败：\n' + r.stderr[-1500:])
    bgm_src = ['-stream_loop', '-1', '-i', a.bgm] if a.bgm else ['-i', str(build / 'audio' / 'bgm.wav')]
    bv = 0 if a.no_bgm else a.bgm_vol * (0.35 if a.bgm else 1.0)
    af = 'aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=stereo'   # 写明采样格式，ffmpeg 4.x 的 sidechaincompress 才选得出格式
    fc = (f'[1:a]{af},asplit=2[vo][key];'
          f'[2:a]{af},volume={bv}[bg0];'
          f'[bg0][key]sidechaincompress=threshold=0.025:ratio=6:attack=15:release=400,{af}[bg];'
          f'[3:a]{af}[fx];'
          f'[vo][bg][fx]amix=inputs=3:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11[a]')
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(video), '-i', str(voice_wav), *bgm_src, '-i', str(build / 'audio' / 'sfx.wav'),
                    '-filter_complex', fc, '-map', '0:v', '-map', '[a]', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
                    '-t', f'{total:.3f}', '-movflags', '+faststart', str(final)], check=True)

    # 5 字幕、口播稿、抽帧
    (out / '字幕.srt').write_text(''.join(f'{k}\n{srt_time(s["from"])} --> {srt_time(s["to"])}\n{plain(s["text"])}\n\n' for k, s in enumerate(all_subs, 1)))
    (out / '口播稿.txt').write_text('\n'.join(f'[{t["start"]:5.1f}s] {(s["who"] if s.get("who") else "旁白")}：{plain(s["say"])}' for t, s in zip(timeline, shots)) + '\n')
    stills = []
    for t in timeline:
        f = build / f'抽帧_{t["shot"]:02d}.png'
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', f'{t["start"] + t["dur"] * 0.6:.2f}', '-i', str(final), '-frames:v', '1', '-vf', 'scale=270:-1', str(f)], check=True)
        stills.append(f)
    if len(stills) == 1:
        shutil.copy(stills[0], out / '抽帧.jpg')
    else:
        cols = min(6, len(stills))
        inputs = sum((['-i', str(p)] for p in stills), [])
        layout = '|'.join(f'{(k % cols) * 270}_{(k // cols) * 480}' for k in range(len(stills)))
        fc = ''.join(f'[{k}]' for k in range(len(stills))) + f'xstack=inputs={len(stills)}:layout={layout}:fill=black'
        subprocess.run(['ffmpeg', '-y', '-v', 'error', *inputs, '-filter_complex', fc, '-frames:v', '1', str(out / '抽帧.jpg')], check=True)
    (build / 'timeline.json').write_text(json.dumps(timeline, ensure_ascii=False, indent=1))

    # 6 封面
    if ep.get('cover'):
        sys.path.insert(0, str(SKILL / 'scripts')); import make_card
        cv = {'type': 'cover', **ep['cover'], 'out': str((out / '封面').resolve())}
        make_card.render([cv], base, ep.get('theme', 'vox'))
        (out / '封面.json').unlink(missing_ok=True)

    # 7 发布文案（标题、简介、话题、置顶评论由分镜里的 publish 提供；署名、出处由脚本补）
    pub = ep.get('publish') or {}
    used = {(base / q['image']).resolve() for s in shots for q in s['cues'] if q.get('image')}
    if ep.get('cover', {}).get('image'): used.add((base / ep['cover']['image']).resolve())
    for f in list(used):   # 卡片（剧照、聊天头像、动态配图）里用到的照片，署名要追到原图
        sc = f.with_suffix('.json')
        if sc.exists():
            try: used |= {Path(x) for x in json.loads(sc.read_text()).get('sources', [])}
            except Exception: pass
    cred_lines = []
    for cj in {p.parent / 'credits.json' for p in used}:
        if cj.exists():
            for name, c in json.loads(cj.read_text()).items():
                if (cj.parent / name).resolve() in used and not re.match(r'(CC0|Public domain|PD)', c['license'], re.I):
                    cred_lines.append(f'- {c["author"]}，{c["license"]}，{c.get("site", "Wikimedia Commons")}（{c["page"]}）')
    md = [f'# 发布文案 · {ep.get("episode", plan.parent.name)}', '', f'时长 {total:.1f} 秒 · {len(shots)} 镜 · 配音 {("豆包音频生成 seed-audio-1.0" if engine == "seed" else voice) or "无（需后配）"}', '']
    if pub.get('titles'): md += ['## 标题（三选一）', *[f'{k}. {t}' for k, t in enumerate(pub['titles'], 1)], '']
    disclaimer = ep.get('disclaimer', '本系列猫咪均为拟人演绎，故事纯属虚构；心理学实验和数据来自真实的人类研究，出处见下。')
    if pub.get('desc') or disclaimer: md += ['## 简介', *([pub['desc']] if pub.get('desc') else []), disclaimer, '']
    if pub.get('tags'): md += ['## 话题', ' '.join(t if t.startswith('#') else '#' + t for t in pub['tags']), '']
    if pub.get('pinned'): md += ['## 置顶评论', pub['pinned'], '']
    md += ['## 出处（可放简介末尾或评论区）', *[f'- {x}' for x in ep.get('sources', [])], '']
    if cred_lines: md += ['## 图片署名（CC BY / BY-SA 必须署名，放简介或评论区）', *sorted(set(cred_lines)), '']
    md += ['## 配乐与音效', '代码合成的原创配乐和音效（' + '、'.join(dict.fromkeys(b['mood'] for b in beds)) + '），没有版权问题。想用抖音热门音乐：用 --no-bgm 重新导出，再在抖音里加。', '']
    if voice:
        who_voice = '、'.join(used_voices) + '：豆包音频生成 seed-audio-1.0 的设计音色' if engine == 'seed' else '、'.join(f'{k}：{v}' for k, v in used_voices.items()) + '（edge-tts）'
        md += ['## 配音', who_voice + '，AI 合成。抖音发布时在「作品声明」里勾选「内容由AI生成」。', '']
    (out / '发布文案.md').write_text('\n'.join(md))
    print(f'\n🎬 成片 -> {final}  （{total:.1f}s）\n   字幕/口播稿/封面/发布文案/抽帧 -> {out}/')


if __name__ == '__main__':
    main()
