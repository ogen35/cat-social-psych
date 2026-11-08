"""把 AI 出的道具图（3×3 等网格，透明底或纯白底）切开、去底、像素化，存进道具库。

用法：python import_sheet.py 图.png 名字1,名字2,…,名字9 [--out 道具库目录] [--size 56] [--cols 3] [--style pixel|line]
  --style line：线条画风（STYLE='line' 的集数用）。不像素化，保留高清抠图，最长边 --size（默认 360 像素），存到 assets/道具库_线条
  - 按网格读出物件：先找前景连通块，再按所在格子归位（一格一件，碎块并进同一格）
  - 像素化：最长边缩到 --size 逻辑像素（BOX 采样），alpha 二值化，调色到 ≤16 色、不抖动
  - 外圈补一圈深色描边，压在照片背景上也清楚
  - 出一张 _检查.png 对照表，人工看一眼再用
"""
import argparse, json, sys
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

INK = (36, 32, 44)


def foreground(im):
    a = np.array(im.convert('RGBA')).astype(np.int16)
    if (a[:, :, 3] < 250).mean() > 0.2:                      # 真透明底
        return a[:, :, 3] > 100
    rgb = a[:, :, :3]; nearw = (rgb.min(2) > 232) & (rgb.max(2) - rgb.min(2) < 18)
    lab, n = ndi.label(nearw)                                 # 只去掉和边框连着的白：物件里的白色（白飞机）保留
    edge = set(np.unique(np.r_[lab[0], lab[-1], lab[:, 0], lab[:, -1]])) - {0}
    return ~np.isin(lab, list(edge))


def pixelize(rgba, size, colors=16):
    im = Image.fromarray(rgba)
    w, h = im.size; k = size / max(w, h)
    nw, nh = max(1, round(w * k)), max(1, round(h * k))
    small = im.resize((nw, nh), Image.BOX)
    a = np.array(small); alpha = a[:, :, 3] > 110
    rgb = Image.fromarray(a[:, :, :3]).quantize(colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert('RGB')
    out = np.zeros((nh + 2, nw + 2, 4), np.uint8)
    out[1:-1, 1:-1, :3] = np.array(rgb); out[1:-1, 1:-1, 3] = np.where(alpha, 255, 0)
    m = out[:, :, 3] > 0; P = np.pad(m, 1)
    ring = (P[:-2, 1:-1] | P[2:, 1:-1] | P[1:-1, :-2] | P[1:-1, 2:]) & ~m
    out[ring, :3] = INK; out[ring, 3] = 255
    return out


def clean_line(rgba, size):
    """线条道具：保留原图的柔和透明边，裁到物件边框，最长边缩到 size 像素。"""
    im = Image.fromarray(rgba)
    k = min(1.0, size / max(im.size))
    if k < 1: im = im.resize((max(1, round(im.width * k)), max(1, round(im.height * k))), Image.LANCZOS)
    return np.array(im)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('sheet'); ap.add_argument('names')
    ap.add_argument('--out', default=None); ap.add_argument('--style', default='pixel', choices=['pixel', 'line'])
    ap.add_argument('--size', type=int, default=0); ap.add_argument('--cols', type=int, default=3); ap.add_argument('--rows', type=int, default=0)
    ap.add_argument('--source', default='')
    a = ap.parse_args()
    line = a.style == 'line'
    a.size = a.size or (360 if line else 56)
    a.out = a.out or str(Path(__file__).resolve().parents[2] / 'assets' / ('道具库_线条' if line else '道具库'))
    names = [x.strip() for x in a.names.split(',')]
    cols = a.cols; rows = a.rows or -(-len(names) // cols)
    im = Image.open(a.sheet).convert('RGBA'); A = np.array(im); fg = foreground(im)
    fg = ndi.binary_opening(fg, iterations=1)
    H, W = fg.shape; cw, ch = W / cols, H / rows
    lab, n = ndi.label(ndi.binary_dilation(fg, iterations=3))
    cells = {}
    for i, sl in enumerate(ndi.find_objects(lab), 1):
        if sl is None: continue
        ys, xs = sl; area = (lab[sl] == i).sum()
        if area < 0.0015 * H * W: continue                     # 碎渣
        cy, cx = (ys.start + ys.stop) / 2, (xs.start + xs.stop) / 2
        key = (min(rows - 1, int(cy // ch)), min(cols - 1, int(cx // cw)))
        cells.setdefault(key, []).append(sl)
    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    meta_p = out / 'index.json'; meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
    tiles = []
    for idx, name in enumerate(names):
        key = (idx // cols, idx % cols)
        if key not in cells: print(f'⚠️ 第 {idx + 1} 格（{name}）没找到物件'); continue
        y0 = min(s[0].start for s in cells[key]); y1 = max(s[0].stop for s in cells[key])
        x0 = min(s[1].start for s in cells[key]); x1 = max(s[1].stop for s in cells[key])
        crop = A[y0:y1, x0:x1].copy()
        if line:
            keep = ndi.binary_dilation(fg[y0:y1, x0:x1], iterations=2)
            crop[:, :, 3] = np.where(keep, crop[:, :, 3] if (A[:, :, 3] < 250).mean() > 0.2 else 255, 0)
            px = clean_line(crop, a.size)
        else:
            crop[:, :, 3] = np.where(fg[y0:y1, x0:x1], 255, 0)
            px = pixelize(crop, a.size)
        Image.fromarray(px).save(out / f'{name}.png')
        meta[name] = dict(w=px.shape[1], h=px.shape[0], source=a.source or Path(a.sheet).name)
        tiles.append((name, px))
        print(f'  {name:<10} {px.shape[1]}×{px.shape[0]}')
    meta_p.write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    if tiles:                                                  # 对照表：每件放大 4 倍，铺在浅底上
        z = 0.5 if line else 4
        cs = int((a.size + 6) * z); sheet = Image.new('RGB', (cs * min(len(tiles), 6), cs * (-(-len(tiles) // 6))), (236, 230, 216))
        for k, (name, px) in enumerate(tiles):
            t = Image.fromarray(px).resize((max(1, int(px.shape[1] * z)), max(1, int(px.shape[0] * z))), Image.LANCZOS if line else Image.NEAREST)
            sheet.paste(t, ((k % 6) * cs + (cs - t.width) // 2, (k // 6) * cs + (cs - t.height) // 2), t)
        sheet.save(Path(a.sheet).with_name(Path(a.sheet).stem + '_检查.png'))


if __name__ == '__main__':
    main()
