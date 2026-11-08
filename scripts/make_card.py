#!/usr/bin/env python3
"""证据卡生成器：把书里的概念、经典实验、猫咪研究做成「桌上的真实纸件」PNG，给 Vox 片段当素材。

uv run --with playwright python make_card.py cards.json [--theme vox]

cards.json 是一张卡（对象）或多张卡（数组）。路径相对 cards.json。每张卡输出 <out>.png 和 <out>.json（高亮坐标）。
文字里用【】包住的词＝重点：卡上加粗着色，并把它在图里的位置写进 <out>.json 的 marks（[x,y,w,h]，0..1，相对整张图），
build_episode.py 里 highlight 写 {"mark": 0} 就能让荧光笔＋红圈精确落在第 0 个重点上，不用目测。

卡型（type）与字段：
  book    读书笔记卡  concept（"从众"）en（"Conformity"，可空）body（自己的话转述，≤70 字）note（猫爪批注，可空）page（书页页码，如 "186"）
  study   实验档案卡  name（"阿希线段实验"）who（"所罗门·阿希"）year（"1951"）rows（[["被试","..."],["做法","..."]]，≤3 行）
                     big（大数字，如"【37%】"，可空）result（一句结论）source（"Asch, 1956, Psychological Monographs"）stamp（红章，默认"经典实验"，不是实验就写 ""）
  catlab  猫咪研究卡  journal（"Scientific Reports"）year team finding（≤60 字）big（可空）source
  vs      对比卡      left right（两栏标题）rows（[["左","右"], ...]，≤4 行）footer（可空）head（页眉，默认"一张图看懂"）mid（中间符号，默认 vs；类比写 ≈）
  quiz    互动选择题  question options（["A ...","B ...","C ..."]，自动成为 marks 0..n-1，答案揭晓时 highlight {"mark": 正确项}）
  note    横线索引卡  text（≤40 字，手写体）sign（落款，默认"—— 喵"）
  cover   抖音封面    image（猫图）title（≤2 行、每行 ≤7 字，\n 换行，【】＝荧光笔高亮）sub（黑底标签副标题，≤10 字）
                     big（可选，红色大数字，如"37%"）circle（可选，照片上的红圈 [x,y,w,h] 0..1）focus（[fx,fy] 裁图焦点）
                     series（可选，系列角标，如"猫说心理学 01"）  默认 1080×1440（3:4），Vox 调查桌风格
通用：out（必填，不带扩展名也行）、w/h（默认 1200×1000；cover 1080×1440）、theme（覆盖命令行的色板）。
"""
import argparse, base64, json, re, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import cards_story

ENGINE = Path(__file__).resolve().parent / 'engine'
FONTS = ENGINE / 'lib' / 'fonts'
PALETTES = {  # 与 engine/lib/palettes.js 同一套，卡片和片段同色
    'paper':   {'bg': '#F3EDE2', 'surface': '#FBF8F2', 'ink': '#1B1A17', 'sub': '#6B655B', 'accent': '#C8402F', 'accent2': '#2F5D62'},
    'poster':  {'bg': '#FFD23F', 'surface': '#FFF6D6', 'ink': '#111111', 'sub': '#4A4433', 'accent': '#FF5A36', 'accent2': '#14213D'},
    'ink':     {'bg': '#121417', 'surface': '#1E2226', 'ink': '#F2EFE8', 'sub': '#A39E93', 'accent': '#F2B33D', 'accent2': '#5FB3A1'},
    'navy':    {'bg': '#0D1B2A', 'surface': '#16293D', 'ink': '#EEF3F6', 'sub': '#8FA3B3', 'accent': '#5CC8E0', 'accent2': '#F2A93B'},
    'bauhaus': {'bg': '#EFE9DD', 'surface': '#FFFFFF', 'ink': '#111111', 'sub': '#555555', 'accent': '#D62828', 'accent2': '#1D4E89'},
    'snow':    {'bg': '#E9EEF0', 'surface': '#FFFFFF', 'ink': '#1F2A30', 'sub': '#5E6B72', 'accent': '#D9482B', 'accent2': '#3E7C8C'},
    'vox':     {'bg': '#E4DDCF', 'surface': '#EEEDEB', 'ink': '#171716', 'sub': '#6B655B', 'accent': '#B8433F', 'accent2': '#93403C'},
    'wood':    {'bg': '#EDE3D1', 'surface': '#F7F1E6', 'ink': '#2B2622', 'sub': '#7A6E62', 'accent': '#C4552D', 'accent2': '#3F5B4B'},
    'chalk':   {'bg': '#23302B', 'surface': '#2E3D37', 'ink': '#F1EFE6', 'sub': '#A9B3AA', 'accent': '#F4D35E', 'accent2': '#E87D5A'},
}
PAW = '''<svg viewBox="0 0 100 100" width="{s}" height="{s}"><g fill="{c}"><ellipse cx="50" cy="66" rx="24" ry="20"/>
<ellipse cx="22" cy="40" rx="9" ry="12"/><ellipse cx="40" cy="26" rx="9" ry="12"/><ellipse cx="60" cy="26" rx="9" ry="12"/><ellipse cx="78" cy="40" rx="9" ry="12"/></g></svg>'''


