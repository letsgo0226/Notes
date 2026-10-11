# 和平演說創作影片｜可重現影片產生器

**作品：**《和平不是等待發生的奇蹟》 / *Peace Is Not a Miracle We Wait For*

這是以**原創角色與合成影音**創作的政治哲學演說，並非真實政治活動的錄影，也不模擬真實政治人物或冒用任何政府、聯合國的身分。影片畫面以演說本身為主，不重複顯示「虛構演說」字樣；發布說明與來源檔保留合成媒體告知。現實戰爭無法由敘事作品直接解決，本專案將可供辯論的公共提案製成短片。

## 生成檔案

執行（Ubuntu；安裝 `python3-pil`, `fonts-noto-cjk`, `ffmpeg`, `espeak`；若用 Microsoft Edge 英語語音，另外安裝 `edge-tts`）：

```sh
python3 Notes/peace_speech/render.py --output dist/peace_speech
```

也可在 GitHub **Actions → Fictional Peace Address Video → Run workflow**，取得 `fictional-peace-address-video` Artifact，其中包含 MP4、繁體中文字幕 SRT、雙語文字、來源證明及 SHA-256 校驗和。

- 預設使用 Microsoft Edge 的 `en-US-AndrewNeural` **英文自然語音**（透過社群套件 `edge-tts`，非官方 Azure Speech API，需網路）；也可用 `--tts espeak` 離線輸出英文旁白。另產生繁體中文及英文字幕、獨立英文 MP3。
- 現行 Python 渲染器使用原創幾何圖像，不使用未取得授權的戰地照片或官方徽章。日後若加入寫實 AI 人物鏡頭，應保持原創人物、不仿冒真實政治人物，並在公開說明中揭露合成影像。
- `speech.json` 是可編輯的演說場景與旁白；`render.py` 產生素材，獨立於既有 HSI 模組。
- 這是一個合成語音與程式渲染流程，不是自主生成新政策、預測戰爭結局或將原創敘事當作真實政治事實的 AI 系統。
- 本專案不聲稱和平已實現；所有實際政策須經人權、法律、當事人與執行條件審查。

## 立論

尊重烏克蘭主權和領土完整；推動可核驗停火及人道救援；保護平民；建立透明重建與問責機制；保護公開異議。公眾意見應透過自由討論而非情緒操縱取得共識。

## 參考背景

見 `speech.json` 中 `sources`。所列聯合國資料僅用來核實背景，並不表示聯合國認可本影片。
