#!/usr/bin/env python3
"""豆包音频生成（seed-audio-1.0）配音：给每个角色「设计」一个固定的声音，再用这个声音带着情绪念每一句。

做法：seed-audio 能按一句描述生成声音、按提示词带情绪说话，但每次纯文字生成，声音都会有点不一样。
所以先按 角色.json 里的 seed.desc 生成一段 15 秒左右的「声音样本」，存成 角色库/<角色>/声音样本.wav；
之后每一句都把样本当参考音频（@音频1）传进去，声音就固定了，情绪写在提示词里（跟分镜的 mood 走，或者单镜写 tone）。
用参考音频不需要买音色槽位。样本也可以换成自己录的 10–30 秒干声（只用自己或明确同意的人的声音）。

  API Key：豆包语音控制台 > API Key 管理 https://console.volcengine.com/speech/new/setting/apikeys
           （不是火山方舟 ark- 开头的 key），并在控制台开通「豆包音频生成模型1.0」。
           放环境变量 DOUBAO_SPEECH_API_KEY，或 ~/.config/cat-social-psych/keys.env 里写一行 DOUBAO_SPEECH_API_KEY=...
  计费：按生成的音频时长，约 1 元/分钟（以控制台为准）。同一句话按内容缓存，重跑不重复扣费。

  python seed_voice.py design <角色库/角色.json> [--who 大比,旁白] [--force]    # 生成声音样本，并拼一个 声音试听.mp3
  python seed_voice.py say <角色库/角色.json> --who 大比 --text 稳赢！ [--tone 得意地大声说] --out 试听.mp3
"""
import argparse, base64, hashlib, json, os, re, subprocess, sys, time, urllib.error, urllib.request, uuid, wave
from pathlib import Path

API = 'https://openspeech.bytedance.com/api/v3/tts/create'
MODEL = 'seed-audio-1.0'
DRY = '纯人声干声，只有这一个人在说话；没有背景音乐、没有音效、没有环境声。'
LINE_LUFS, SAMPLE_LUFS = -18, -20                            # 每句、样本统一到的响度
MAX_GAP = 0.65                                               # 句中停顿最长留多久（模型演悬疑时会停 1.5 秒以上，一镜就超 8 秒）
KEY_FILE = Path.home() / '.config' / 'cat-social-psych' / 'keys.env'


class SeedError(Exception):
    pass


def api_key():
    k = os.environ.get('DOUBAO_SPEECH_API_KEY', '').strip()
    if not k and KEY_FILE.exists():
        for line in KEY_FILE.read_text().splitlines():
            if line.startswith('DOUBAO_SPEECH_API_KEY='): k = line.split('=', 1)[1].strip()
    return k or None


def sample_path(cast_dir, who):
    """角色的声音样本：角色库/大比/声音样本.wav；旁白是 角色库/旁白/声音样本.wav。"""
    return Path(cast_dir) / who.lstrip('_') / '声音样本.wav'


def norm(s):
    return re.sub(r'[\W_]+', '', s or '')


def probe(f):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', str(f)]).decode().strip())


def lufs(f):
    """整段响度（LUFS）；太短或没声音时返回 None。"""
    r = subprocess.run(['ffmpeg', '-nostats', '-i', str(f), '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    m = re.findall(r'^\s+I:\s+(-?[\d.]+) LUFS', r, re.M)
    return float(m[-1]) if m and float(m[-1]) > -60 else None


def level(src, dst, target, extra=()):
    """把一段人声拉到统一响度（不同角色、不同情绪的句子音量差很多），顶部用限幅兜住。"""
    i = lufs(src); gain = 0 if i is None else max(-20, min(24, target - i))
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(src), '-af', f'volume={gain:.2f}dB,alimiter=limit=0.89:level=false', *extra, str(dst)], check=True)


def cap_gaps(src, dst, words, codec=()):
    """把句中超过 MAX_GAP 的停顿剪短到 MAX_GAP（剪掉停顿中间那段），逐词时间跟着前移。没有长停顿就原样复制。"""
    keep, removed, out, t0 = [], 0.0, [], 0.0
    for k, w in enumerate(words):
        if k:
            a = words[k - 1]['t'] + words[k - 1]['d']; gap = w['t'] - a
            if gap > MAX_GAP:
                keep.append((t0, a + MAX_GAP / 2)); t0 = w['t'] - MAX_GAP / 2; removed += gap - MAX_GAP
        out.append({**w, 't': round(w['t'] - removed, 3)})
    if not keep:
        if Path(src) != Path(dst): subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(src), *codec, str(dst)], check=True)
        return words
    keep.append((t0, None))
    fc = ''.join(f'[0]atrim=start={a:.3f}' + (f':end={b:.3f}' if b else '') + f',asetpts=PTS-STARTPTS[s{k}];' for k, (a, b) in enumerate(keep))
    fc += ''.join(f'[s{k}]' for k in range(len(keep))) + f'concat=n={len(keep)}:v=0:a=1[o]'
    tmp = Path(dst).with_suffix('.gap' + Path(dst).suffix)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(src), '-filter_complex', fc, '-map', '[o]', *codec, str(tmp)], check=True)
    tmp.replace(dst)
    return out


