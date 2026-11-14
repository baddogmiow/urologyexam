# 交班紀錄（HANDOFF）

> 規則：對話要結束或重開前，先更新此檔；新對話的第一件事是讀此檔。
> 只保留「目前狀態」，舊的移到文末「歷史」。

## 目前狀態
- 更新時間：2026-11-14
- 更新者：Claude（本機桌面版 session）
- 分支：`claude/claude-md-handoff`（含 CLAUDE.md、HANDOFF.md，尚未合併、尚未 push）；`main` 已含 5f8a683 並已推到遠端

## 2026-11-14 本機 session 進度
- `tools/ai_dispatch.py`：`read` 角色改用本機 agy（Antigravity CLI）；長 prompt（>8000 字元）寫暫存檔讓 agy 讀；找不到 agy／逾時顯示中文錯誤；本機讀環境變數 `OPENROUTER_API_KEY`。已驗證（py_compile、短中文、45k 字元長文、draft 角色），已合併 main 並 push（5f8a683）。
- 新增根目錄 `CLAUDE.md`：多引擎分工（Claude／OpenRouter／agy／Codex）、品質關卡、對話負擔預警（15 輪／8 檔／500 行）。
- 引擎狀態：OpenRouter 可用；agy 可用；Codex 已登入 ChatGPT 官方帳號，但工作區唯讀，改檔與跑指令失敗，需醫師開放沙盒寫入才能派工。GitHub Models 已於 2026-07-30 停用；Gemini API 已不用。
- 桌面版目前走閘道模式（`~/.claude/settings.json` 的 `ANTHROPIC_BASE_URL` 等指向 127.0.0.1:3456）；是否還原為一般登入未決定。
- 竹北租屋每日排程（`zhubei-3br-rental-daily`，本機排程，12:00）已加 OpenRouter／agy 可選步驟；尚未在新版指令下實跑，Gmail 寄信與手機推播的首次核准未驗證。
- 全域 `~/.claude/CLAUDE.md` 的 gy 規則已改為 agy（備份 `CLAUDE.md.bak`）。
- 未 commit／未處理：本機舊分支 `claude/busy-davinci-d6xmss`（速查手冊，見下）。

## 做到哪（2026-11-09）
- 協作骨架（HANDOFF、roles、cards、drafts、AGENTS 規則）、eager-darwin（AI 分派工具、每週論文摘要、BRAIN）、UTF-8 修正，皆已合併進 main。UTF-8 修正是醫師在雲端 session 明確同意（「合併 utf8」）後才推 main。
- 醫師身分轉為已取得專科執照，1/1 起在北港分院服務；門診：週一早上、週三下午、週四早上與下午。repo 用途轉向門診支援。
- 門診速查手冊 v3（結石、血尿、PSA 高、BPH＋LUTS、夜尿、性功能）依 EAU 2026 寫成，放在分支 `claude/busy-davinci-d6xmss` 的 `clinic/index.html`，**尚未合併進 main**。私人網頁連結：https://claude.ai/artifact/AyVUDWiSWk1byb99vMn7Nj
- 醫師的 Windows 電腦（C136390R）已能用 `claude remote-control` 從手機遙控。

## 卡在哪／待醫師核對
- 速查手冊：頁面上約 19 處「待核對」（劑量、AUA 切點、夜間多尿單位 mL/min 疑為 mL/h 筆誤）；醫師核對後才合併。
- AUA 指引全文未讀（AUA 網站禁止用於 AI 工具）。AUA 部分只引公開摘要：微量血尿 2025 修訂、BPH 2023 修訂。需醫師自行貼段落對照。
- EAU 前列腺癌 2026 只讀 Pocket 版（篩檢與切片）；EAU 結石 10 mm 以下輸尿管結石的部位細節在流程圖，未逐項抄入。
- 口試共筆不在 repo 內（在 App 匯入），未對照。
- 未決定：是否建每日排程（檢查 `bot/*` 分支與 `cards/` 待核對）。

## 下一步
1. 醫師核對速查手冊後，決定是否把 `clinic/` 合併進 main。
2. 視需要補 AUA 對照、更多門診主題（UTI、衛教單、病歷範本）。
3. 決定是否建立每日排程。

## 注意事項
- 遙控用的 PowerShell 視窗不能關，電腦不能睡眠；卡住時重啟 `claude remote-control`。
- 不要把可辨識病人的資料貼給任何雲端 AI；院內使用雲端 AI 的規定待確認。
- 雲端 session 的預設環境已加白名單：uroweb.org、EAU PDF 主機（d56bochluxqnz.cloudfront.net）、pubmed.ncbi.nlm.nih.gov（不含 auanet.org）。
- 題庫既有 Case 的題號、順序、已核對詳解不可改。

## 歷史
（舊紀錄貼在這裡）
