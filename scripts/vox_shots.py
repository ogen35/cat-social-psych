#!/usr/bin/env python3
"""Vox 拼贴版的镜头：把 <集目录>/镜头表.json 渲成 huashu-art-motion 引擎的片段（默认语法 cat_vox），帧放进 build/clips/<镜头>/ 给 film.py 播。

分工：cat_vox 画整幅画面——纸纹桌面、灰度网点冲印件（照片、视频）、剪报、索引卡、纸条、红线、红圈、荧光笔、印章、黑卡纸、
猫贴纸拼贴式张嘴，以及 Vox 样式的顶部标题、字幕、名牌（film.py 写 OVERLAY = False）；build_pixel 出声音、封面、文案、自检。
两边靠同一条配音时间轴对齐：每镜从「第一句开口前 PRE 秒」开始，到下一镜开始为止；cue 的时刻写成台词锚点。
画面规矩、坐标、字段说明见 references/Vox版工作流.md；cue 字段全集见 assets/示例_v8_第3章反事实思维_Vox/cat_vox.js 开头。

  V="uv run -q --with numpy --with pillow python vox_shots.py"
  $V <集目录> --plan [--est]    # 只打印每镜起止和时长（超过 8 秒提示拆镜）
  $V <集目录> --stills          # 每镜几张静帧 → build/vox/静帧/<镜头>/（看构图、红圈位置）
  $V <集目录> --jaw             # 每个说话的猫在第一次张嘴那一拍出静帧，裁脸拼成 build/vox/张嘴核对.jpg（核 mouth 标得对不对）
  $V <集目录> --covers          # 镜头表.json 的 covers 渲成 素材/vox封面_竖.png、vox封面_横.png（film.py 的 cover_v / cover_h 铺满它们）
  $V <集目录> [--only A,C]      # 按配音缓存的真实时间轴渲片段、抽帧（spec、语法文件、用到的图片都没变的镜头跳过）
  加 --est：不读配音，按字数估时长（配音前先看画面）。

镜头表.json（cat_vox）：
{
  "grammar": "cat_vox",
  "topbar": {"text": "为什么「差一点」最难受？", "hi": ["差一点"]},
  "safe": {"top": 330, "bottom": 590}, "fy": 820,
  "covers": {"竖": {"size": [1080, 1440], "fy": 720, "cues": [...]}, "横": {"size": [1440, 1080], "fy": 540, "cues": [...]}},
  "shots": [
    {"name": "C",
     "cam": [{"t": 0, "x": 540, "y": 560, "z": 1.12}, {"t": "reveal@反而+0.9", "x": 540, "y": 830, "z": 0.96, "ease": "tail"}],
     "cues": [
       {"kind": "clipping", "at": -1, "data": {"x": 540, "y": 560, "w": 900, "kicker": "…", "head": ["铜牌的，", "反而比银牌的开心"],
        "marks": [{"at": "reveal@铜牌的", "kind": "circle", "line": 1, "sub": "铜牌"}]}},
       {"kind": "photo", "at": -1, "video": "素材/网络素材/mk_45913.mp4", "ss": 0.5, "data": {"x": 800, "y": 1110, "w": 430, "h": 320, "label": "铜牌"}},
       {"kind": "cat", "at": 0.1, "image": "素材/抠图/胜利/04_脸部特写_震惊_抠图.png",
        "data": {"x": 880, "y": 1335, "h": 560, "mouth": [0.607, 0.40, 0.45], "jaw": 0.07, "talk": ["hook"]}}
     ]}
  ]
}
时刻（cue 的 at、data 里所有 at / t / labelAt）：数字＝这一镜里的秒（负数＝切进来时已经摆好）；"句id"＝这句开口；"句id@词"＝念到这个词；
后面可跟 +0.3 / -0.2。猫的 talk 写这只猫说的句子 id，换算成真实出声区间。镜头从哪句开始看 film.py 的 SHOTS。
旧的 y2_vox 参数化写法（不写 grammar）还能渲，只是第 31 期起不用了。
"""
import ast, hashlib, json, re, shutil, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
FPS = 30


def film_vals(ep):
    """不执行 film.py（它要 skia）：只取简单赋值。"""
    tree = ast.parse((ep / 'film.py').read_text()); out = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            try: out[node.targets[0].id] = eval(compile(ast.Expression(node.value), 'film.py', 'eval'), {'dict': dict, '__builtins__': {}})
            except Exception: pass
    return out


