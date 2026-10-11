# HSI TM Open-Corpus 三部曲研究札記（完全無 AI 模型）

此子系統將 Notes 資料夾的全部十二份鎖定檔案納入來源稽核。每次執行其中已鎖定的 OriginalXY_reference.py 有限圖靈機，保留 checkpoint；由機器真實計算記錄選出下一個未完成章節及固定規則的文字編排重點。

輸出是哲學研究札記，不是以 AI 自動完成三本出版級著作。它不呼叫 AI 模型、AI API，不主張計算編碼可以證成任何形上學命題。

## 使用

離線預覽：python3 trilogy_tm_corpus.py --plan

無網路編纂一個章節：python3 trilogy_tm_corpus.py --build --offline

包含公開題錄搜索：python3 trilogy_tm_corpus.py --build

GitHub Actions 的「HSI TM Open-Corpus Trilogy (No AI)」會在程式首次合併到 main 時嘗試執行，之後預定每日臺灣時間 11:23 執行；也可人工觸發。排程實際執行時間受 GitHub 服務情況影響。GitHub Actions 運算仍受 GitHub 帳戶額度限制；無 AI 模型呼叫費用。

## 輸出與進度

每次至多生成一章研究札記，三本共 25 章。每章：

- dossier.md — 根據既有論證規則、短摘與題錄生成的研究札記
- manifest.json — 來源清單、每個檔案的雜湊、引用路徑及網路檢索狀態
- tm_trace.json — 真實圖靈機有限執行記錄

state.json 保存程序檢查點與完成章節，避免覆寫已保存的內容。

## 開放網路來源

每次最多呼叫 Crossref 的一筆 REST API 搜尋，取得最多四筆學術文獻題錄（作者、標題、年份、DOI）；不是搜尋到完整論文並閱讀全部內容。網路失敗會標示 UNAVAILABLE，不能被描述成已取得證據。參考官方文件：https://www.crossref.org/documentation/retrieve-metadata/rest-api/ 。

## 安全與學術限制

程序只執行經 hsi_notes_review.lock.json 核對的圖靈機參考程式，其餘來源檔均當作資料讀取。有限步數、超時與資料限制避免無界運行。所有文字輸出在 books/reading-trilogy/open-corpus/，不更動原本 Notes 資料夾或其鎖定檔案。

此系統只替代「資料庫搜索、編輯性組織與研究札記的規則生成」，不等於已具備人類作者的理解、原創論證與倫理判斷。真正出版仍須正式寫作、查證原典、對抗反例與審訂。