def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def marked(s):
    """【重点】→ <span class=mk>；返回 HTML。"""
    return re.sub(r'【(.+?)】', lambda m: f'<span class="mk">{m.group(1)}</span>', esc(s or '')).replace('\n', '<br>')


def font_css():
    faces = {'H5': 'NotoSansSC-500', 'H7': 'NotoSansSC-700', 'H8': 'NotoSansSC-800', 'H9': 'NotoSansSC-900', 'KAI': 'LXGWWenKai-500', 'NUM': 'Anton-400'}
    return '\n'.join(f"@font-face{{font-family:'{k}';src:url('{(FONTS / (v + '.woff')).as_uri()}') format('woff')}}" for k, v in faces.items())


BASE_CSS = '''
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:transparent}
#card{position:relative;display:flex;flex-direction:column;width:var(--w);height:var(--h);background:var(--surface);color:var(--ink);font-family:H5,sans-serif;overflow:hidden;
  background-image:repeating-linear-gradient(0deg,transparent 0 63px,var(--rule) 63px 65px)}
.mk{font-family:H9;color:var(--accent)}
.hd{display:flex;align-items:center;gap:18px;background:var(--ink);color:var(--surface);padding:22px 48px;font:38px H7;letter-spacing:2px}
.hd .r{margin-left:auto;font:30px H5;opacity:.75}
.stamp{position:absolute;right:52px;top:120px;border:7px solid var(--accent);color:var(--accent);font:46px H9;padding:6px 22px;transform:rotate(8deg);opacity:.85;border-radius:10px}
.pad{flex:1;display:flex;flex-direction:column;justify-content:center;padding:30px 60px 120px}
#card div,#card td{text-wrap:balance}
.k{font:44px KAI;color:var(--sub)}
.big{font:190px NUM;color:var(--accent);line-height:1;white-space:nowrap;flex-shrink:0}
.big .mk{font-family:NUM,H9}
.src{position:absolute;left:60px;right:60px;bottom:30px;font:28px H5;color:var(--sub);border-top:3px dashed var(--sub);padding-top:14px}
'''