class Line:
    def __init__(self, d, start, dur, words, mp3=None):
        self.id, self.start, self.dur, self.words, self.d, self.mp3 = d['id'], start, dur, words or [], d, mp3
        self.who = d.get('who', '旁白')
        self.plain = re.sub(r'[【】]', '', d['say'])
        self._voiced = None

    def voiced(self):
        """真实出声的区间（整片秒），和 build_pixel 的嘴型同一算法；没有配音就整句算出声。"""
        if self._voiced is None:
            if self.mp3:
                import numpy as np, seed_voice
                raw = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(self.mp3), '-f', 's16le', '-ac', '1', '-ar', '48000', '-'])
                x = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
                self._voiced = [(self.start + a, self.start + b) for a, b in seed_voice.voiced(seed_voice.envelope(x), merge=0.12)]
            else: self._voiced = [(self.start, self.start + self.dur)]
        return self._voiced

    def at(self, word):
        i = self.plain.find(word)
        if i < 0: raise SystemExit(f'「{self.id}」里没有「{word}」')
        t = self.dur * i / max(1, len(self.plain)); k = 0
        for w in self.words:
            j = self.plain.find(w['text'], k)
            if j < 0: continue
            if j >= i: t = w['t']; break
            k = j + len(w['text'])
        return self.start + t


def timeline(ep, est=False):
    """和 build_pixel 同一套算法：句子首尾相接，句间 GAP（或这句的 gap），开头 0.1 秒（快节奏）。"""
    v = film_vals(ep); lines = v['LINES']
    if est or v.get('VOICE') != 'libtv':
        vo = [(None, [], len(re.sub(r'[【】]', '', d['say'])) / (5.2 if v.get('PACE') == 'fast' else 4.5)) for d in lines]; missing = [d['id'] for d in lines]   # 和 build_pixel --no-voice 同一个估法
    else:
        import libtv_voice
        vo, missing = libtv_voice.for_build(ep, ep / 'build', v.get('VOICE_TEMPO', 1.0), v.get('VOICE_MAX_GAP'), v.get('VOICE_MIN_RATE'))
    fast = v.get('PACE') == 'fast'
    T, t = {}, (0.1 if fast else 0.4)
    for d, (mp3, words, dur) in zip(lines, vo):
        T[d['id']] = Line(d, t, dur, words, mp3); t += dur + d.get('gap', v.get('GAP', 0.12 if fast else 0.28))
    total = round((t + v.get('TAIL', 0.8 if fast else 1.6)) * FPS) / FPS
    return T, total, v, missing


def resolve(at, T, s0):
    if isinstance(at, (int, float)): return float(at)
    m = re.fullmatch(r'([\w]+)(?:@([^+\-]+))?([+-][\d.]+)?', at.strip())
    if not m: raise SystemExit(f'看不懂的 at：{at}')
    lid, word, off = m.groups()
    if lid not in T: raise SystemExit(f'at 里的句子 {lid} 不在 LINES 里')
    t = T[lid].at(word) if word else T[lid].start
    return round(t + float(off or 0) - s0, 3)


def caption_chunks(say, words, dur, maxc=14):
    """和 scripts/pixel/kit.py 的 caption_chunks 同一算法（字幕块 ≤14 字、优先在标点断、按逐字时间给起止）。"""
    plain = re.sub(r'[【】]', '', say); pieces, cur = [], ''
    for ch in plain:
        if not cur and pieces and ch in '，。！？；：、—': pieces[-1] += ch; continue
        cur += ch
        if ch in '，。！？；：、—' and len(cur) >= 4: pieces.append(cur); cur = ''
        elif len(cur) >= maxc: pieces.append(cur); cur = ''
    if cur.strip():
        if pieces and not cur.strip('，。！？；：、— '): pieces[-1] += cur
        else: pieces.append(cur)
    hl = re.findall(r'【(.+?)】', say); n = max(1, len(plain)); times = [dur * i / n for i in range(n + 1)]
    k = 0
    for w in words or []:
        j = plain.find(w['text'], k)
        if j < 0: continue
        for q in range(j, j + len(w['text'])): times[q] = w['t']
        k = j + len(w['text'])
    out, i = [], 0
    for p in pieces:
        t0 = times[min(i, n - 1)]; i += len(p); out.append([t0, dur, p.rstrip('，。、；：— '), [h for h in hl if h in p]])
    for j in range(len(out) - 1): out[j][1] = out[j + 1][0]
    return out


def resolve_tree(o, T, s0):
    """cat_vox：data 里凡是叫 at / t / labelAt 的值都按台词锚点换算成这一镜里的秒。"""
    if isinstance(o, dict): return {k: (resolve(v, T, s0) if k in ('at', 't', 'labelAt') else resolve_tree(v, T, s0)) for k, v in o.items()}
    if isinstance(o, list): return [resolve_tree(v, T, s0) for v in o]
    return o


