#!/usr/bin/env python3
"""从网上找免费、可商用的素材：Wikimedia Commons 的真实照片 ＋ Openverse 的照片和插画。下载到项目，写署名清单，出带编号的预览图。

uv run --with pillow python fetch_images.py "sleeping" --coat ragdoll --out <集目录>/素材/图
     [--coat ragdoll|bicolor|mainecoon|black|white|tabby|tuxedo] [--source auto|all|commons|openverse] [--kind photo|illustration|any] [--n 12] [--min-side 900] [--no-cat] [--no-sheet]

- 主角的照片优先用用户自己的（角色库）。自己的照片不够时，用 --coat 找同品种的替身，query 只写动作或表情：staring、hiding、yawning、sitting、looking up。
- 关键词用英文（两个库的描述大多是英文）。
  动作词在标题里不一定有，搜不到就只写一个词或者留空字符串 ""。
- 默认只找有猫的图：Commons 加结构化筛选「画面里有家猫」，Openverse 在关键词里补 cat。找道具、场景、插画背景时加 --no-cat。
- --kind illustration 只要插画、版画、复古插图（Openverse 的 illustration / digitized_artwork），适合做拼贴、背景、配角。
- 只留能商用、能改的授权：CC0、公有领域、CC BY、CC BY-SA。CC BY/BY-SA 要署名，build_episode.py 会把用到的图的署名写进发布文案。
- 标题、描述、标签里有交配、死亡、受伤、捕猎、裸露等词的图自动跳过；每张图都打印原标题，挑图时要看——缩略图看不出的问题常写在标题里。
- 文件名：<关键词>_c01（Commons）/ _o01（Openverse）；同一目录多次运行会累加，同一张图不会重复下载；署名合并进 <out>/credits.json。
- 预览图 <out>/预览_<关键词>.jpg，编号与文件名对应。用 Read 看预览挑图。
"""
import argparse, base64, html, json, re, sys, time, urllib.parse, urllib.request
from pathlib import Path

UA = 'cat-social-psych-skill/1.1 (educational short-video tool; python urllib)'
COMMONS = 'https://commons.wikimedia.org/w/api.php'
OPENVERSE = 'https://api.openverse.org/v1/images/'
# 缩略图看不出来、发到抖音会出事的图（2026-10 实测：一张「离群的猫」原标题是 Cats having sex）
BAD_WORDS = re.compile(r'\b(sex\w*|mating|mate|copulat\w*|dead|death|corpse|carcass|roadkill|injur\w*|wound\w*|blood\w*|abuse\w*|surgery|necrop\w*|euthan\w*|slaughter\w*|meat|eaten|killing|kills?|prey|hunting|nude|naked|erotic\w*|gore|vomit\w*|feces|poop)\b', re.I)
NO_SA = False   # --no-sa：不要 CC BY-SA（用在视频里会牵涉「相同方式共享」，做像素背景时都加上）
OK_LIC = re.compile(r'^(CC0|Public domain|PD|CC BY(-SA)? \d(\.\d)?( [A-Za-z\-]+)?)', re.I)
IMG_EXT = ('.jpg', '.jpeg', '.png', '.webp')
# 角色花色 → 检索条件。Commons 按文件标题筛（关键词检索不管毛色；deepcat 不稳定、还会被限流），Openverse 按关键词
COATS = {
    'black':  ('intitle:"black cat" haswbstatement:P180=Q146', 'black cat'),   # 只按标题会混进叫 Black Cat 的酒吧、杂志、cosplay 真人
    'white':  ('intitle:"white cat" -intitle:black haswbstatement:P180=Q146', 'white cat'),
    'tabby':  ('intitle:tabby haswbstatement:P180=Q146', 'tabby cat'),        # 只按标题会混进叫 tabby 的蝴蝶
    'tuxedo': ('intitle:tuxedo intitle:cat haswbstatement:P180=Q146', 'tuxedo cat'),
    # 三个主角的替身（自己的照片不够用时）：大比＝布偶，胜利＝长毛白底虎斑，大宝＝缅因
    'ragdoll':   ('intitle:ragdoll haswbstatement:P180=Q146', 'ragdoll cat'),
    'bicolor':   ('intitle:"tabby and white" haswbstatement:P180=Q146', 'long hair tabby and white cat'),
    'mainecoon': ('intitle:"maine coon" haswbstatement:P180=Q146', 'maine coon cat'),
}


