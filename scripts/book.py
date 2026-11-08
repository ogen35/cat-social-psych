#!/usr/bin/env python3
"""查书：《社会心理学》（第11版）扫描版 PDF 的目录、OCR、检索、读页、看图。

  B="uv run --with pymupdf --with rapidocr_onnxruntime python $S/scripts/book.py"
  $B toc                                  章节表：每章的 PDF 页码范围和书上的页码
  $B search 从众 [--chapter 6] [--n 20]   在 OCR 文本里搜关键词，给出页码和上下文（没 OCR 过的页会先 OCR）
  $B read --pages 222-224                 读几页的全文（PDF 页码；缺的先 OCR）
  $B read --book-pages 186-188            同上，用书上印的页码
  $B page 230 [--out 图.png]              把一页渲染成图片（看图表、实验插图、版式），再用 Read 看
  $B ocr --chapter 6 | --pages 221-260 | --all [--jobs 2]   预先 OCR 并缓存

- 书放在 skill 的 `书籍/` 目录（或用 --pdf 指定）。这本是扫描版，没有文字层，文字靠 OCR（RapidOCR，本地运行，不联网）；
  每页约 5 秒，结果缓存在 `书籍/文本/p0222.txt`，只做一次。整本已经 OCR 过时，search 立刻出结果。
- OCR 文本是按版面块拼的：正文、页边栏、图注可能混在一起，个别字会认错。引用书里的数字和原话前，用 `page` 看一眼原图核对。
- 书上印的页码 = PDF 页码 − 偏移（book.json 的 page_offset，正文部分是 36：PDF 第 222 页 = 书上第 186 页）。
"""
import argparse, json, re, sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent


def find_pdf(arg):
    if arg: return Path(arg).resolve()
    for d in (SKILL / '书籍', Path.cwd() / '书籍', Path.cwd().parent / '书籍'):
        pdfs = sorted(d.glob('*.pdf')) if d.is_dir() else []
        if pdfs: return pdfs[0]
    sys.exit('找不到书：把 PDF 放进 skill 的 书籍/ 目录，或用 --pdf 指定。')


def load(pdf):
    import pymupdf
    doc = pymupdf.open(pdf)
    meta_f = pdf.parent / 'book.json'
    meta = json.loads(meta_f.read_text()) if meta_f.exists() else {}
    if 'chapters' not in meta:
        toc = [(lvl, t, p) for lvl, t, p in doc.get_toc()]
        starts = [(t, p) for _, t, p in toc]
        chs = []
        for i, (t, p) in enumerate(starts):
            end = (starts[i + 1][1] - 1) if i + 1 < len(starts) else doc.page_count
            m = re.match(r'第(\d+)章', t)
            chs.append({'title': t, 'chapter': int(m.group(1)) if m else None, 'from': p, 'to': max(p, end)})
        meta = {'pdf': pdf.name, 'pages': doc.page_count, 'page_offset': meta.get('page_offset', 36), 'chapters': chs}
        meta_f.write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    return doc, meta


def cache_dir(pdf):
    d = pdf.parent / '文本'; d.mkdir(exist_ok=True); return d


def txt_path(pdf, pno):
    return cache_dir(pdf) / f'p{pno:04d}.txt'


_ocr = None
def _ocr_page(args):
    """worker：渲染一页 → OCR → 按版面从上到下、从左到右拼成文本。"""
    global _ocr
    pdf, pno = args
    import pymupdf
    from rapidocr_onnxruntime import RapidOCR
    if _ocr is None:
        try: _ocr = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=1)   # 每个进程最多 2 线程：多进程并行时不互相抢 CPU
        except TypeError: _ocr = RapidOCR()
    doc = pymupdf.open(pdf)
    png = doc[pno - 1].get_pixmap(dpi=150).tobytes('png')
    res, _ = _ocr(png)
    lines = []
    for box, text, conf in (res or []):
        y = min(p[1] for p in box); x = min(p[0] for p in box)
        lines.append((round(y / 18), x, text))
    lines.sort()
    out = '\n'.join(t for _, _, t in lines)
    txt_path(Path(pdf), pno).write_text(out)
    return pno, len(out)


