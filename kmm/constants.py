"""常數定義（對應 C# Core/Constants.cs）。"""
import sys
from pathlib import Path

APP_NAME = "Kenshi 模組管理器"
APP_VERSION = "1.0.1"

KENSHI_APP_ID = "233860"

# 解析相依時要略過的遊戲本體檔案（小寫比對）
SKIPPABLE_MODS = {"gamedata.base", "rebirth.mod", "newwworld.mod", "dialogue.mod"}


def _resolve_base_dir() -> Path:
    """獨立執行檔（PyInstaller frozen）時以 .exe 所在目錄為工作基準；開發時以目前目錄為基準。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path.cwd()


def _resolve_resource(filename: str) -> Path:
    """取得隨附於 kmm 套件內的靜態資源檔（支援 PyInstaller _MEIPASS 單一執行檔解壓路徑）。"""
    local = Path(__file__).with_name(filename)
    if local.exists():
        return local
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        bundled = Path(meipass) / "kmm" / filename
        if bundled.exists():
            return bundled
    return local


# 程式資料檔（設定與規則放在程式工作目錄，日誌與訂閱備份收納於 logs/ 子目錄）
BASE_DIR = _resolve_base_dir()
LOGS_DIR = BASE_DIR / "logs"
ERROR_FILE = LOGS_DIR / "error.log"
LOG_FILE = LOGS_DIR / "info.log"
CONFIG_FILE = BASE_DIR / "config.json"
MASTERLIST_FILE = BASE_DIR / "masterlist.json"
MOD_NAMES_ZH_FILE = BASE_DIR / "mod_names_zh.json"
BACKUP_SUBSCRIBE_LIST = "bkpsubscribedList"
REPORTS_DIR = BASE_DIR / "reports"

BASE_RULES_FILE = _resolve_resource("base_rules.json")
BASE_NAMES_ZH_FILE = _resolve_resource("base_mod_names_zh.json")
DONATE_QR_FILE = _resolve_resource("donate_qr.png")

STEAM_REGISTRY_PATHS = [
    (r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
    (r"SOFTWARE\Valve\Steam", "InstallPath"),
]
STEAM_USER_REGISTRY = (r"Software\Valve\Steam", "SteamPath")
DEFAULT_STEAM_DIRECTORY = r"C:\Program Files (x86)\Steam"

# 「優先（自訂）」規則，未被規則命中的模組都放這組
DEFAULT_RULE_ORDER = 10
RULE_MAX_RANGE = 5000