def get(url, binary=False, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            with urllib.request.urlopen(req, timeout=40) as r:
                data = r.read()
                return data if binary else json.loads(data)
        except Exception:  # 429 / 网络抖动：退避重试
            if i == tries - 1:
                raise
            time.sleep(2 * (i + 1))


def strip_html(s):
    return html.unescape(re.sub(r'<[^>]+>', '', s or '')).strip()


def slug(s):
    return re.sub(r'[^0-9A-Za-z一-鿿]+', '_', s).strip('_')[:40] or 'img'


def commons(q, n, cat, min_side, kind, coat=None):
    query = (COATS[coat][0] + ' ' + q) if coat else q + (' haswbstatement:P180=Q146' if cat else '') + (' filetype:bitmap' if kind != 'illustration' else ' filetype:bitmap illustration')
    params = {'action': 'query', 'generator': 'search', 'gsrsearch': query, 'gsrnamespace': 6, 'gsrlimit': min(50, n * 4),
              'prop': 'imageinfo', 'iiprop': 'url|extmetadata|size|mime', 'iiurlwidth': 1600,
              'iiextmetadatafilter': 'LicenseShortName|Artist|LicenseUrl|ImageDescription', 'format': 'json'}
    d = get(COMMONS + '?' + urllib.parse.urlencode(params))
    out = []
    for p in sorted(d.get('query', {}).get('pages', {}).values(), key=lambda p: p.get('index', 0)):
        ii = (p.get('imageinfo') or [{}])[0]; m = ii.get('extmetadata', {})
        lic = (m.get('LicenseShortName') or {}).get('value', '')
        if BAD_WORDS.search(p['title']) or BAD_WORDS.search(strip_html((m.get('ImageDescription') or {}).get('value', ''))): continue
        if not OK_LIC.match(lic) or re.search(r'\b(NC|ND)\b', lic) or (NO_SA and re.search(r'\bSA\b', lic)): continue
        if min(ii.get('width', 0), ii.get('height', 0)) < min_side or ii.get('mime') not in ('image/jpeg', 'image/png', 'image/webp'): continue
        out.append({'src': 'c', 'title': p['title'].removeprefix('File:'), 'url': ii.get('thumburl') or ii.get('url'), 'page': ii.get('descriptionurl'),
                    'license': lic, 'license_url': (m.get('LicenseUrl') or {}).get('value', ''), 'site': 'Wikimedia Commons',
                    'author': strip_html((m.get('Artist') or {}).get('value', '')) or '佚名', 'w': ii['width'], 'h': ii['height']})
        if len(out) >= n: break
    return out


def openverse_license(r):
    l, v = (r.get('license') or '').lower(), r.get('license_version') or ''
    if l == 'cc0': return 'CC0'
    if l in ('pdm', 'pd'): return 'Public domain'
    return f'CC {l.upper()} {v}'.strip()


def openverse(q, n, cat, min_side, kind, coat=None):
    if coat: q = COATS[coat][1] + ' ' + q
    elif cat and 'cat' not in q.lower().split(): q += ' cat'
    params = {'q': q, 'license_type': 'commercial,modification', 'page_size': min(40, n * 3), 'mature': 'false'}
    if kind == 'photo': params['category'] = 'photograph'
    elif kind == 'illustration': params['category'] = 'illustration,digitized_artwork'
    d = get(OPENVERSE + '?' + urllib.parse.urlencode(params))
    out = []
    for r in d.get('results', []):
        tags = ' '.join(t.get('name', '') for t in (r.get('tags') or []))
        if r.get('mature') or BAD_WORDS.search(r.get('title') or '') or BAD_WORDS.search(tags): continue
        lic = openverse_license(r)
        if not OK_LIC.match(lic) or re.search(r'\b(NC|ND)\b', lic, re.I) or (NO_SA and re.search(r'\bSA\b', lic, re.I)): continue
        ft = (r.get('filetype') or Path(urllib.parse.urlparse(r['url']).path).suffix.lstrip('.') or 'jpg').lower()
        if ft not in ('jpg', 'jpeg', 'png', 'webp'): continue
        w, h = r.get('width') or 0, r.get('height') or 0
        if w and h and min(w, h) < min_side: continue
        out.append({'src': 'o', 'title': r.get('title') or '无题', 'url': r['url'], 'thumb': r.get('thumbnail'), 'page': r.get('foreign_landing_url') or r.get('detail_url'),
                    'license': lic, 'license_url': r.get('license_url') or '', 'site': f'Openverse / {r.get("source", "")}',
                    'author': r.get('creator') or '佚名', 'w': w, 'h': h, 'ext': '.png' if ft == 'png' else '.jpg'})
        if len(out) >= n: break
    return out


def contact_sheet(files, dest):
    """带编号的缩略图拼版：有 Pillow 就用 Pillow（轻），否则用 Playwright 截图。"""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return _sheet_playwright(files, dest)
    cells = []
    for f in files:
        im = Image.open(f).convert('RGB'); im.thumbnail((300, 300)); c = Image.new('RGB', (300, 300), (17, 17, 17))
        c.paste(im, ((300 - im.width) // 2, (300 - im.height) // 2)); d = ImageDraw.Draw(c)
        tag = Path(f).stem.rsplit('_', 1)[-1]; d.rectangle([6, 6, 18 + 12 * len(tag), 30], fill=(255, 216, 77)); d.text((12, 10), tag, fill=(0, 0, 0))
        cells.append(c)
    rows = (len(cells) + 3) // 4; sheet = Image.new('RGB', (4 * 308 + 8, rows * 308 + 8), (34, 34, 34))
    for k, c in enumerate(cells): sheet.paste(c, (8 + (k % 4) * 308, 8 + (k // 4) * 308))
    sheet.save(dest, quality=80)


def _sheet_playwright(files, dest):
    from playwright.sync_api import sync_playwright
    uri = lambda f: f'data:image/{"png" if f.suffix == ".png" else "jpeg"};base64,' + base64.b64encode(f.read_bytes()).decode()
    cells = ''.join(f'<div class=c><img src="{uri(Path(f))}"><b>{Path(f).stem.rsplit("_", 1)[-1]}</b></div>' for f in files)
    page = f'''<html><body style="margin:0;background:#222"><div style="display:grid;grid-template-columns:repeat(4,300px);gap:8px;padding:8px;width:1232px">{cells}</div>
<style>.c{{position:relative;width:300px;height:300px;background:#111}}.c img{{width:100%;height:100%;object-fit:contain}}
.c b{{position:absolute;left:6px;top:6px;background:#ffd84d;font:700 26px sans-serif;padding:2px 10px;border-radius:6px}}</style></body></html>'''
    with sync_playwright() as p:
        b = p.chromium.launch(); pg = b.new_page(viewport={'width': 1248, 'height': 400})
        pg.set_content(page); pg.wait_for_load_state('networkidle')
        pg.screenshot(path=str(dest), full_page=True, type='jpeg', quality=80); b.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('query', help='英文关键词，如 "black cat staring" "tabby cat hiding" "vintage office illustration"')
    ap.add_argument('--out', required=True)
    ap.add_argument('--source', default='auto', choices=['auto', 'all', 'commons', 'openverse'], help='auto：照片走 Commons（按花色准），插画走 Openverse（插画多），any 两个都搜')
    ap.add_argument('--kind', default='photo', choices=['photo', 'illustration', 'any'])
    ap.add_argument('--n', type=int, default=12, help='最多下载几张（多个来源合计）')
    ap.add_argument('--min-side', type=int, default=None, help='短边至少多少像素；默认照片 900、插画 600')
    ap.add_argument('--no-cat', action='store_true', help='不限定画面里有猫（找道具、场景、背景时用）')
    ap.add_argument('--coat', choices=list(COATS), help='按花色或品种找：ragdoll 大比的替身 / bicolor 胜利的替身 / mainecoon 大宝的替身，也可 black / white / tabby / tuxedo；query 只写动作表情')
    ap.add_argument('--no-sheet', action='store_true')
    ap.add_argument('--no-sa', action='store_true', help='排除 CC BY-SA，只要 CC0 / 公有领域 / CC BY（做视频背景时加上）')
    a = ap.parse_args()
    global NO_SA; NO_SA = a.no_sa
    min_side = a.min_side or (600 if a.kind == 'illustration' else 900)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    cred_f = out / 'credits.json'
    credits = json.loads(cred_f.read_text()) if cred_f.exists() else {}
    have = {c.get('url') for c in credits.values()}
    hits = []
    if a.source == 'auto': a.source = {'photo': 'commons', 'illustration': 'openverse'}.get(a.kind, 'all')
    srcs = ['commons', 'openverse'] if a.source == 'all' else [a.source]
    per = a.n if len(srcs) == 1 else (a.n + 1) // 2
    for s in srcs:
        try:
            hits += (commons if s == 'commons' else openverse)(a.query, per, not a.no_cat, min_side, a.kind, a.coat)
        except Exception as e:
            print(f'⚠ {s} 搜索失败：{e}', file=sys.stderr)
    if not hits:
        sys.exit(f'没搜到合用的图：「{a.query}」。换个说法、减少关键词、换 --source，或加 --no-cat。')
    base, got, k = slug((a.coat + ' ' if a.coat else '') + a.query), [], {'c': 0, 'o': 0}
    for h in hits:
        if h['url'] in have:
            continue
        while True:
            k[h['src']] += 1
            f = out / f'{base}_{h["src"]}{k[h["src"]]:02d}{h.get("ext", ".png" if h["url"].split("?")[0].lower().endswith(".png") else ".jpg")}'
            if not f.exists(): break
        try:
            data = get(h['url'], binary=True)
        except Exception:
            if not h.get('thumb'): continue
            try: data = get(h['thumb'], binary=True)
            except Exception: continue
        if len(data) < 8000: continue        # 占位图、错误页
        f.write_bytes(data); time.sleep(0.3)
        credits[f.name] = {kk: h[kk] for kk in ('title', 'author', 'license', 'license_url', 'page', 'site', 'url')}
        got.append(f)
        print(f'{f.name}  {h["w"]}x{h["h"]}  {h["license"]}  {h["author"][:24]}  ｜原标题：{h["title"][:80]}')
    cred_f.write_text(json.dumps(credits, ensure_ascii=False, indent=1))
    if not got:
        sys.exit('搜到的图都已经下载过了，换个关键词。')
    if not a.no_sheet:
        sheet = out / f'预览_{base}.jpg'; contact_sheet(got, sheet); print('预览 ->', sheet)
    print(f'署名清单 -> {cred_f}（CC BY / BY-SA 发布时要署名）')


if __name__ == '__main__':
    main()
