#!/usr/bin/env python3
"""LibTV Seed Audio 1.0 配音（2026-11-07 用户指定：配音一律用 LibTV 里的 Seed Audio）。

为什么要单独一个脚本：LibTV 只能通过 MCP 调（create_node），出片脚本 build_pixel 调不了。所以分三步：
  1. plan：按 film.py 的 LINES，给每句拼好 Seed Audio 提示词（参考音频 = 角色的声音样本节点），写进 build/tts/配音单.json，
     列出还没配的句子。
  2. 由 Claude 用 LibTV MCP 逐句生成：
       create_node(nodeType='audio', model='seed-audio-1.0', left=[样本节点], prompt=配音单里的 prompt,
                   params=配音单里的 params, run=true, idempotencyKey=配音单里的 idem)
     等生成完，用 read_node 拿音频 url。
  3. fetch：下载音频，用 whisper 核对字（按拼音比，同音字不算错）、量声纹相似度、按真实声音裁掉头尾静音和长停顿，
     写进缓存 build/tts/libtv_<key>.*。出问题的句子会标出来，重新生成那一句。
film.py 里写 VOICE = 'libtv'，build_pixel 就只读这个缓存；缺哪句会报出来，不会悄悄出无声片。

提示词写法是用户 2026-11-07 听过三版后选的 V1：「完全复刻样本：同一个嗓音、<角色特点，音高写在最前>；不要改变音调，不要播音腔」，
不额外降调。语气写在后面，并要求「嗓音和音高还是样本里那样」（情绪一上来音调容易变高）。每个角色的样本节点和特点写在
角色.json 的 libtv_voice（node / clone / pron）。

  python3 libtv_voice.py plan   <集目录>
  python3 libtv_voice.py fetch  <集目录> <句id>=<音频url> [<句id>=<音频url> ...]
  python3 libtv_voice.py status <集目录>
  python3 libtv_voice.py direct <集目录> [<句id> ...]   # 只在用户明确要求「豆包直连」时用：同模型、同样本、同提示词直连豆包语音接口（用户规定配音走 LibTV）

fetch 需要：uv run --with numpy --with faster-whisper --with opencc-python-reimplemented --with pypinyin [--with sherpa-onnx] python …
（sherpa-onnx 用来量声纹，没有就跳过这一项）
"""
import ast, hashlib, json, re, subprocess, sys, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import seed_voice as SV
from cards_story import find_cast

MODEL = 'seed-audio-1.0'
DRY = SV.DRY
SPK_MIN = 0.70                                  # 声纹相似度低于它就标黄（同一个人一般 0.75 以上，不同角色 0.07–0.44）
SPK_MODEL = Path.home() / '.cache' / 'cat-social-psych' / 'eres2net_zh.onnx'
SPK_URL = ('https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/'
           '3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx')


# ---------------------------------------------------------------- 读 film.py（不执行它：只取 LINES 和几项设置）
def film_spec(ep):
    src = (Path(ep) / 'film.py').read_text()
    tree = ast.parse(src); out = {'VOICE_SPEED': 1.0}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in ('LINES', 'VOICE_SPEED', 'VOICE'):
                out[name] = eval(compile(ast.Expression(node.value), 'film.py', 'eval'), {'dict': dict, '__builtins__': {}})
    if 'LINES' not in out: sys.exit('film.py 里没有 LINES')
    return out


def plain(text):
    return re.sub(r'[【】]', '', text)


def prompt_for(text, tone, lv):
    """V1 写法（用户选定）。lv = 角色.json 里的 libtv_voice。"""
    p = (f'{DRY}完全复刻 {{{{Node {lv["node"]}}}}} 里这个人的声音：同一个嗓音、{lv["clone"]}，'
         f'就像{lv.get("pron", "他")}平时随口说话一样；不要改变音调，不要播音腔。')
    if tone: p += f'语气：{tone}；但嗓音和音高还是样本里那样。'
    return p + f'一字不差地念：“{text}”不要增加、删减或改动任何字。念完自然收住，留一秒安静。'