def gaps_ok(words):
    return all(b['t'] - (a['t'] + a['d']) <= MAX_GAP + 0.01 for a, b in zip(words, words[1:]))


# ---------------------------------------------------------------- 按真实声音裁剪、对齐
# 豆包返回的逐字时间常常不准：整体早 0.2–0.5 秒、数字（「100」）一个词占 1.7 秒、开头有 1 秒静音却标成 0 秒。
# 按这些时间裁音频会剪掉最后一个字、留下开头静音（字幕和张嘴先出来，声音后到）。
# 所以裁头尾、剪长停顿都看真实波形；逐字时间只用来分配每个字在真实发声区间里的位置。
FIT_V = 5                                                    # 缓存里 meta['fit'] 不等于它的句子会重新裁
HOP = 0.01                                                   # 包络 10 毫秒一格
HEAD, TAIL = 0.05, 0.16                                      # 声音前留 50 毫秒、后留 160 毫秒（字尾的余音）


def _np():
    try:
        import numpy
        return numpy
    except ImportError:
        sys.exit('seed_voice 需要 numpy：用 uv run --with numpy python seed_voice.py …（build_pixel.py 已经带上）')


def pcm(path, sr=48000):
    np = _np()
    raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(path), '-f', 's16le', '-ac', '1', '-ar', str(sr), '-'])
    return np.frombuffer(raw, np.int16).astype(np.float32) / 32768


def envelope(x, sr=48000):
    """10 毫秒一格的响度（dBFS）。"""
    np = _np(); n = int(sr * HOP); m = len(x) // n
    if m == 0: return np.full(1, -120.0)
    return 20 * np.log10(np.sqrt((x[:m * n].reshape(m, n) ** 2).mean(1)) + 1e-9)


def voiced(db, merge=0.08, min_len=0.04):
    """有声区间 [(起, 止) 秒]：阈值跟着这句的峰值走（峰值 −32 dB，最低 −55 dB），间隔小于 merge 的并成一段。"""
    np = _np()
    thr = max(-55.0, float(np.percentile(db, 99)) - 32)
    on = db > thr; runs, i = [], 0
    while i < len(on):
        if on[i]:
            j = i
            while j < len(on) and on[j]: j += 1
            runs.append([i * HOP, j * HOP]); i = j
        else: i += 1
    out = []
    for r in runs:
        if out and r[0] - out[-1][1] < merge: out[-1][1] = r[1]
        else: out.append(r)
    out = [r for r in out if r[1] - r[0] >= min_len]
    # 模型偶尔在开头或结尾多出一下爆音（不是字）：离正文 0.1 秒以上、短于 0.1 秒的头尾小段去掉
    while len(out) > 1 and out[-1][1] - out[-1][0] < 0.1 and out[-1][0] - out[-2][1] > 0.1: out.pop()
    while len(out) > 1 and out[0][1] - out[0][0] < 0.1 and out[1][0] - out[0][1] > 0.1: out.pop(0)
    return [tuple(r) for r in out]


def truncated(path):
    """句尾被截断：最后 30 毫秒还在出声（模型生成时偶尔把最后一个字截掉，旧版按时间戳裁剪也会剪掉）。"""
    np = _np(); x = pcm(path); db = envelope(x); runs = voiced(db)
    if len(db) < 10 or not runs or runs[-1][1] < len(db) * HOP - 0.03: return False   # 正文早就说完了（结尾的小爆音不算）
    tail = 10 * np.log10(np.mean(10 ** (db[-3:] / 10)))     # 最后 30 毫秒的平均响度
    return bool(tail > float(np.percentile(db, 99)) - 22)    # 比峰值低不到 22 dB：还在正常说话的音量上就断了（自然收尾会落到 −30 dB 以下）


def _syl(s):
    """估一个词念几个音节，用来在真实发声区间里分配时间。"""
    n = 0.0
    for ch in s:
        if '一' <= ch <= '鿿': n += 1
        elif ch.isdigit(): n += 0.9
        elif ch in '，。！？；：、': n += 0.6
        elif ch in '…—': n += 0.4
        elif ch.isalpha(): n += 0.5
    return n


