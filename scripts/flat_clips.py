"""平涂画风的 LibTV 镜头工具：多参提示词、下载、抽帧、对口型时间、检查、清理。

    python3 flat_clips.py prompts <集目录>            # 按 镜头单.json 拼海螺 H3 多参提示词 → 写回 镜头单.json，并出 镜头单_提示词.md
    python3 flat_clips.py fetch   <集目录> <镜头> <url>   # 下载片段 → 素材/片段/<镜头>.mp4，抽帧，量出片段里说话的起止时间
    python3 flat_clips.py frames  <集目录> [镜头 ...]  # 重新抽帧：build/clips/<镜头>/%04d.jpg（30fps，铺满 1080×1920，不拉伸）
    python3 flat_clips.py sheet   <集目录> <镜头> [--every 0.5]   # 联系表 → build/qa/片段_<镜头>.jpg（对动作时间）
    python3 flat_clips.py limbs   <集目录> <镜头> [--from 秒 --dur 秒]  # 多手多脚检查大图 → build/qa/肢体_<镜头>.jpg
    python3 flat_clips.py clean   <集目录>            # 出片确认后：只留 output/ 里的成片、竖封面 3:4、横封面 4:3、抖音文案.txt，其余全删

镜头单.json 的写法、镜头角度和提示词规则见 references/平涂画风.md。
"""
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
PROJECT = '55630bcc61e34037b599b51aadb333e8'           # LibTV 项目「喵喵剧团 · IP 重设计」：设定图、场景库、道具库都在这里
IP_NODE = {'大比': 'i-YhN0mW6J3P', '胜利': 'i-f2SGkGT58O', '大宝': 'i-xZdZGWNKSB'}   # IP 造型 v3（2026-11-07 确认，Style Image V8.2 出图）
EN = {'大比': 'Dabi', '胜利': 'Shengli', '大宝': 'Dabao'}
# 多参提示词里的角色短描述（和 IP 造型 v2 一致；长描述会挤爆 2000 字的上限）
H3_CAT = {'大比': 'fluffy cream ragdoll cat, round dark-brown face mask around big blue eyes, dark ears, bushy dark-brown tail, red heart tag',
          '胜利': 'chubby white cat with dark-brown tabby cap and back patch, smug orange eyes, huge upright striped bushy tail, small red crown',
          '大宝': 'biggest cat, grey-brown striped Maine Coon, black ear tufts, cream chest ruff, yellow-green grumpy eyes'}
# 官方指南：不要写否定句（模型没有负向分支），用正面描述
H3_STYLE = ('Naive contemporary art illustration matching the references: hand-painted gouache brushstrokes with colored-pencil texture, '
            'bold saturated color blocks, wobbly black outlines, deadpan humor. Each cat has four legs with round paws and one tail; '
            'paws stay on the ground, the cats act with heads, ears, eyes and tails, and props stand on their own.')
# ↑ 2026-11-07 第 27b 期实测：只要写猫用前爪做动作（握话筒、拍胸口、挥爪、捂嘴、搭爪子），H3 就会保留着地的两只前爪、
#   再多画一只（三只前爪），或者画成带手指的人手。所以镜头单里一律不写前爪动作，道具放支架上、桌上。
H3_SAFE = 'One continuous take with no cuts. Vertical frame; every cat stays in the upper three quarters, the lower quarter is plain floor.'
SCENE_LIB = SKILL / 'assets' / '平涂' / '场景库.json'      # {名字: {node, desc, kind: scene|prop}}
KEEP = ('成片.mp4', '封面_竖屏_3x4.png', '封面_横屏_4x3.png', '抖音文案.txt')
LIMIT = 2000                                          # LibTV 的提示词上限


def lib():
    return json.loads(SCENE_LIB.read_text()) if SCENE_LIB.exists() else {}


