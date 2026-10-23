# TRADING ARENA 交易競技場（公開看板）

交易員-1 vs 交易員-2 的 OKX 交易競賽看板，由 GitHub Actions 定時更新、GitHub Pages 上線，不依賴任何本機電腦。

- `index.html`：前端頁面，每 30 秒抓一次 `data.json` / `history.json`。
- `updater.py`：只呼叫 OKX 唯讀端點（餘額、持倉、成交、帳單），不下單。
- `.github/workflows/update.yml`：排程約每 5 分鐘執行一次（GitHub 實際可能延遲到 5–15 分鐘以上），拉資料後部署到 Pages；權益曲線歷史保存在 `data` 分支。
- API 金鑰只存在 repo 的 Actions secrets，不在程式碼裡。
