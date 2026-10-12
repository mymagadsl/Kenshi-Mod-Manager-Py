import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kmm import loader, rules, steam  # noqa: E402
from kmm.config import KenshiToolConfig  # noqa: E402
from kmm.mod_reader import Metadata, load_metadata, write_metadata_for_test  # noqa: E402
from kmm.models import Mod, Rule, Source  # noqa: E402


def make_mods(*names, active=True):
    return [Mod(file_path=f"C:/x/{n}/{n}.mod", order=i if active else -1, active=active)
            for i, n in enumerate(names)]


class ModReaderTest(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            for ver in (16, 17):
                p = Path(d) / f"a_{ver}.mod"
                write_metadata_for_test(
                    p, Metadata(3, "作者", "描述 desc", ["dep.mod", "gamedata.base"], ["ref.mod"]),
                    file_version=ver,
                )
                md = load_metadata(str(p))
                self.assertEqual(md.version, 3)
                self.assertEqual(md.author, "作者")
                self.assertEqual(md.description, "描述 desc")
                self.assertEqual(md.dependencies, ["dep.mod"])  # gamedata.base 被略過
                self.assertEqual(md.referenced, ["ref.mod"])

    def test_old_format_and_truncated(self):
        with tempfile.TemporaryDirectory() as d:
            old = Path(d) / "old.mod"
            old.write_bytes(struct.pack("<i", 10))
            self.assertIsNone(load_metadata(str(old)))
            bad = Path(d) / "bad.mod"
            bad.write_bytes(struct.pack("<ii", 16, 1) + struct.pack("<i", 100))
            self.assertIsNone(load_metadata(str(bad)))
            self.assertIsNone(load_metadata(str(Path(d) / "missing.mod")))


class VdfTest(unittest.TestCase):
    def test_parse(self):
        text = '''"libraryfolders"
{
    "0" { "path" "C:\\\\Program Files (x86)\\\\Steam" "apps" { "228980" "1" } }
    "1" { "path" "D:\\\\SteamLibrary" "apps" { "233860" "123" } }
}'''
        data = steam.parse_vdf(text)
        lf = data["libraryfolders"]
        self.assertEqual(lf["1"]["path"], r"D:\SteamLibrary")
        self.assertIn("233860", lf["1"]["apps"])

    def test_find_kenshi(self):
        with tempfile.TemporaryDirectory() as d:
            steam_dir = Path(d) / "Steam"
            lib = Path(d) / "Lib"
            (steam_dir / "steamapps").mkdir(parents=True)
            (lib / "steamapps" / "common" / "Kenshi").mkdir(parents=True)
            p = str(lib).replace("\\", "\\\\")
            (steam_dir / "steamapps" / "libraryfolders.vdf").write_text(
                f'"libraryfolders" {{ "1" {{ "path" "{p}" "apps" {{ "233860" "1" }} }} }}')
            game, ws = steam.find_kenshi(steam_dir)
            self.assertEqual(game, lib / "steamapps" / "common" / "Kenshi")
            self.assertTrue(str(ws).endswith(r"workshop\content\233860"))


class OrderTest(unittest.TestCase):
    def test_set_new_order_move_up(self):
        mods = make_mods("a", "b", "c", "d")
        loader.set_new_order(mods, mods[3], 1)
        self.assertEqual([m.file_name for m in sorted(mods, key=lambda m: m.order)],
                         ["a.mod", "d.mod", "b.mod", "c.mod"])

    def test_set_new_order_beyond_end(self):
        mods = make_mods("a", "b", "c")
        loader.set_new_order(mods, mods[0], 99)
        self.assertEqual([m.file_name for m in sorted(mods, key=lambda m: m.order)],
                         ["b.mod", "c.mod", "a.mod"])
        self.assertEqual(mods[0].order, 2)

    def test_set_active(self):
        mods = make_mods("a", "b", "c")
        loader.set_active(mods, [mods[0]], False)
        self.assertEqual((mods[0].order, mods[1].order, mods[2].order), (-1, 0, 1))
        loader.set_active(mods, [mods[0]], True)
        self.assertEqual(mods[0].order, 2)
        loader.set_active(mods, [mods[1]], None)
        self.assertFalse(mods[1].active)

    def test_missing_dependencies(self):
        mods = make_mods("base", "addon")
        mods[1].dependencies = ["base.mod"]
        self.assertEqual(loader.missing_dependencies(mods, mods[1]), [])
        mods[0].order, mods[1].order = 1, 0
        self.assertEqual(loader.missing_dependencies(mods, mods[1]), ["base.mod"])


class RulesTest(unittest.TestCase):
    def test_order_by_rules_and_dependencies(self):
        mods = make_mods("Patch", "Dark UI", "Unknown", "Needs")
        mods[3].dependencies = ["Unknown.mod"]
        r = [Rule(0, "UI", ["Dark UI.mod"]), Rule(8, "Patches", ["Patch.mod", "Needs.mod"]),
             Rule(10, "Custom", [])]
        ordered = rules.order_mods(mods, r)
        names = [m.file_name for m in ordered]
        self.assertEqual(names[0], "Dark UI.mod")
        self.assertLess(names.index("Unknown.mod"), names.index("Needs.mod"))
        self.assertEqual([m.order for m in ordered], list(range(4)))
        # 再執行一次結果不變（原版靜態清單會殘留）
        again = [m.file_name for m in rules.order_mods(mods, r)]
        self.assertEqual(again, names)

    def test_base_rules_load(self):
        r = rules.get_rules(Path("does-not-exist.json"))
        self.assertEqual(len(r), 11)
        self.assertTrue(any(x.order == 10 for x in r))

    def test_category_sort_and_patch_translation_followup(self):
        # 測試未在 masterlist 內的模組依分類標籤排序，且補丁與漢化包自動跟隨原版模組、全域漢化排最後
        m_global = Mod(file_path="C:/x/TraditionalChinese.mod", order=0, active=True)
        m_overhaul = Mod(file_path="C:/x/BigWorldOverhaul.mod", order=1, active=True,
                         categories=["Total Overhaul", "Characters"])
        m_race_cht = Mod(file_path="C:/x/Mist Ghouls_cht.mod", order=2, active=True)
        m_race_patch = Mod(file_path="C:/x/Mist_Ghouls_Playable.mod", order=3, active=True)
        m_weapon = Mod(file_path="C:/x/AncientKatana.mod", order=4, active=True,
                       categories=["Items/Weapons"])
        m_race = Mod(file_path="C:/x/Mist Ghouls.mod", order=5, active=True,
                     categories=["Races"])
        m_ui = Mod(file_path="C:/x/CleanMapGUI.mod", order=6, active=True,
                   categories=["GUI"])

        base_rules = rules.get_rules(Path("does-not-exist.json"))
        ordered = rules.order_mods(
            [m_global, m_overhaul, m_race_cht, m_race_patch, m_weapon, m_race, m_ui],
            base_rules,
        )
        names = [m.file_name for m in ordered]
        # 預期順序：GUI(0) -> Races(2) -> 補丁跟隨 -> 漢化跟隨 -> Weapons(6) -> Overhaul(7) -> 全域漢化(最後)
        self.assertEqual(
            names,
            [
                "CleanMapGUI.mod",
                "Mist Ghouls.mod",
                "Mist_Ghouls_Playable.mod",
                "Mist Ghouls_cht.mod",
                "AncientKatana.mod",
                "BigWorldOverhaul.mod",
                "TraditionalChinese.mod",
            ],
        )


class LoaderTest(unittest.TestCase):
    def test_scan_and_save(self):
        with tempfile.TemporaryDirectory() as d:
            game = Path(d) / "Kenshi"
            ws = Path(d) / "workshop"
            (game / "data").mkdir(parents=True)
            for folder, name in ((game / "Mods" / "Local", "Local"), (ws / "111", "Steamy")):
                folder.mkdir(parents=True)
                write_metadata_for_test(folder / f"{name}.mod", Metadata(1, "me", "d", [], []))
            (ws / "111" / "_Steamy.info").write_text(
                "<ModData><id>111</id><tags><string>Armor</string><string>UI</string></tags></ModData>",
                encoding="utf-8")
            (ws / "222").mkdir()  # 空資料夾 -> 讀取錯誤
            (game / "data" / "mods.cfg").write_text("Steamy.mod\nLocal.mod\n", encoding="utf-8")

            cfg = KenshiToolConfig(GamePath=str(game), SteamModsPath=str(ws))
            mods = loader.get_list_of_mods(cfg)
            by = {m.file_name: m for m in mods}
            self.assertEqual(by["Steamy.mod"].source, Source.STEAM)
            self.assertEqual(by["Steamy.mod"].id, "111")
            self.assertEqual(by["Steamy.mod"].categories, ["Armor", "UI"])
            self.assertEqual(by["Local.mod"].source, Source.GAME_FOLDER)
            self.assertEqual((by["Steamy.mod"].order, by["Local.mod"].order), (0, 1))
            self.assertTrue(by["222"].display_name.startswith("[錯誤]"))

            loader.set_new_order(mods, by["Local.mod"], 0)
            loader.save_mods_cfg(cfg, mods)
            self.assertEqual((game / "data" / "mods.cfg").read_bytes(), b"Local.mod\r\nSteamy.mod\r\n")
            self.assertTrue((game / "data" / "mods.cfg.backup").exists())

            # 建立 junction 後重新掃描，不應重複列出
            errors = loader.create_links([(game / "Mods" / "Steamy", ws / "111")])
            self.assertEqual(errors, [])
            self.assertTrue(loader.is_link(game / "Mods" / "Steamy"))
            self.assertEqual(len(loader.get_list_of_mods(cfg)), 3)
            loader.delete_folder(game / "Mods" / "Steamy")
            self.assertFalse(os.path.lexists(game / "Mods" / "Steamy"))
            self.assertTrue((ws / "111" / "Steamy.mod").exists())  # 來源沒被刪

    def test_duplicate_mod_deduplication_and_readonly_save(self):
        import stat
        with tempfile.TemporaryDirectory() as d:
            game = Path(d) / "Kenshi"
            ws = Path(d) / "workshop"
            (game / "data").mkdir(parents=True)
            # 在 Steam 工作坊與本機 Mods 同時放同名 DupMod.mod（實體複製，非連結）
            for folder in (ws / "999", game / "Mods" / "DupMod"):
                folder.mkdir(parents=True)
                write_metadata_for_test(folder / "DupMod.mod", Metadata(1, "me", "d", [], []))
            cfg_file = game / "data" / "mods.cfg"
            cfg_file.write_text("DupMod.mod\n", encoding="utf-8")

            cfg = KenshiToolConfig(GamePath=str(game), SteamModsPath=str(ws))
            mods = loader.get_list_of_mods(cfg)
            dup_mods = [m for m in mods if m.file_name == "DupMod.mod"]
            self.assertEqual(len(dup_mods), 2)
            # 載入時只會保留第一個為啟用狀態，避免重複啟用
            self.assertEqual([m.active for m in dup_mods], [True, False])

            # 即使手動將兩個同名模組都設為 active，active_file_names 與 save_mods_cfg 也會自動去重
            for i, m in enumerate(dup_mods):
                m.active = True
                m.order = i
            self.assertEqual(loader.active_file_names(dup_mods), ["DupMod.mod"])

            # 將 mods.cfg 設為唯讀，測試 save_mods_cfg 能自動解除唯讀並成功寫入
            os.chmod(cfg_file, stat.S_IREAD)
            loader.save_mods_cfg(cfg, dup_mods)
            self.assertEqual(cfg_file.read_bytes(), b"DupMod.mod\r\n")

            # 將 config.json 設為唯讀，測試 cfg.save() 能自動解除唯讀並成功寫入
            conf_path = Path(d) / "config.json"
            cfg.save(conf_path)
            os.chmod(conf_path, stat.S_IREAD)
            cfg.GamePath = "C:/NewPath"
            cfg.save(conf_path)
            self.assertEqual(KenshiToolConfig.load(conf_path).GamePath, "C:/NewPath")

    def test_cleanup(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "a" / "b").mkdir(parents=True)
            (root / "keep").mkdir()
            (root / "keep" / "f.txt").write_text("x")
            removed = loader.folder_cleanup(root)
            self.assertEqual(len(removed), 2)
            self.assertTrue((root / "keep").exists())

    def test_remove_invalid_and_inactive_mods(self):
        with tempfile.TemporaryDirectory() as d:
            game = Path(d) / "Kenshi"
            ws = Path(d) / "workshop"
            (game / "data").mkdir(parents=True)
            (game / "Mods").mkdir(parents=True)
            for folder, name in ((ws / "100", "ActiveMod"), (ws / "200", "InactiveMod")):
                folder.mkdir(parents=True)
                write_metadata_for_test(folder / f"{name}.mod", Metadata(1, "a", "d", [], []))
            (ws / "300").mkdir(parents=True)  # 無 .mod 檔的殘留資料夾
            (game / "data" / "mods.cfg").write_text("ActiveMod.mod\n", encoding="utf-8")

            cfg = KenshiToolConfig(GamePath=str(game), SteamModsPath=str(ws))
            mods = loader.get_list_of_mods(cfg)
            self.assertEqual(len(mods), 3)

            invalid = loader.find_invalid_mods(mods)
            self.assertEqual(len(invalid), 1)
            self.assertEqual(invalid[0].file_name, "300")
            n, errs = loader.remove_mods_and_folders(cfg, mods, invalid)
            self.assertEqual((n, errs), (1, []))
            self.assertFalse((ws / "300").exists())
            self.assertEqual(len(mods), 2)

            inactive = [m for m in mods if not m.active]
            self.assertEqual(len(inactive), 1)
            self.assertEqual(inactive[0].file_name, "InactiveMod.mod")
            n, errs = loader.remove_mods_and_folders(cfg, mods, inactive)
            self.assertEqual((n, errs), (1, []))
            self.assertFalse((ws / "200").exists())
            self.assertTrue((ws / "100").exists())
            self.assertEqual([m.file_name for m in mods], ["ActiveMod.mod"])

    def test_backup_in_logs_dir_and_clear(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            logs = root / "logs"
            # 在根目錄預先放一個舊版遺留的 bkpsubscribedList 檔案與 info.log
            legacy_bkp = root / "bkpsubscribedList20200101000000.info"
            legacy_bkp.write_text("111\r\n", encoding="utf-8")
            (root / "info.log").write_text("old log", encoding="utf-8")

            cfg = KenshiToolConfig(MaxLogFiles=5)
            mods = [Mod(file_path="C:/ws/222/Test.mod", id="222", source=Source.STEAM)]
            loader.backup_subscribed_list(cfg, mods, logs_dir=logs, base_dir=root)

            # 根目錄舊備份檔已被自動移入 logs/，且新備份也在 logs/ 內
            self.assertEqual(list(root.glob("bkpsubscribedList*")), [])
            bkp_files = sorted(logs.glob("bkpsubscribedList*"))
            self.assertEqual(len(bkp_files), 2)
            self.assertEqual(bkp_files[-1].read_text(encoding="utf-8").strip(), "222")

            # 測試一鍵清除備份與日誌檔
            (logs / "error.log").write_text("err", encoding="utf-8")
            removed = loader.clear_logs_and_backups(base_dir=root, logs_dir=logs)
            self.assertEqual(removed, 4)  # 2 個 bkp + root/info.log + logs/error.log
            self.assertEqual(list(logs.glob("bkpsubscribedList*")), [])
            self.assertFalse((logs / "error.log").exists())
            self.assertFalse((root / "info.log").exists())


class ConflictTest(unittest.TestCase):
    @staticmethod
    def _build_mod(path: Path, sid: str, name: str, price: int, flags: int = 1) -> None:
        def s(v: str) -> bytes:
            b = v.encode("utf-8")
            return struct.pack("<i", len(b)) + b

        header = struct.pack("<i", 1) + s("auth") + s("desc") + s("") + s("")
        item = (
            struct.pack("<iii", 0, 2, 1)  # unused, ItemType.WEAPON=2, num_id
            + s(name) + s(sid)
            + struct.pack("<i", flags)    # flags (1=MODIFIED)
            + struct.pack("<i", 0)        # bool count
            + struct.pack("<i", 0)        # float count
            + struct.pack("<i", 1) + s("value") + struct.pack("<i", price)  # int: value=price
            + struct.pack("<iiiii", 0, 0, 0, 0, 0)  # vec, quat, str, file, ref, inst (remaining 5)
            + struct.pack("<i", 0)
        )
        raw = struct.pack("<ii", 17, len(header)) + header + struct.pack("<ii", 10, 1) + item
        path.write_bytes(raw)

    def test_detects_conflict_and_winner(self):
        from kmm import conflicts

        with tempfile.TemporaryDirectory() as d:
            p1, p2 = Path(d) / "ModA.mod", Path(d) / "ModB.mod"
            self._build_mod(p1, "10-gamedata.base", "Katana", 100)
            self._build_mod(p2, "10-gamedata.base", "Katana", 250)
            m1 = Mod(file_path=str(p1), order=0, active=True)
            m2 = Mod(file_path=str(p2), order=1, active=True)

            idx = conflicts.analyze_conflicts([m1, m2])
            self.assertEqual(len(idx), 1)
            self.assertEqual(len(m1.conflicts), 1)
            self.assertEqual(len(m2.conflicts), 1)
            detail = idx["10-gamedata.base::value"]
            self.assertEqual(detail.winning_index, 1)
            self.assertEqual(detail.changes[1].mod_name, "ModB.mod")
            self.assertEqual(detail.changes[1].value, 250)

    def test_translation_detection_and_conflict_exclusion(self):
        from kmm import conflicts

        with tempfile.TemporaryDirectory() as d:
            p_base = Path(d) / "ChineseAcientWeapon.mod"
            p_trans = Path(d) / "ChineseAncientWeapon CHN.mod"
            p_font = Path(d) / "BeautifulChineseFont.mod"
            p_global = Path(d) / "zh_TW.mod"

            self._build_mod(p_base, "99-weapon.mod", "Ancient Sword", 500, flags=0)
            self._build_mod(p_trans, "99-weapon.mod", "古風長劍", 500, flags=3)
            self._build_mod(p_font, "100-font.mod", "Font", 1, flags=0)
            self._build_mod(p_global, "99-weapon.mod", "古劍", 500, flags=3)

            m_base = Mod(file_path=str(p_base), order=0, active=True, categories=["Items/Weapons"])
            m_trans = Mod(file_path=str(p_trans), order=1, active=True)  # 即使無 Translation 標籤或相依，也能靠名稱模糊配對
            m_font = Mod(file_path=str(p_font), order=2, active=True, categories=["GUI"])
            m_global = Mod(file_path=str(p_global), order=3, active=True)

            all_mods = [m_base, m_trans, m_font, m_global]
            self.assertFalse(conflicts.is_translation_mod(m_base))
            self.assertFalse(conflicts.is_translation_mod(m_font))
            self.assertTrue(conflicts.is_translation_mod(m_trans))
            self.assertTrue(conflicts.is_translation_mod(m_global))

            tmap = conflicts.detect_translation_map(all_mods)
            self.assertEqual(tmap["ChineseAncientWeapon CHN.mod"], ["ChineseAcientWeapon.mod"])
            self.assertEqual(tmap["zh_TW.mod"], [])

            # 預設排除漢化衝突：原版與漢化包之間應為 0 衝突
            idx_filtered = conflicts.analyze_conflicts(all_mods, ignore_translations=True)
            self.assertEqual(len(idx_filtered), 0)
            self.assertEqual(m_base.conflicts, [])
            self.assertEqual(m_trans.conflicts, [])

            # 若關閉排除漢化衝突：則會檢出原版與漢化包之間的覆蓋
            idx_raw = conflicts.analyze_conflicts(all_mods, ignore_translations=False)
            self.assertGreater(len(idx_raw), 0)
            self.assertTrue(m_base.conflicts)
            self.assertTrue(m_trans.conflicts)

    def test_patch_detection_and_conflict_exclusion(self):
        from kmm import conflicts

        with tempfile.TemporaryDirectory() as d:
            p_knights = Path(d) / "KnightsOfBD.mod"
            p_kfix = Path(d) / "KightsOfBD Kan fix.mod"  # 故意少拼 n 測試名稱模糊比對
            p_pfix = Path(d) / "Particle fix.mod"        # 獨立模組（無對應 Particle 主模組）
            p_affix = Path(d) / "KenshiAffixes.mod"      # 單字內含 fix，不應誤判

            self._build_mod(p_knights, "50-knights.mod", "Knight", 100, flags=0)
            self._build_mod(p_kfix, "50-knights.mod", "Knight", 200, flags=1)
            self._build_mod(p_pfix, "60-particle.mod", "Dust", 10, flags=1)
            self._build_mod(p_affix, "70-affix.mod", "Affix", 10, flags=0)

            m_knights = Mod(file_path=str(p_knights), order=0, active=True)
            m_kfix = Mod(file_path=str(p_kfix), order=1, active=True)  # 無 dependencies，純靠名稱辨識
            m_pfix = Mod(file_path=str(p_pfix), order=2, active=True)
            m_affix = Mod(file_path=str(p_affix), order=3, active=True)

            all_mods = [m_knights, m_kfix, m_pfix, m_affix]
            pmap = conflicts.detect_patch_map(all_mods)
            self.assertEqual(pmap.get("KightsOfBD Kan fix.mod"), ["KnightsOfBD.mod"])
            self.assertNotIn("Particle fix.mod", pmap)
            self.assertNotIn("KenshiAffixes.mod", pmap)

            # 預設開啟 ignore_patches=True：KnightsOfBD 與 KightsOfBD Kan fix 之間的覆蓋應被排除
            idx_filtered = conflicts.analyze_conflicts(all_mods, ignore_patches=True)
            self.assertEqual(len(idx_filtered), 0)
            self.assertEqual(m_knights.conflicts, [])
            self.assertEqual(m_kfix.conflicts, [])

            # 關閉 ignore_patches=False：應檢出兩者之間的覆蓋衝突
            idx_raw = conflicts.analyze_conflicts(all_mods, ignore_patches=False)
            self.assertEqual(len(idx_raw), 1)
            self.assertEqual(len(m_knights.conflicts), 1)
            self.assertEqual(len(m_kfix.conflicts), 1)


class NameTranslatorTest(unittest.TestCase):
    def test_four_layer_zh_name_resolution(self):
        from kmm import conflicts, name_translator

        with tempfile.TemporaryDirectory() as d:
            custom_path = Path(d) / "mod_names_zh.json"
            # 1. 內建辭典命中
            m_dark = Mod(file_path="C:/x/Dark UI.mod")
            # 2. 從 .info <title> 提取並簡轉繁
            m_med = Mod(file_path="C:/x/SuperMedkit.mod", title="Super Medkit / 超级急救包药量合并 [RE_Kenshi]")
            # 3. 從漢化包反向推導原版英文模組名稱
            m_base = Mod(file_path="C:/x/MysteryDungeon.mod")
            m_trans = Mod(file_path="C:/x/MysteryDungeon CN.mod", title="神秘地牢探索汉化补丁")
            # 4. 日文假名描述不應誤判為中文標題
            m_jp = Mod(file_path="C:/x/SomeJpMod.mod", description="このMODをマージしないでください。")

            mods = [m_dark, m_med, m_base, m_trans, m_jp]
            tmap = conflicts.detect_translation_map(mods)
            pmap = conflicts.detect_patch_map(mods, tmap)
            name_translator.populate_zh_names(mods, tmap, pmap, custom_dict_path=custom_path)

            self.assertEqual(m_dark.zh_name, "深色介面")
            self.assertEqual(m_dark.ui_name(True), "【深色介面】 Dark UI")
            self.assertEqual(m_dark.ui_name(False), "Dark UI")
            self.assertEqual(m_med.zh_name, "超級急救包藥量合併")
            self.assertEqual(m_base.zh_name, "神秘地牢探索")
            self.assertEqual(m_jp.zh_name, "")

            # 測試使用者自訂別名覆蓋與清除
            name_translator.save_custom_zh_name("SomeJpMod", "自訂日系動作模組", path=custom_path)
            name_translator.populate_zh_names(mods, tmap, pmap, custom_dict_path=custom_path)
            self.assertEqual(m_jp.zh_name, "自訂日系動作模組")

            name_translator.save_custom_zh_name("SomeJpMod", "", path=custom_path)
            name_translator.populate_zh_names(mods, tmap, pmap, custom_dict_path=custom_path)
            self.assertEqual(m_jp.zh_name, "")


class I18nTest(unittest.TestCase):
    def test_language_switching_and_default_zh_tw(self):
        from ui import i18n

        # 確保三種語言字典的鍵集合完全一致
        self.assertEqual(set(i18n._ZH_TW.keys()), set(i18n._ZH_CN.keys()))
        self.assertEqual(set(i18n._ZH_TW.keys()), set(i18n._EN_US.keys()))

        # 預設為繁體中文
        cfg = KenshiToolConfig()
        self.assertEqual(cfg.Language, "zh_TW")

        try:
            i18n.set_language("zh_TW")
            self.assertEqual(i18n.get_language(), "zh_TW")
            self.assertEqual(i18n.APP_TITLE, "Kenshi 模組管理器")
            self.assertEqual(i18n.source_label(Source.GAME_FOLDER), "遊戲資料夾")

            i18n.set_language("zh_CN")
            self.assertEqual(i18n.get_language(), "zh_CN")
            self.assertEqual(i18n.APP_TITLE, "Kenshi 模组管理器")
            self.assertEqual(i18n.source_label(Source.GAME_FOLDER), "游戏文件夹")

            i18n.set_language("en_US")
            self.assertEqual(i18n.get_language(), "en_US")
            self.assertEqual(i18n.APP_TITLE, "Kenshi Mod Manager")
            self.assertEqual(i18n.source_label(Source.GAME_FOLDER), "Game Folder")
        finally:
            i18n.set_language("zh_TW")


class BuildGuiTest(unittest.TestCase):
    def test_build_pyinstaller_args(self):
        import build_gui

        args = build_gui.build_pyinstaller_args(
            exe_name="MyKenshiTool",
            onefile=True,
            noconsole=True,
            clean=True,
        )
        self.assertIn("--onefile", args)
        self.assertIn("--noconsole", args)
        self.assertIn("--clean", args)
        self.assertIn("MyKenshiTool", args)
        self.assertIn("customtkinter", args)
        joined = " ".join(args)
        self.assertIn("base_rules.json", joined)
        self.assertIn("base_mod_names_zh.json", joined)

    def test_bump_app_version(self):
        import build_gui

        with tempfile.TemporaryDirectory() as d:
            dummy_const = Path(d) / "constants.py"
            dummy_const.write_text('APP_NAME = "Kenshi"\nAPP_VERSION = "1.0.0"\n', encoding="utf-8")

            old1, new1 = build_gui.bump_app_version(dummy_const)
            self.assertEqual((old1, new1), ("1.0.0", "1.0.1"))
            self.assertIn('APP_VERSION = "1.0.1"', dummy_const.read_text(encoding="utf-8"))

            old2, new2 = build_gui.bump_app_version(dummy_const)
            self.assertEqual((old2, new2), ("1.0.1", "1.0.2"))
            self.assertIn('APP_VERSION = "1.0.2"', dummy_const.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

