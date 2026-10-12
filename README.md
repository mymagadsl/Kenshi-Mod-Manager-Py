# Kenshi 模組管理器（Kenshi Mod Manager - Python 繁體中文強化版）

<p align="center">
  <a href="https://github.com/mymagadsl/Kenshi-Mod-Manager-Py/releases/latest">
    <img src="https://img.shields.io/github/v/release/mymagadsl/Kenshi-Mod-Manager-Py?label=%E6%9C%80%E6%96%B0%E7%89%88%E6%9C%AC%20Release&style=for-the-badge&color=e67e22" alt="Latest Release">
  </a>
  <a href="https://github.com/mymagadsl/Kenshi-Mod-Manager-Py/releases/latest">
    <img src="https://img.shields.io/github/downloads/mymagadsl/Kenshi-Mod-Manager-Py/total?label=%E7%B4%AF%E7%A9%8D%E4%B8%8B%E8%BC%89%20Downloads&style=for-the-badge&color=2ecc71" alt="Downloads">
  </a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+">
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-MIT-blue?style=for-the-badge" alt="MIT License">
  </a>
</p>

<p>
  本專案由 <b>北極企鵝 (mymagadsl@gmail.com)</b> 基於原作者 <a href="https://github.com/millerscout/Kenshi-Mod-Manager" target="_blank">MillerScout / Kenshi-Mod-Manager</a>（C# / WPF）重新以 <b>Python + CustomTkinter</b> 改寫並大幅強化。
  自動排序規則與負載順序邏輯參考自 Steam 社群經典指南 <a href="https://steamcommunity.com/sharedfiles/filedetails/?id=1850250979" target="_blank">Proper Load Order &amp; You (id=1850250979)</a> 與 <a href="https://discord.gg/g7F6aHw" target="_blank">Genesis Modding Guild</a>。
</p>

---

## 📥 玩家快速下載與安裝（免安裝 Python！）

如果您是一般玩家，**不需要安裝 Python 或任何額外環境**，直接下載編譯好的獨立執行檔即可使用：

