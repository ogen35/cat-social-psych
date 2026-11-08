"""画风模板 v3（天真当代艺术插画）：拼 Style Image V8.2（mj-v8.2）的出图提示词。规则见 references/画风模板.md。

    python3 style_prompt.py character "<角色英文描述，或 大比/胜利/大宝>" [--palette 粉薄荷]
    python3 style_prompt.py scene     "<场景英文描述>"   [--palette 紫黄]
    python3 style_prompt.py prop      "<道具英文描述>"   [--palette 橙绿]
    python3 style_prompt.py shot      "<镜头英文描述（谁在哪做什么）>" [--palette 钴蓝粉]

出图参数：ratio（角色 3:4、场景和镜头 9:16、道具 1:1）、stylize 250、count 4（这个模型固定 4 张）。
参考图是别人的作品：提示词里只写风格的文字描述，不写作者名字。
"""
import argparse

STYLE = ('Naive contemporary art illustration, hand-painted gouache with visible brushstrokes and a subtle colored-pencil texture, '
         'bold flat saturated color blocks in {main} and {accent} with black, white and a touch of red, '
         'wobbly hand-drawn black outlines, simplified quirky geometric shapes, deadpan absurd humor, slightly flattened perspective.')
PALETTE = {'橙绿': ('burnt orange', 'emerald green'), '紫黄': ('violet blue', 'mustard yellow'),
           '粉薄荷': ('hot pink', 'mint green'), '钴蓝粉': ('cobalt blue', 'bubblegum pink')}
CAT_RULE = 'Round eyes with tiny black pupils, deadpan faces, each cat has four legs and one tail.'
NO = '--no text, letters, watermark, 3d render, photo, realistic fur'
CATS = {   # IP 造型 v3（2026-11-07 用户确认：大比 4、胜利 4、大宝 3）；与 flat_clips.H3_CAT 保持一致
    '大比': ('a fluffy ragdoll cat named Dabi with a cream-white pear-shaped body, a dark chocolate-brown face mask, dark brown ears and a long '
             'dark brown tail, a white stripe down the middle of its face, big round blue eyes, a small red heart-shaped tag on its collar, '
             'a shy, worried, deadpan expression'),
    '胜利': ('a round white cat named Shengli with large dark-brown tabby patches (a striped tabby cap on its head and big striped patches on '
             'its back), amber eyes, a puffed-out chest, short legs, a huge bushy striped tail as big as its body, a small red crown worn tilted, '
             'smug half-closed eyes'),
    '大宝': ('the biggest cat, a grey-brown striped Maine Coon named Dabao with an M mark on its forehead, a cream chest ruff, yellow-green eyes, '
             'very tall antenna-like ear tufts, a loaf-shaped body, droopy eyelids and a grumpy, unimpressed deadpan face'),
}
LAYOUT = {
    'character': 'Character design: full body, front view, plain background in the main color, a small potted plant beside it, a simple patterned floor strip.',
    'scene': ('An empty room seen from the front at eye level, no animals and no people; furniture, potted plants, framed abstract paintings and '
              'patterns; the floor starts at about 60% of the image height and the lower quarter is patterned floor.'),
    'prop': 'A single object, centered, plain background in the main color, nothing else in the image.',
    'shot': 'Vertical 9:16 frame; the cats stay in the upper three quarters and the lower quarter shows the patterned floor.',
}
DEFAULT_PALETTE = {'character': '粉薄荷', 'scene': '紫黄', 'prop': '橙绿', 'shot': '紫黄'}


def build(kind, subject, palette=None, extra=''):
    main, accent = PALETTE[palette or DEFAULT_PALETTE[kind]]
    subject = CATS.get(subject, subject)
    parts = [STYLE.format(main=main, accent=accent), subject.rstrip('.') + '.']
    if kind in ('character', 'shot'): parts.append(CAT_RULE)
    parts.append(LAYOUT[kind])
    if extra: parts.append(extra)
    return ' '.join(parts) + ' ' + NO


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('kind', choices=list(LAYOUT)); ap.add_argument('subject')
    ap.add_argument('--palette', choices=list(PALETTE)); ap.add_argument('--extra', default='')
    a = ap.parse_args()
    print(build(a.kind, a.subject, a.palette, a.extra))
