"""多國語系字串集中管理（預設：繁體中文 zh_TW，支援简体中文 zh_CN 與 English en_US）。"""
from __future__ import annotations

LANGUAGES: dict[str, str] = {
    "zh_TW": "繁體中文",
    "zh_CN": "简体中文",
    "en_US": "English",
}

_CURRENT_LANG = "zh_TW"

_LICENSE_TEXT = (
    "MIT License\n\n"
    "Copyright (c) 2020 Antonio M S S Jr. (MillerScout)\n"
    "Copyright (c) 2026 北極企鵝 (mymagadsl@gmail.com)\n\n"
    "Permission is hereby granted, free of charge, to any person obtaining a copy\n"
    "of this software and associated documentation files (the \"Software\"), to deal\n"
    "in the Software without restriction, including without limitation the rights\n"
    "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell\n"
    "copies of the Software, and to permit persons to whom the Software is\n"
    "furnished to do so, subject to the following conditions:\n\n"
    "The above copyright notice and this permission notice shall be included in all\n"
    "copies or substantial portions of the Software.\n\n"
    "THE SOFTWARE IS PROVIDED \"AS IS\", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR\n"
    "IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,\n"
    "FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE\n"
    "AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER\n"
    "LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,\n"
    "OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE\n"
    "SOFTWARE."
)