def tpl(c, P):
    t = c['type']
    if t == 'book':
        note = f'<div style="align-self:flex-end;margin-top:34px;max-width:640px;font:48px KAI;color:var(--accent2);transform:rotate(-3deg)">{PAW.format(s=46, c=P["accent2"])} {marked(c["note"])}</div>' if c.get('note') else ''
        return f'''<div class="hd">读书笔记<span class="r">{esc(c.get("en", ""))}</span></div>
<div class="pad"><div style="font:150px H9;letter-spacing:4px;margin-top:10px">{marked(c["concept"])}</div>
<div style="height:30px"></div>
<div style="font:60px/1.55 H7;max-width:1080px">{marked(c["body"])}</div>{note}</div>
<div class="src">戴维·迈尔斯《社会心理学》（第11版）{(" · 书页 " + esc(c["page"])) if c.get("page") else ""} · 笔记为转述，非原文</div>'''
    if t == 'study':
        rows = ''.join(f'<tr><td style="font:40px H8;color:var(--sub);padding:12px 26px 12px 0;white-space:nowrap;vertical-align:top">{esc(k)}</td><td style="font:44px/1.45 H7;padding:12px 0">{marked(v)}</td></tr>' for k, v in c.get('rows', []))
        big = f'<div class="big" style="margin-top:6px">{marked(c["big"])}</div>' if c.get('big') else ''
        return f'''<div class="hd">实验档案<span class="r">{esc(c.get("year", ""))}</span></div>{('<div class="stamp">' + esc(c.get("stamp", "经典实验")) + '</div>') if c.get("stamp", "经典实验") else ""}
<div class="pad"><div style="font:84px H9;max-width:860px">{marked(c["name"])}</div>
<div style="font:40px H7;color:var(--sub);margin:10px 0 18px">{esc(c.get("who", ""))}</div>
<table style="border-collapse:collapse">{rows}</table>
<div style="display:flex;align-items:flex-end;gap:30px">{big}<div style="font:52px/1.4 H8;padding-bottom:22px">{marked(c.get("result", ""))}</div></div></div>
<div class="src">出处：{esc(c.get("source", ""))}</div>'''
    if t == 'catlab':
        big = f'<div class="big">{marked(c["big"])}</div>' if c.get('big') else ''
        return f'''<div class="hd">{PAW.format(s=44, c=P["surface"])} 猫咪研究<span class="r">{esc(c.get("journal", ""))} · {esc(c.get("year", ""))}</span></div>
<div class="pad"><div style="font:40px H7;color:var(--sub);margin-bottom:20px">{esc(c.get("team", ""))}</div>
{big}<div style="font:{72 if not c.get("big") else 62}px/1.5 H8;margin-top:18px;max-width:1080px">{marked(c["finding"])}</div></div>
<div style="position:absolute;right:50px;top:150px;opacity:.13">{PAW.format(s=260, c=P["accent"])}</div>
<div class="src">出处：{esc(c.get("source", ""))}</div>'''
    if t == 'vs':
        mid = esc(c.get('mid', 'vs'))   # 中间的符号：对比用 vs，类比（人 ≈ 猫）用 ≈
        rows = ''.join(f'<tr><td>{marked(a)}</td><td class="m">{mid}</td><td>{marked(b)}</td></tr>' for a, b in c['rows'])
        foot = f'<div class="src" style="font:44px H8;color:var(--ink);text-align:center">{marked(c["footer"])}</div>' if c.get('footer') else ''
        return f'''<style>.vs td{{font:48px/1.4 H7;padding:22px 10px;border-bottom:3px solid var(--rule2);width:46%;text-align:center}}.vs td.m{{width:8%;font:44px H9;color:var(--sub)}}
.vs th{{font:70px H9;padding:30px 0 20px}}</style>
<div class="hd">{esc(c.get("head", "一张图看懂"))}<span class="r">{esc(c.get("left", "人类"))} vs {esc(c.get("right", "猫咪"))}</span></div>
<table class="vs" style="width:calc(100% - 100px);margin:10px 50px;border-collapse:collapse"><tr><th>{esc(c.get("left", "人类"))}</th><th></th><th style="color:var(--accent)">{esc(c.get("right", "猫咪"))}</th></tr>{rows}</table>{foot}'''
    if t == 'quiz':
        opts = ''.join(f'<div style="font:58px H8;padding:20px 34px;margin:18px 0;border:4px solid var(--ink);border-radius:18px;background:var(--bg)"><span class="mk" style="color:var(--ink);font-family:H8">{esc(o)}</span></div>' for o in c['options'])
        return f'''<div class="hd">{PAW.format(s=44, c=P["surface"])} 先猜一猜<span class="r">答案在视频里</span></div>
<div class="pad"><div style="font:68px/1.4 H9;margin-bottom:22px">{marked(c["question"])}</div>{opts}</div>'''
    if t == 'note':
        return f'''<div style="position:absolute;inset:0;background:var(--surface);background-image:repeating-linear-gradient(0deg,transparent 0 118px,rgba(80,140,200,.32) 118px 121px);background-position:0 40px"></div>
<div style="position:absolute;left:0;right:0;top:150px;height:4px;background:var(--accent);opacity:.6"></div>
<div style="position:relative;flex:1;display:flex;align-items:center;padding:150px 80px 170px;font:84px/1.42 KAI;color:var(--ink)"><div>{marked(c["text"])}</div></div>
<div style="position:absolute;right:80px;bottom:70px;font:56px KAI;color:var(--ink);display:flex;align-items:center;gap:14px">{esc(c.get("sign", "—— 喵"))}{PAW.format(s=64, c=P["ink"])}</div>'''
    if t == 'cover':
        return cover_tpl(c, P)
    if t in cards_story.TYPES:
        return cards_story.TYPES[t](c, P, c['_cx'])
    raise SystemExit(f'不认识的卡型：{t}（book/study/catlab/vs/quiz/note/cover/{"/".join(cards_story.TYPES)}）')