1. 前往 **[👉 GitHub Releases 最新版本下載頁面](https://github.com/mymagadsl/Kenshi-Mod-Manager-Py/releases/latest)**。
2. 下載 **`KenshiModManager.exe`**（或 **`KenshiModManager-v1.0.2-win64.zip`** 解壓縮）。
3. 將 `KenshiModManager.exe` 放在任意資料夾，雙擊即可直接執行！
   - 首次啟動時，程式會自動從 Windows 登錄檔與 Steam `libraryfolders.vdf` 偵測您的 **Kenshi 遊戲資料夾**與 **Steam 工作坊模組資料夾**（無須先開啟 Steam）。
   - 若您使用的是 GOG 或非 Steam 版本，也可在啟動提示或「`⚙ 設定`」視窗中手動指定 Kenshi 遊戲路徑。

---

## ✨ 功能特色（Features & Enhancements）

### 1. 基礎模組管理功能（相容原版所有特性）
- **雙來源自動整合**：同時掃描並管理 **Steam 工作坊（Workshop）** 與 **遊戲本體 `mods/` 資料夾** 的所有模組，並自動去除同一模組子目錄中的備份重複 `.mod` 檔。
- **完整二進位檔頭解析**：完整支援最新 **Kenshi FCS v17** 二進位 `.mod` 檔案格式（舊版 C# 工具在 v17 會因標頭偏移導致亂碼與無法讀取相依性），精準讀取作者、版本、描述、相依（Dependencies）、參考（References）與 `_xxx.info` 工作坊分類標籤。
- **直覺調整載入順序**：
  - 支援滑鼠**拖曳排序**、**雙擊順序欄直接輸入數字**、點擊欄位標題排序，或使用右鍵移至最頂端／最底端。
  - 缺少相依模組或載入順序顛倒時自動以**紅底警示**，並在下方詳細資訊面板以**綠字（正常）／紅字（缺失或順序錯誤）**清楚標示。
- **設定檔匯出與匯入（Profile）**：支援儲存與載入 `.cfg` 模組排序設定檔（與原版格式 100% 相容），方便在不同模組組合間快速切換。
- **快速連結與工作坊退訂**：點擊網址直接開啟 Steam 工作坊或 NexusMods 頁面，亦可右鍵在 Steam 上取消訂閱或直接開啟模組本機資料夾。

### 2. 進階強化功能（本改寫版獨家新增）
- **🩺 Kenshi 當機與 Log 診斷分析器（Crash & Log Diagnostic Analyzer）**：
  - 工具列提供「**🩺 分析當機 Log**」按鈕，一鍵深度解析遊戲目錄下的 `crashDump*.zip`（內建 Windows Minidump `.dmp` 二進位解析器，直接讀取崩潰瞬間 Exception Code `0xC0000005`、故障指令位址 `RIP` 與當下掛載於記憶體的 `.dll` 插件清單）、`RE_Kenshi_log.txt`、`RE_Kenshi/DesoCrash.log`、`MyGUI.log`、`kenshi_info.log` 與 `Havok.log`。
  - **🎯 可疑當機來源模組排行榜**：綜合崩潰位址、當機前密集運作紀錄與 `.dll` 二進位 Hook 特徵自動計分排序（嚴格過濾已取消勾選或未載入記憶體的模組），點擊排行榜上的按鈕即可在主視窗**一鍵定位並選取該模組**！
  - **🧟 獨家偵測「關不掉的 INVENTORY 僵屍視窗／搜刮視窗異常」**：自動識別 `RE_Kenshi_log.txt` 中的 `engine GUI update raised exception`，精準揪出攔截背包建立、拿取物品與視窗關閉解構子（`~InventoryGUI`）而引發孤兒視窗的插件。
  - **🖼 缺失貼圖真實來源反查**：自動對已啟用插件 `.dll` 進行二進位字串反查，精準找出 `MyGUI.log` 報錯的缺失貼圖實際由哪個外掛呼叫。
  - **🗑 遊戲 Log 與龐大 CrashDump 一鍵清理**：於診斷視窗與設定視窗支援一鍵掃描並清除遊戲目錄、`RE_Kenshi/` 與 `logs/` 下無限累積的龐大歷史紀錄（如數十 MB 的 `DesoCrash.log.1` 與舊 `crashDump*.zip`），釋放硬碟空間並避免舊紀錄干擾後續診斷。
- **⚠ 高速模組屬性衝突檢查器（Conflict Checker）**：
  - 深度解析所有啟用模組的 FCS 二進位紀錄（Records）與欄位變動，精準列出哪些模組修改了同一個遊戲物件與屬性。
  - 自動標示依目前載入順序「**◀ 最終生效（Winner）**」的模組。
  - **點擊名稱一鍵跳轉**：在下方衝突明細中直接點擊任何模組名稱，主清單會自動捲動並選取該模組！
- **🛡 智慧辨識「漢化模組」與「補丁／擴充模組」並排除假警報**：
  - 自動透過檔名、工作坊標題與相依性配對辨識**漢化包（Translation）**與**相容補丁／擴充包（Fix / Patch / Add-on / Playable）**。
  - 篩選列提供「**排除漢化衝突**」與「**排除補丁衝突**」開關（預設開啟），讓您專注於真正需要排解的第三方模組衝突。
- **🔀 進階智慧自動排序（Smart Auto-Sort）**：
  - 結合線上／內建 `masterlist.json` 規則與 **Steam 工作坊分類標籤（Categories）權重推斷**，即使是不在 Masterlist 名單內的新模組也能自動歸類至正確區段（UI/地圖 → 建築/動畫 → 陣營/裝備 → 全面大修 → 補丁/漢化）。
  - **自動跟隨原則**：自動排序時，會將擴充補丁與漢化模組**自動緊跟在原版主模組之後**，避免載入順序顛倒導致失效。
- **🈵 四層智慧中文模組名稱顯示系統**：
  - 解決大量 Steam 工作坊模組只有英文檔名、看不出用途的困擾！開啟「**顯示中文譯名**」後，會依四層機制自動解析並顯示為 `【繁體中文譯名】 OriginalName`：
    1. **第 1 層**：自動從工作坊 `.info` 標題提取中文名稱，並內建零依賴簡轉繁引擎自動轉為繁體中文。
    2. **第 2 層**：從您已安裝的漢化包標題反向推導出英文原版主模組的中文名稱。
    3. **第 3 層**：內建百大熱門 Kenshi 模組繁體中文辭典（`base_mod_names_zh.json`）與個人自訂辭典（`mod_names_zh.json`）。
    4. **第 4 層**：右鍵選單支援「**✏ 設定中文別名／備註…**」手動命名，以及「**🌐 自動翻譯未知英文模組**」一鍵線上翻譯並快取至本機！
- **🔗 資料夾管理（免管理員權限建立目錄連接點 Junction）**：
  - 內建「資料夾管理」工具視窗，可將勾選的 Steam 工作坊模組以 Windows Junction 連結至遊戲 `mods/` 資料夾（**不需要系統管理員權限**），方便離線遊玩或供 FCS 編輯器讀取，並支援一鍵清除空資料夾。
- **🧹 右鍵清理、Steam 工作坊快取修復與集中式日誌管理**：
  - 右鍵選單支援一鍵「**移除該資料夾不存在的模組**」與「**移除未勾選的模組與資料夾**」。
  - **自動修復 `appworkshop_233860.acf` 工作坊快取**：自動清除已退訂或已刪除的孤兒模組快取紀錄，防止 Steam 無限重抓已退訂的舊模組。
  - 自動將訂閱備份檔（`bkpsubscribedList*.info`）與執行日誌收納至 `logs/` 子目錄，並在設定視窗提供「**🗑 清除備份與日誌**」一鍵清理按鈕。
- **🌍 多國語言操作介面即時熱切換**：
  - 於「`⚙ 設定`」視窗支援 **繁體中文（預設）**、**简体中文**、**English** 三種介面語言，儲存後無須重啟程式即可即時切換全部介面文字。

---

## ⌨ 快捷鍵一覽（Shortcuts）

| 快捷鍵 | 功能說明 |
| :--- | :--- |
| `空白鍵 (Space)` | 切換目前選取模組的啟用／停用勾選狀態 |
| `Alt + ↑` / `Alt + ↓` | 將選取的單一啟用模組往上 / 往下移動一格 |
| `Ctrl + S` | 儲存目前啟用模組順序至遊戲 `data/mods.cfg`（自動處理唯讀屬性並備份 `mods.cfg.backup`） |
| `Ctrl + F` | 將游標聚焦至搜尋欄（輸入關鍵字後按 `Enter` 可跳至下一筆符合項目） |
| `F5` | 重新掃描並整理模組清單 |
| `滑鼠雙擊「順序」欄` | 直接輸入數字指定該模組的載入順序 |

---

## 🛠 開發者指南：從原始碼執行與自行編譯（Run from Source & Build）

### 系統需求（Requisites）
- Windows 10 / 11 (x64)
- Python `3.11` 以上版本（建議 `3.12` ~ `3.14`）

### 1. 從原始碼直接執行
```powershell
git clone https://github.com/mymagadsl/Kenshi-Mod-Manager-Py.git
cd Kenshi-Mod-Manager-Py
pip install -r requirements.txt
python main.py
```
（或直接雙擊專案目錄下的 `啟動模組管理器.bat`）

### 2. 使用內建視窗化編譯工具打包獨立 `.exe`
本專案附帶專屬的 **CustomTkinter 繁體中文視窗化編譯工具**（`build_gui.py`），可一鍵將專案封裝為單一獨立執行檔：

```powershell
python build_gui.py
```
1. 啟動後會自動檢查環境，若尚未安裝 `PyInstaller`，可點擊右上角「**📦 安裝 / 更新 PyInstaller**」。
2. 選擇「**單一獨立執行檔 (`--onefile`)**」並點擊下方「**🚀 開始編譯獨立執行檔 (.exe)**」。
3. 編譯完成後會在 `dist/KenshiModManager.exe` 產出包含完整主題與內建繁中辭典的獨立執行檔。

---

## 🌐 English Summary

**Kenshi Mod Manager (Python Rewrite & Enhanced Edition)** is a modern **Python + CustomTkinter** rewrite of [MillerScout's Kenshi-Mod-Manager](https://github.com/millerscout/Kenshi-Mod-Manager), created by **北極企鵝 (`mymagadsl@gmail.com`)**.

### Key Highlights
- **Standalone `.exe` Ready**: Download `KenshiModManager.exe` directly from [Releases](https://github.com/mymagadsl/Kenshi-Mod-Manager-Py/releases/latest) — no Python installation required.
- **Multi-Language UI**: Built-in support for **Traditional Chinese (`繁體中文`, default)**, **Simplified Chinese (`简体中文`)**, and **English** (switchable in `⚙ Settings` -> `Interface Language`).
- **Kenshi FCS v17 Binary Parser**: Fixes header offset changes in FCS v17 `.mod` files and accurately inspects records.
- **Fast Property-Level Conflict Checker**: Identifies conflicting records/fields, highlights the effective **Winner**, filters out false-positive conflicts from **Translation** and **Patch/Add-on** mods, and supports **click-to-jump** navigation.
- **Smart Auto-Sort**: Combines Masterlist rules, Steam Workshop category weights, dependency ordering, and automatic follow-up placement for patches and translations right after their base mods.

---

## ☕ 隨喜贊助與支持（Donation & Support）

> 💡 **特別說明**：本工具完全免費且開源，**捐款並非必要**！僅供玩家覺得本工具很好用、願意隨喜捐款鼓勵時使用。  
> 若您對我的開發工作很有興趣或有任何合作想法，也十分歡迎透過捐款備註告知，或直接來信與我交流（[`mymagadsl@gmail.com`](mailto:mymagadsl@gmail.com)）！

下方收款 QR Code 同時支援 **TWQR（台灣所有銀行行動網銀 App、台灣 Pay、全支付、一卡通 iPASS MONEY 等）** 以及 **街口支付（街口代碼 `396`／帳號 `900610912` 北極企鵝）**：

<p align="center">
  <img src="kmm/donate_qr.png" width="320" alt="TWQR / 街口支付 隨喜贊助收款碼 (北極企鵝 396-900610912)">
</p>

---

## 📜 授權條款與致謝（License & Credits）

本專案遵循原專案之 **[MIT License](LICENSE)** 授權條款釋出：

- **Python 改寫與擴充作者**：北極企鵝 (`mymagadsl@gmail.com`) — `Copyright (c) 2026 北極企鵝`
- **原始 C# 專案作者**：[MillerScout (Antonio M S S Jr.)](https://github.com/millerscout/Kenshi-Mod-Manager) — `Copyright (c) 2020 Antonio M S S Jr.`
- **自動排序規則指南**：[Steam Community Guide #1850250979](https://steamcommunity.com/sharedfiles/filedetails/?id=1850250979) / Genesis Modding Guild