def entries(ep):
    """每句：id、谁、台词、语气、参考节点、提示词、参数、缓存 key。"""
    spec = film_spec(ep); cast, cast_dir = find_cast(ep)
    speed = float(spec.get('VOICE_SPEED', 1.0)); out = []
    for d in spec['LINES']:
        who = d.get('who', '旁白'); key = who if who in cast else '_旁白'
        lv = (cast.get(key) or {}).get('libtv_voice')
        if not lv: sys.exit(f'角色.json 里「{key}」没有 libtv_voice（node / clone / pron）：先把声音样本传到 LibTV，再登记')
        text, tone = plain(d['say']), d.get('tone', '')
        prompt = prompt_for(text, tone, lv)
        params = {'language': 'zh', 'format': 'mp3'}
        if abs(speed - 1.0) > 1e-6: params['speed'] = speed
        k = hashlib.sha1(json.dumps([MODEL, prompt, params], ensure_ascii=False).encode()).hexdigest()[:12]
        out.append(dict(id=d['id'], who=who, cast_key=key, text=text, tone=tone, node=lv['node'], prompt=prompt, params=params,
                        key=k, idem=f'vo-{k}', sample=str(SV.sample_path(cast_dir, key)) if cast_dir else None))
    return out


def files(build, k):
    t = Path(build) / 'tts'
    return t / f'libtv_{k}.raw.mp3', t / f'libtv_{k}.mp3', t / f'libtv_{k}.json'


def cached(ep, build, e):
    """缓存里有就返回 (mp3, 逐字时间, 时长, 念错时的实际文本或 None)；没有返回 None。裁剪规则升级（FIT_V 变了）就用原始音频重裁。"""
    raw, mp3, js = files(build, e['key'])
    if not (mp3.exists() and js.exists()): return None
    meta = json.loads(js.read_text())
    if meta.get('fit') != SV.FIT_V and raw.exists():
        meta['words'] = SV.fit(raw, mp3, meta['raw_words']); meta['fit'] = SV.FIT_V
        js.write_text(json.dumps(meta, ensure_ascii=False))
    return mp3, meta['words'], SV.probe(mp3), meta.get('heard')


def paced(build, e, mp3, words, tempo=1.0, max_gap=None):
    """按整集节奏再加工一份：句中停顿压到 max_gap 秒，整体用 atempo 加速 tempo 倍（只变快，不变调）。
    Seed Audio 平均每秒只念 3.5 个字、句中停顿多，第 27b 期原样拼起来 115 秒；film.py 写 VOICE_TEMPO / VOICE_MAX_GAP 调。"""
    if abs(tempo - 1.0) < 1e-3 and not max_gap: return mp3, words
    raw, _, js = files(build, e['key'])
    out = mp3.with_name(mp3.stem + f'.t{tempo:.2f}g{max_gap or 0:.2f}.mp3')
    meta = json.loads(js.read_text()); tag = f'{tempo:.2f}/{max_gap or 0:.2f}'
    if out.exists() and meta.get('paced', {}).get(tag): return out, meta['paced'][tag]
    src, ws = mp3, words
    if max_gap and raw.exists():                       # 停顿按更紧的上限，从原始音频重新裁一遍
        old = SV.MAX_GAP; SV.MAX_GAP = max_gap
        tmp = out.with_suffix('.gap.mp3')
        try: ws = SV.fit(raw, tmp, meta['raw_words'])
        finally: SV.MAX_GAP = old
        src = tmp
    if abs(tempo - 1.0) >= 1e-3:
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), '-af', f'atempo={tempo:.3f}', '-c:a', 'libmp3lame', '-q:a', '2', str(out)], check=True)
        ws = [{**w, 't': round(w['t'] / tempo, 3), 'd': round(w['d'] / tempo, 3)} for w in ws]
    else: Path(src).replace(out)
    if src != mp3 and Path(src).exists() and Path(src) != out: Path(src).unlink()
    meta.setdefault('paced', {})[tag] = ws; js.write_text(json.dumps(meta, ensure_ascii=False))
    return out, ws


