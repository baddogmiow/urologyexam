#!/usr/bin/env python3
"""把低風險、量大的工作派給便宜的 AI，減少 Claude token。

用法：
  python3 tools/ai_dispatch.py <role> -i prompt.txt -o out.md [-s system.txt]
  python3 tools/ai_dispatch.py models          # 列出 OpenRouter 目前可用模型
角色與模型對照見 ROLES；模型常被下架，404 時先跑 `models` 再改這裡。
金鑰：雲端環境由 proxy 注入；本機 Windows 讀環境變數 OPENROUTER_API_KEY。
read 角色走本機 Antigravity CLI（agy），不需要 Gemini 金鑰。本檔不含任何金鑰。
輸出一律加「（<模型> 草稿，待核對）」標註，符合 AGENTS.md。
"""
import argparse, json, os, shutil, subprocess, sys, tempfile, time, urllib.error, urllib.request

ROLES = {
    # role: (provider, model, 用途)
    "draft":  ("openrouter", "deepseek/deepseek-v4.1-flash", "大量詳解草稿、格式轉換（最便宜）"),
    "read":   ("agy",        "agy",                          "長文閱讀、摘要、整理 pptx/pdf 文字（Antigravity CLI）"),
    "second": ("openrouter", "x-ai/grok-4.3",                "第二意見、替代答案"),
    "check":  ("openrouter", "openai/gpt-5.5",               "交叉核對矛盾、查漏"),
    "alt":    ("openrouter", "qwen/qwen3.7-plus",            "中文潤飾、備援"),
}

def auth_headers(url):
    # 雲端環境由 proxy 注入金鑰；本機沒有 proxy 時改讀環境變數（金鑰不寫進檔案）。
    h = {"Content-Type": "application/json"}
    if "openrouter.ai" in url and os.environ.get("OPENROUTER_API_KEY"):
        h["Authorization"] = "Bearer " + os.environ["OPENROUTER_API_KEY"]
    if "googleapis.com" in url and os.environ.get("GEMINI_API_KEY"):
        h["x-goog-api-key"] = os.environ["GEMINI_API_KEY"]
    return h

def post(url, body, tries=4):
    req = urllib.request.Request(url, json.dumps(body).encode(), auth_headers(url))
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
    if provider == "agy":
        # Antigravity CLI 非互動模式；system prompt 併入 prompt 前面。
        exe = os.environ.get("AGY_EXE") or shutil.which("agy") or os.path.expandvars(r"%LOCALAPPDATA%\agy\bin\agy.exe")
        full = (system + "\n\n" if system else "") + prompt
        tmpdir = None
        cmd = [exe, "-p", full, "--print-timeout", "240s"]
        if len(full) > 8000:
            # Windows 命令列上限約 32k 字元：長 prompt 改寫成暫存檔，讓 agy 只讀該檔。
            tmpdir = tempfile.mkdtemp(prefix="agy_prompt_")
            pf = os.path.join(tmpdir, "prompt.txt")
            with open(pf, "w", encoding="utf-8") as f:
                f.write(full)
            ins = (f"Read the file {pf} (the only tool you may use is reading that one file) "
                   "and follow the instructions inside it. Reply with the answer only.")
            cmd = [exe, "-p", ins, "--add-dir", tmpdir, "--print-timeout", "240s"]
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=300)
        except FileNotFoundError:
            raise SystemExit(f"找不到 agy：{exe}。請設定環境變數 AGY_EXE 指向 agy.exe，或把它加進 PATH。")
        except subprocess.TimeoutExpired:
            raise SystemExit("agy 逾時（超過 300 秒）。可縮短輸入再試。")
        finally:
            if tmpdir:
                shutil.rmtree(tmpdir, ignore_errors=True)
        if r.returncode != 0:
            raise SystemExit("agy 失敗：" + r.stderr.decode("utf-8", "replace")[:500])
        text = r.stdout.decode("utf-8", "replace").strip()
        model = "agy"
    elif provider == "gemini":
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
    prompt = open(a.input, encoding="utf-8").read() if a.input else sys.stdin.read()
    system = open(a.system, encoding="utf-8").read() if a.system else None
    out = call(a.role, prompt, system)
    (open(a.output, "w", encoding="utf-8").write(out) if a.output else print(out))

if __name__ == "__main__":
    main()
