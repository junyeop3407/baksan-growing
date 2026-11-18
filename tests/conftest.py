# 테스트 준비 코드: src/ 폴더의 모듈을 import할 수 있게 하고,
# 그림 테스트에 쓸 tkinter 창(tk_root)을 만들어 준다.
import os
import sys

import pytest

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)


@pytest.fixture
def tk_root():
    """테스트 하나 동안 쓸 tkinter 창을 만들고 끝나면 닫는다."""
    tk = pytest.importorskip("tkinter")
    try:
        root = tk.Tk()
    except tk.TclError:
        pytest.skip("화면(디스플레이)이 없어 tkinter 창을 만들 수 없음")
    root.withdraw()
    yield root
    root.destroy()
