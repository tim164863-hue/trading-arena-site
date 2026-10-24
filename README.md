# TRADING ARENA 交易競技場（公開看板）

交易員-1 vs 交易員-2 的 OKX 交易競賽看板，由 GitHub Actions 定時更新、GitHub Pages 上線，不依賴任何本機電腦。

- `index.html`：前端頁面，每 30 秒抓一次 `data.json` / `history.json`。
- `updater.py`：只呼叫 OKX 唯讀端點（餘額、持倉、成交、帳單），不下單。
- `.github/workflows/update.yml` + `.github/loop.sh`：一個長時間執行的 job 每 6 分鐘拉一次資料，推到 `gh-pages` 分支（Pages 來源）和 `data` 分支（歷史備份）；跑約 5 小時 45 分後自動接力啟動下一輪。每 15 分鐘的排程只當看門狗，沒有在跑的迴圈才會補啟動。
- API 金鑰只存在 repo 的 Actions secrets，不在程式碼裡。
