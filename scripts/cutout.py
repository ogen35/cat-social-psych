#!/usr/bin/env python3
"""把猫从照片里抠出来（透明底 PNG），给角色剧照卡（make_card.py 的 scene）当贴纸用。

uv run --with "rembg[cpu]" --with pillow --with scipy python cutout.py <图1> [<图2> ...] [--out <目录>] [--pad 0.04]

- **每只猫单独一个 --out 目录**（素材/抠图/胜利、素材/抠图/大比……）：三只猫的照片同名（01_脸部特写_委屈.jpg），放一个目录会互相覆盖。
- 抠完自动修成剪纸的硬边：只留最大的一块（去掉背景里漏进来的碎片）、补洞、去细毛刺、边缘顺一下。
- 透明度阈值 --alpha 默认 100；大宝这种长毛、身子在阴影里的猫用 --alpha 40（150 会把身子剪掉，只剩一个头）。
  2026-11-09 第 31 期：rembg 的半透明背景雾和小碎片在 Vox 贴纸上会变成一圈圈白边小环。

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


def clean(cut, thr=100):
    """剪纸硬边：alpha 二值化 → 只留最大连通块 → 补洞 → 开运算去毛刺 → 高斯后再二值化（边缘顺）。"""
    import numpy as np
    from PIL import Image
    from scipy import ndimage as nd
    im = np.array(cut.convert('RGBA')); a = im[..., 3] > thr
    def biggest(m):
        lab, n = nd.label(m)
        return m if n <= 1 else lab == (int(np.argmax(nd.sum(m, lab, range(1, n + 1)))) + 1)
    a = biggest(a); a = nd.binary_fill_holes(a)
    a = biggest(nd.binary_opening(a, structure=np.ones((5, 5)), iterations=2))
    im[..., 3] = np.where(nd.gaussian_filter(a.astype(float), 2.0) > 0.5, 255, 0).astype(np.uint8)
    return Image.fromarray(im)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('images', nargs='+')
    ap.add_argument('--out', help='输出目录（默认和原图同目录）')
    ap.add_argument('--pad', type=float, default=0.04, help='裁切时四周留白（相对猫的大小）')
    ap.add_argument('--max', type=int, default=1600, help='输入先缩到这个长边，太大的图抠得慢')
    ap.add_argument('--alpha', type=int, default=100, help='透明度阈值：长毛、深色的猫（大宝）用 40，不然身子会被当成背景剪掉')
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
        cut = clean(cut.crop(box), a.alpha); cut.save(dst); box = (0, 0, cut.width, cut.height)
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
        print(f'{dst}  {cut.width}x{cut.height}')


if __name__ == '__main__':
    main()
