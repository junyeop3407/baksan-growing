# 박산 키우기 진입점: 창을 만들고 게임 화면(ui.App)을 띄운다.
# 실행: python src/main.py  (exe로 만들 때도 이 파일이 시작점이다)
import tkinter as tk

import db
from ui import App


def main():
    """창을 만들고 game.db 위치를 정해 게임을 시작한다."""
    root = tk.Tk()
    App(root, db.get_db_path())
    root.mainloop()


if __name__ == "__main__":
    main()
