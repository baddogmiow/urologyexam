#!/usr/bin/env python3
"""把低風險、量大的工作派給便宜的 AI，減少 Claude token。

用法：
  python3 tools/ai_dispatch.py <role> -i prompt.txt -o out.md [-s system.txt]
  python3 tools/ai_dispatch.py models          # 列出 OpenRouter 目前可用模型
角色與模型對照見 ROLES；模型常被下架，404 時先跑 `models` 再改這裡。
OpenRouter / Gemini 的金鑰由環境 proxy 注入，本檔不含任何金鑰。
輸出一律加「（<模型> 草稿，待核對）」標註，符合 AGENTS.md。
"""
import argparse, json, sys, time, urllib.error, urllib.request

ROLES = {
    # role: (provider, model, 用途)
    "draft":  ("openrouter", "deepseek/deepseek-v4.1-flash", "大量詳解草稿、格式轉換（最便宜）"),
    "read":   ("gemini",     "gemini-3.8-flash",             "長文閱讀、摘要、整理 pptx/pdf 文字"),
    "second": ("openrouter", "x-ai/grok-4.3",                "第二意見、替代答案"),
    "check":  ("openrouter", "openai/gpt-5.5",               "交叉核對矛盾、查漏"),
    "alt":    ("openrouter", "qwen/qwen3.7-plus",            "中文潤飾、備援"),
}

def post(url, body, tries=4):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    for i in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or i == tries - 1:
                raise
            time.sleep(2 ** (i + 1))

def call(role, prompt, system=None):
    provider, model, _ = ROLES[role]
    if provider == "gemini":
        body = {"contents": [{"parts": [{"text": prompt}]}]}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        d = post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent", body)
        text = "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"])
    else:
        msgs = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
        d = post("https://openrouter.ai/api/v1/chat/completions", {"model": model, "messages": msgs, "max_tokens": 6000})
        text = d["choices"][0]["message"]["content"]
    return f"（{model} 草稿，待核對）\n{text}\n"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("role", choices=list(ROLES) + ["models"])
    ap.add_argument("-i", "--input", help="prompt 檔，省略則讀 stdin")
    ap.add_argument("-s", "--system", help="system prompt 檔")
    ap.add_argument("-o", "--output", help="輸出檔，省略則印到 stdout")
    a = ap.parse_args()
    if a.role == "models":
        with urllib.request.urlopen("https://openrouter.ai/api/v1/models") as r:
            for m in json.load(r)["data"]:
                print(m["id"], m["pricing"]["prompt"], m["pricing"]["completion"])
        return
    prompt = open(a.input).read() if a.input else sys.stdin.read()
    system = open(a.system).read() if a.system else None
    out = call(a.role, prompt, system)
    (open(a.output, "w").write(out) if a.output else print(out))

if __name__ == "__main__":
    main()
