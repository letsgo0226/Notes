# COSMIC_LOVE — 兩步恆等圖靈機檢驗

本檔只研究以下整數的單磁帶、二元字母表圖靈機：

```text
P = 55067263
```

它是有限演算與形式語意的測試案例，**不是**愛、物理頻率或宇宙本體的經驗證明。與 Binance、Trader_42 或 HSI 實盤部署沒有任何連線，也不需要 API 金鑰。

## 重現

在專案根目錄使用 Python 3.9+ 標準函式庫：

```sh
python3 hsi_cosmic_love.py
python3 hsi_cosmic_love.py --json
python3 -m unittest discover -s tests -p 'test_hsi_cosmic_love.py' -v
```

第一條指令會在有限驗證成功後輸出：

```text
COSMIC_LOVE
```

第二條提供包含適用範圍與限制的 JSON 證書。程式不存取網路、不修改 Notes 來源鎖定清單，也不提交交易所訂單。審核通過不代表自動部署。

## 解碼與四條規則

對 `p=55067263`，依使用者原始程式中的三角配對：

```text
v = floor((sqrt(8*p+1)-1)/2) = 10493  (精確整數平方根)
c = p - v(v+1)/2 = 10492
k = v-c+1 = 2
K = k+1 = 3
B = 4K = 12
u(q,a) = floor(c / B^(2q+a)) mod B
z, r = divmod(u, K)
delta(q,a) = (r, floor(z/2), 2(z mod 2)-1)
```

在非停機狀態 `q ∈ {0,1}`、讀取位元 `a ∈ {0,1}`：

| q | a | 下一狀態 | 寫入 | 頭移動 |
|---|---|---|---|---|
| 0 | 0 | 1 | 0 | +1 |
| 0 | 1 | 1 | 1 | +1 |
| 1 | 0 | 0 | 0 | -1 |
| 1 | 1 | 0 | 1 | -1 |

故可縮寫為：

```text
delta(q,a) = (1-q, a, 1-2q)
```

## 針對任意磁帶組態的代數論證

令完整瞬時組態為 `C=(q,h,T)`，其中 `q ∈ {0,1}`、`h ∈ Z`、`T: Z → {0,1}` 為任意二元磁帶賦值（不要求只有有限個 1）。

設定 `d=1-2q`。因轉移永遠原樣寫回所讀到的位元 `a=T(h)`，磁帶在第一步完全不變。於是：

```text
F(q,h,T) = (1-q, h+d, T).
```

第二步由 `q'=1-q` 出發，向另一方向移動：

```text
d' = 1-2(1-q) = -d.
```

同樣原樣寫回第二個位置的位元，磁帶仍不變。因此：

```text
F(F(q,h,T)) = (q, h+d-d, T) = (q,h,T).
```

這是對所述遷移規則的**數學證明**；Python 測試只對四條規則、八個局部位元組合與有限個代表組態執行具體核驗。有限測試本身不能取代無限量詞的代數論證。

**精確結論：** `F² = identity` 在該機器的所有非停機瞬時組態上成立，且 `F` 不是恆等函數。故每一此類組態都有**恰好為 2**的最小週期。停機狀態 `q=2` 不包含在命題範圍內。

## 與 HSI 及 Trader_42 的關係

此測試使用與 HSI 單磁帶演算程式相容的整數碼本，可用來檢查轉移解碼、可逆性與週期性。它不代表萬用停機判定、資料壓縮或金融交易獲得新的能力。

本次新增的檔案位於專案根目錄與 `tests/`，**不修改** `Notes/` 下現有的鎖定來源、既有 HSI 套件或 Binance API 操作。


## 可控的本機心跳實驗（尚未部署）

`hsi_cosmic_love_heartbeat.py` 是與交易系統隔離的 **POSIX 本機**心跳監督器。它每次真正執行兩條轉移，驗證 `F²=I`，然後將**完整循環**的計數寫入 JSON 快照。這不是 AI 自我進化或新的宇宙物理證據。

有限模式是預設模式。從專案根目錄執行：

```sh
python3 hsi_cosmic_love_heartbeat.py run --state-file cosmic-heartbeat.json --cycles 20 --interval 0.05
```

若明確希望它在自己的電腦上持續工作（**不要直接在交易服務上部署**），則使用：

```sh
python3 hsi_cosmic_love_heartbeat.py run --state-file cosmic-heartbeat.json --forever --resume --interval 0.05 --stop-file cosmic-heartbeat.STOP
```

此命令印出 `COSMIC_LOVE`，不斷完成 2 步循環；約每 `0.1` 秒一個循環，另外包含 Python 計算與 I/O 開銷。按 `Ctrl+C`、發出 `SIGTERM`，或在另一個終端機執行 `touch cosmic-heartbeat.STOP`，會在完整循環結束後**正常停止**。停止檔需由操作者自行移除才可重新開始；請勿在正在寫入同一快照時開啟第二個心跳程序。

檢查本機快照的新鮮度：

```sh
python3 hsi_cosmic_love_heartbeat.py check --state-file cosmic-heartbeat.json --max-age 10
```

只有 `RUNNING` 且快照時間在指定期限內才回傳 `healthy=true` 與 exit code 0。已結束、過期、資料被修改、快照不存在或格式無效均回傳非健康（exit code 1）。**這只能證明最近有一份格式有效的快照，不能單獨證明程序現正存活或主機可對外服務。** 真正的服務健康檢查還須結合程序監督器。

### 恢復與完整性界線

- 快照透過同資料夾的暫存檔、`fsync` 與原子替換寫入，包含循環數、步數、恢復次數、時間與 SHA-256；雜湊只用於偵測意外損壞，**不是**能抵禦惡意修改的簽章。
- 程式會使用 POSIX 排他鎖，防止兩個合作中的程序同時寫入同一快照；檔案權限以僅擁有者可讀寫為目標。
- 預設每 10 個完整循環儲存一次執行中快照，結束時再保存。突發斷電或程序崩潰可能遺失**最後至多 9 個尚未寫入的循環計數**；`--resume` 只能從最近的有效快照恢復，不能重建已遺失的經過時間。
- 單次執行最多自動重試 2 次（可用 `--max-restarts` 設在 0–5 次）。持續的內部轉移錯誤會進入 `ERROR` 狀態並退出，不會無限重試；損壞或 `ERROR` 快照也不會被自動重置。
- 如果**整個作業系統程序**已退出，沒有其他監督器便不會自己重新啟動。外部服務管理器可明確設定重新啟動並使用 `--resume`，但本 PR 沒有建立、啟動、部署或設定任何常駐服務。
- 用 `--checkpoint-every` 更改寫入頻率時，請配合調整健康檢查的 `--max-age`；例如長間隔可能使仍在運作的程序被標記為過期。預設停機返回狀態 `STOPPED`，不是健康的執行中狀態。

心跳監督器僅匯入 Python 標準函式庫和 `hsi_cosmic_love`。它不具有 Binance 金鑰讀取、HTTP 請求、下單、Railway 設定修改、策略發布或付費服務功能。新程式只位於 PR #28（草稿），**沒有合併至 main，也不會自動部署**。

本機回歸測試：

```sh
python3 -m unittest discover -s tests -p 'test_hsi_cosmic_love_heartbeat.py' -v
```