def for_build(ep, build, tempo=1.0, max_gap=None, min_rate=None):
    """build_pixel 用：按 LINES 顺序返回 [(mp3, words, dur)]，以及缺的句子 id。
    min_rate（film.py 的 VOICE_MIN_RATE，每秒几个字）：整集加速后还慢于它的句子再单独加速，最多再快 1.25 倍。
    2026-11-08 第 29 期：大宝「懒洋洋」的语气每秒只念 2.9–3.5 个字，整集拖到 102 秒。"""
    out, missing = [], []
    for e in entries(ep):
        got = cached(ep, build, e)
        if not got: missing.append(e['id']); out.append((None, [], len(e['text']) / 4.5)); continue
        mp3, words, dur, heard = got
        raw_mp3, raw_words = mp3, words
        mp3, words = paced(build, e, raw_mp3, raw_words, tempo, max_gap); dur = SV.probe(mp3)
        n = len(re.sub(r'[^\w]', '', e['text']))
        if min_rate and n / dur < min_rate:
            t2 = round(tempo * min(1.25, min_rate * dur / n), 2)
            mp3, words = paced(build, e, raw_mp3, raw_words, t2, max_gap); dur = SV.probe(mp3)
        if heard: print(f'🟡 {e["id"]} 念出来和稿子不一样：「{heard}」')
        print(f'  {e["id"]:<8} {dur:5.2f}s {e["who"]}：{e["text"][:26]}')
        out.append((mp3, words, dur))
    return out, missing


# ---------------------------------------------------------------- 核字：按拼音比（whisper 常把「划走」听成「滑走」，不算念错）
CN_DIGIT = '零一二三四五六七八九'


def _num_cn(m):
    s = m.group(0); pct = s.endswith('%'); s = s.rstrip('%')
    if '.' in s or len(s) > 4: n = ''.join(CN_DIGIT[int(c)] if c.isdigit() else '点' for c in s)
    else:
        v, n, units = int(s), '', ['', '十', '百', '千']
        digits = list(map(int, str(v)))
        for i, dg in enumerate(digits):
            u = units[len(digits) - 1 - i]
            if dg: n += CN_DIGIT[dg] + u
            elif n and not n.endswith('零'): n += '零'
        n = n.rstrip('零') or '零'
        if n.startswith('一十'): n = n[1:]
    return ('百分之' if pct else '') + n


SAME = str.maketrans({'愈': '越', '似': '是', '两': '二', 'A': '诶', 'a': '诶', 'B': '比', 'b': '比', '必': '比', '币': '比'})          # whisper 常把「越……越」写成「愈……愈」：意思一样，按同一个字比


def say_key(s):
    from pypinyin import lazy_pinyin
    s = (s or '').translate(SAME)
    s = re.sub(r'\d+(?:\.\d+)?%?', _num_cn, s)
    s = re.sub(r'[^一-鿿]', '', s)
    return ''.join(lazy_pinyin(s))


_WH = None


def transcribe(path):
    """whisper：返回 (文本, 逐词时间 [{t,d,text}])。"""
    global _WH
    import numpy as np, opencc
    from faster_whisper import WhisperModel
    if _WH is None: _WH = (WhisperModel('small', device='cpu', compute_type='int8', cpu_threads=2), opencc.OpenCC('t2s'))
    m, cc = _WH
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-ac', '1', '-ar', '16000', '-f', 's16le', '-'])
    x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    segs, _ = m.transcribe(x, language='zh', word_timestamps=True, initial_prompt='以下是普通话的句子，有标点。')
    text, words = '', []
    for s in segs:
        text += s.text
        for w in s.words or []:
            t = cc.convert(w.word.strip())
            if t: words.append({'t': round(w.start, 3), 'd': round(max(0.02, w.end - w.start), 3), 'text': t})
    return cc.convert(text.strip()), words


