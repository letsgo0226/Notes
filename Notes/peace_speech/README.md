# 虛構和平演說｜可重現影片產生器

**作品：**《和平不是等待發生的奇蹟》 / *Peace Is Not a Miracle We Wait For*

這是明確標示的**虛構公民演說**，不是聯合國或任何政府發言，也不模擬真實政治人物。現實戰爭不能由敘事作品直接解決。本專案將可供辯論的公共提案製成短片。

## 生成檔案

執行（Ubuntu；安裝 `python3-pil`, `fonts-noto-cjk`, `ffmpeg`, `espeak`）：

```sh
python3 Notes/peace_speech/render.py --output dist/peace_speech
```

也可在 GitHub **Actions → Fictional Peace Address Video → Run workflow**，取得 `fictional-peace-address-video` Artifact，其中包含 MP4、繁體中文字幕 SRT、雙語文字、來源證明及 SHA-256 校驗和。

- 影片音軌為離線 `espeak` **英語合成語音**，而畫面及 SRT 採繁體中文；音質功能性優先，非真人旁白。
- 原創幾何圖像，不使用未取得授權的戰地照片、官方徽章或演說者影像。
- `speech.json` 是可編輯的演說場景與旁白；`render.py` 產生素材，獨立於既有 HSI 模組。
- 這是一個以規則及文字合成方式製作影片的流程，並不是自主生成新政策、推斷戰爭結局或讓虛構內容成為真實政治事實的 AI 系統。
- 本專案不聲稱和平已實現；所有實際政策須經人權、法律、當事人與執行條件審查。

## 立論

尊重烏克蘭主權和領土完整；推動可核驗停火及人道救援；保護平民；建立透明重建與問責機制；保護公開異議。公眾意見應透過自由討論而非情緒操縱取得共識。

## 參考背景

見 `speech.json` 中 `sources`。所列聯合國資料僅用來核實背景，並不表示聯合國認可本影片。
