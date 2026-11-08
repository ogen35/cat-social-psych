"""演技表：三只猫 × 姿势 / 表情，外加特效样例。"""
import sys; from pathlib import Path; sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts' / 'pixel'))
import numpy as np
from PIL import Image
import kit, chibi as cb
out = sys.argv[1]
names = ['大比', '胜利', '大宝']
poses = list(cb.POSES); exprs = ['dizzy', 'star', 'blank', 'xx', 'love', 'rage', 'grin', 'sob', 'gloom', 'shock', 'smug', 'cry']
pages = []
# 姿势页：每只猫一行，配合适的表情
pe = {'stand': None, 'cheer': 'grin', 'jump': 'star', 'headhold': 'blank', 'akimbo': 'smug', 'point': 'rage', 'flop': 'xx', 'slump': 'gloom'}
fr = kit.Frame(size=(len(poses) * 46 + 10, 3 * 64 + 26))
for j, n in enumerate(names):
    for i, p in enumerate(poses):
        fr.cat(n, 28 + i * 46, 70 + j * 64, 1 if False else 1, 'front', pe[p], pose=p)
for i, p in enumerate(poses): fr.text(p, (28 + i * 46), 4, 24, kit.INK, stroke=0)
pages.append(fr.render())
fr = kit.Frame(size=(len(exprs) * 34 + 10, 3 * 40 + 26))
for j, n in enumerate(names):
    for i, e in enumerate(exprs):
        fr.cat(n, 22 + i * 34, 50 + j * 40, 1, 'front', e, shadow=False)
for i, e in enumerate(exprs): fr.text(e, 22 + i * 34, 4, 22, kit.INK, stroke=0)
pages.append(fr.render())
for k, im in enumerate(pages): im.save(out.replace('.png', f'_{k}.png'))
# 特效样例（成片尺寸）
T = 0.3
fr = kit.Frame()
fr.focus(135, 230, 70, t=T); fr.burst(135, 230, 80, t=T)
top = fr.cat('大比', 135, 330, 6, 'front', 'blank', pose='headhold'); fr.bolt(210, top - 10, 60); fr.soul('大比', 135, top - 50, 1.0, 0.4, 2)
fr.text('集中线＋爆炸星＋抱头白眼＋闪电＋灵魂出窍', 135, 400, 40, kit.INK)
fr.render().save(out.replace('.png', '_fx1.png'))
fr = kit.Frame()
top = fr.cat('胜利', 80, 300, 5, 'front', 'star', pose='jump', lift=kit.hop(0.21, 0, 30)); fr.sparkles(80, top + 40, 50, T)
top2 = fr.cat('大宝', 200, 300, 4, 'front', 'gloom', pose='slump'); fr.gloom(200, top2 - 26, 70, T)
fr.cat('大比', 135, 420, 4, 'front', 'xx', pose='flop')
fr.text('跳起星星眼＋闪光 / 垂头乌云 / 瘫成一摊', 135, 40, 40, kit.INK)
fr.render().save(out.replace('.png', '_fx2.png'))
print('ok')
