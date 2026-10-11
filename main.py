"""Kenshi 模組管理器（Python + CustomTkinter 繁體中文版）進入點。

原作：millerscout / Kenshi-Mod-Manager（MIT License）
"""
from kmm import constants, logging_util
from ui.main_window import MainWindow


def main() -> None:
    try:
        app = MainWindow()
        app.mainloop()
    except Exception as exc:
        logging_util.write_exception(constants.ERROR_FILE, exc)
        raise


if __name__ == "__main__":
    main()
