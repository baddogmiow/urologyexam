# AI 內容自動化工具 (ai-content-tool)

用 AI 把「選題 → 腳本 → 配音 → 剪輯 → 縮圖 → 發布」整條流程自動化的工具,產出短影音並發布到 YouTube(或依 `src/publishers/` 的介面擴充到其他平台),透過平台的廣告分潤機制取得收入。

## 重要聲明(請務必先讀)

- **這不是「刷觀看數 / 假互動」的工具**,也不會做任何點擊農場、機器人瀏覽之類的事。這類行為違反所有主流平台的服務條款,帳號會被停權,且在多數地區可能構成詐欺。工具只負責「產生原創內容並發布」,實際收益仍取決於真實觀眾與平台的創作者收益計畫審核(例如 YouTube Partner Program 的訂閱數/觀看時數門檻)。
- **AI 生成內容請依平台政策揭露**。YouTube 自 2024 年起要求創作者標示「經過大幅改造或合成的實境內容」(見 YouTube說明中心的「已變更或合成內容」政策),本工具產生的 description 會加上「內容由 AI 輔助生成,僅供參考」字樣,但**上傳時的合成內容揭露設定仍需你自己在 YouTube Studio 或 API 參數中確認勾選**,腳本目前未自動設定該欄位。
- **版權**:預設的漸層背景與生成文字不涉及第三方版權;若你設定 `PEXELS_API_KEY` 改用真實圖片,請遵守 Pexels 授權條款;背景音樂 (`--bgm`) 請自備已取得授權或免版稅的音樂。
- **不保證收益**。廣告分潤金額、頻道能否通過各平台的創作者計畫審核,完全由平台與市場決定,本工具無法也不會做任何保證。

## 架構

```
選題 (topic_research.py, 可選)
   -> 腳本生成 (script_generator.py, 呼叫 Claude 或 OpenAI)
   -> 逐句配音 (tts.py, ElevenLabs / gTTS / 離線 pyttsx3)
   -> 影片剪輯 (video_builder.py, Pillow 產生字幕畫面 + moviepy 組成 mp4)
   -> 縮圖生成 (thumbnail.py)
   -> 上傳發布 (publishers/youtube.py, 可選, 使用官方 YouTube Data API v3)
```

每個階段都是獨立模組,可以單獨呼叫,也可以用 `cli.py run` 一次跑完整條流程。

## 安裝

```bash
cd ai-content-tool
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

還需要系統安裝 **ffmpeg**(moviepy 剪輯影片依賴它):

```bash
# macOS
brew install ffmpeg
# Ubuntu/Debian
sudo apt install ffmpeg
```

字幕/縮圖上要顯示中文,需要一個中文字型檔(系統若已有 Noto Sans CJK / 微軟正黑體等會自動偵測;若偵測不到,下載任一免費中文字型,例如 [Noto Sans TC](https://fonts.google.com/noto/specimen/Noto+Sans+TC),存成 `assets/fonts/cjk.ttf`)。

## 設定 API 金鑰

複製 `.env.example` 為 `.env`,依需求填入:

```bash
cp .env.example .env
```

| 變數 | 必填? | 用途 |
|---|---|---|
| `ANTHROPIC_API_KEY` 或 `OPENAI_API_KEY` | 兩者擇一必填 | 腳本生成 |
| `ELEVENLABS_API_KEY` / `ELEVENLABS_VOICE_ID` | 選填 | 高品質語音;不填則用免費的 gTTS,再不行則用離線 pyttsx3 |
| `PEXELS_API_KEY` | 選填 | 用真實圖片當背景;不填則用純色漸層背景 |
| `YOUTUBE_CLIENT_SECRET_FILE` | 要上傳才需要 | Google Cloud Console 下載的 OAuth 用戶端金鑰,詳見 `src/publishers/youtube.py` 檔頭說明 |
| `TRENDS_REGION` | 選填 | 熱門選題的地區代碼,預設 `TW` |

## 使用方式

```bash
# 只看目前熱門選題,不產生內容
python cli.py research

# 手動指定主題,產生影片但不上傳(輸出在 output/<標題>/ 底下)
python cli.py run --topic "如何挑選一台筆電"

# 自動抓熱門選題 + 產生 + 直接上傳到 YouTube
python cli.py run --publish

# 加上背景音樂
python cli.py run --topic "..." --bgm assets/my_bgm.mp3
```

每次執行的產出物都在 `output/<影片標題>/` 底下:`script.json`(腳本)、`audio/`(逐句配音)、`video.mp4`(成品影片)、`thumbnail.png`(縮圖)。

首次執行 `--publish` 時會跳出瀏覽器要求登入 Google 帳號並授權上傳權限,授權後的 token 存在 `.youtube_token.json`,之後不用重複登入。

## 擴充其他平台

`src/publishers/base.py` 定義了 `Publisher` 抽象介面(`upload(video_path, title, description, tags, thumbnail_path)`)。要支援其他平台,依該平台**官方公開的開發者 API** 實作一個新的 `Publisher` 子類即可,例如 Bilibili、Facebook/Instagram Reels 等。請勿嘗試用未公開的內部介面或自動化網頁操作來規避平台審核,那會違反對應平台的服務條款。

## 已知限制

- 影片目前是「文字字幕 + 純色漸層或素材圖」的簡報式短片,不是真人講解或動畫;適合知識型/清單型主題。
- `pytrends`(Google Trends 的非官方套件)可能因 Google 調整內部端點而失效,失效時會靜默回傳空結果,請改用 `--topic` 手動指定。
- YouTube OAuth 用戶端預設是「測試中」狀態,有較嚴格的配額與使用者上限,要正式公開使用需送 Google 審核驗證,這是 Google 官方流程,本工具無法跳過。