def tail_extra(words, text):
    """念对了稿子、后面又多说了：返回该剪的位置（秒）；没多说或前面就念错了返回 None。"""
    ek = say_key(text); acc = ''
    for i, w in enumerate(words):
        acc += w['text']; k = say_key(acc)
        if len(k) >= len(ek):
            if k[:len(ek)] != ek or i == len(words) - 1: return None
            end = w['t'] + w['d']; nxt = words[i + 1]['t']
            return round(min(end + 0.25, (end + nxt) / 2 + 0.05), 3)
    return None


_SPK = None


def speaker_sim(a, b):
    """两段音频的声纹余弦相似度；没有 sherpa-onnx 就返回 None。"""
    global _SPK
    try:
        import numpy as np, sherpa_onnx
    except ImportError:
        return None
    if _SPK is None:
        if not SPK_MODEL.exists():
            SPK_MODEL.parent.mkdir(parents=True, exist_ok=True)
            print('  （第一次用：下载声纹模型 ~40MB）'); urllib.request.urlretrieve(SPK_URL, SPK_MODEL)
        _SPK = sherpa_onnx.SpeakerEmbeddingExtractor(sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=str(SPK_MODEL), num_threads=2))

    def emb(f):
        raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(f), '-ac', '1', '-ar', '16000', '-f', 's16le', '-'])
        x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
        s = _SPK.create_stream(); s.accept_waveform(16000, x); s.input_finished()
        v = np.array(_SPK.compute(s)); return v / np.linalg.norm(v)
    return round(float(emb(a) @ emb(b)), 3)


# ---------------------------------------------------------------- 命令
def plan_file(ep):
    return Path(ep) / 'build' / 'tts' / '配音单.json'


def cmd_plan(ep):
    ep = Path(ep).resolve(); build = ep / 'build'; (build / 'tts').mkdir(parents=True, exist_ok=True)
    es = entries(ep)
    for e in es: e['cached'] = files(build, e['key'])[1].exists()
    plan_file(ep).write_text(json.dumps(es, ensure_ascii=False, indent=1))
    todo = [e for e in es if not e['cached']]
    print(f'{len(es)} 句，已配 {len(es) - len(todo)} 句，还要生成 {len(todo)} 句 -> {plan_file(ep)}')
    for e in todo:
        print(f'\n[{e["id"]}] {e["who"]}  参考 {e["node"]}  idem={e["idem"]}  params={json.dumps(e["params"], ensure_ascii=False)}\n{e["prompt"]}')


def check_take(build, e, raw, src):
    """核一条刚生成的原始音频（raw）：whisper 核字、剪句尾多说的、查截断、量声纹，写进缓存。返回问题列表（空＝通过）。"""
    lid = e['id']; _, mp3, js = files(build, e['key'])
    got, words = transcribe(raw)
    cut_at = tail_extra(words, e['text'])
    if cut_at:                                     # 念完稿子又接着说了一截（参考样本里的话漏出来）：按逐字时间剪掉
        tmp = raw.with_suffix('.cut.mp3')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(raw), '-t', f'{cut_at:.3f}', '-c:a', 'libmp3lame', '-q:a', '2', str(tmp)], check=True)
        tmp.replace(raw); got, words = transcribe(raw)
        print(f'   ✂ {lid}：句尾多说的部分剪掉了（{cut_at:.2f}s 之后）')
    heard = None if say_key(got) == say_key(e['text']) else got
    cut = SV.truncated(raw)
    fitted = SV.fit(raw, mp3, words)
    sim = speaker_sim(e['sample'], raw) if e.get('sample') else None
    js.write_text(json.dumps({'words': fitted, 'raw_words': words, 'heard': heard, 'tone': e['tone'], 'fit': SV.FIT_V,
                              'raw_cut': cut, 'spk': sim, 'url': src, 'prompt': e['prompt']}, ensure_ascii=False))
    flags = (['念错：「' + heard + '」'] if heard else []) + (['最后一个字被截断'] if cut else []) + \
            ([f'声纹 {sim}（低于 {SPK_MIN}，不太像）'] if sim is not None and sim < SPK_MIN else [])
    print(f'{"🟡" if flags else "✅"} {lid:<8} {SV.probe(mp3):5.2f}s 声纹 {sim}  {e["who"]}：{e["text"][:24]}' + ('  ← ' + '；'.join(flags) if flags else ''))
    return flags