def h3_prompt(s, spec):
    """一条镜头 → 海螺 H3 全参考模式提示词（MiniMax 官方结构：subject_definitions / summary / retention_analysis /
    detailed_description / overall_soundscape / non_diegetic_music）。
    镜头字段：scene（场景库名）、cast（出镜的猫）、props（道具库名，可省）、camera（景别+角度+运镜，英文）、
    blocking（站位和动作，英文，用 {大宝} {胜利} {大比} {scene} {道具名} 指代）、speaker、say（中文台词）、voice（语气，英文）、after（说完的反应，可省）、
    safe（False＝特写等不按「下四分之一留空」构图，可省）。"""
    L = {**lib(), **spec.get('library', {})}
    labels, defs = {}, []
    k = 1
    sc = L[s['scene']]
    labels['scene'] = f'<Subject {k}>'; defs.append(f'<Subject {k}> is the {sc["desc"]} in {{{{Node {sc["node"]}}}}}.'); k += 1
    for c in s['cast']:
        labels[c] = f'<Subject {k}>'; defs.append(f'<Subject {k}> is {EN[c]} from {{{{Node {IP_NODE[c]}}}}}: {H3_CAT[c]}.'); k += 1
    for p in s.get('props', []):
        pr = L[p]
        labels[p] = f'<Subject {k}>'; defs.append(f'<Subject {k}> is the {pr["desc"]} in {{{{Node {pr["node"]}}}}}.'); k += 1

    def lab(text):
        return re.sub(r'\{(.+?)\}', lambda m: labels.get(m.group(1), m.group(0)), text)
    blocking = lab(s['blocking'])
    talks = s.get('lines') or ([dict(speaker=s['speaker'], say=s['say'], voice=s.get('voice', 'natural'), after=s.get('after', ''))]
                               if s.get('speaker') else [])
    sid, talk = {}, ''
    for d in talks:                                   # 官方格式：说话的角色写成 <Subject N> (Sx)，台词放在 <d>[Chinese] …</d>
        sid.setdefault(d['speaker'], f'S{len(sid) + 1}')
        talk += f' {labels[d["speaker"]]} ({sid[d["speaker"]]}) says ({d.get("voice", "natural")}), <d>[Chinese] {d["say"]}</d>'
        if d.get('after'): talk += ' ' + lab(d['after'])
    if not talks and s.get('after'): talk = ' ' + lab(s['after'])
    allsub = ', '.join(labels.values())
    summary = lab(s.get('summary') or f'One shot in {{scene}} with {", ".join("{" + c + "}" for c in s["cast"])}.')
    safe = H3_SAFE if s.get('safe', True) else 'One continuous take with no cuts. Vertical frame.'
    # ↑ 2026-11-08 第 28 期：H3 常在一个片段里先给远景再硬切近景，甚至切到别的背景；写明一镜到底能减少。
    p = (f'subject_definitions:\n' + '\n'.join(defs) + '\n\n'
         f'summary:\n[reference generation] {summary}\n\n'
         f'retention_analysis:\n{allsub} ([Shot 1]): fully_preserved - designs, colors, painting style.\n\n'
         f'detailed_description:\n{H3_STYLE} {safe}\n[Shot 1] {lab(s["camera"])} {blocking}{talk}\n\n'
         f'overall_soundscape:\n{s.get("sound", "Quiet indoor room tone.")}\n\nnon_diegetic_music:\nN/A')
    if len(p) > LIMIT:
        raise SystemExit(f'镜头 {s["id"]} 的提示词 {len(p)} 字，超过 LibTV 上限 {LIMIT}：把 blocking / camera 写短一点')
    return p


def refs(s, spec):
    L = {**lib(), **spec.get('library', {})}
    return [L[s['scene']]['node']] + [IP_NODE[c] for c in s['cast']] + [L[p]['node'] for p in s.get('props', [])]


def cmd_prompts(ep):
    spec = json.loads((ep / '镜头单.json').read_text())
    out = ['# 镜头单 · 海螺 H3 多参提示词', '',
           f'项目 {PROJECT}；generate_video(model=MiniMax-Hailuo-H3, referenceImageNodes=下面的参考节点, '
           'params={ratio:"9:16", resolution:"768P", duration:镜头秒数, count:1})。', '']
    for s in spec['shots']:
        s['h3_prompt'] = h3_prompt(s, spec); s['refs'] = refs(s, spec)
        out += [f'## {s["id"]} · {s.get("angle", "")} · 台词 {s.get("line", "")}（{len(s["h3_prompt"])} 字）', '',
                f'参考节点：{s["refs"]}；时长 {s.get("duration", 6)} 秒', '', '```', s['h3_prompt'], '```', '']
    (ep / '镜头单_提示词.md').write_text('\n'.join(out))
    (ep / '镜头单.json').write_text(json.dumps(spec, ensure_ascii=False, indent=1))
    print(ep / '镜头单_提示词.md', f'（{len(spec["shots"])} 个镜头）')


def frames(ep, name):
    """抽帧：按比例铺满 1080×1920 再居中裁切（H3 的 768×1344 和 9:16 差一点，不能直接拉伸）。"""
    src = ep / '素材' / '片段' / f'{name}.mp4'
    d = ep / 'build' / 'clips' / name
    d.mkdir(parents=True, exist_ok=True)
    for f in d.glob('*.jpg'): f.unlink()
    vf = 'fps=30,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920'
    subprocess.run(['nice', 'ffmpeg', '-v', 'error', '-y', '-i', str(src), '-vf', vf, '-q:v', '3', str(d / '%04d.jpg')], check=True)
    print(name, len(list(d.glob('*.jpg'))), 'frames')


