# 交班紀錄（HANDOFF）

> 規則：對話要結束或重開前，先更新此檔；新對話的第一件事是讀此檔。
> 只保留「目前狀態」，舊的移到文末「歷史」。

## 目前狀態
- 更新時間：2026-11-09
- 更新者：Claude（雲端 session）
- 分支：claude/busy-davinci-d6xmss（尚未合併進 main）

## 做到哪
- 新增協作骨架：`HANDOFF.md`、`roles/`、`cards/`、`drafts/`、`docs/remote-and-schedule.md`，並在 `AGENTS.md` 補上交班／單一窗口／草稿確認／工作卡規則。
- 醫師的 Windows 電腦（C136390R）已安裝 Claude Code，`claude remote-control` 可從手機 Code 分頁遙控 `urologyexam`。
- 手機已能讀到本分支的 `HANDOFF.md` 與 `AGENTS.md`。

## 卡在哪／待醫師核對
- 本分支要不要合併進 `main`：待醫師決定。
- `claude/eager-darwin-hbj48i`（AI 分派工具 `tools/ai_dispatch.py`、`tools/weekly_papers.py`、`docs/BRAIN.md`、`digests/`）：與 main 比對顯示 `english/index.html` 在該分支不存在，合併前要先確認不會誤刪，並由醫師核對內容。
- 未決定：是否建立每日排程檢查 `bot/*` 分支與 `cards/` 待核對項。

## 下一步
1. 醫師決定是否合併本分支。
2. 逐一檢查 `eager-darwin-hbj48i` 的內容與差異，再決定怎麼合併。
3. 決定是否建立每日檢查排程（建議每日一次）。

## 注意事項
- 遙控用的 PowerShell 視窗不能關，電腦不能睡眠。
- 題庫既有 Case 的題號、順序、已核對詳解不可改。

## 歷史
（舊紀錄貼在這裡）
