#!/usr/bin/env python3
"""把猫从照片里抠出来（透明底 PNG），给角色剧照卡（make_card.py 的 scene）当贴纸用。

uv run --with "rembg[cpu]" --with pillow python cutout.py <图1> [<图2> ...] [--out <目录>] [--pad 0.04]

- 输出 <原名>_抠图.png（裁到猫的边缘，四周留一点边），默认放在原图旁边；原图的署名自动抄进输出目录的 credits.json。
- 抠图模型 u2net（约 176MB）第一次用时下载到 ~/.u2net/。rembg 自带的下载器在部分网络下会卡住不动（2026-10 实测卡了 11 分钟），
  所以这里先用 urllib 自己下好再交给 rembg。之后每张约 5–15 秒（CPU）。
- 抠完用 Read 看一眼：毛发边缘、胡须会丢一点，没关系（贴纸会加白边、转网点）；如果把背景里的东西也抠进来了，换一张图。
"""
import argparse, json, os, sys, urllib.request
from pathlib import Path

MODEL_URL = 'https://github.com/danielgatis/rembg/releases/download/v0.0.0/u2net.onnx'


def ensure_model():
    home = Path(os.environ.get('U2NET_HOME', Path.home() / '.u2net'))
    f = home / 'u2net.onnx'
    if f.exists() and f.stat().st_size > 170_000_000:
        return
    home.mkdir(parents=True, exist_ok=True)
    part = f.with_suffix('.part')
    print('第一次使用：下载抠图模型 u2net（约 176MB）…', flush=True)
    with urllib.request.urlopen(urllib.request.Request(MODEL_URL, headers={'User-Agent': 'cat-social-psych-skill'}), timeout=60) as r, open(part, 'wb') as out:
        total, done = int(r.headers.get('Content-Length') or 0), 0
        while chunk := r.read(1 << 20):
            out.write(chunk); done += len(chunk)
            if total and done % (20 << 20) < (1 << 20): print(f'  {done >> 20}/{total >> 20} MB', flush=True)
    part.replace(f)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('images', nargs='+')
    ap.add_argument('--out', help='输出目录（默认和原图同目录）')
    ap.add_argument('--pad', type=float, default=0.04, help='裁切时四周留白（相对猫的大小）')
    ap.add_argument('--max', type=int, default=1600, help='输入先缩到这个长边，太大的图抠得慢')
    a = ap.parse_args()
    ensure_model()
    from rembg import new_session, remove
    from PIL import Image
    sess = new_session('u2net')
    for src in map(Path, a.images):
        outdir = Path(a.out) if a.out else src.parent
        outdir.mkdir(parents=True, exist_ok=True)
        dst = outdir / f'{src.stem}_抠图.png'
        im = Image.open(src).convert('RGB'); im.thumbnail((a.max, a.max))
        cut = remove(im, session=sess)
        box = cut.getchannel('A').point(lambda v: 255 if v > 24 else 0).getbbox()
        if not box:
            print(f'⚠ {src.name}：没抠出东西，换一张图', file=sys.stderr); continue
        pw, ph = int((box[2] - box[0]) * a.pad), int((box[3] - box[1]) * a.pad)
        box = (max(0, box[0] - pw), max(0, box[1] - ph), min(cut.width, box[2] + pw), min(cut.height, box[3] + ph))
        cut.crop(box).save(dst)
        if max(box[2] - box[0], box[3] - box[1]) < 700:
            print(f'⚠ {dst.name} 只有 {box[2] - box[0]}x{box[3] - box[1]}：猫在原图里太小，放大后会糊。换一张猫占满画面的图', file=sys.stderr)
        # 署名：抠图是对原图的改编，CC BY / BY-SA 照样要署名
        sc = src.parent / 'credits.json'
        if sc.exists():
            c = json.loads(sc.read_text()).get(src.name)
            if c:
                dc = outdir / 'credits.json'
                d = json.loads(dc.read_text()) if dc.exists() else {}
                d[dst.name] = {**c, 'title': c.get('title', '') + '（抠图）'}
                dc.write_text(json.dumps(d, ensure_ascii=False, indent=1))
        print(f'{dst}  {cut.crop(box).size[0]}x{cut.crop(box).size[1]}')


if __name__ == '__main__':
    main()