def speech(src):
    """片段自带音轨里说话的区间（H3 会按 <d> 台词出声、对口型）：[(起, 止), …]。没有音轨返回 []。"""
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', str(src), '-af', 'silencedetect=n=-35dB:d=0.2', '-f', 'null', '-'],
                       capture_output=True, text=True)
    if 'Audio:' not in r.stderr: return []
    h, m, sec = re.search(r'Duration: (\d+):(\d+):([\d.]+)', r.stderr).groups(); dur = int(h) * 3600 + int(m) * 60 + float(sec)
    st = [float(x) for x in re.findall(r'silence_start: ([\d.]+)', r.stderr)]
    en = [float(x) for x in re.findall(r'silence_end: ([\d.]+)', r.stderr)]
    runs = []
    if st and st[0] <= 0.01: st = st[1:]
    else: en = [0.0] + en
    for a, b in zip(en, st + [dur]):
        if b - a > 0.08: runs.append((round(a, 3), round(b, 3)))
    return runs


def cmd_fetch(ep, name, url):
    (ep / '素材' / '片段').mkdir(parents=True, exist_ok=True)
    dst = ep / '素材' / '片段' / f'{name}.mp4'
    urllib.request.urlretrieve(url, dst)
    frames(ep, name)
    sp = speech(dst)
    (ep / '素材' / '片段' / f'{name}.json').write_text(json.dumps({'speech': sp}, ensure_ascii=False))
    print(name, '说话区间', sp)


def cmd_sheet(ep, name, every=0.5):
    src = ep / '素材' / '片段' / f'{name}.mp4'
    out = ep / 'build' / 'qa' / f'片段_{name}.jpg'
    out.parent.mkdir(parents=True, exist_ok=True)
    fps = 1 / every
    vf = (f"fps={fps},scale=180:-1,drawtext=fontfile={SKILL}/scripts/pixel/fonts/SmileySans-Oblique.ttf:"
          f"text='%{{eif\\:n*{every}\\:d}}.%{{eif\\:mod(n*{every * 10:g}\\,10)\\:d}}s':x=6:y=6:fontsize=22:fontcolor=white:box=1:boxcolor=black@0.5,tile=6x2")
    r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), '-vf', vf, '-frames:v', '1', str(out)])
    if r.returncode:
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(src), '-vf', f'fps={fps},scale=180:-1,tile=6x2', '-frames:v', '1', str(out)], check=True)
    print(out, f'（每格 {every} 秒，从 0 秒开始，从左到右、从上到下）')


def cmd_limbs(ep, name, t0=0.0, dur=None):
    """多手多脚检查：从 t0 起每 1/3 秒一格的大图 → build/qa/肢体_<镜头>.jpg。"""
    src = ep / '素材' / '片段' / f'{name}.mp4'
    out = ep / 'build' / 'qa' / f'肢体_{name}.jpg'
    out.parent.mkdir(parents=True, exist_ok=True)
    args = ['ffmpeg', '-v', 'error', '-y', '-ss', str(t0)] + (['-t', str(dur)] if dur else []) + ['-i', str(src), '-vf',
            'fps=3,scale=270:-1,tile=6x3', '-frames:v', '1', str(out)]
    subprocess.run(args, check=True)
    print(out, f'（从 {t0} 秒起每 1/3 秒一格；数一数每只猫的前爪、后爪、尾巴，看有没有人手、手指）')


def cmd_clean(ep):
    """用户要求：每期只留成片、竖封面 3:4、横封面 4:3、抖音文案.txt。"""
    out = ep / 'output'
    missing = [k for k in KEEP if not (out / k).exists()]
    if missing: raise SystemExit(f'output/ 里还缺 {missing}，先出片再清理')
    for p in ep.iterdir():
        if p.name == 'output': continue
        shutil.rmtree(p) if p.is_dir() else p.unlink()
    for p in out.iterdir():
        if p.name not in KEEP: shutil.rmtree(p) if p.is_dir() else p.unlink()
    print('只留下：', ', '.join(KEEP))


def main(a):
    if len(a) < 2: print(__doc__); return
    cmd, ep = a[0], Path(a[1]).resolve()
    if cmd == 'prompts': cmd_prompts(ep)
    elif cmd == 'fetch': cmd_fetch(ep, a[2], a[3])
    elif cmd == 'frames':
        names = a[2:] or [p.stem for p in sorted((ep / '素材' / '片段').glob('*.mp4'))]
        for n in names: frames(ep, n)
    elif cmd == 'limbs':
        t0 = float(a[a.index('--from') + 1]) if '--from' in a else 0.0
        dur = float(a[a.index('--dur') + 1]) if '--dur' in a else None
        cmd_limbs(ep, a[2], t0, dur)
    elif cmd == 'sheet':
        every = float(a[a.index('--every') + 1]) if '--every' in a else 0.5
        cmd_sheet(ep, a[2], every)
    elif cmd == 'clean': cmd_clean(ep)
    else: print(__doc__)


if __name__ == '__main__':
    main(sys.argv[1:])
