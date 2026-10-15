# 台灣客戶地圖 · ClickUp → GitHub Pages

將 ClickUp List 的任務與自訂欄位「地址」轉成台灣互動地圖；每天台灣時間約 08:00 自動同步，亦可按鈕手動同步。前端包含客戶搜尋、縣市／狀態篩選、標點聚合及 ClickUp 任務連結（僅完整模式）。

## 已對應的 ClickUp 設定

- Workspace：`9018037308`
- List：`901800292253`（原網址：https://app.clickup.com/9018037308/v/l/6-901800292253-1）
- `地址`：**text**，field ID：`005e585c-bce2-4f59-9dcd-ff1cfbe1aa63`
- `公司地址`：**location**，field ID：`0e79099e-1e0e-4a5f-a6ef-acdc4da3f1eb`

系統讀取「地址」文字；若沒有則改讀「公司地址」格式化地址。定位時先利用「公司地址」現有經緯度（若有）；其次採用使用者選擇的地理編碼服務；都沒有時按**縣市中心**顯示概略位置。若文字地址與公司地址座標不一致，需到 ClickUp 檢查。

> **重要安全提醒**：多數 GitHub Pages 網站**對外公開**；「Private repository」不代表其 Pages 對外不可見。預設採 `PUBLIC_MODE=safe`：**去識別客戶名稱、不公開完整地址與任務連結、座標四捨五入至小數 1 位**。不要在公開 Pages 使用 `PUBLIC_MODE=full`！只有 GitHub Enterprise Cloud 符合條件的組織可以設定 Pages 私有存取，或改用公司內部部署。公開的網站其產生的 JSON 也可被下載，不能靠前端密碼或隱藏按鈕保護資料。

## GitHub 部署（建議）

1. 解壓縮全部檔案到自己的 GitHub Repository **根目錄**，主分支名稱使用 `main`。
2. 前往 Repository → **Settings → Secrets and variables → Actions → Secrets → New repository secret**，新增 `CLICKUP_TOKEN`，值為個人的 ClickUp API Token。**不要把 Token 寫入程式或上傳 GitHub。**
3. Repository → **Settings → Pages → Build and deployment → Source**，選擇 **GitHub Actions**。
4. Repository → **Actions → Sync ClickUp Customer Map → Run workflow** 執行首次同步。等待 build/deploy 都顯示成功後，在 **Settings → Pages** 取得網址。
5. 之後每天台灣時間約 **08:00** 會排程同步（GitHub 排程可能延後）；也可隨時按 **Run workflow**。

如果 Github Pages 尚未啟用，`configure-pages` 可能會失敗：先完成第 3 步。若 `403`／`401`，確認 Token 權限和 List 存取權。

## 地理位置精度

只放 `CLICKUP_TOKEN` 即可產生地圖，精度視欄位而定：

| 情況 | 結果 |
|---|---|
| 「公司地址」已有經緯度 | 直接使用 ClickUp 座標（完整模式） |
| 只有文字「地址」，無地理編碼金鑰 | 偵測到縣市後，以縣市中心代表概略位置 |
| 只有文字「地址」，啟用 Google Geocoding | 透過 Google Geocoding API 找更細座標，需自行開啟 API 並設定計費 |
| 未能解析縣市／位置 | 在頁面「需補地址」數值中反映，不亂標在地圖 |

### 更精準地址定位（選用）

**Google Geocoding**：Repository → **Settings → Secrets and variables → Actions**：

- Variable `GEOCODER_PROVIDER` 設定 `google`
- Secret `GOOGLE_GEOCODING_API_KEY` 設定有效金鑰

Google Geocoding API 有額度、計費與資料使用條款；請在公司政策允許將客戶地址傳送第三方時使用。程式將對地址雜湊後快取座標，避免對同一地址重複查詢。

**OpenStreetMap Nominatim 公用 API**（僅**手動明確選用**，不會預設啟用）：設定 Variable `GEOCODER_PROVIDER=nominatim`，並於 Secret `GEOCODER_CONTACT_EMAIL` 填可識別的聯絡信箱。啟用前必須自行閱讀並確認遵循 [Nominatim Usage Policy](https://operations.osmfoundation.org/policies/nominatim/)：單機、串行、有效 User-Agent、快取，且定時執行腳本每分鐘最多 4 次請求。程式以每 16 秒 1 次限制並用 GitHub Actions cache，仍可能被公用服務拒絕；**客戶資料量大時請改用合規付費服務或自行架設的 Nominatim**。不要在未經核准時把客戶地址傳給公用第三方服務。

## 資料公開模式

Repository → Settings → Secrets and variables → Actions → **Variables**：

- `PUBLIC_MODE=safe`（**預設**）：以「客戶 001」等代稱顯示，無原始地址、狀態、任務 URL，位置約略到小數一位（約 10 公里網格）。
- `PUBLIC_MODE=full`：顯示公司／客戶名稱、地址、ClickUp 狀態、任務連結、最大可用座標精度。**此模式僅適合具備實際存取控制的網站／本機環境；不適合一般公開 Pages。**

如只在自己電腦看完整資料，可用本機模式，不要發布到公網：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export CLICKUP_TOKEN='你的Token'
export PUBLIC_MODE=full
python scripts/sync_clickup.py
python3 -m http.server 8000 --directory dist
```

瀏覽器開啟 `http://localhost:8000`。Token 僅用於 Python 後端，不會送到瀏覽器。請不要把 `.env`、`.cache/`、`dist/` 提交 Git；本專案已有 `.gitignore`。

## 本機測試／假資料展示

不須 ClickUp Token：

```bash
python scripts/create_demo.py
python3 -m http.server 8000 --directory dist
python -m unittest discover -s tests -v
```

展示資料全部虛構，不能視為真實客戶。實際同步執行 `python scripts/sync_clickup.py` 會覆蓋 `dist/`。

## 專案結構

```text
site/index.html               互動地圖頁面
site/style.css                RWD 版型
site/app.js                   搜尋、篩選、圖釘、聚合
scripts/sync_clickup.py       ClickUp API 同步、地理定位、公開資料處理
scripts/create_demo.py        產生不含真實客戶的假資料預覽
.github/workflows/update-map.yml  每日同步 + 部署 Pages
requirements.txt             Python 依賴
tests/                        基本測試
```

## 常見問題

- **地圖上多個客戶重疊**：未啟用地址定位服務且只有文字地址時，會落在相同縣市中心；點擊聚合點可展開。公開 safe 模式因刻意模糊位置，也可能有重疊。
- **缺少客戶**：只會顯示有有效地址／座標的任務；未填地址和無法定位的任務都計入「需補地址」。預設只抓主 Task，不把 Subtask 當成客戶。
- **沒有同步**：GitHub 排程不保證分秒準時；先用 Actions 手動執行檢查。
- **行政區辨識**：目前支援台灣 22 個縣市文字，可接受「台／臺」寫法。沒有自行假設街道座標。縣市中心是視覺化代表點，不是客戶實際門牌。
- **工作表與安全**：本程式只讀取 ClickUp，不會修改客戶 Task 或 custom field。

官方參考：[ClickUp Get Tasks](https://developer.clickup.com/reference/gettasks)、[GitHub Pages 自訂 Actions](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)。