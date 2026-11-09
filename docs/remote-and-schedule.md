# 遠端下指令與定時喚醒（備忘）

## 手機遙控（Remote Control）
- 概念：AI 在一台常開的電腦上跑，手機只是遙控。
- 前提：一台常開的 Linux／Mac 電腦、Claude App 的 Code 分頁。
- 設定步驟以官方文件為準（會更動）：Claude App → Settings → Claude Code → Remote Control。
- 注意：電腦睡眠或關機就無法遙控；不要把 API key 放進 repo。

## 讓對話常駐
- 用終端機工作區管理器（tmux 等）開對話，關視窗不中斷。
- 重開機自動回來：用 systemd 啟動該 session；接回後先讀 `HANDOFF.md`。

## 定時喚醒
- 用排程任務定時檢查：是否有新的 `bot/*` 分支、`cards/` 有無「待核對」。
- 有新東西才叫醒總協調；沒有就不打擾。
- 建議頻率：每日一次即可。