def align(words, on, off):
    """把逐字时间对到真实发声区间 [on, off]：时间戳整体可信就平移缩放；有离谱的（一个词占太久、全挤在一起）就按音节平均分。"""
    if not words: return words
    w0 = words[0]['t']; we = words[-1]['t'] + words[-1]['d']
    bad = we - w0 < 0.25 or any(w['d'] > 0.5 * max(1, _syl(w['text'])) + 0.15 for w in words)
    if not bad:
        k = (off - on) / (we - w0)
        return [{**w, 't': round(on + (w['t'] - w0) * k, 3), 'd': round(w['d'] * k, 3)} for w in words]
    wt = [max(0.3, _syl(w['text'])) for w in words]; tot = sum(wt); t = on; out = []
    for w, x in zip(words, wt):
        d = (off - on) * x / tot; out.append({**w, 't': round(t, 3), 'd': round(d, 3)}); t += d
    return out


def fit(src, dst, words):
    """按真实声音：去掉开头结尾的静音（前留 HEAD、后留 TAIL），句中超过 MAX_GAP 的停顿剪到 MAX_GAP，逐字时间跟着对齐。
    src 可以就是 dst。返回对齐后的逐字时间。"""
    np = _np()
    x = pcm(src); db = envelope(x); runs = voiced(db); total = len(x) / 48000
    if not runs:
        if Path(src) != Path(dst): level(src, dst, LINE_LUFS, ['-c:a', 'libmp3lame', '-q:a', '2'])
        return words
    # 句尾多出来的一小段气声、杂音（短于 0.22 秒、离正文 0.35 秒以上），而且逐字时间显示字早就念完了：不算正文
    # （只看句尾：句首「看！」「对，」这种短字后面也常有停顿，不能删）
    if words and len(runs) > 1:
        we = words[-1]['t'] + words[-1]['d']
        r = runs[-1]
        if r[1] - r[0] < 0.22 and r[0] - runs[-2][1] > 0.35 and we + 0.3 < r[0]: runs = runs[:-1]
    on, off = runs[0][0], runs[-1][1]
    words = align(words, on, off)
    segs, a = [], max(0.0, on - HEAD)
    for (r0, r1), (n0, n1) in zip(runs, runs[1:]):
        if n0 - r1 > MAX_GAP: segs.append((a, r1 + MAX_GAP / 2)); a = n0 - MAX_GAP / 2
    segs.append((a, min(total, off + TAIL)))

    def remap(t):
        acc = 0.0
        for s0, s1 in segs:
            if t < s0: return acc
            if t <= s1: return acc + t - s0
            acc += s1 - s0
        return acc
    words = [{**w, 't': round(remap(w['t']), 3), 'd': round(max(0.0, remap(w['t'] + w['d']) - remap(w['t'])), 3)} for w in words]
    parts = []
    fade = int(0.008 * 48000)
    for k, (s0, s1) in enumerate(segs):
        y = x[int(s0 * 48000):int(s1 * 48000)].copy()
        if len(y) > 2 * fade:
            y[:fade] *= np.linspace(0, 1, fade); y[-fade:] *= np.linspace(1, 0, fade)
        if k == len(segs) - 1 and len(y) > 4800: y[-4800:] *= np.linspace(1, 0, 4800) ** 2   # 句尾 100 毫秒淡出，余音不硬断
        parts.append(y)
    y = np.concatenate(parts)
    tmp = Path(dst).with_suffix('.fit.wav')
    with wave.open(str(tmp), 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(48000); w.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())
    level(tmp, dst, LINE_LUFS, ['-c:a', 'libmp3lame', '-q:a', '2']); tmp.unlink()
    return words