_ZH_TW: dict[str, str] = {
    "APP_TITLE": "Kenshi 模組管理器",
    "SOURCE_STEAM": "Steam",
    "SOURCE_GAME_FOLDER": "遊戲資料夾",

    # 工具列
    "BTN_SAVE_ORDER": "💾 儲存模組順序",
    "BTN_AUTO_ORDER": "🔀 自動排序",
    "BTN_CHECK_CONFLICTS": "⚠ 檢查衝突",
    "BTN_ANALYZE_LOGS": "🩺 分析當機 Log",
    "BTN_SETTINGS": "⚙ 設定",
    "BTN_UPDATE_RULES": "🔄 更新排序規則",
    "BTN_FCS": "🛠 開啟 FCS 編輯器",

    # 當機與 Log 診斷視窗
    "LA_TITLE": "🩺 Kenshi 當機與 Log 診斷分析",
    "LA_ANALYZING": "正在掃描並分析遊戲 Log、RE_Kenshi 外掛與 CrashDump 紀錄…",
    "LA_BTN_REANALYZE": "🔄 重新分析",
    "LA_BTN_CLEAN_LOGS": "🗑 清理遊戲 Log",
    "LA_BTN_COPY": "📋 複製完整報告",
    "LA_BTN_OPEN_DIR": "📂 開啟遊戲目錄",
    "LA_SUSPECTS_HINT": "🎯 可疑當機來源模組排行（點擊按鈕可直接跳轉並選取主視窗中的該模組）：",
    "LA_NO_SUSPECTS": "目前未在 Log 中偵測到明確的當機可疑模組。",
    "LA_JUMPED_TO_MOD": "✔ 已在主視窗清單中定位並選取模組：{name}",
    "LA_MOD_NOT_IN_LIST": "ℹ 「{name}」屬於獨立 DLL 外掛或未列於模組清單中。",
    "LA_COPIED": "✔ 診斷報告已複製到剪貼簿！",
    "LA_CLEAN_NONE": "目前遊戲目錄中沒有可清理的 Log 或 CrashDump 檔案。",
    "LA_CLEAN_CONFIRM": (
        "掃描到遊戲目錄與 RE_Kenshi 中共有 {n} 個日誌／崩潰傾印檔案（合計 {size}）：\n\n"
        "{preview}\n\n"
        "確定要清除這些舊 Log 與 CrashDump 檔案以釋放空間並避免干擾後續診斷嗎？"
    ),
    "LA_CLEAN_DONE": "✔ 已成功清理 {n} 個遊戲 Log 與 CrashDump 檔案（釋放 {size}）！",
    "LA_CLEAN_ERRORS": "已清理 {n} 個檔案（釋放 {size}），但有部分檔案無法刪除：\n{e}",

    # 搜尋 / 篩選
    "SEARCH_PLACEHOLDER": "搜尋模組中文譯名、英文名稱或 Steam ID…（Enter 跳到下一筆）",
    "BTN_REFRESH": "重新整理",
    "FILTER_LABEL": "篩選：",
    "FILTER_STEAM": "Steam 模組",
    "FILTER_REGULAR": "一般模組",
    "FILTER_ACTIVE_ONLY": "只顯示已啟用",
    "FILTER_CONFLICT_ONLY": "只顯示有衝突",
    "FILTER_IGNORE_TRANSLATION": "排除漢化衝突",
    "FILTER_IGNORE_PATCH": "排除補丁衝突",
    "FILTER_SHOW_ZH_NAME": "顯示中文譯名",
    "SEARCH_NOT_FOUND": "找不到符合的模組",
    "SEARCH_FOUND": "找到 {cur}/{total}",
    "STATUS_SUMMARY": "共 {total} 個模組，已啟用 {active} 個",
    "STATUS_SUMMARY_CONFLICTS": "共 {total} 個模組，已啟用 {active} 個｜衝突模組：{cmods} 個（{citems} 項）",

    # 列表欄位
    "COL_ACTIVE": "啟用",
    "COL_ORDER": "順序",
    "COL_NAME": "名稱",
    "COL_CATEGORIES": "分類",
    "COL_SOURCE": "來源",

    # 右鍵選單
    "MENU_VISIT_PAGE": "前往模組頁面",
    "MENU_OPEN_FOLDER": "開啟模組資料夾",
    "MENU_EDIT_ZH_NAME": "✏ 設定中文別名／備註…",
    "MENU_TRANSLATE_MISSING": "🌐 自動翻譯未知英文模組",
    "MENU_ACTIVATE": "啟用選取的模組",
    "MENU_DEACTIVATE": "停用選取的模組",
    "MENU_TOGGLE": "切換選取模組的啟用狀態",
    "MENU_MOVE_TOP": "移到最前面",
    "MENU_MOVE_BOTTOM": "移到最後面",
    "MENU_UNSUBSCRIBE": "在 Steam 取消訂閱（開啟工作坊頁面）",
    "MENU_REMOVE_MISSING": "移除該資料夾不存在的模組",
    "MENU_REMOVE_INACTIVE": "移除未勾選的模組與資料夾",

    # 下方按鈕
    "BTN_OPEN_GAME": "開啟遊戲資料夾",
    "BTN_OPEN_GAME_MODS": "開啟遊戲 Mods 資料夾",
    "BTN_OPEN_STEAM_MODS": "開啟 Steam 模組資料夾",
    "BTN_FOLDER_TOOL": "資料夾管理",
    "BTN_SAVE_PROFILE": "儲存設定檔",
    "BTN_LOAD_PROFILE": "載入設定檔",
    "BTN_ABOUT": "ℹ 關於",
    "BTN_LAUNCH": "▶ 啟動遊戲",

    # 詳細資訊
    "D_ZH_NAME": "中文譯名：",
    "D_WORKSHOP_TITLE": "工作坊標題：",
    "D_TRANSLATION": "漢化辨識：",
    "D_TRANSLATION_TARGET": "🌐 漢化模組（自動配對原版：{targets}）",
    "D_TRANSLATION_GLOBAL": "🌐 全域／獨立漢化模組",
    "D_PATCH": "補丁辨識：",
    "D_PATCH_TARGET": "🔧 補丁／擴充模組（自動配對主模組：{targets}）",
    "D_DEPENDENCIES": "相依：",
    "D_REFERENCES": "參考：",
    "D_AUTHOR": "作者：",
    "D_VERSION": "版本：",
    "D_PATH": "路徑：",
    "D_URL": "網址：",
    "D_DESCRIPTION": "描述：",
    "D_STEAM_ID": "Steam ID：",
    "D_LEGEND": "（綠色 = 已在此模組之前載入；紅色 = 缺少或順序在後面）",
    "D_EMPTY": "選擇一個模組以查看詳細資訊。",
    "D_CONFLICTS_HEADER": "══════════ 模組衝突明細（共 {n} 項，依載入順序排列）══════════",
    "D_CONFLICTS_HINT": "提示：點擊下方衝突明細中的「模組名稱」可直接跳轉選取該模組；調整順序後請再次點擊「⚠ 檢查衝突」。",
    "D_CONFLICTS_WINNER": "  ◀ 最終生效",
    "D_CONFLICTS_MORE": "…尚有 {more} 項衝突未顯示（僅列出前 {shown} 項）。",

    # 訊息
    "DLG_EDIT_ZH_TITLE": "設定模組中文別名",
    "DLG_EDIT_ZH_PROMPT": "請輸入「{name}」的繁體中文別名（留空則恢復自動判斷）：",
    "MSG_TRANSLATING_MODS": "正在線上翻譯未知模組名稱 ({cur}/{total})：{name}…",
    "MSG_TRANSLATE_NONE": "目前所有模組皆已有中文譯名，無需額外翻譯！",
    "MSG_TRANSLATE_DONE": "自動翻譯完成：已新增 {n} 個模組的繁體中文譯名（已快取至 mod_names_zh.json）。",
    "MSG_TITLE_INFO": "提示",
    "MSG_TITLE_ERROR": "錯誤",
    "MSG_TITLE_CONFIRM": "確認",
    "MSG_GAME_FOLDER_BAD": "遊戲資料夾設定不正確，請到「設定」檢查遊戲路徑。",
    "MSG_STEAM_FOLDER_BAD": "Steam 模組資料夾設定不正確。",
    "MSG_SAVED": "已儲存 {n} 個啟用模組到 mods.cfg（舊檔已備份為 mods.cfg.backup）。",
    "MSG_NOT_SAVED": "模組順序未儲存！",
    "MSG_SAVE_PERMISSION_DENIED": (
        "無法寫入檔案（權限不足或檔案被其他程式鎖定）：\n{err}\n\n"
        "請確認遊戲或 FCS 編輯器未鎖定該檔案，或以「系統管理員身分」執行本程式。"
    ),
    "MSG_ASK_STEAM": "找不到 Steam 版 Kenshi。\n\n你使用的是 Steam 版嗎？\n（選「否」會改為只讀取遊戲 Mods 資料夾）",
    "MSG_ASK_GAME_FOLDER": "請選擇 Kenshi 遊戲資料夾（包含 kenshi_x64.exe 的資料夾）",
    "MSG_NUMBERS_ONLY": "請輸入數字！",
    "MSG_GAME_NOT_FOUND": "找不到 kenshi_x64.exe，請檢查遊戲路徑。",
    "MSG_FCS_NOT_FOUND": "找不到 forgotten construction set.exe。",
    "MSG_AUTO_ORDER_CONFIRM": (
        "自動排序會依照 masterlist 規則、Steam 工作坊分類標籤，\n"
        "以及補丁／漢化模組自動跟隨原則重新排列所有模組順序。\n\n"
        "確定要繼續嗎？（排序後仍需按「儲存模組順序」才會寫入）"
    ),
    "MSG_AUTO_ORDER_DONE": "自動排序完成，確認無誤後請按「儲存模組順序」。",
    "MSG_RULES_UPDATED": "排序規則已更新到版本 {v}。",
    "MSG_RULES_LATEST": "排序規則已是最新版本（{v}）。",
    "MSG_RULES_FAILED": "無法連線取得排序規則，將使用本機規則。",
    "MSG_PROFILE_LOADED": "已載入設定檔：對應到 {hit}/{total} 個模組。",
    "MSG_UNSAVED_EXIT": "模組順序有變更尚未儲存，確定要離開嗎？",
    "MSG_LOADING": "正在讀取模組…",
    "MSG_DRAG_NEED_ORDER_SORT": "請先依「順序」欄位排序，才能拖曳調整順序。",
    "MSG_NO_STEAM_ID": "這個模組沒有 Steam ID。",
    "MSG_NEED_ACTIVE_FOR_CONFLICT": "請先啟用至少 2 個模組再檢查衝突。",
    "MSG_CHECKING_CONFLICTS": "正在檢查衝突 ({cur}/{total})：{name}…",
    "MSG_CONFLICTS_DONE": "衝突檢查完成：在 {cmods} 個模組中發現 {citems} 項屬性衝突（耗時 {sec:.2f} 秒）。",
    "MSG_CONFLICTS_DONE_SKIPPED": "衝突檢查完成：在 {cmods} 個模組中發現 {citems} 項屬性衝突（已排除漢化 {skipped_trans} 個、補丁 {skipped_patch} 個，耗時 {sec:.2f} 秒）。",
    "MSG_CONFLICTS_NONE": "衝突檢查完成：未發現任何模組衝突！",
    "MSG_NO_MISSING_MODS": "目前沒有任何「資料夾不存在」或「缺少 .mod 檔案」的無效模組。",
    "MSG_CONFIRM_REMOVE_MISSING": (
        "找到 {n} 個無效模組（資料夾不存在或缺少 .mod 檔案）：\n\n"
        "{preview}\n\n"
        "確定要將這些無效模組與殘留資料夾一併移除嗎？"
    ),
    "MSG_NO_INACTIVE_MODS": "目前沒有任何「未勾選（未啟用）」的模組。",
    "MSG_CONFIRM_REMOVE_INACTIVE": (
        "⚠ 警告：即將從硬碟永久刪除 {n} 個「未勾選」的模組與其資料夾！\n\n"
        "{preview}\n\n"
        "（注意：若是 Steam 工作坊模組且未取消訂閱，Steam 下次可能會重新下載）\n"
        "確定要刪除這 {n} 個未勾選模組與資料夾嗎？"
    ),
    "MSG_REMOVE_DONE": "已成功移除 {n} 個模組與其資料夾。",
    "MSG_REMOVE_ERRORS": "已移除 {n} 個模組，但有部分資料夾刪除失敗：\n{e}",

    # 設定視窗
    "SET_TITLE": "設定",
    "SET_GAME_PATH": "遊戲資料夾",
    "SET_STEAM_PATH": "Steam 模組資料夾（不使用 Steam 請填 NONE）",
    "SET_MASTERLIST": "Masterlist 來源（GitHub 儲存庫）",
    "SET_LANGUAGE": "操作介面語言 (Language)",
    "SET_AUTO_UPDATE": "啟動時自動檢查排序規則更新",
    "SET_BROWSE": "瀏覽…",
    "SET_AUTODETECT": "自動偵測",
    "SET_CLEAR_LOGS": "🗑 清除備份與日誌",
    "SET_LOGS_CLEARED": "已清除 {n} 個訂閱備份與管理日誌，以及 {gn} 個遊戲 Log／CrashDump 檔案（釋放 {size}）。",
    "SET_SAVE": "儲存",
    "SET_CANCEL": "取消",
    "SET_SAVED": "設定已儲存，模組清單將重新讀取。",
    "SET_DETECT_FAIL": "無法自動偵測 Steam 版 Kenshi。",

    # 資料夾管理視窗
    "FT_TITLE": "資料夾管理",
    "FT_HELP": (
        "把 Steam 工作坊模組以「目錄連接點」連結到遊戲 Mods 資料夾（不需要系統管理員權限）。\n"
        "🔗 表示已建立連結。勾選模組後使用下方按鈕。"
    ),
    "FT_SELECT_ALL": "全選",
    "FT_INVERT": "反向選取",
    "FT_CLEAR_EMPTY": "清除空資料夾",
    "FT_CREATE_LINKS": "為勾選項目建立連結",
    "FT_REMOVE_LINKS": "移除勾選項目的連結",
    "FT_TOGGLE_LINKS": "切換勾選項目的連結",
    "FT_COL_SELECTED": "勾選",
    "FT_COL_LINK": "連結",
    "FT_DONE_CREATE": "已建立 {n} 個連結。",
    "FT_DONE_REMOVE": "已移除 {n} 個連結。",
    "FT_DONE_CLEAN": "已刪除 {n} 個空資料夾。",
    "FT_ERRORS": "部分連結建立失敗：\n{e}",
    "FT_NOTHING": "沒有勾選任何可處理的 Steam 模組。",

    # 關於視窗
    "ABOUT_TITLE": "關於 Kenshi 模組管理器",
    "ABOUT_HEADING": "Kenshi 模組管理器（Python 繁體中文改寫版）",
    "ABOUT_REWRITE_AUTHOR": "作者：北極企鵝 (mymagadsl@gmail.com)",
    "ABOUT_ORIGINAL_AUTHOR": "原始作者：MillerScout (Antonio M S S Jr.)",
    "ABOUT_ORIGINAL_REPO_URL": "https://github.com/millerscout/Kenshi-Mod-Manager",
    "ABOUT_SORT_GUIDE_URL": "https://steamcommunity.com/sharedfiles/filedetails/?id=1850250979",
    "ABOUT_OPEN_ORIG_REPO": "🔗 開啟原始專案 GitHub",
    "ABOUT_OPEN_SORT_GUIDE": "📖 開啟自動排序規則指南",
    "ABOUT_CLOSE": "關閉",
    "ABOUT_DONATE_TITLE": "☕ 隨喜贊助支持（非必要）",
    "ABOUT_DONATE_NOTE": (
        "本工具完全免費開源，僅是玩家覺得很好用、願意捐款鼓勵時才使用，並非必要！\n"
        "若您對我的工作很有興趣，也十分歡迎捐款告知或來信交流（mymagadsl@gmail.com）。\n"
        "支援：TWQR（全台各家銀行／電支）與 街口支付 (396-900610912)"
    ),
    "ABOUT_DONATE_ZOOM": "🔍 點擊放大檢視收款 QR Code",
    "ABOUT_DESCRIPTION_TEXT": (
        "【專案改寫與致謝聲明】\n"
        "• Python 改寫與擴充作者：北極企鵝 (mymagadsl@gmail.com)\n"
        "• 原始專案作者：MillerScout (Antonio M S S Jr.)\n"
        "• 原始專案網址：https://github.com/millerscout/Kenshi-Mod-Manager\n"
        "• 排序規則參考來源：Steam 社群指南 (id=1850250979) / Genesis Modding Guild\n\n"
        "【新增與強化功能一覽】\n"
        "本軟體係基於原作者 MillerScout 所開發之 C# 版 Kenshi-Mod-Manager，\n"
        "由北極企鵝使用 Python + CustomTkinter 重新改寫並大幅強化，包含：\n"
        "  1. 完整支援 Kenshi FCS v17 最新二進位模組檔頭格式與紀錄解析\n"
        "  2. 高速模組屬性衝突檢查器：標示最終生效者（Winner），並支援點擊衝突明細中的模組名稱一鍵跳轉定位\n"
        "  3. 智慧辨識「漢化模組」與「補丁／擴充模組」：自動配對原版主模組，提供「排除漢化衝突」與「排除補丁衝突」篩選開關，消除假警報衝突\n"
        "  4. 進階智慧自動排序：結合 Masterlist 規則、Steam 工作坊分類標籤（Categories）權重推斷，並讓補丁與漢化模組自動緊跟在原版主模組之後\n"
        "  5. 四層智慧中文模組譯名系統：\n"
        "     • 自動提取工作坊 .info 標題中的中文並自動簡轉繁\n"
        "     • 從已安裝的漢化包反向推導英文原版模組的中文名稱\n"
        "     • 內建百大熱門模組繁中辭典（base_mod_names_zh.json）與自訂辭典（mod_names_zh.json）\n"
        "     • 右鍵支援「✏ 設定中文別名／備註…」與「🌐 自動翻譯未知英文模組（線上翻譯並本機快取）」\n"
        "  6. 右鍵一鍵清理工具：支援「移除該資料夾不存在的模組」與「移除未勾選的模組與資料夾」\n"
        "  7. 重複 .mod 自動去重與唯讀權限防護：自動跳過子目錄備份 .mod，並於儲存時自動解除唯讀屬性\n"
        "  8. 備份與日誌集中管理：將訂閱備份（bkpsubscribedList）與日誌統一收納至 logs/ 資料夾，並於設定視窗提供「🗑 清除備份與日誌」功能\n"
        "  9. 多語言操作介面即時切換：支援繁體中文（預設）、简体中文、English 三語無須重啟即時熱切換\n\n"
        "══════════════════════ 授權條款（MIT License）══════════════════════\n"
        "本專案遵循原專案之 MIT 授權條款釋出，保留原作者版權宣告如下：\n\n"
        + _LICENSE_TEXT
    ),
}