def cmd_fetch(ep, pairs):
    ep = Path(ep).resolve(); build = ep / 'build'
    if not plan_file(ep).exists(): cmd_plan(ep)
    es = {e['id']: e for e in json.loads(plan_file(ep).read_text())}
    bad = []
    for pair in pairs:
        lid, url = pair.split('=', 1)
        if lid not in es: sys.exit(f'配音单里没有 {lid}（film.py 改过就先重跑 plan）')
        e = es[lid]; raw = files(build, e['key'])[0]
        urllib.request.urlretrieve(url, raw)
        if check_take(build, e, raw, url): bad.append(lid)
    if bad: print(f'\n要重新生成：{", ".join(bad)}（create_node 换一个 idempotencyKey，例如在 idem 后面加 -2；生成后再 fetch）')


def cmd_direct(ep, ids):
    """只在用户明确要求时用（用户规定配音一律走 LibTV）：同一个模型（seed-audio-1.0）、同一份声音样本、同一套 V1 提示词，直接调豆包语音接口。
    样本作为参考音频（@音频1）上传，提示词里的 {{Node …}} 换成 @音频1。不带句 id：只生成还没配的句子；带句 id：重新生成这几句
    （旧的那一版留成 libtv_<key>.take<N>.mp3，听过再挑）。要 ~/.config/cat-social-psych/keys.env 里的 DOUBAO_SPEECH_API_KEY。"""
    ep = Path(ep).resolve(); build = ep / 'build'; (build / 'tts').mkdir(parents=True, exist_ok=True)
    es = entries(ep); plan_file(ep).write_text(json.dumps(es, ensure_ascii=False, indent=1))
    want = set(ids); unknown = want - {e['id'] for e in es}
    if unknown: sys.exit(f'film.py 里没有这些句子：{", ".join(sorted(unknown))}')
    bad = []
    for e in es:
        raw, mp3, js = files(build, e['key'])
        if want and e['id'] not in want: continue
        if not want and mp3.exists(): continue
        if raw.exists():                                # 重做：旧的一版留着
            n = 1
            while raw.with_name(f'libtv_{e["key"]}.take{n}.mp3').exists(): n += 1
            raw.replace(raw.with_name(f'libtv_{e["key"]}.take{n}.mp3'))
        prompt = re.sub(r'\{\{Node [^}]+\}\}', '@音频1', e['prompt'])
        try:
            audio, _, _ = SV.create(prompt, ref=e['sample'])
        except SV.SeedError as err:
            print(f'🔴 {e["id"]}：{err}'); bad.append(e['id']); continue
        raw.write_bytes(audio)
        if check_take(build, e, raw, 'doubao-direct'): bad.append(e['id'])
    if bad: print(f'\n要重新生成：{" ".join(bad)}（再跑一次 direct <集目录> {" ".join(bad)}）')


def cmd_status(ep):
    ep = Path(ep).resolve(); build = ep / 'build'
    for e in entries(ep):
        got = files(build, e['key'])[2]
        if got.exists():
            m = json.loads(got.read_text())
            print(f'✅ {e["id"]:<8} 声纹 {m.get("spk")}  ' + (f'念成「{m["heard"]}」' if m.get('heard') else ''))
        else: print(f'·  {e["id"]:<8} 还没配')


if __name__ == '__main__':
    if len(sys.argv) < 3 or sys.argv[1] not in ('plan', 'fetch', 'status', 'direct'): sys.exit(__doc__)
    cmd, ep = sys.argv[1], sys.argv[2]
    if cmd == 'plan': cmd_plan(ep)
    elif cmd == 'fetch': cmd_fetch(ep, sys.argv[3:])
    elif cmd == 'direct': cmd_direct(ep, sys.argv[3:])
    else: cmd_status(ep)
