# HSI Trilogy Writer — 草稿區

本資料夾將由 GitHub Actions 定期新增未審訂的哲學書稿，依序撰寫 Caduceus、Hu Mantra、Love 三本書。每次執行寫一節，進度由 state.json 保存。完成全部預定節次不等於已完成出版審訂。

執行：GitHub Actions → HSI Trilogy Writer → Run workflow。也可本地執行 python3 trilogy_writer.py --plan 檢視下一節。

預設使用 GitHub Models API（需具備權限、模型供應及額度）；可透過 Secrets: WRITER_API_KEY 和 Variables: WRITER_API_URL、WRITER_MODEL 使用其他相容模型。請勿將密鑰提交至 GitHub。使用額度與費用依供應商而定。

所有內容標示 UNREVIEWED AI DRAFT；需核實原始來源、引文、著作權、論證及跨章一致性。程式僅讀取 Notes/ 中有限的文字片段，不執行其中任何檔案。