_ZH_CN: dict[str, str] = {
    "APP_TITLE": "Kenshi 模组管理器",
    "SOURCE_STEAM": "Steam",
    "SOURCE_GAME_FOLDER": "游戏文件夹",

    # 工具栏
    "BTN_SAVE_ORDER": "💾 保存模组顺序",
    "BTN_AUTO_ORDER": "🔀 自动排序",
    "BTN_CHECK_CONFLICTS": "⚠ 检查冲突",
    "BTN_ANALYZE_LOGS": "🩺 分析崩溃 Log",
    "BTN_SETTINGS": "⚙ 设置",
    "BTN_UPDATE_RULES": "🔄 更新排序规则",
    "BTN_FCS": "🛠 打开 FCS 编辑器",

    # 崩溃与 Log 诊断窗口
    "LA_TITLE": "🩺 Kenshi 崩溃与 Log 诊断分析",
    "LA_ANALYZING": "正在扫描并分析游戏 Log、RE_Kenshi 插件与 CrashDump 记录…",
    "LA_BTN_REANALYZE": "🔄 重新分析",
    "LA_BTN_CLEAN_LOGS": "🗑 清理游戏 Log",
    "LA_BTN_COPY": "📋 复制完整报告",
    "LA_BTN_OPEN_DIR": "📂 打开游戏目录",
    "LA_SUSPECTS_HINT": "🎯 可疑崩溃来源模组排行（点击按钮可直接跳转并选中主窗口中的该模组）：",
    "LA_NO_SUSPECTS": "当前未在 Log 中检测到明确的崩溃可疑模组。",
    "LA_JUMPED_TO_MOD": "✔ 已在主窗口列表中定位并选中模组：{name}",
    "LA_MOD_NOT_IN_LIST": "ℹ “{name}”属于独立 DLL 插件或未列于模组列表中。",
    "LA_COPIED": "✔ 诊断报告已复制到剪贴板！",
    "LA_CLEAN_NONE": "当前游戏目录中没有可清理的 Log 或 CrashDump 文件。",
    "LA_CLEAN_CONFIRM": (
        "扫描到游戏目录与 RE_Kenshi 中共有 {n} 个日志／崩溃转储文件（合计 {size}）：\n\n"
        "{preview}\n\n"
        "确定要清除这些旧 Log 与 CrashDump 文件以释放空间并避免干扰后续诊断吗？"
    ),
    "LA_CLEAN_DONE": "✔ 已成功清理 {n} 个游戏 Log 与 CrashDump 文件（释放 {size}）！",
    "LA_CLEAN_ERRORS": "已清理 {n} 个文件（释放 {size}），但有部分文件无法删除：\n{e}",

    # 搜索 / 筛选
    "SEARCH_PLACEHOLDER": "搜索模组中文译名、英文名称或 Steam ID…（Enter 跳到下一项）",
    "BTN_REFRESH": "刷新",
    "FILTER_LABEL": "筛选：",
    "FILTER_STEAM": "Steam 模组",
    "FILTER_REGULAR": "本地模组",
    "FILTER_ACTIVE_ONLY": "只显示已启用",
    "FILTER_CONFLICT_ONLY": "只显示有冲突",
    "FILTER_IGNORE_TRANSLATION": "排除汉化冲突",
    "FILTER_IGNORE_PATCH": "排除补丁冲突",
    "FILTER_SHOW_ZH_NAME": "显示中文译名",
    "SEARCH_NOT_FOUND": "找不到符合的模组",
    "SEARCH_FOUND": "找到 {cur}/{total}",
    "STATUS_SUMMARY": "共 {total} 个模组，已启用 {active} 个",
    "STATUS_SUMMARY_CONFLICTS": "共 {total} 个模组，已启用 {active} 个｜冲突模组：{cmods} 个（{citems} 项）",

    # 列表字段
    "COL_ACTIVE": "启用",
    "COL_ORDER": "顺序",
    "COL_NAME": "名称",
    "COL_CATEGORIES": "分类",
    "COL_SOURCE": "来源",

    # 右键菜单
    "MENU_VISIT_PAGE": "访问模组页面",
    "MENU_OPEN_FOLDER": "打开模组文件夹",
    "MENU_EDIT_ZH_NAME": "✏ 设置中文别名／备注…",
    "MENU_TRANSLATE_MISSING": "🌐 自动翻译未知英文模组",
    "MENU_ACTIVATE": "启用选中的模组",
    "MENU_DEACTIVATE": "禁用选中的模组",
    "MENU_TOGGLE": "切换选中模组的启用状态",
    "MENU_MOVE_TOP": "移到最顶部",
    "MENU_MOVE_BOTTOM": "移到最底部",
    "MENU_UNSUBSCRIBE": "在 Steam 取消订阅（打开创意工坊页面）",
    "MENU_REMOVE_MISSING": "移除该文件夹不存在的模组",
    "MENU_REMOVE_INACTIVE": "移除未勾选的模组与文件夹",

    # 下方按钮
    "BTN_OPEN_GAME": "打开游戏文件夹",
    "BTN_OPEN_GAME_MODS": "打开游戏 Mods 文件夹",
    "BTN_OPEN_STEAM_MODS": "打开 Steam 模组文件夹",
    "BTN_FOLDER_TOOL": "文件夹管理",
    "BTN_SAVE_PROFILE": "保存配置文件",
    "BTN_LOAD_PROFILE": "加载配置文件",
    "BTN_ABOUT": "ℹ 关于",
    "BTN_LAUNCH": "▶ 启动游戏",

    # 详细信息
    "D_ZH_NAME": "中文译名：",
    "D_WORKSHOP_TITLE": "工坊标题：",
    "D_TRANSLATION": "汉化识别：",
    "D_TRANSLATION_TARGET": "🌐 汉化模组（自动配对原版：{targets}）",
    "D_TRANSLATION_GLOBAL": "🌐 全局／独立汉化模组",
    "D_PATCH": "补丁识别：",
    "D_PATCH_TARGET": "🔧 补丁／扩展模组（自动配对主模组：{targets}）",
    "D_DEPENDENCIES": "依赖：",
    "D_REFERENCES": "引用：",
    "D_AUTHOR": "作者：",
    "D_VERSION": "版本：",
    "D_PATH": "路径：",
    "D_URL": "网址：",
    "D_DESCRIPTION": "描述：",
    "D_STEAM_ID": "Steam ID：",
    "D_LEGEND": "（绿色 = 已在此模组之前加载；红色 = 缺失或顺序在后面）",
    "D_EMPTY": "选择一个模组以查看详细信息。",
    "D_CONFLICTS_HEADER": "══════════ 模组冲突明细（共 {n} 项，按加载顺序排列）══════════",
    "D_CONFLICTS_HINT": "提示：点击下方冲突明细中的“模组名称”可直接跳转选中该模组；调整顺序后请再次点击“⚠ 检查冲突”。",
    "D_CONFLICTS_WINNER": "  ◀ 最终生效",
    "D_CONFLICTS_MORE": "…还有 {more} 项冲突未显示（仅列出前 {shown} 项）。",

    # 消息
    "DLG_EDIT_ZH_TITLE": "设置模组中文别名",
    "DLG_EDIT_ZH_PROMPT": "请输入“{name}”的中文别名（留空则恢复自动判断）：",
    "MSG_TRANSLATING_MODS": "正在在线翻译未知模组名称 ({cur}/{total})：{name}…",
    "MSG_TRANSLATE_NONE": "当前所有模组均已有中文译名，无需额外翻译！",
    "MSG_TRANSLATE_DONE": "自动翻译完成：已新增 {n} 个模组的中文译名（已缓存至 mod_names_zh.json）。",
    "MSG_TITLE_INFO": "提示",
    "MSG_TITLE_ERROR": "错误",
    "MSG_TITLE_CONFIRM": "确认",
    "MSG_GAME_FOLDER_BAD": "游戏文件夹设置不正确，请到“设置”检查游戏路径。",
    "MSG_STEAM_FOLDER_BAD": "Steam 模组文件夹设置不正确。",
    "MSG_SAVED": "已保存 {n} 个启用模组到 mods.cfg（旧文件已备份为 mods.cfg.backup）。",
    "MSG_NOT_SAVED": "模组顺序未保存！",
    "MSG_SAVE_PERMISSION_DENIED": (
        "无法写入文件（权限不足或文件被其他程序锁定）：\n{err}\n\n"
        "请确认游戏或 FCS 编辑器未锁定该文件，或以“管理员身份”运行本程序。"
    ),
    "MSG_ASK_STEAM": "找不到 Steam 版 Kenshi。\n\n你使用的是 Steam 版吗？\n（选“否”将改为只读取游戏 Mods 文件夹）",
    "MSG_ASK_GAME_FOLDER": "请选择 Kenshi 游戏文件夹（包含 kenshi_x64.exe 的文件夹）",
    "MSG_NUMBERS_ONLY": "请输入数字！",
    "MSG_GAME_NOT_FOUND": "找不到 kenshi_x64.exe，请检查游戏路径。",
    "MSG_FCS_NOT_FOUND": "找不到 forgotten construction set.exe。",
    "MSG_AUTO_ORDER_CONFIRM": (
        "自动排序会按照 masterlist 规则、Steam 创意工坊分类标签，\n"
        "以及补丁／汉化模组自动跟随原则重新排列所有模组顺序。\n\n"
        "确定要继续吗？（排序后仍需按“保存模组顺序”才会写入）"
    ),
    "MSG_AUTO_ORDER_DONE": "自动排序完成，确认无误后请按“保存模组顺序”。",
    "MSG_RULES_UPDATED": "排序规则已更新到版本 {v}。",
    "MSG_RULES_LATEST": "排序规则已是最新版本（{v}）。",
    "MSG_RULES_FAILED": "无法连接获取排序规则，将使用本地规则。",
    "MSG_PROFILE_LOADED": "已加载配置文件：匹配到 {hit}/{total} 个模组。",
    "MSG_UNSAVED_EXIT": "模组顺序有变更尚未保存，确定要退出吗？",
    "MSG_LOADING": "正在读取模组…",
    "MSG_DRAG_NEED_ORDER_SORT": "请先按“顺序”列排序，才能拖拽调整顺序。",
    "MSG_NO_STEAM_ID": "这个模组没有 Steam ID。",
    "MSG_NEED_ACTIVE_FOR_CONFLICT": "请先启用至少 2 个模组再检查冲突。",
    "MSG_CHECKING_CONFLICTS": "正在检查冲突 ({cur}/{total})：{name}…",
    "MSG_CONFLICTS_DONE": "冲突检查完成：在 {cmods} 个模组中发现 {citems} 项属性冲突（耗时 {sec:.2f} 秒）。",
    "MSG_CONFLICTS_DONE_SKIPPED": "冲突检查完成：在 {cmods} 个模组中发现 {citems} 项属性冲突（已排除汉化 {skipped_trans} 个、补丁 {skipped_patch} 个，耗时 {sec:.2f} 秒）。",
    "MSG_CONFLICTS_NONE": "冲突检查完成：未发现任何模组冲突！",
    "MSG_NO_MISSING_MODS": "当前没有任何“文件夹不存在”或“缺少 .mod 文件”的无效模组。",
    "MSG_CONFIRM_REMOVE_MISSING": (
        "找到 {n} 个无效模组（文件夹不存在或缺少 .mod 文件）：\n\n"
        "{preview}\n\n"
        "确定要将这些无效模组与残留文件夹一并移除吗？"
    ),
    "MSG_NO_INACTIVE_MODS": "当前没有任何“未勾选（未启用）”的模组。",
    "MSG_CONFIRM_REMOVE_INACTIVE": (
        "⚠ 警告：即将从硬盘永久删除 {n} 个“未勾选”的模组与其文件夹！\n\n"
        "{preview}\n\n"
        "（注意：若是 Steam 创意工坊模组且未取消订阅，Steam 下次可能会重新下载）\n"
        "确定要删除这 {n} 个未勾选模组与文件夹吗？"
    ),
    "MSG_REMOVE_DONE": "已成功移除 {n} 个模组与其文件夹。",
    "MSG_REMOVE_ERRORS": "已移除 {n} 个模组，但有部分文件夹删除失败：\n{e}",

    # 设置窗口
    "SET_TITLE": "设置",
    "SET_GAME_PATH": "游戏文件夹",
    "SET_STEAM_PATH": "Steam 模组文件夹（不使用 Steam 请填 NONE）",
    "SET_MASTERLIST": "Masterlist 来源（GitHub 仓库）",
    "SET_LANGUAGE": "操作界面语言 (Language)",
    "SET_AUTO_UPDATE": "启动时自动检查排序规则更新",
    "SET_BROWSE": "浏览…",
    "SET_AUTODETECT": "自动检测",
    "SET_CLEAR_LOGS": "🗑 清除备份与日志",
    "SET_LOGS_CLEARED": "已清除 {n} 个订阅备份与管理日志，以及 {gn} 个游戏 Log／CrashDump 文件（释放 {size}）。",
    "SET_SAVE": "保存",
    "SET_CANCEL": "取消",
    "SET_SAVED": "设置已保存，模组列表将重新读取。",
    "SET_DETECT_FAIL": "无法自动检测 Steam 版 Kenshi。",

    # 文件夹管理窗口
    "FT_TITLE": "文件夹管理",
    "FT_HELP": (
        "把 Steam 创意工坊模组以“目录联接点”链接到游戏 Mods 文件夹（不需要管理员权限）。\n"
        "🔗 表示已建立链接。勾选模组后使用下方按钮。"
    ),
    "FT_SELECT_ALL": "全选",
    "FT_INVERT": "反向选择",
    "FT_CLEAR_EMPTY": "清除空文件夹",
    "FT_CREATE_LINKS": "为勾选项目建立链接",
    "FT_REMOVE_LINKS": "移除勾选项目的链接",
    "FT_TOGGLE_LINKS": "切换勾选项目的链接",
    "FT_COL_SELECTED": "勾选",
    "FT_COL_LINK": "链接",
    "FT_DONE_CREATE": "已建立 {n} 个链接。",
    "FT_DONE_REMOVE": "已移除 {n} 个链接。",
    "FT_DONE_CLEAN": "已删除 {n} 个空文件夹。",
    "FT_ERRORS": "部分链接建立失败：\n{e}",
    "FT_NOTHING": "没有勾选任何可处理的 Steam 模组。",

    # 关于窗口
    "ABOUT_TITLE": "关于 Kenshi 模组管理器",
    "ABOUT_HEADING": "Kenshi 模组管理器（Python 改写增强版）",
    "ABOUT_REWRITE_AUTHOR": "作者：北極企鵝 (mymagadsl@gmail.com)",
    "ABOUT_ORIGINAL_AUTHOR": "原始作者：MillerScout (Antonio M S S Jr.)",
    "ABOUT_ORIGINAL_REPO_URL": "https://github.com/millerscout/Kenshi-Mod-Manager",
    "ABOUT_SORT_GUIDE_URL": "https://steamcommunity.com/sharedfiles/filedetails/?id=1850250979",
    "ABOUT_OPEN_ORIG_REPO": "🔗 打开原始项目 GitHub",
    "ABOUT_OPEN_SORT_GUIDE": "📖 打开自动排序规则指南",
    "ABOUT_CLOSE": "关闭",
    "ABOUT_DONATE_TITLE": "☕ 随喜赞助支持（非必要）",
    "ABOUT_DONATE_NOTE": (
        "本工具完全免费开源，仅是玩家觉得很好用、愿意捐款鼓励时才使用，并非必要！\n"
        "若您对我的工作很有兴趣，也十分欢迎捐款告知或来信交流（mymagadsl@gmail.com）。\n"
        "支持：TWQR（全台各家银行／电支）与 街口支付 (396-900610912)"
    ),
    "ABOUT_DONATE_ZOOM": "🔍 点击放大查看收款 QR Code",
    "ABOUT_DESCRIPTION_TEXT": (
        "【项目改写与致谢声明】\n"
        "• Python 改写与扩展作者：北極企鵝 (mymagadsl@gmail.com)\n"
        "• 原始项目作者：MillerScout (Antonio M S S Jr.)\n"
        "• 原始项目网址：https://github.com/millerscout/Kenshi-Mod-Manager\n"
        "• 排序规则参考来源：Steam 社区指南 (id=1850250979) / Genesis Modding Guild\n\n"
        "【新增与强化功能一览】\n"
        "本软件基于原作者 MillerScout 开发的 C# 版 Kenshi-Mod-Manager，\n"
        "由北極企鵝使用 Python + CustomTkinter 重新改写并大幅强化，包含：\n"
        "  1. 完整支持 Kenshi FCS v17 最新二进制模组文件头格式与记录解析\n"
        "  2. 高速模组属性冲突检查器：标示最终生效者（Winner），并支持点击冲突明细中的模组名称一键跳转定位\n"
        "  3. 智能识别“汉化模组”与“补丁／扩展模组”：自动配对原版主模组，提供“排除汉化冲突”与“排除补丁冲突”筛选开关，消除误报冲突\n"
        "  4. 进阶智能自动排序：结合 Masterlist 规则、Steam 创意工坊分类标签（Categories）权重推断，并让补丁与汉化模组自动紧跟在原版主模组之后\n"
        "  5. 四层智能中文模组译名系统：\n"
        "     • 自动提取创意工坊 .info 标题中的中文\n"
        "     • 从已安装的汉化包反向推导英文原版模组的中文名称\n"
        "     • 内置百大热门模组中文辞典（base_mod_names_zh.json）与自定义辞典（mod_names_zh.json）\n"
        "     • 右键支持“✏ 设置中文别名／备注…”与“🌐 自动翻译未知英文模组（在线翻译并本地缓存）”\n"
        "  6. 右键一键清理工具：支持“移除该文件夹不存在的模组”与“移除未勾选的模组与文件夹”\n"
        "  7. 重复 .mod 自动去重与只读权限防护：自动跳过子目录备份 .mod，并于保存时自动解除只读属性\n"
        "  8. 备份与日志集中管理：将订阅备份（bkpsubscribedList）与日志统一收纳至 logs/ 文件夹，并于设置窗口提供“🗑 清除备份与日志”功能\n"
        "  9. 多语言操作界面即时切换：支持繁體中文（默认）、简体中文、English 三语无须重启即时热切换\n\n"
        "══════════════════════ 授权条款（MIT License）══════════════════════\n"
        "本项目遵循原项目的 MIT 授权条款发布，保留原作者版权声明如下：\n\n"
        + _LICENSE_TEXT
    ),
}