def ensure(pdf, pages, jobs=2):
    todo = [p for p in pages if not txt_path(pdf, p).exists()]
    if not todo: return
    print(f'OCR {len(todo)} 页（每页约 5 秒，{jobs} 路并行）…', file=sys.stderr, flush=True)
    if jobs <= 1:
        for k, p in enumerate(todo, 1):
            _ocr_page((str(pdf), p))
            if k % 10 == 0: print(f'  {k}/{len(todo)}', file=sys.stderr, flush=True)
        return
    from multiprocessing import Pool
    with Pool(jobs) as pool:
        for k, _ in enumerate(pool.imap_unordered(_ocr_page, [(str(pdf), p) for p in todo]), 1):
            if k % 20 == 0 or k == len(todo): print(f'  {k}/{len(todo)}', file=sys.stderr, flush=True)


def parse_range(s):
    a, _, b = s.partition('-'); return list(range(int(a), int(b or a) + 1))


def chapter_pages(meta, n):
    for c in meta['chapters']:
        if c['chapter'] == n: return list(range(c['from'], c['to'] + 1)), c
    sys.exit(f'没有第 {n} 章（toc 里看章节表）')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pdf')
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('toc')
    s = sub.add_parser('search'); s.add_argument('q'); s.add_argument('--chapter', type=int); s.add_argument('--n', type=int, default=20); s.add_argument('--context', type=int, default=70)
    r = sub.add_parser('read'); r.add_argument('--pages'); r.add_argument('--book-pages'); r.add_argument('--chapter', type=int)
    g = sub.add_parser('page'); g.add_argument('pno', type=int); g.add_argument('--out'); g.add_argument('--book', action='store_true', help='pno 是书上印的页码'); g.add_argument('--dpi', type=int, default=110)
    o = sub.add_parser('ocr'); o.add_argument('--chapter', type=int); o.add_argument('--pages'); o.add_argument('--all', action='store_true'); o.add_argument('--jobs', type=int, default=2)
    a = ap.parse_args()
    pdf = find_pdf(a.pdf); doc, meta = load(pdf); off = meta['page_offset']
    bp = lambda p: p - off   # PDF 页码 → 书上页码

    if a.cmd == 'toc':
        done = {int(f.stem[1:]) for f in cache_dir(pdf).glob('p*.txt')}
        for c in meta['chapters']:
            n = c['to'] - c['from'] + 1; got = sum(1 for p in range(c['from'], c['to'] + 1) if p in done)
            print(f'{c["title"]:<28} PDF {c["from"]:>3}–{c["to"]:<3}  书页 {bp(c["from"]):>4}–{bp(c["to"]):<4}  OCR {got}/{n}')
    elif a.cmd == 'ocr':
        pages = list(range(1, meta['pages'] + 1)) if a.all else chapter_pages(meta, a.chapter)[0] if a.chapter else parse_range(a.pages)
        ensure(pdf, pages, a.jobs); print('完成')
    elif a.cmd == 'search':
        if a.chapter:
            pages = chapter_pages(meta, a.chapter)[0]; ensure(pdf, pages)
        else:
            pages = sorted(int(f.stem[1:]) for f in cache_dir(pdf).glob('p*.txt'))
            if len(pages) < meta['pages'] * 0.9:
                print(f'⚠ 只有 {len(pages)}/{meta["pages"]} 页 OCR 过，结果可能不全：加 --chapter N 搜指定章（会先 OCR 那一章），或先 ocr --all', file=sys.stderr)
        hits = 0
        for p in pages:
            t = txt_path(pdf, p).read_text().replace('\n', '')
            for m in re.finditer(re.escape(a.q), t):
                s0, s1 = max(0, m.start() - a.context), m.end() + a.context
                ch = next((c['title'] for c in meta['chapters'] if c['from'] <= p <= c['to']), '')
                print(f'[PDF {p} · 书页 {bp(p)} · {ch}] …{t[s0:s1]}…\n')
                hits += 1
                if hits >= a.n: return
        if not hits: print('没搜到。换个说法（书里的译名可能不同），或者先 OCR 相关章节。')
    elif a.cmd == 'read':
        if a.chapter: pages = chapter_pages(meta, a.chapter)[0]
        elif a.book_pages: pages = [p + off for p in parse_range(a.book_pages)]
        else: pages = parse_range(a.pages)
        ensure(pdf, pages)
        for p in pages:
            print(f'===== PDF {p} · 书页 {bp(p)} =====\n{txt_path(pdf, p).read_text()}\n')
    elif a.cmd == 'page':
        p = a.pno + off if a.book else a.pno
        out = Path(a.out or f'/tmp/书页_{p}.png')
        doc[p - 1].get_pixmap(dpi=a.dpi).save(str(out)); print(out)


if __name__ == '__main__':
    main()