def hand_ellipse(cx, cy, rx, ry, seed=3):
    """手画红圈：一笔、首尾略交叉、半径轻微抖动（同引擎 DG.ellipsePts 的做法）。"""
    import math, random
    r = random.Random(seed); pts = []
    for k in range(60):
        a = -2.6 + k / 59 * math.pi * 2 * 1.08
        j = 1 + (r.random() - 0.5) * 0.05 + 0.04 * math.sin(a * 1.7 + seed)
        pts.append((cx + math.cos(a) * rx * j, cy + math.sin(a) * ry * j))
    return 'M' + ' L'.join(f'{x:.1f},{y:.1f}' for x, y in pts)


def cover_tpl(c, P):
    """3:4 封面。版式：上 40% 两行大字钩子（关键词荧光笔＋可选红圈），中间一张灰度网点冲印照（白边、胶带、微斜），
    照片左下压黑底撕边标签（副标题），可选一个红色大数字当唯一的视觉锚点；纸纹桌面底，四角压暗。
    抖音主页网格里左下角会盖点赞数，所以最下 120px 不放字。"""
    img = Path(c['image'])
    uri = f'data:image/{"png" if img.suffix.lower() == ".png" else "jpeg"};base64,' + base64.b64encode(img.read_bytes()).decode()
    fx, fy = (c.get('focus') or [0.5, 0.4]) if isinstance(c.get('focus'), list) else (0.5, 0.4)
    title = marked(c['title']).replace('class="mk"', 'class="mk hl"')
    lines = c['title'].count('\n') + 1
    tsize = c.get('title_size', 150 if lines <= 2 and max(len(plain_len) for plain_len in re.sub(r'[【】]', '', c['title']).split('\n')) <= 6 else 128)
    big = f'''<div style="position:absolute;right:56px;top:{c.get('big_top', 960)}px;transform:rotate(6deg);z-index:5">
  <div style="background:var(--surface);padding:6px 30px 0;box-shadow:3px 8px 14px rgba(0,0,0,.28);clip-path:polygon(0 3%,8% 0,22% 2%,40% 0,60% 3%,78% 0,100% 2%,99% 30%,100% 62%,98% 100%,70% 98%,45% 100%,20% 97%,0 100%,2% 60%)">
  <div style="font:150px NUM;color:var(--accent);line-height:1.08">{esc(c['big'])}</div></div>
  <div style="position:absolute;left:50%;top:-14px;width:26px;height:26px;margin-left:-13px;border-radius:50%;background:radial-gradient(circle at 35% 35%,#e06a64,var(--accent) 60%,#6e2421);box-shadow:1px 3px 3px rgba(0,0,0,.35)"></div></div>''' if c.get('big') else ''
    sub = f'''<div class="lab" style="position:absolute;left:46px;top:{c.get('sub_top', 1100)}px;transform:rotate(-2deg);z-index:6">{esc(c['sub'])}</div>''' if c.get('sub') else ''
    series = f'''<div style="position:absolute;left:64px;top:56px;font:40px H8;color:var(--accent);letter-spacing:3px;border:5px solid var(--accent);padding:2px 18px;transform:rotate(-3deg);opacity:.9">{esc(c['series'])}</div>''' if c.get('series') else ''
    ring = ''
    if c.get('circle'):   # 照片上的红圈：[x,y,w,h] 相对照片 0..1
        x, y, w, h = c['circle']; PW, PH = 900, 640
        ring = f'''<svg style="position:absolute;left:0;top:0;overflow:visible" width="{PW}" height="{PH}"><path d="{hand_ellipse((x + w / 2) * PW, (y + h / 2) * PH, w * PW * 0.62, h * PH * 0.62)}" fill="none" stroke="var(--accent)" stroke-width="11" stroke-linecap="round" stroke-linejoin="round"/></svg>'''
    ttop = 150 if c.get('series') else 96
    return f'''<style>
#card{{background:var(--bg);background-image:none}}
#paper{{position:absolute;inset:0;filter:url(#fib);opacity:.55}}
.hl{{color:var(--ink)!important;background:linear-gradient(176deg,transparent 12%,rgba(218,207,8,.92) 14%,rgba(218,207,8,.92) 88%,transparent 90%);padding:0 .06em;margin:0 -.03em;-webkit-box-decoration-break:clone}}
.lab{{background:var(--ink);color:var(--surface);font:62px H9;padding:16px 34px 18px;letter-spacing:2px;box-shadow:3px 6px 10px rgba(0,0,0,.3);clip-path:polygon(0 4%,6% 0,30% 3%,55% 0,80% 4%,100% 0,98% 50%,100% 100%,75% 96%,50% 100%,25% 97%,0 100%,2% 50%)}}
</style>
<svg width="0" height="0" style="position:absolute"><filter id="fib"><feTurbulence type="fractalNoise" baseFrequency=".9 .05" numOctaves="2" seed="7"/><feColorMatrix values="0 0 0 0 .43  0 0 0 0 .37  0 0 0 0 .27  0 0 0 .22 0"/></filter></svg>
<div id="paper"></div>
<div style="position:absolute;inset:0;background:radial-gradient(ellipse at 50% 45%,transparent 55%,rgba(40,30,20,.28) 100%)"></div>
{series}
<div style="position:absolute;left:60px;right:60px;top:{ttop}px;font:{tsize}px/1.2 H9;color:var(--ink);letter-spacing:2px;z-index:4">{title}</div>
<div style="position:absolute;left:90px;top:{c.get('photo_top', 480)}px;width:900px;height:640px;transform:rotate(-2.2deg);z-index:3">
  <div style="position:absolute;inset:-18px;background:var(--surface);box-shadow:3px 9px 16px rgba(0,0,0,.30)"></div>
  <canvas id="ph" width="900" height="640" style="position:absolute;left:0;top:0"></canvas>{ring}
  <div style="position:absolute;left:-40px;top:-30px;width:190px;height:56px;background:rgba(236,230,214,.62);transform:rotate(-28deg);box-shadow:0 1px 2px rgba(0,0,0,.12)"></div>
  <div style="position:absolute;right:-40px;top:-26px;width:190px;height:56px;background:rgba(236,230,214,.62);transform:rotate(24deg);box-shadow:0 1px 2px rgba(0,0,0,.12)"></div>
</div>
{big}{sub}
<script>
window.__done = false;
(() => {{
  const im = new Image();
  im.onload = () => {{
    const W = 900, H = 640, cv = document.getElementById('ph'), g = cv.getContext('2d');
    // 按焦点裁满（cover）
    const s = Math.max(W / im.width, H / im.height), sw = W / s, sh = H / s;
    const sx = Math.min(Math.max(im.width * {fx} - sw / 2, 0), im.width - sw), sy = Math.min(Math.max(im.height * {fy} - sh / 2, 0), im.height - sh);
    const t = document.createElement('canvas'); t.width = W; t.height = H; const tg = t.getContext('2d'); tg.drawImage(im, sx, sy, sw, sh, 0, 0, W, H);
    const d = tg.getImageData(0, 0, W, H).data;
    // 灰度 45° 网点（与引擎 CL.halftone 同算法）
    const cell = {c.get('cell', 6)}, ca = Math.cos(Math.PI / 4), sa = Math.sin(Math.PI / 4), R = Math.hypot(W, H);
    g.fillStyle = getComputedStyle(document.getElementById('card')).getPropertyValue('--surface'); g.fillRect(0, 0, W, H);
    g.fillStyle = getComputedStyle(document.getElementById('card')).getPropertyValue('--ink'); g.beginPath();
    for (let v = -R; v < R; v += cell) for (let u = -R; u < R; u += cell) {{
      const x = W / 2 + u * ca - v * sa, y = H / 2 + u * sa + v * ca; if (x < -cell || y < -cell || x > W + cell || y > H + cell) continue;
      const ix = Math.min(Math.max(x | 0, 0), W - 1), iy = Math.min(Math.max(y | 0, 0), H - 1), i = (iy * W + ix) * 4;
      let L = (d[i] * .3 + d[i + 1] * .59 + d[i + 2] * .11) / 255; L = Math.min(Math.max((L - .5) * 1.3 + .5, 0), 1);
      const rr = cell * 0.66 * Math.sqrt(1 - L); if (rr < 0.35) continue;
      g.moveTo(x + rr, y); g.arc(x, y, rr, 0, Math.PI * 2);
    }}
    g.fill(); window.__done = true;
  }};
  im.src = "{uri}";
}})();
</script>'''