def create(prompt, ref=None, fmt='mp3', speech_rate=0, subtitle=True, tries=3):
    """调一次接口：返回 (音频字节, 字幕 dict, 计费时长秒)。"""
    key = api_key()
    if not key: raise SeedError(f'没有豆包语音的 API Key：设环境变量 DOUBAO_SPEECH_API_KEY，或写进 {KEY_FILE}')
    body = {'model': MODEL, 'text_prompt': prompt,
            'audio_config': {'format': fmt, 'sample_rate': 48000, 'speech_rate': int(speech_rate), 'enable_subtitle': subtitle}}
    if ref: body['references'] = [{'audio_data': base64.b64encode(Path(ref).read_bytes()).decode()}]
    last = None
    for attempt in range(tries):
        req = urllib.request.Request(API, data=json.dumps(body, ensure_ascii=False).encode(),
                                     headers={'Content-Type': 'application/json', 'X-Api-Key': key, 'X-Api-Request-Id': str(uuid.uuid4())})
        try:
            with urllib.request.urlopen(req, timeout=300) as r: d = json.loads(r.read())
        except urllib.error.HTTPError as e:
            msg, logid = e.read()[:400].decode('utf-8', 'replace'), e.headers.get('X-Tt-Logid')
            if e.code in (401, 403):
                raise SeedError(f'鉴权失败（HTTP {e.code}）：{msg}\n要用豆包语音控制台的 API Key（不是火山方舟 ark- 开头的），并开通「豆包音频生成模型1.0」。logid={logid}')
            if e.code == 429 or e.code >= 500: last = f'HTTP {e.code} {msg}'; time.sleep(4 * (attempt + 1)); continue
            raise SeedError(f'HTTP {e.code}：{msg}（logid={logid}）')
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = e; time.sleep(4 * (attempt + 1)); continue
        audio = base64.b64decode(d['audio']) if d.get('audio') else None
        if not audio and d.get('url'): audio = urllib.request.urlopen(d['url'], timeout=120).read()
        if not audio: raise SeedError('接口没有返回音频：' + json.dumps({k: v for k, v in d.items() if k != 'audio'}, ensure_ascii=False)[:400])
        return audio, d.get('subtitle') or {}, d.get('original_duration') or d.get('duration') or 0
    raise SeedError(f'重试 {tries} 次仍失败（网络或服务繁忙）：{last}')


def words_of(sub):
    ws = sub.get('words') or [w for s in sub.get('sentences') or [] for w in s.get('words') or []]
    return [{'t': w['start_time'] / 1000, 'd': (w['end_time'] - w['start_time']) / 1000, 'text': w['text']} for w in ws if w.get('text', '').strip()]


def line_prompt(text, tone, strict=False, tail=False):
    return (f'{DRY}用 @音频1 里这个人一模一样的嗓音和口音说话。语气：{tone}。一字不差地念：“{text}”'
            + ('不要增加、删减或改动任何字。' if strict else '')
            + ('最后一个字要完整念完、自然收住，念完以后留一秒安静。' if tail else ''))


def say(text, sample, tone, cache, speech_rate=0):
    """念一句：返回 (mp3, 逐词时间 [{t,d,text}], 时长秒, 念错时的实际文本或 None)。按内容缓存。"""
    cache = Path(cache); cache.mkdir(parents=True, exist_ok=True)
    key = hashlib.sha1(json.dumps([MODEL, text, tone, speech_rate, hashlib.sha1(Path(sample).read_bytes()).hexdigest()], ensure_ascii=False).encode()).hexdigest()[:12]
    mp3, js, raw = cache / f'seed_{key}.mp3', cache / f'seed_{key}.json', cache / f'seed_{key}.raw.mp3'
    if mp3.exists() and js.exists():
        meta = json.loads(js.read_text())
        if meta.get('fit') == FIT_V: return mp3, meta['words'], probe(mp3), meta.get('heard')
        if raw.exists() and meta.get('raw_words') is not None:
            if not truncated(raw) or meta.get('raw_cut'): meta['words'] = fit(raw, mp3, meta['raw_words'])
            else: meta = None                                                      # 生成时就截断了最后一个字：重新生成
        elif not truncated(mp3): meta['words'] = fit(mp3, mp3, meta['words'])      # 旧缓存、声音完整：按真实声音重新裁、重新对齐
        else: meta = None                                                          # 旧缓存把最后一个字剪掉了：重新生成
        if meta:
            meta['fit'] = FIT_V; js.write_text(json.dumps(meta, ensure_ascii=False))
            return mp3, meta['words'], probe(mp3), meta.get('heard')
        print(f'  （「{text[:12]}」旧配音的最后一个字被截断了，重新生成）')
    heard = None
    tries = [(text, False), (text, True)]                     # 念错了（多字、少字、改字）就加重要求再来一次
    if re.search(r'[「」『』]', text): tries.append((re.sub(r'[「」『』]', '', text), True))   # 句中引号偶尔会让模型把引号里的词挪到句首：最后去掉引号再试
    tries.append((text, True))                                # 留一次机会给「最后一个字被截断」重来
    cut = False
    for said, strict in tries:
        audio, sub, _ = create(line_prompt(said, tone, strict, tail=cut), ref=sample, speech_rate=speech_rate)
        got = sub.get('text') or ''.join(w['text'] for w in words_of(sub))
        heard = None if (not got or norm(got) == norm(text)) else got
        raw.write_bytes(audio)                               # 原始音频留着：以后改裁剪规则不用重新花钱生成
        cut = truncated(raw)
        if not heard and not cut: break
        if cut and not heard: print(f'  （「{text[:12]}」生成的音频把最后一个字截断了，重来一次）')
    raw_words = words_of(sub)
    words = fit(raw, mp3, raw_words)
    js.write_text(json.dumps({'words': words, 'raw_words': raw_words, 'heard': heard, 'tone': tone, 'fit': FIT_V, 'raw_cut': cut}, ensure_ascii=False))
    return mp3, words, probe(mp3), heard