def cat_vox_spec(ep, table, sh, name, T, s0, dur):
    cues = []
    for k, c in enumerate(sh['cues']):
        q = resolve_tree({kk: vv for kk, vv in c.items() if kk not in ('video', 'ss')}, T, s0)
        q['at'] = resolve(c.get('at', -1.0), T, s0); D = q.setdefault('data', {})
        if c.get('video'):
            ss = float(c.get('ss', 0)); need = max(0.5, dur - max(0, q['at']))
            q['frames'] = str(frames_for(ep, c['video'], ss + max(0, -q['at']), need, [D.get('fx', 0.5), D.get('fy', 0.5)],
                                         D['w'] / D['h'], f'{name}{k}', size=(D['w'], D['h'])))
            D['fx'] = D['fy'] = 0.5
        if q.get('image') and not Path(q['image']).is_absolute(): q['image'] = str(ep / q['image'])
        if q['kind'] == 'cat' and isinstance(D.get('talk'), list) and all(isinstance(x, str) for x in D.get('talk', [])):
            D['talk'] = [[round(a - s0, 3), round(b - s0, 3)] for lid in D['talk'] for a, b in T[lid].voiced() if b > s0 and a < s0 + dur]
        cues.append(q)
    caps = []
    for L in T.values():
        if L.start >= s0 + dur or L.start + L.dur + 0.3 <= s0: continue
        for c0, c1, txt, hi in caption_chunks(L.d['say'], L.words, L.dur):
            a, b = L.start + c0 - s0, L.start + c1 + (0.25 if c1 >= L.dur - 1e-6 else 0) - s0
            if b > 0 and a < dur: caps.append({'t0': round(a, 3), 't1': round(b, 3), 'text': txt, 'hi': hi, 'who': None if L.who == '旁白' else L.who})
    data = {'cam': resolve_tree(sh.get('cam', []), T, s0), 'caps': caps, 'topbar': table.get('topbar'), 'fy': table.get('fy', 820)}
    return {'grammar': 'cat_vox', 'duration': dur, 'fps': FPS, 'width': 1080, 'height': 1920,
            'safe': table.get('safe', {'top': 330, 'bottom': 590}), 'data': data, 'cues': cues}


def frames_for(ep, video, ss, dur, focus, aspect, key, size=None):
    """把视频的 [ss, ss+dur] 裁成 aspect（宽/高）、按 focus 取景，抽成 30fps 帧序列。按参数缓存。"""
    src = (ep / video) if not Path(video).is_absolute() else Path(video)
    h = hashlib.sha1(json.dumps([str(src), ss, round(dur, 2), focus, aspect, size]).encode()).hexdigest()[:10]
    d = ep / 'build' / 'vox' / 'frames' / f'{key}_{h}'
    if d.exists() and any(d.iterdir()): return d
    d.mkdir(parents=True, exist_ok=True)
    w, hh = map(int, subprocess.check_output(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height',
                                              '-of', 'csv=p=0', str(src)]).decode().strip().split(','))
    if w / hh > aspect: cw, ch = int(hh * aspect) // 2 * 2, hh
    else: cw, ch = w, int(w / aspect) // 2 * 2
    fx, fy = focus
    x = int(min(max(0, fx * w - cw / 2), w - cw)); y = int(min(max(0, fy * hh - ch / 2), hh - ch))
    sc = f'scale={size[0]}:{size[1]}' if size else ('scale=-2:1080' if ch > 1080 else 'scale=-2:ih')
    subprocess.run(['nice', '-n', '10', 'ffmpeg', '-v', 'error', '-y', '-ss', f'{ss:.3f}', '-t', f'{dur + 0.5:.3f}', '-i', str(src),
                    '-vf', f'crop={cw}:{ch}:{x}:{y},{sc},fps={FPS}', '-q:v', '3', str(d / '%04d.jpg')], check=True)
    return d