def img_size(f):
    """读 PNG / JPEG 的宽高（不依赖 PIL）。"""
    b = Path(f).read_bytes()
    if b[:8] == b'\x89PNG\r\n\x1a\n':
        return int.from_bytes(b[16:20], 'big'), int.from_bytes(b[20:24], 'big')
    i = 2
    while i < len(b):
        if b[i] != 0xFF: i += 1; continue
        m = b[i + 1]
        if m in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            return int.from_bytes(b[i + 7:i + 9], 'big'), int.from_bytes(b[i + 5:i + 7], 'big')
        i += 2 + int.from_bytes(b[i + 2:i + 4], 'big')
    raise SystemExit(f'读不出图片尺寸：{f}')


def data_uri(f):
    f = Path(f)
    return f'data:image/{"png" if f.suffix.lower() == ".png" else "jpeg"};base64,' + base64.b64encode(f.read_bytes()).decode()


STORY_SIZE = {'scene': (1200, 1000), 'chat': (1080, 'auto'), 'moments': (1080, 'auto'), 'memo': (1080, 'auto'), 'diary': (1080, 'auto'), 'hot': (1080, 'auto')}
AUTO_MIN_H = 760   # 道具卡默认按内容定高：太矮的卡在桌面上像纸条，至少这么高


def render(cards, base, theme):
    from playwright.sync_api import sync_playwright
    tmpd = tempfile.TemporaryDirectory(prefix='cards_'); tmp = Path(tmpd.name)   # 用完自动删
    cast, cast_dir = cards_story.find_cast(base)
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--allow-file-access-from-files'])
        for i, c in enumerate(cards):
            # 每张卡一个新标签页、用完就关：同一个标签页连着渲十几张带大图的卡，内存会越积越多，机器紧时标签页会卡死
            pg = b.new_page(device_scale_factor=1)
            pg.set_default_timeout(180000)   # 机器忙（比如后台在 OCR）时加载大图会慢，别 30 秒就放弃
            if c.get('type') == 'cover' and c.get('image'):
                c = {**c, 'image': str((base / c['image']).resolve())}
            P = PALETTES[c.get('theme', theme)]
            dw, dh = STORY_SIZE.get(c['type'], (1080, 1440) if c['type'] == 'cover' else (1200, 1000))
            w, h = c.get('w', dw), c.get('h', dh)
            cx = None
            if c['type'] in cards_story.TYPES:
                def path(r, _b=base):
                    f = (_b / r).resolve()
                    if not f.exists(): raise SystemExit(f'卡片里引用的图片不存在：{r}（相对 {_b}）')
                    return f
                cx = {'uri': data_uri, 'path': path, 'size': img_size, 'esc': esc, 'marked': marked, 'PAW': PAW,
                      'cast': cast, 'cast_dir': cast_dir, 'sources': [], 'js': [], 'after': []}
                c = {**c, '_cx': cx, '_w': w, '_h': h}
            css = font_css() + BASE_CSS
            auto_h = h == 'auto'
            root = f'--w:{w}px;' + (f'--h:auto;min-height:{AUTO_MIN_H}px;' if auto_h else f'--h:{h}px;') + ''.join(f'--{k}:{v};' for k, v in P.items()) + f'--rule:{P["sub"]}22;--rule2:{P["sub"]}55'
            body = tpl(c, P)
            extra_head, extra_tail = '', ''
            if cx is not None:
                extra_head = cards_story.HT_JS + '<style>.lab{background:var(--ink);color:var(--surface);font-family:H9;padding:12px 30px 14px;letter-spacing:2px;box-shadow:3px 6px 10px rgba(0,0,0,.3);white-space:nowrap;clip-path:polygon(0 4%,6% 0,30% 3%,55% 0,80% 4%,100% 0,98% 50%,100% 100%,75% 96%,50% 100%,25% 97%,0 100%,2% 50%)}</style>'
                extra_tail = '<script>' + '\n'.join(cx['js']) + '\nwindow.__after = [' + ','.join(f'() => {{ {a} }}' for a in cx['after']) + '];</script>'
            page = f'<html><head><meta charset="utf-8"><style>{css}</style>{extra_head}</head><body><div id="card" style="{root}">{body}</div>{extra_tail}</body></html>'
            f = tmp / f'c{i}.html'; f.write_text(page)
            pg.set_viewport_size({'width': w, 'height': 2600 if auto_h else h})
            pg.goto(f.as_uri(), wait_until='load')   # 不等 networkidle：本地字体请求有时一直挂着，页面画完了也等不到；画完靠下面的 __done 和字体检查
            pg.wait_for_function('window.__done !== false', timeout=180000)
            if auto_h:
                h = int(pg.evaluate("Math.ceil(document.getElementById('card').getBoundingClientRect().height)"))
                pg.set_viewport_size({'width': w, 'height': h})
            bad = pg.evaluate('''async () => { const fs = ['H5','H7','H8','H9','KAI','NUM']; await Promise.all(fs.map(f => document.fonts.load(`20px ${f}`, '猫9'))); await document.fonts.ready; return fs.filter(f => !document.fonts.check(`20px ${f}`, '猫9')); }''')
            if bad: print(f'⚠ 字体没加载：{bad}', file=sys.stderr)
            off = pg.evaluate('''() => { const c = document.getElementById('card').getBoundingClientRect(); return [...document.querySelectorAll('.stk')].filter(e => { const r = e.getBoundingClientRect(); return r.left < c.left - r.width * .08 || r.right > c.right + r.width * .08 || r.top < c.top - r.height * .08 || r.bottom > c.bottom + r.height * .08; }).length; }''')
            if off: print(f'⚠ {c["out"]}：有 {off} 张猫贴纸超出卡片边缘，调小 h 或挪 x/y', file=sys.stderr)
            over = pg.evaluate('''() => { const c = document.getElementById('card').getBoundingClientRect(); return [...document.querySelectorAll('#card *')].filter(e => e.children.length === 0 && e.textContent.trim()).some(e => { const r = e.getBoundingClientRect(); return r.bottom > c.bottom + 1 || r.right > c.right + 1; }); }''')
            marks = pg.evaluate('''([w,h]) => [...document.querySelectorAll('.mk')].map((e,i) => { const rs = [...e.getClientRects()]; const x0 = Math.min(...rs.map(r=>r.left)), y0 = Math.min(...rs.map(r=>r.top)), x1 = Math.max(...rs.map(r=>r.right)), y1 = Math.max(...rs.map(r=>r.bottom));
                return {i, text: e.textContent, rect: [x0/w, y0/h, (x1-x0)/w, (y1-y0)/h].map(v => Math.round(v*1e4)/1e4)}; })''', [w, h])
            out = (base / c['out']).with_suffix('.png'); out.parent.mkdir(parents=True, exist_ok=True)
            pg.locator('#card').screenshot(path=str(out))
            srcs = sorted(set(cx['sources'])) if cx else ([str(Path(c['image']).resolve())] if c['type'] == 'cover' and c.get('image') else [])
            out.with_suffix('.json').write_text(json.dumps({'type': c['type'], 'w': w, 'h': h, 'marks': marks, 'sources': srcs}, ensure_ascii=False, indent=1))
            print(f'{out}  {w}x{h}  marks={[m["text"] for m in marks]}' + ('  ⚠ 有文字出了卡片边界，删字或拆卡' if over else ''))
            pg.close()
        b.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('cards')
    ap.add_argument('--theme', default='vox', choices=list(PALETTES))
    a = ap.parse_args()
    f = Path(a.cards).resolve(); d = json.loads(f.read_text())
    cards = d if isinstance(d, list) else [d]
    for c in cards:
        if 'type' not in c or 'out' not in c: raise SystemExit(f'每张卡要有 type 和 out：{c}')
    render(cards, f.parent, a.theme)


if __name__ == '__main__':
    main()
