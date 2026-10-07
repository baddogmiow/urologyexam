#!/usr/bin/env python3
"""把口試簡報 (.pptx) 轉成口試練習頁的匯入格式。

一個 Case（一大題）一筆，格式與網頁相同：
  Q: 【領域｜Case 名稱】病例：... （第一題）題目 （第二題）題目 ...
  A: ■ 第一題
     詳解...
     【給分點】...
     【出處】...
     ■ 第二題 ...

用法：
  python tools/pptx_to_oral.py 簡報資料夾\\ --domain "01 結石" > oral_結石.txt
  python tools/pptx_to_oral.py a.pptx b.pptx --domain "03 腎臟輸尿管膀胱腫瘤" > oral_腫瘤.txt

--domain 是這批簡報所屬的領域（網頁會依它歸類到 10 個領域）。
領域：01 結石、02 前列腺疾病含癌症、03 腎臟輸尿管膀胱腫瘤、04 腎上腺&外生殖器腫瘤、
      06 排尿功能障礙&女性泌尿、07 男性學、08 小兒泌尿、09 移植、10 感染、11 外傷
不同領域的簡報請分開執行，再把產出的檔案合併。

辨識規則（依常見簡報結構）：
  - 首行以「Case」開頭的投影片 = 病例敘述，會放在該 Case 的 Q 前面
  - 首行為「第N題」的投影片 = 題目
  - 首行為「第N題: 標題」的投影片 = 詳解，「Checkpoint:」之後是給分點，
    其餘含 edition / doi / PMID / guideline 的短行當成出處
  - 圖片不轉換，只標示張數，請回簡報對照
沒有標出處的小題會標「待查（簡報未標示）」。轉完請抽查幾題與原簡報是否一致。
"""
import argparse
import os
import re
import sys

from pptx import Presentation

NUM = '一二三四五六七八九十'
Q_RE = re.compile(r'^第\s*([0-9一二三四五六七八九十]+)\s*題\s*$')
A_RE = re.compile(r'^第\s*([0-9一二三四五六七八九十]+)\s*題\s*[:：]')
CASE_RE = re.compile(r'^\s*case\b', re.I)
SRC_RE = re.compile(r'doi|PMID|edition|guideline|et al', re.I)


def cn(n):
    """1 -> 一；已經是中文就原樣回傳。"""
    return NUM[int(n) - 1] if str(n).isdigit() and 1 <= int(n) <= 10 else str(n)


def slide_text(slide):
    lines, pics = [], 0
    for sh in slide.shapes:
        if sh.shape_type == 13:
            pics += 1
        if sh.has_text_frame:
            lines += [l.strip() for l in sh.text_frame.text.splitlines() if l.strip()]
        if getattr(sh, 'has_table', False) and sh.has_table:
            for r in sh.table.rows:
                lines.append(' | '.join(c.text.strip() for c in r.cells))
    return lines, pics


def parse(path):
    """回傳 [{label, stem, subs: [{num, q, ans, cp, src, pics}]}]"""
    prs = Presentation(path)
    cases, cur, sub = [], None, None
    for slide in prs.slides:
        lines, pics = slide_text(slide)
        if not lines:
            continue
        head = lines[0]
        if CASE_RE.match(head):
            cur = {'label': re.sub(r'\s+', ' ', head).strip(), 'stem': ' '.join(lines[1:]), 'subs': []}
            cases.append(cur)
            sub = None
            continue
        if cur is None:                      # 沒有 Case 投影片：建立一個預設 Case
            cur = {'label': os.path.splitext(os.path.basename(path))[0], 'stem': '', 'subs': []}
            cases.append(cur)
        m = Q_RE.match(head)
        if m:
            sub = {'num': cn(m.group(1)), 'q': ' '.join(lines[1:]), 'ans': [], 'cp': [], 'src': [], 'pics': 0}
            cur['subs'].append(sub)
            continue
        m = A_RE.match(head)
        if m:
            num = cn(m.group(1))
            target = next((s for s in cur['subs'] if s['num'] == num), None) or sub
            if target is None:
                continue
            sub = target
            sub['pics'] += pics
            in_cp = False
            for l in lines[1:]:
                if re.match(r'^checkpoint\s*[:：]?', l, re.I):
                    in_cp = True
                    rest = re.sub(r'^checkpoint\s*[:：]?\s*', '', l, flags=re.I)
                    if rest:
                        sub['cp'].append(rest)
                elif SRC_RE.search(l) and len(l) < 400:
                    sub['src'].append(l)
                elif in_cp:
                    sub['cp'].append(l)
                else:
                    sub['ans'].append(l)
            continue
        # 續頁（只有圖或出處）：併入最近一題
        if sub is not None:
            sub['pics'] += pics
            for l in lines:
                if SRC_RE.search(l):
                    sub['src'].append(l)
    return cases


def render(case, domain, deck):
    name = case['label']
    head = '【' + (domain + '｜' if domain else '') + name + '】'
    q = head + ('病例：' + case['stem'] + ' ' if case['stem'] else '')
    q += ' '.join('（第%s題）%s' % (s['num'], s['q']) for s in case['subs'])
    blocks = []
    for s in case['subs']:
        a = ['■ 第%s題' % s['num']]
        a += s['ans'] or ['（簡報未提供文字詳解）']
        if s['cp']:
            a.append('【給分點】' + ' '.join(s['cp']))
        a.append('【出處】' + ('；'.join(dict.fromkeys(s['src'])) if s['src'] else '待查（簡報未標示）'))
        if s['pics']:
            a.append('【圖片】詳解頁含 %d 張圖，請回簡報對照' % s['pics'])
        blocks.append('\n'.join(a))
    return 'Q: ' + q + '\nA: ' + '\n\n'.join(blocks)


def main():
    ap = argparse.ArgumentParser(description='口試簡報 -> 口試練習頁匯入格式')
    ap.add_argument('paths', nargs='+', help='.pptx 檔或資料夾')
    ap.add_argument('--domain', default='', help='這批簡報的領域，例如 "01 結石"')
    args = ap.parse_args()
    paths = []
    for a in args.paths:
        if os.path.isdir(a):
            paths += sorted(os.path.join(a, f) for f in os.listdir(a) if f.lower().endswith('.pptx'))
        else:
            paths.append(a)
    if not paths:
        sys.exit('找不到 .pptx 檔')
    out = []
    for p in paths:
        cs = parse(p)
        sys.stderr.write('%s：%d 個 Case、%d 個小題\n' % (os.path.basename(p), len(cs), sum(len(c['subs']) for c in cs)))
        out += [render(c, args.domain, p) for c in cs if c['subs']]
    sys.stderr.write('共 %d 個 Case\n' % len(out))
    if not args.domain:
        sys.stderr.write('提醒：沒有指定 --domain，匯入後會被歸為「未分類」。\n')
    sys.stdout.reconfigure(encoding='utf-8')
    print('\n\n'.join(out))


if __name__ == '__main__':
    main()
