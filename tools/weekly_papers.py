#!/usr/bin/env python3
"""每週泌尿科新論文摘要：PubMed 抓近 N 天 → 便宜模型挑選並摘要 → digests/YYYY-MM-DD.md

用法：python3 tools/weekly_papers.py [--days 7] [--top 12] [--out digests]
期刊清單改 JOURNALS；摘要只依 abstract，不得補充數字（符合 AGENTS.md 出處規範）。
"""
import argparse, datetime, json, os, sys, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(__file__))
from ai_dispatch import call

JOURNALS = ["Eur Urol", "J Urol", "BJU Int", "Urology", "Eur Urol Oncol",
            "Eur Urol Focus", "Prostate Cancer Prostatic Dis", "World J Urol",
            "Urol Oncol", "Neurourol Urodyn", "J Endourol", "Int J Impot Res"]
EU = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/"

def get(url):
    with urllib.request.urlopen(url, timeout=120) as r:
        return r.read()

def search(days):
    term = "(" + " OR ".join(f'"{j}"[jour]' for j in JOURNALS) + ")"
    q = urllib.parse.urlencode({"db": "pubmed", "retmode": "json", "retmax": 80,
                                "reldate": days, "datetype": "edat", "term": term})
    return json.loads(get(EU + "esearch.fcgi?" + q))["esearchresult"]["idlist"]

def fetch(ids):
    q = urllib.parse.urlencode({"db": "pubmed", "retmode": "xml", "id": ",".join(ids)})
    out = []
    for a in ET.fromstring(get(EU + "efetch.fcgi?" + q)).iter("PubmedArticle"):
        abst = " ".join("".join(t.itertext()) for t in a.iter("AbstractText"))
        if not abst:
            continue
        out.append({"pmid": a.findtext(".//PMID"),
                    "title": "".join(a.find(".//ArticleTitle").itertext()),
                    "journal": a.findtext(".//Journal/ISOAbbreviation"),
                    "abstract": abst[:1800]})
    return out

PROMPT = """你是泌尿科期刊速讀助理。以下是本週 PubMed 新文章（含摘要）。
請挑出最值得臨床泌尿科醫師閱讀的 {top} 篇（優先：RCT、系統性回顧／統合分析、大型世代、改變實務的研究），
每篇用繁體中文輸出：
### 標題（英文原題）
- 期刊｜PMID
- 重點：1–2 句
- 對臨床的意義：1 句
規則：只能依摘要內容，不得補充摘要沒有的數字或結論；摘要沒寫的寫「摘要未載」；不要編造。
最後加一行「共篩選 {n} 篇，挑出 {top} 篇」。

{papers}
"""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--out", default="digests")
    a = ap.parse_args()
    ids = search(a.days)
    papers = fetch(ids) if ids else []
    if not papers:
        sys.exit("本期沒有符合的新文章")
    text = "\n\n".join(f"[PMID {p['pmid']}] {p['journal']}\n{p['title']}\n{p['abstract']}" for p in papers)
    prompt = PROMPT.format(top=a.top, n=len(papers), papers=text)
    for role in ("read", "alt", "draft"):  # 主通道失敗就換下一個
        try:
            body = call(role, prompt)
            break
        except Exception as e:
            print(f"{role} 失敗：{e}", file=sys.stderr)
    else:
        sys.exit("所有模型都失敗")
    os.makedirs(a.out, exist_ok=True)
    path = os.path.join(a.out, f"{datetime.date.today()}.md")
    open(path, "w").write(f"# 泌尿科每週新論文 {datetime.date.today()}\n\n{body}")
    print(path)

if __name__ == "__main__":
    main()