def render_one(ep, eng, out, name, sp, body, mp4, frames, dur, spec, stills):
    render = ['nice', '-n', '10', 'uv', 'run', '-q', '--with', 'playwright', 'python', str(eng / 'render.py'), '--spec', str(sp)]
    if stills:
        sp = sp.with_suffix('.stills.json'); sp.write_text(body); render[-1] = str(sp)
        ts = sorted({0.05, dur - 0.15, *[min(dur - 0.15, max(0.05, c['at'] + 0.9)) for c in spec['cues'] if c['at'] > 0],
                     *[min(dur - 0.15, max(0.05, k['t'])) for k in spec['data'].get('cam', [])]})
        subprocess.run(render + ['--stills', ','.join(f'{x:.2f}' for x in ts), '--out', str(out / '静帧' / name)], check=True); return False
    gram = eng / 'clips' / f"{spec['grammar']}.js"            # 语法文件改了也要重渲
    stamp = ''.join(f"{c['image']}@{Path(c['image']).stat().st_mtime_ns}" for c in spec['cues'] if c.get('image') and Path(c['image']).exists())   # 换了抠图、照片也要重渲
    key = hashlib.sha1((body + (gram.read_text() if gram.exists() else '') + stamp).encode()).hexdigest()
    kf = sp.with_suffix('.key')
    if kf.exists() and kf.read_text() == key and mp4.exists() and frames.exists() and any(frames.iterdir()):
        print('   （没变，跳过）'); return False
    sp.write_text(body)
    subprocess.run(render + ['--out', str(mp4)], check=True)
    if frames.exists(): shutil.rmtree(frames)
    frames.mkdir(parents=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(mp4), '-q:v', '2', str(frames / '%04d.jpg')], check=True)
    kf.write_text(key)
    return True


def render_covers(ep, eng, table):
    out = ep / 'build' / 'vox'; out.mkdir(parents=True, exist_ok=True)
    for name, c in (table.get('covers') or {}).items():
        W_, H_ = c['size']; fy = c.get('fy', H_ / 2); cues = []
        for q in c['cues']:
            q = dict(q); q.setdefault('at', -1.0)
            if q.get('image') and not Path(q['image']).is_absolute(): q['image'] = str(ep / q['image'])
            cues.append(q)
        spec = {'grammar': 'cat_vox', 'duration': 2, 'fps': FPS, 'width': W_, 'height': H_,
                'data': {'cam': [{'t': 0, 'x': W_ / 2, 'y': fy, 'z': 1}], 'caps': [], 'fy': fy}, 'cues': cues}
        sp = out / f'封面_{name}.json'; sp.write_text(json.dumps(spec, ensure_ascii=False)); d = out / f'封面_{name}'
        subprocess.run(['nice', '-n', '10', 'uv', 'run', '-q', '--with', 'playwright', 'python', str(eng / 'render.py'), '--spec', str(sp),
                        '--stills', '1.5', '--out', str(d)], check=True)
        dst = ep / '素材' / f'vox封面_{name}.png'; shutil.copy(sorted(d.glob('*.png'))[-1], dst); print(f'封面 → {dst}')
    if not table.get('covers'): sys.exit('镜头表.json 里没有 covers')