def design(cast_json, who=None, force=False):
    """按 角色.json 里每个角色的 seed（desc 声音描述、style 说话方式、sample_text 样本台词）生成声音样本。"""
    cast_json = Path(cast_json); cast = json.loads(cast_json.read_text()); root = cast_json.parent
    names = [k for k, v in cast.items() if isinstance(v, dict) and v.get('seed')]
    if who: names = [n for n in names if n in who or n.lstrip('_') in who]
    if not names: raise SeedError('角色.json 里没有写 seed 的角色（seed.desc / style / sample_text）')
    outs = []
    for n in names:
        sd, out = cast[n]['seed'], sample_path(root, n)
        if out.exists() and not force:
            print(f'  · {n.lstrip("_")}：已有 {out}（--force 重新设计）'); outs.append((n, out)); continue
        if out.exists(): out.replace(out.with_name('声音样本.旧.wav'))   # 重新设计前备份一份，不满意可以改回来
        prompt = f'{DRY}{sd["desc"]}。{sd.get("style", "")}。说：“{sd["sample_text"]}”'
        audio, _, dur = create(prompt, fmt='wav', subtitle=False)
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix('.raw.wav'); tmp.write_bytes(audio)
        mono = out.with_suffix('.mono.wav')
        subprocess.run(['ffmpeg', '-y', '-v', 'error', '-i', str(tmp), '-t', '28', '-ac', '1', '-ar', '24000', str(mono)], check=True)  # 参考音频上限 30 秒、10MB
        level(mono, out, SAMPLE_LUFS); mono.unlink()
        tmp.unlink(); print(f'  ✓ {n.lstrip("_")}：{probe(out):.1f}s -> {out}'); outs.append((n, out))
    demo = root / '声音试听.mp3'                              # 拼成一个文件，方便一口气听完
    inputs = sum((['-i', str(p)] for _, p in outs), [])
    fc = ''.join(f'[{k}]aformat=sample_rates=24000:channel_layouts=mono,apad=pad_dur=0.8[a{k}];' for k in range(len(outs))) + ''.join(f'[a{k}]' for k in range(len(outs))) + f'concat=n={len(outs)}:v=0:a=1[o]'
    subprocess.run(['ffmpeg', '-y', '-v', 'error', *inputs, '-filter_complex', fc, '-map', '[o]', '-c:a', 'libmp3lame', '-q:a', '2', str(demo)], check=True)
    print(f'试听（顺序：{"、".join(n.lstrip("_") for n, _ in outs)}）-> {demo}')
    return outs


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=['design', 'say'])
    ap.add_argument('cast', help='角色库/角色.json')
    ap.add_argument('--who', help='design：只做这些角色（逗号分隔）；say：用谁的声音')
    ap.add_argument('--force', action='store_true', help='已有样本也重新设计（会覆盖，旧样本先备份）')
    ap.add_argument('--text'); ap.add_argument('--tone', default='自然地'); ap.add_argument('--out', default='试听.mp3')
    a = ap.parse_args()
    try:
        if a.cmd == 'design':
            design(a.cast, a.who.split(',') if a.who else None, a.force)
        else:
            if not (a.who and a.text): sys.exit('say 需要 --who 和 --text')
            who = a.who if a.who in json.loads(Path(a.cast).read_text()) else '_' + a.who
            smp = sample_path(Path(a.cast).parent, who)
            if not smp.exists(): sys.exit(f'{a.who} 还没有声音样本：先跑 design')
            mp3, words, d, heard = say(a.text, smp, a.tone, Path(a.out).resolve().parent / '.seed_cache')
            Path(a.out).write_bytes(mp3.read_bytes()); print(f'{d:.2f}s -> {a.out}' + (f'（念成了：{heard}）' if heard else ''))
    except SeedError as e:
        sys.exit(f'🔴 {e}')


if __name__ == '__main__':
    main()
