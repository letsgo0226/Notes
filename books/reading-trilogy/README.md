# HSI Autonomous Trilogy Writer (experimental)

三本哲學著作的**未審訂草稿**預定儲存於此路徑。每次產生一節，不覆寫既有正文；所有生成結果保留 Git 提交紀錄與 `state.json` 進度。生成完成不代表哲學命題已被證明，也不代表書稿通過出版審查。

- Book 1 — Caduceus：如何閱讀一本書
- Book 2 — Hu Mantra：如何閱讀自己
- Book 3 — Love Is The Solution For Everything：如何閱讀生命

每章八節，全部共 200 節。每節最低 800 個漢字；這僅是防止過短輸出的門檻，不是學術品質認證。可用 `python3 trilogy_writer.py --plan` 離線查看下一節。

## 啟用前（預設關閉）

1. 查看 `tests/test_trilogy_writer.py`、workflow 和 GitHub Actions 的既有失敗狀況；不要在未審核時合併。
2. 確認 GitHub Models 的存取資格、可用模型與額度；若使用外部相容模型，將 `WRITER_API_KEY` 設為 Actions secret；可選 `WRITER_API_URL` / `WRITER_MODEL` 變數。
3. 只有**主動**建立 Repository variable `TRILOGY_ENABLED=true` 才會執行自動文字生成；否則排程不會使用任何文字模型。
4. 在 Actions → HSI Trilogy Writer → Run workflow，可選擇 dry plan（write=false），或正式生成一節（write=true 且已啟用）。
5. 排程為每日 03:17 UTC / 臺灣 11:17，可能因 GitHub 排程壅塞延遲或省略。程式硬性限制每日最多一節，避免額度意外失控。

預設端點：`https://models.github.ai/inference/chat/completions`；其他端點**不會**自動沿用 GitHub token。任何模型費用與服務限制須事先確認。只有支援的第三方端點才能適用相容的聊天回應格式。

## 學術與安全界限

以原有 `Notes/` 為唯讀來源之數學和 HSI 文件，只能作為研究上下文，不保證生成內容的真值。程式只讀取少量 UTF-8 文字摘錄，不執行來源檔案；不會下載未授權的其他資料。

系統無法自行證明「精神能量」、「高頻率」、「Higher Self」等形上學主張；所有內容標記 UNREVIEWED AI DRAFT，引用、原典、前提、反例、論證一致性及著作權均需人工核實。免費或沒有付費 API 不代表有免費且無限量的高品質生成。