def jaw_sheet(out, picks):
    """picks: [(镜头, 静帧 png, 猫的 data)] → 裁脸拼一张（张嘴那一拍，看嘴缝是不是在鼻子下面）。"""
    from PIL import Image, ImageDraw
    tiles = []
    for name, png, D in picks:
        im = Image.open(png).convert('RGB'); x, y, h = D['x'], D['y'], D['h']; cy = y - h + D['mouth'][1] * h
        t = im.crop((int(x - h * .42), int(cy - h * .36), int(x + h * .42), int(cy + h * .22))).resize((300, 270))
        ImageDraw.Draw(t).text((6, 4), name, fill=(220, 30, 30)); tiles.append(t)
    if not tiles: print('没有说话的猫'); return
    cols = min(7, len(tiles)); rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * 300, rows * 270), 'white')
    for k, t in enumerate(tiles): sheet.paste(t, ((k % cols) * 300, (k // cols) * 270))
    sheet.save(out / '张嘴核对.jpg', quality=85); print(f'→ {out / "张嘴核对.jpg"}')


def main():
    a = sys.argv[1:]
    if not a: sys.exit(__doc__)
    ep = Path(a[0]).resolve(); est = '--est' in a; stills = '--stills' in a; plan_only = '--plan' in a; jaw = '--jaw' in a
    only = set(a[a.index('--only') + 1].split(',')) if '--only' in a else None
    table = json.loads((ep / '镜头表.json').read_text())
    T, total, v, missing = timeline(ep, est)
    pre = v.get('PRE', 0.25); order = v.get('SHOTS') or []
    starts = {name: T[lid].start - pre for name, lid in order}
    names = [n for n, _ in order]
    if missing and not est: print(f'🟡 {len(missing)} 句还没配音，按字数估：{", ".join(missing[:8])}{"…" if len(missing) > 8 else ""}')
    eng = ep / '代码工程'
    if not (eng / 'render.py').exists() and not plan_only: sys.exit(f'没有 {eng}：cp -R ~/.claude/skills/huashu-art-motion/scripts/engine {eng}')
    out = ep / 'build' / 'vox'; out.mkdir(parents=True, exist_ok=True)
    if '--covers' in a: render_covers(ep, eng, table); return
    shots = {s['name']: s for s in table['shots']}; picks = []
    for i, name in enumerate(names):
        s0 = starts[name]; s1 = starts[names[i + 1]] if i + 1 < len(names) else total
        dur = round(s1 - s0 + 0.2, 2)
        print(f'{name}  {max(0, s0):6.2f}–{s1:6.2f}s  {dur:4.1f}s' + ('  （超过 8 秒：拆镜）' if dur > 8.2 else ''))
        if plan_only or (only and name not in only): continue
        if name not in shots: print(f'   🟡 镜头表里没有 {name}'); continue
        sh = shots[name]; cues = []
        if table.get('grammar') == 'cat_vox':
            spec = cat_vox_spec(ep, table, sh, name, T, s0, dur)
            if jaw:
                cats = [c for c in spec['cues'] if c['kind'] == 'cat' and c['data'].get('talk')]
                if cats:
                    t0 = max(0.05, cats[0]['data']['talk'][0][0] + 0.02); sp = out / f'{name}.jaw.json'; sp.write_text(json.dumps(spec, ensure_ascii=False))
                    d = out / '张嘴' / name
                    subprocess.run(['nice', '-n', '10', 'uv', 'run', '-q', '--with', 'playwright', 'python', str(eng / 'render.py'), '--spec', str(sp),
                                    '--stills', f'{t0:.2f}', '--out', str(d)], check=True, capture_output=True)
                    picks.append((name, sorted(d.glob('*.png'))[-1], cats[0]['data']))
                continue
            sp = out / f'{name}.json'; body = json.dumps(spec, ensure_ascii=False, indent=1)
            mp4 = out / f'{name}.mp4'; frames = ep / 'build' / 'clips' / name
            if not render_one(ep, eng, out, name, sp, body, mp4, frames, dur, spec, stills): continue
            continue
        for k, c in enumerate(sh['cues']):
            q = {kk: vv for kk, vv in c.items() if kk not in ('video', 'ss', 'focus', 'aspect')}
            q['at'] = resolve(c['at'], T, s0)
            if c.get('video'):
                ss = float(c.get('ss', 0)); need = max(0.5, dur - max(0, q['at']))
                q['frames'] = str(frames_for(ep, c['video'], ss + max(0, -q['at']), need, c.get('focus', [0.5, 0.5]),
                                             c.get('aspect', table.get('aspect', 0.8)), f'{name}{k}'))
                q['kind'] = 'clip'
            if q.get('image') and not Path(q['image']).is_absolute(): q['image'] = str(ep / q['image'])
            cues.append(q)
        spec = {'grammar': 'y2_vox', 'duration': dur, 'fps': FPS, 'width': 1080, 'height': 1920,
                'safe': table.get('safe', {'top': 330, 'bottom': 590}), 'cues': cues}
        if table.get('theme'): spec['theme'] = table['theme']
        if sh.get('camera') or table.get('camera'): spec['data'] = {'camera': sh.get('camera') or table.get('camera')}
        sp = out / f'{name}.json'; body = json.dumps(spec, ensure_ascii=False, indent=1)
        mp4 = out / f'{name}.mp4'; frames = ep / 'build' / 'clips' / name
        render = ['nice', '-n', '10', 'uv', 'run', '-q', '--with', 'playwright', 'python', str(eng / 'render.py'), '--spec', str(sp)]
        if stills:
            sp.write_text(body); ts = ','.join(f'{x:.2f}' for x in sorted({0.05, *[min(dur - 0.1, max(0.05, c["at"] + 0.9)) for c in cues]}))
            subprocess.run(render + ['--stills', ts, '--out', str(out / '静帧' / name)], check=True); continue
        if sp.exists() and sp.read_text() == body and mp4.exists() and frames.exists() and any(frames.iterdir()):
            print('   （没变，跳过）'); continue
        sp.write_text(body)
        subprocess.run(render + ['--out', str(mp4)], check=True)
        if frames.exists(): shutil.rmtree(frames)
        frames.mkdir(parents=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(mp4), '-q:v', '2', str(frames / '%04d.jpg')], check=True)
    if jaw: jaw_sheet(out, picks)
    print(f'全片 {total:.1f} 秒')


if __name__ == '__main__':
    main()