_EN_US: dict[str, str] = {
    "APP_TITLE": "Kenshi Mod Manager",
    "SOURCE_STEAM": "Steam",
    "SOURCE_GAME_FOLDER": "Game Folder",

    # Toolbar
    "BTN_SAVE_ORDER": "💾 Save Load Order",
    "BTN_AUTO_ORDER": "🔀 Auto Sort",
    "BTN_CHECK_CONFLICTS": "⚠ Check Conflicts",
    "BTN_ANALYZE_LOGS": "🩺 Analyze Crash Logs",
    "BTN_SETTINGS": "⚙ Settings",
    "BTN_UPDATE_RULES": "🔄 Update Rules",
    "BTN_FCS": "🛠 Launch FCS",

    # Log Analyzer Window
    "LA_TITLE": "🩺 Kenshi Crash & Log Diagnostic Analyzer",
    "LA_ANALYZING": "Scanning and analyzing Kenshi logs, RE_Kenshi plugins, and CrashDumps…",
    "LA_BTN_REANALYZE": "🔄 Re-Analyze",
    "LA_BTN_COPY": "📋 Copy Report",
    "LA_BTN_OPEN_DIR": "📂 Open Game Dir",
    "LA_BTN_CLEAN_LOGS": "🗑 Clean Game Logs",
    "LA_SUSPECTS_HINT": "🎯 Suspected Crash Source Mods (Click to jump & select in main window):",
    "LA_NO_SUSPECTS": "No specific suspected crash mods detected in current logs.",
    "LA_JUMPED_TO_MOD": "✔ Jumped to and selected mod in main window: {name}",
    "LA_MOD_NOT_IN_LIST": "ℹ '{name}' is a standalone DLL plugin or not in the mod list.",
    "LA_COPIED": "✔ Diagnostic report copied to clipboard!",
    "LA_CLEAN_NONE": "There are currently no game logs or CrashDump files to clean.",
    "LA_CLEAN_CONFIRM": (
        "Detected {n} game logs & CrashDump files (Total size: {size}):\n\n"
        "{preview}\n\n"
        "Are you sure you want to delete these log files to free up space?\n"
        "(Kenshi will automatically regenerate new logs on next launch)"
    ),
    "LA_CLEAN_DONE": "✔ Cleaned {n} game log files, freed {size} of disk space!",
    "LA_CLEAN_ERRORS": "Cleaned {n} files (freed {size}), but some files are locked and could not be deleted:\n{e}",

    # Search / Filter
    "SEARCH_PLACEHOLDER": "Search mod name, translated title, or Steam ID… (Enter for next)",
    "BTN_REFRESH": "Refresh",
    "FILTER_LABEL": "Filter:",
    "FILTER_STEAM": "Steam Mods",
    "FILTER_REGULAR": "Local Mods",
    "FILTER_ACTIVE_ONLY": "Active Only",
    "FILTER_CONFLICT_ONLY": "Conflicts Only",
    "FILTER_IGNORE_TRANSLATION": "Ignore Translation Conflicts",
    "FILTER_IGNORE_PATCH": "Ignore Patch Conflicts",
    "FILTER_SHOW_ZH_NAME": "Show Chinese Alias",
    "SEARCH_NOT_FOUND": "No matching mods found",
    "SEARCH_FOUND": "Found {cur}/{total}",
    "STATUS_SUMMARY": "Total: {total} mods | Active: {active}",
    "STATUS_SUMMARY_CONFLICTS": "Total: {total} mods | Active: {active} | Conflicting Mods: {cmods} ({citems} items)",

    # Columns
    "COL_ACTIVE": "Active",
    "COL_ORDER": "Order",
    "COL_NAME": "Name",
    "COL_CATEGORIES": "Categories",
    "COL_SOURCE": "Source",

    # Context Menu
    "MENU_VISIT_PAGE": "Visit Mod Page",
    "MENU_OPEN_FOLDER": "Open Mod Folder",
    "MENU_EDIT_ZH_NAME": "✏ Set Custom Alias / Note…",
    "MENU_TRANSLATE_MISSING": "🌐 Auto-Translate Untranslated Mods",
    "MENU_ACTIVATE": "Activate Selected",
    "MENU_DEACTIVATE": "Deactivate Selected",
    "MENU_TOGGLE": "Toggle Selected Active State",
    "MENU_MOVE_TOP": "Move to Top",
    "MENU_MOVE_BOTTOM": "Move to Bottom",
    "MENU_UNSUBSCRIBE": "Unsubscribe on Steam (Open Workshop Page)",
    "MENU_REMOVE_MISSING": "Remove Missing / Broken Mods",
    "MENU_REMOVE_INACTIVE": "Delete Inactive Mods & Folders",

    # Bottom Bar
    "BTN_OPEN_GAME": "Open Game Folder",
    "BTN_OPEN_GAME_MODS": "Open Game Mods Folder",
    "BTN_OPEN_STEAM_MODS": "Open Steam Mods Folder",
    "BTN_FOLDER_TOOL": "Folder Manager",
    "BTN_SAVE_PROFILE": "Save Profile",
    "BTN_LOAD_PROFILE": "Load Profile",
    "BTN_ABOUT": "ℹ About",
    "BTN_LAUNCH": "▶ Launch Game",

    # Detail Panel
    "D_ZH_NAME": "Chinese Alias:",
    "D_WORKSHOP_TITLE": "Workshop Title:",
    "D_TRANSLATION": "Translation:",
    "D_TRANSLATION_TARGET": "🌐 Translation Mod (Paired with: {targets})",
    "D_TRANSLATION_GLOBAL": "🌐 Global / Standalone Translation Mod",
    "D_PATCH": "Patch / Add-on:",
    "D_PATCH_TARGET": "🔧 Patch / Add-on Mod (Paired with: {targets})",
    "D_DEPENDENCIES": "Dependencies:",
    "D_REFERENCES": "References:",
    "D_AUTHOR": "Author:",
    "D_VERSION": "Version:",
    "D_PATH": "Path:",
    "D_URL": "URL:",
    "D_DESCRIPTION": "Description:",
    "D_STEAM_ID": "Steam ID:",
    "D_LEGEND": "(Green = Loaded before this mod; Red = Missing or loaded after)",
    "D_EMPTY": "Select a mod to view its details.",
    "D_CONFLICTS_HEADER": "══════════ Mod Conflicts ({n} items, in load order) ══════════",
    "D_CONFLICTS_HINT": "Tip: Click any mod name below to jump to it in the list; click '⚠ Check Conflicts' again after reordering.",
    "D_CONFLICTS_WINNER": "  ◀ Effective Winner",
    "D_CONFLICTS_MORE": "…and {more} more conflicts not shown (displaying first {shown}).",

    # Messages
    "DLG_EDIT_ZH_TITLE": "Set Custom Mod Alias",
    "DLG_EDIT_ZH_PROMPT": "Enter custom alias for '{name}' (leave blank to reset to automatic):",
    "MSG_TRANSLATING_MODS": "Translating mod names online ({cur}/{total}): {name}…",
    "MSG_TRANSLATE_NONE": "All mods already have translated aliases!",
    "MSG_TRANSLATE_DONE": "Auto-translation complete: added {n} mod aliases (cached in mod_names_zh.json).",
    "MSG_TITLE_INFO": "Information",
    "MSG_TITLE_ERROR": "Error",
    "MSG_TITLE_CONFIRM": "Confirm",
    "MSG_GAME_FOLDER_BAD": "Invalid Kenshi game folder path. Please check Settings.",
    "MSG_STEAM_FOLDER_BAD": "Invalid Steam Workshop mods folder path.",
    "MSG_SAVED": "Saved {n} active mods to mods.cfg (previous file backed up as mods.cfg.backup).",
    "MSG_NOT_SAVED": "Mod load order was not saved!",
    "MSG_SAVE_PERMISSION_DENIED": (
        "Cannot write file (permission denied or locked by another process):\n{err}\n\n"
        "Please make sure Kenshi or FCS is not locking the file, or run this tool as Administrator."
    ),
    "MSG_ASK_STEAM": "Could not auto-detect Steam Kenshi.\n\nAre you using the Steam version?\n(Choosing 'No' will only load from the Game Mods folder)",
    "MSG_ASK_GAME_FOLDER": "Select Kenshi Game Folder (containing kenshi_x64.exe)",
    "MSG_NUMBERS_ONLY": "Please enter a valid number!",
    "MSG_GAME_NOT_FOUND": "Could not find kenshi_x64.exe. Please check your game path.",
    "MSG_FCS_NOT_FOUND": "Could not find forgotten construction set.exe.",
    "MSG_AUTO_ORDER_CONFIRM": (
        "Auto Sort will reorder all mods according to masterlist rules,\n"
        "Steam Workshop categories, and automatic patch/translation follow-up rules.\n\n"
        "Do you want to continue? (Remember to click 'Save Load Order' afterwards)"
    ),
    "MSG_AUTO_ORDER_DONE": "Auto-sorting complete. Click 'Save Load Order' when ready.",
    "MSG_RULES_UPDATED": "Sorting rules updated to version {v}.",
    "MSG_RULES_LATEST": "Sorting rules are already up to date ({v}).",
    "MSG_RULES_FAILED": "Could not fetch sorting rules online. Using local rules.",
    "MSG_PROFILE_LOADED": "Profile loaded: matched {hit}/{total} mods.",
    "MSG_UNSAVED_EXIT": "You have unsaved load order changes. Are you sure you want to exit?",
    "MSG_LOADING": "Loading mods…",
    "MSG_DRAG_NEED_ORDER_SORT": "Please sort by the 'Order' column first to drag-and-drop mods.",
    "MSG_NO_STEAM_ID": "This mod does not have a Steam ID.",
    "MSG_NEED_ACTIVE_FOR_CONFLICT": "Please activate at least 2 mods before checking conflicts.",
    "MSG_CHECKING_CONFLICTS": "Checking conflicts ({cur}/{total}): {name}…",
    "MSG_CONFLICTS_DONE": "Conflict check complete: found {citems} property conflicts across {cmods} mods ({sec:.2f}s).",
    "MSG_CONFLICTS_DONE_SKIPPED": (
        "Conflict check complete: found {citems} property conflicts across {cmods} mods "
        "(excluded {skipped_trans} translations, {skipped_patch} patches in {sec:.2f}s)."
    ),
    "MSG_CONFLICTS_NONE": "Conflict check complete: no mod conflicts found!",
    "MSG_NO_MISSING_MODS": "No broken or missing-folder mods found.",
    "MSG_CONFIRM_REMOVE_MISSING": (
        "Found {n} invalid mods (missing folder or missing .mod file):\n\n"
        "{preview}\n\n"
        "Are you sure you want to remove these entries and any leftover folders?"
    ),
    "MSG_NO_INACTIVE_MODS": "There are currently no unchecked (inactive) mods.",
    "MSG_CONFIRM_REMOVE_INACTIVE": (
        "⚠ WARNING: You are about to permanently delete {n} inactive mods and their folders from disk!\n\n"
        "{preview}\n\n"
        "(Note: Steam Workshop mods may be re-downloaded by Steam unless unsubscribed)\n"
        "Are you sure you want to delete these {n} inactive mods?"
    ),
    "MSG_REMOVE_DONE": "Successfully removed {n} mods and their folders.",
    "MSG_REMOVE_ERRORS": "Removed {n} mods, but some folders could not be deleted:\n{e}",

    # Settings Window
    "SET_TITLE": "Settings",
    "SET_GAME_PATH": "Kenshi Game Folder",
    "SET_STEAM_PATH": "Steam Workshop Mods Folder (enter NONE if not using Steam)",
    "SET_MASTERLIST": "Masterlist Source (GitHub Repository)",
    "SET_LANGUAGE": "Interface Language (介面語言)",
    "SET_AUTO_UPDATE": "Check for masterlist rule updates on startup",
    "SET_BROWSE": "Browse…",
    "SET_AUTODETECT": "Auto Detect",
    "SET_CLEAR_LOGS": "🗑 Clear Backups & Logs",
    "SET_LOGS_CLEARED": "Cleared {n} manager backups & logs, and {gn} game logs (freed {size}).",
    "SET_SAVE": "Save",
    "SET_CANCEL": "Cancel",
    "SET_SAVED": "Settings saved. Reloading mod list.",
    "SET_DETECT_FAIL": "Could not auto-detect Steam Kenshi installation.",

    # Folder Manager Window
    "FT_TITLE": "Folder Manager",
    "FT_HELP": (
        "Link Steam Workshop mods into the Kenshi Game Mods folder using directory junctions (no Admin required).\n"
        "🔗 indicates an active link. Check mods below and use the action buttons."
    ),
    "FT_SELECT_ALL": "Select All",
    "FT_INVERT": "Invert Selection",
    "FT_CLEAR_EMPTY": "Remove Empty Folders",
    "FT_CREATE_LINKS": "Create Links for Checked",
    "FT_REMOVE_LINKS": "Remove Links for Checked",
    "FT_TOGGLE_LINKS": "Toggle Links for Checked",
    "FT_COL_SELECTED": "Select",
    "FT_COL_LINK": "Linked",
    "FT_DONE_CREATE": "Created {n} directory links.",
    "FT_DONE_REMOVE": "Removed {n} directory links.",
    "FT_DONE_CLEAN": "Deleted {n} empty folders.",
    "FT_ERRORS": "Some links failed to create:\n{e}",
    "FT_NOTHING": "No Steam Workshop mods are checked.",

    # About Window
    "ABOUT_TITLE": "About Kenshi Mod Manager",
    "ABOUT_HEADING": "Kenshi Mod Manager (Python Rewrite & Enhanced Edition)",
    "ABOUT_REWRITE_AUTHOR": "Author: 北極企鵝 (mymagadsl@gmail.com)",
    "ABOUT_ORIGINAL_AUTHOR": "Original Author: MillerScout (Antonio M S S Jr.)",
    "ABOUT_ORIGINAL_REPO_URL": "https://github.com/millerscout/Kenshi-Mod-Manager",
    "ABOUT_SORT_GUIDE_URL": "https://steamcommunity.com/sharedfiles/filedetails/?id=1850250979",
    "ABOUT_OPEN_ORIG_REPO": "🔗 Open Original GitHub Repo",
    "ABOUT_OPEN_SORT_GUIDE": "📖 Open Load Order Guide",
    "ABOUT_CLOSE": "Close",
    "ABOUT_DONATE_TITLE": "☕ Optional Donation (TWQR / JKOPay)",
    "ABOUT_DONATE_NOTE": (
        "This tool is 100% free and open-source. Donations are completely optional and only for players who find it useful!\n"
        "If you are interested in my development work, feel free to donate with a note or reach out (mymagadsl@gmail.com).\n"
        "Supports: TWQR (Taiwan Banks & E-Wallets) & JKOPay (396-900610912)"
    ),
    "ABOUT_DONATE_ZOOM": "🔍 Click to Enlarge QR Code",
    "ABOUT_DESCRIPTION_TEXT": (
        "[Project Rewrite & Attribution]\n"
        "• Python Rewrite & Enhancements Author: 北極企鵝 (mymagadsl@gmail.com)\n"
        "• Original Project Author: MillerScout (Antonio M S S Jr.)\n"
        "• Original Repository: https://github.com/millerscout/Kenshi-Mod-Manager\n"
        "• Load Order Guide Reference: Steam Community Guide (id=1850250979) / Genesis Modding Guild\n\n"
        "[New & Enhanced Features]\n"
        "This software is a Python + CustomTkinter rewrite and major enhancement of the original C#\n"
        "Kenshi-Mod-Manager by MillerScout, adding:\n"
        "  1. Full support for Kenshi FCS v17 binary mod header and record parsing\n"
        "  2. Fast property-level mod conflict detector with Winner indicator and click-to-jump navigation\n"
        "  3. Smart detection of Translation and Patch/Add-on mods with toggleable filters to exclude false-positive conflicts\n"
        "  4. Advanced Auto-Sort: combines Masterlist rules, Steam Workshop category weights, and automatic placement of patches & translations right after their base mods\n"
        "  5. 4-Layer Smart Chinese Mod Alias System:\n"
        "     • Extracts Chinese titles from Workshop .info files with automatic Simplified-to-Traditional conversion\n"
        "     • Reverse-infers Chinese names for English base mods from installed translation packs\n"
        "     • Built-in dictionary of popular Kenshi mods (base_mod_names_zh.json) + user custom dictionary (mod_names_zh.json)\n"
        "     • Right-click '✏ Set Custom Alias / Note…' and '🌐 Auto-Translate Untranslated Mods' (online translation with local cache)\n"
        "  6. Right-click Cleanup Tools: one-click removal of missing/broken mods and inactive mod folders\n"
        "  7. Duplicate .mod deduplication (skips backup .mod files in subfolders) and automatic read-only attribute handling on save\n"
        "  8. Centralized Backups & Logs: stores subscription backups (bkpsubscribedList) and logs in logs/ with a '🗑 Clear Backups & Logs' button in Settings\n"
        "  9. Hot-Switchable Multi-Language UI: supports Traditional Chinese (default), Simplified Chinese, and English without restarting\n\n"
        "══════════════════════ License (MIT License) ══════════════════════\n"
        "Released under the same MIT License as the original project:\n\n"
        + _LICENSE_TEXT
    ),
}

_ALL_BUNDLES: dict[str, dict[str, str]] = {
    "zh_TW": _ZH_TW,
    "zh_CN": _ZH_CN,
    "en_US": _EN_US,
}


def set_language(lang: str) -> str:
    """切換目前介面語言並動態更新 i18n 模組層級常數；未知代碼時回退至繁體中文 zh_TW。"""
    global _CURRENT_LANG
    code = lang if lang in _ALL_BUNDLES else "zh_TW"
    _CURRENT_LANG = code
    globals().update(_ALL_BUNDLES["zh_TW"])
    globals().update(_ALL_BUNDLES[code])
    return code


def get_language() -> str:
    return _CURRENT_LANG


def source_label(source) -> str:
    """根據目前語系回傳模組來源顯示名稱（Steam / 遊戲資料夾 / 游戏文件夹 / Game Folder）。"""
    return SOURCE_STEAM if getattr(source, "value", "") == "Steam" else SOURCE_GAME_FOLDER


# 預設初始化為繁體中文
set_language("zh_TW")
