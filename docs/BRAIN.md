# 首腦記憶（Claude 總協調用）

> 每次新 session 先讀本檔與 AGENTS.md。目標：**省 Claude token**——Claude 只做判斷、驗收、合併，大量產出交給便宜模型。

## 可用 AI（2026-10-19 實測可呼叫）
| 角色 | 模型 | 通道 | 用途 |
|---|---|---|---|
| draft | deepseek/deepseek-v4.1-flash | OpenRouter | 大量詳解草稿、格式轉換（最便宜） |
| read | gemini-3.8-flash | Gemini API 直連 | 長文閱讀、摘要、pptx/pdf 文字整理 |
| second | x-ai/grok-4.3 | OpenRouter | 第二意見、替代答案 |
| check | openai/gpt-5.5 | OpenRouter | 交叉核對、找矛盾 |
| alt | qwen/qwen3.7-plus | OpenRouter | 中文潤飾、備援 |

- OpenRouter 金鑰額度上限 US$100（測試時已用 $0）；金鑰由 proxy 注入，**不要寫進 repo**。
- 模型 ID 常被下架（gemini-2.5-flash、grok-4-fast、qwen3-235b 都已 404）。失敗先跑 `python3 tools/ai_dispatch.py models` 再改 `tools/ai_dispatch.py` 的 ROLES。
- 呼叫工具：`tools/ai_dispatch.py <role> -i prompt.txt -o out.md`，輸出自動標「（模型 草稿，待核對）」。

## 分工（省 token 原則）
1. **Claude 不做**：整批詳解撰寫、長檔逐行閱讀、重複格式轉換 → 派 draft / read。
2. **Claude 做**：寫派工 prompt（短）、比對差異與矛盾、套用 AGENTS.md 格式規則、合併、維護 `index.html` / `tools/`。
3. **使用者做**：最終醫學核對；口試答案以共筆為準。
4. 派工流程：Claude 寫精簡 prompt → 工具呼叫便宜模型 → 輸出存 `bot/<名字>/<任務>` 分支或暫存檔 → Claude 只讀 diff/摘要，不整份重讀 → 使用者核對 → 合併。
5. 讀 `index.html`（約 1.3MB）時不要整檔 Read，用 Grep/行範圍；大檔交給 `read`（Gemini）摘要。
6. 數字、劑量、LE 等級無出處一律標「待核對」，不採信模型輸出。

## 待辦／備註
- 目前尚未以此流程產出任何題庫內容；首個任務需使用者指定。

## 每週論文摘要
- `python3 tools/weekly_papers.py [--days 7] [--top 12]`：PubMed（eutils，需環境網路白名單）→ 模型挑選並摘要 → `digests/YYYY-MM-DD.md`。
- 模型依序嘗試 read（Gemini）→ alt → draft；Gemini 偶發 502/503。期刊清單在腳本 JOURNALS。
- 摘要只依 abstract，仍須使用者核對；PMID 可回 PubMed 查原文。
