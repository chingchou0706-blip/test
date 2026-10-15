# 台灣客戶地圖 · GitHub Pages

網站：https://chingchou0706-blip.github.io/test/clickup-taiwan-map/

## 功能
公開模式僅顯示匿名客戶和概略座標；完整模式使用 AES-256-GCM 加密資料，只有在網頁輸入正確解鎖密碼後，才能查看公司名稱、原始地址、ClickUp 連結和定位精度。

定位來源依序為 ClickUp 公司地址欄位的經緯度、Geoapify 地址查詢（需 API Key）、縣市中心概略點位。精確座標標綠色，概略位置標橘色。

## 需要在 GitHub Repository secrets 新增
開啟 https://github.com/chingchou0706-blip/test/settings/secrets/actions

1. CLICKUP_TOKEN：已有的 ClickUp Token。
2. MAP_PASSPHRASE：長度至少 16 字元的強隨機解鎖密碼，之後在網頁輸入相同密碼。請勿貼到聊天或上傳到程式庫。
3. GEOAPIFY_API_KEY：在 https://www.geoapify.com/ 申請 Geocoding API Key。設定後，文字地址才能自動轉為更精確座標。可先不填，但此時沒有 ClickUp 位置座標的客戶仍會停留在縣市中心。

設定完成後，在 https://github.com/chingchou0706-blip/test/actions/workflows/update-taiwan-customer-map.yml 按 Run workflow。

每日台灣時間約 08:00 自動同步，也能手動執行。同步完成後，GitHub 上的 customers.json 只含匿名、概略點位；customers.secure.json 只含加密資訊，包含公司名稱和完整地址的明文不會公開提交。

## 注意
- GitHub Pages 仍是公開網站；加密保護不等於公司內部帳號的權限控管。密碼只提供給獲授權的同事，並使用高強度密碼。
- 啟用 Geoapify 後，客戶的文字地址會送至 Geoapify 轉換座標；請遵守公司外部資料使用規範。前端地圖使用 OpenStreetMap，並保留 Geoapify 標示。
- 若想要權限分級與登入驗證，需轉到有伺服器端存取控管的內部站台。
- 欄位來自 ClickUp List 901800292253，使用「地址」（文字）和「公司地址」（location）。
- 「地址定位」也可能有偏差；橘色點不是實際公司位置。
- 本程式只讀 ClickUp，不修改任何 task。

## 檔案
- clickup-taiwan-map/index.html：入口頁
- clickup-taiwan-map/app.js：地圖、客戶搜尋、解鎖
- clickup-taiwan-map/style.css：頁面樣式
- clickup-taiwan-map/scripts/sync_clickup.py：讀取資料、Geoapify 定位、AES 加密
- .github/workflows/update-taiwan-customer-map.yml：GitHub Actions 排程
