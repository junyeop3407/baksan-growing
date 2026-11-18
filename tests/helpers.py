# 화면 테스트 도우미: 정해진 총알만 내는 가짜 무작위와, tkinter 이벤트를 돌리며 기다리는 함수.
import time


class PatternRng:
    """choice()는 정해 둔 총알 순서를 돌고, sample()은 앞에서부터 고른다."""

    WEAK = ["연습탄", "연습탄", "보통탄", "보통탄", "보통탄", "연습탄", "연습탄", "연습탄", "보통탄"]  # 줄 0개, 13점
    STRONG = ["철갑탄"] * 9                                                                         # 줄 8개, 405점

    def __init__(self, pattern):
        self.pattern = list(pattern)
        self.i = 0

    def choice(self, seq):
        kind = self.pattern[self.i % len(self.pattern)]
        self.i += 1
        return kind

    def sample(self, population, k):
        return list(population)[:k]


def pump(app, ms):
    """ms 동안 tkinter 이벤트를 돌린다."""
    end = time.monotonic() + ms / 1000
    while time.monotonic() < end:
        app.root.update()
        time.sleep(0.002)


def wait_until(app, condition, timeout=5.0):
    """condition()이 참이 될 때까지 이벤트를 돌린다. 시간 안에 안 되면 실패."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        app.root.update()
        if condition():
            return
        time.sleep(0.002)
    raise AssertionError("시간 안에 조건이 맞지 않음")


def start(app, name="박산"):
    """시작 화면에서 이름을 넣고 [게임 시작]을 누른다."""
    app.name_entry.delete(0, "end")
    app.name_entry.insert(0, name)
    app.start_button.invoke()


def play_round(app):
    """남은 스핀을 모두 돌리고 상점이나 게임 오버 화면이 될 때까지 기다린다."""
    while True:
        wait_until(app, lambda: not app.busy or app.screen != "game")
        if app.screen != "game" or app.game.spins_left == 0:
            break
        app.spin_button.invoke()
    wait_until(app, lambda: app.screen in ("shop", "gameover"))
