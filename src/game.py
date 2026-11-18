# 게임 규칙(골드·스핀, 병사 소환·합체, 자동 전투, 웨이브 보상, 상점, 계급)을 담당한다.
# 화면(ui.py)과 분리되어 있어 콘솔이나 테스트에서도 그대로 쓸 수 있다.
# 콘솔에서 한 판 해 보기: python src/game.py
import random

from symbols import BULLETS, BULLET_ORDER, RANKS, SOLDIERS, START_DECK

NAME_MAX = 10
NAME_MESSAGE = "이름을 1~10글자로 입력해 주세요."

# ---- 준비 단계 ----
START_GOLD = 500
START_HEARTS = 3
MAX_HEARTS = 5
SPIN_BASE = 100        # 준비 단계 첫 스핀 비용
SPIN_STEP = 50         # 스핀할 때마다 오르는 비용
SLOTS = 6              # 병사 칸 수
FULL_REFUND = 50       # 칸이 꽉 차 소환하지 못했을 때 돌려주는 골드
STAR_POWER = {1: 1, 2: 2, 3: 4}
MAX_STAR = 3

# ---- 전투 ----
FIELD = 100.0          # 적이 나오는 곳(오른쪽 끝)에서 방어선(0)까지 거리
# 적 속도 (조정용, 300판 시뮬레이션으로 정함 → 기획서 "난이도 조정값")
ENEMY_SPEED = 5.0      # 1웨이브 적이 1초에 걷는 거리 (방어선까지 20초)
SPEED_STEP = 10.0      # 웨이브마다 더 빨라지는 만큼
SPEED_MAX = 33.0       # 상한: 방어선까지 최소 3초 (100 / 3 ≈ 33.3 → 33, 약 3.03초). 4웨이브부터
SPAWN_GAP = 0.35       # 적이 나오는 간격(초). 느려진 만큼 촘촘히 나와 난이도를 맞춘다
BOSS_EVERY = 5         # 5웨이브마다 보스
BOSS_HP_TIMES = 10
LEAK_NORMAL, LEAK_BOSS = 1, 2

# ---- 보상과 상점 ----
WAVE_GOLD = 200
KILL_GOLD = 10
ATTACK_STEP = 0.1      # 공격력 +10%
SHOP_ITEMS = ["총알 추가", "하트 +1", "공격력 +10%", "첫 스핀 무료"]

# ---- 점수 ----
KILL_SCORE = 10
WAVE_SCORE = 100

MSG_MISS = "꽝! 맞은 줄이 없습니다"
MSG_FULL = "병사 칸이 꽉 찼습니다 (+50골드)"

# 9칸 번호         같은 총알 3개를 검사하는 줄 8개
#  0 1 2           가로 3줄, 세로 3줄, 대각선 2줄
#  3 4 5
#  6 7 8
LINES = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),
    (0, 3, 6), (1, 4, 7), (2, 5, 8),
    (0, 4, 8), (2, 4, 6),
]

EPS = 1e-9             # 소수 계산 오차 여유


def count_lines(board):
    """판(9칸)에서 같은 총알 3개가 맞은 줄 수를 센다. 한 칸이 여러 줄에 속해도 줄마다 센다."""
    return len(matched_lines(board))


def matched_lines(board):
    """같은 총알 3개가 맞은 줄 목록 (LINES 순서)."""
    return [line for line in LINES if board[line[0]] == board[line[1]] == board[line[2]]]


def enemy_count(wave):
    """웨이브 n의 일반 적 수 = 5 + 2n."""
    return 5 + 2 * wave


def enemy_hp(wave):
    """웨이브 n의 일반 적 체력 = 20 × 1.2^(n-1), 소수점은 버린다 (정수 계산으로 오차 없이)."""
    return 20 * 6 ** (wave - 1) // 5 ** (wave - 1)


def enemy_speed(wave):
    """웨이브 n의 적 속도 = 5 + 10 × (n-1), 최대 33 (방어선까지 3초 이상)."""
    return min(SPEED_MAX, ENEMY_SPEED + SPEED_STEP * (wave - 1))


def rank_for(cleared_waves):
    """막은 웨이브 수로 계급 이름을 정한다 (하사가 끝)."""
    return RANKS[min(cleared_waves, len(RANKS) - 1)][0]


def face_ratio_for(cleared_waves):
    """막은 웨이브 수로 얼굴의 최산 비율(0~1)을 정한다."""
    return RANKS[min(cleared_waves, len(RANKS) - 1)][1]


def clean_name(text):
    """이름 앞뒤 공백을 빼고 1~10글자인지 확인해 (이름, 안내 문구)를 돌려준다."""
    name = text.strip()
    if 1 <= len(name) <= NAME_MAX:
        return name, ""
    return None, NAME_MESSAGE


class Game:
    """한 판의 상태(덱, 골드, 하트, 병사, 웨이브, 적)를 들고 규칙대로 진행한다."""

    def __init__(self):
        self.deck = [kind for kind, count in START_DECK.items() for _ in range(count)]
        self.gold = START_GOLD
        self.hearts = START_HEARTS
        self.wave = 1
        self.cleared = 0          # 막은 웨이브 수
        self.kills = 0            # 지금까지 처치한 적 수
        self.wave_kills = 0       # 이번 웨이브에서 처치한 적 수
        self.soldiers = []        # [(총알 종류, 별)] 최대 SLOTS명
        self.attack_bonus = 0     # "공격력 +10%"를 고른 횟수
        self.free_spin = False    # 다음 준비 단계 첫 스핀 무료
        self.spins = 0            # 이번 준비 단계에서 스핀한 횟수
        self.phase = "prepare"    # "prepare" / "battle" / "over"
        self.queue = []           # 아직 나오지 않은 적 [(체력, 보스인지)]
        self.enemies = []         # 전장의 적 [{hp, max_hp, x, boss, lane}], x는 방어선까지 거리
        self.spawn_timer = 0.0
        self.spawned = 0
        self.board = []
        self.lines = 0
        self.message = ""

    # ---- 상태 ----

    @property
    def rank(self):
        """지금 계급 이름."""
        return rank_for(self.cleared)

    @property
    def face_ratio(self):
        """지금 얼굴의 최산 비율."""
        return face_ratio_for(self.cleared)

    @property
    def score(self):
        """점수 = 처치 수 × 10 + 막은 웨이브 수 × 100."""
        return self.kills * KILL_SCORE + self.cleared * WAVE_SCORE

    def deck_counts(self):
        """덱에 총알이 종류별로 몇 개 있는지 돌려준다."""
        return {kind: self.deck.count(kind) for kind in BULLET_ORDER}

    def add_to_deck(self, kind):
        """총알 1개를 덱에 더한다."""
        if kind not in BULLETS:
            raise ValueError("없는 총알: " + str(kind))
        self.deck.append(kind)

    # ---- 준비 단계: 스핀과 소환 ----

    def spin_cost(self):
        """다음 스핀 비용: 100에서 시작해 스핀마다 +50. "첫 스핀 무료"면 첫 스핀은 0."""
        if self.free_spin and self.spins == 0:
            return 0
        return SPIN_BASE + SPIN_STEP * self.spins

    def can_spin(self):
        """준비 단계이고 골드가 스핀 비용 이상이면 스핀할 수 있다."""
        return self.phase == "prepare" and self.gold >= self.spin_cost()

    def spin(self, rng):
        """골드를 내고 덱에서 9칸을 뽑아, 맞은 줄마다 그 총알의 병사를 소환한다. 소환한 총알 목록을 돌려준다."""
        if not self.can_spin():
            raise ValueError("지금은 스핀할 수 없다 (골드 부족 또는 전투 중)")
        self.gold -= self.spin_cost()
        if self.spins == 0:
            self.free_spin = False
        self.spins += 1
        self.board = [rng.choice(self.deck) for _ in range(9)]
        summoned = [self.board[line[0]] for line in matched_lines(self.board)]
        self.lines = len(summoned)
        if not summoned:
            self.message = MSG_MISS
            return summoned
        placed = [kind for kind in summoned if self.summon(kind) != "full"]
        full = len(summoned) - len(placed)
        full_text = "병사 칸이 꽉 찼습니다 (+" + str(FULL_REFUND * full) + "골드)"
        if not placed:
            self.message = full_text
            return summoned
        names = ", ".join(SOLDIERS[kind]["name"] for kind in placed)
        self.message = "병사 " + str(len(placed)) + "명 소환! (" + names + ")"
        if full:   # 일부만 들어갔으면 소환과 반환을 둘 다 알린다
            self.message += "\n" + full_text
        return summoned

    def summon(self, kind):
        """병사 1명(★1)을 소환한다. 같은 종류·별 짝이 있으면 연달아 합체한다.
        "summoned"(빈 칸에 들어감) / "merged"(합체) / "full"(칸이 꽉 차 골드 반환)을 돌려준다."""
        star = 1
        pos = None
        while star < MAX_STAR and (kind, star) in self.soldiers:
            pos = self.soldiers.index((kind, star))
            del self.soldiers[pos]
            star += 1
        if pos is not None:
            self.soldiers.insert(pos, (kind, star))
            return "merged"
        if len(self.soldiers) >= SLOTS:
            self.gold += FULL_REFUND
            self.message = MSG_FULL
            return "full"
        self.soldiers.append((kind, 1))
        return "summoned"

    def soldier_dps(self, soldier):
        """병사 한 명의 초당 공격력 = 기본 × 별 배수 × (1 + 0.1 × 공격력 강화 횟수)."""
        kind, star = soldier
        return SOLDIERS[kind]["dps"] * STAR_POWER[star] * (1 + ATTACK_STEP * self.attack_bonus)

    def total_dps(self):
        """모든 병사의 초당 공격력 합."""
        return sum(self.soldier_dps(s) for s in self.soldiers)

    # ---- 전투 ----

    def start_battle(self):
        """이번 웨이브의 적을 줄 세우고 전투를 시작한다. 보스는 5웨이브마다 마지막에 나온다."""
        hp = enemy_hp(self.wave)
        self.queue = [(hp, False)] * enemy_count(self.wave)
        if self.wave % BOSS_EVERY == 0:
            self.queue.append((hp * BOSS_HP_TIMES, True))
        self.enemies = []
        self.spawn_timer = 0.0
        self.spawned = 0          # 이번 웨이브에 나온 적 수 (화면에서 줄을 나누는 데 쓴다)
        self.wave_kills = 0
        self.phase = "battle"
        self.message = ""

    @property
    def battle_over(self):
        """하트가 0 이하이거나, 나올 적과 전장의 적이 모두 없으면 전투가 끝난 것이다."""
        return self.hearts <= 0 or (not self.queue and not self.enemies)

    def battle_step(self, dt):
        """전투를 dt초 진행한다: 적 나오기 → 병사 공격(앞 적부터, 남은 피해는 다음 적) → 적 이동·통과."""
        if self.phase != "battle" or self.battle_over:
            return
        # 1. 나오기
        self.spawn_timer -= dt
        while self.queue and self.spawn_timer <= EPS:
            hp, boss = self.queue.pop(0)
            self.enemies.append({"hp": hp, "max_hp": hp, "x": FIELD, "boss": boss, "lane": self.spawned % 3})
            self.spawned += 1
            self.spawn_timer += SPAWN_GAP
        # 2. 공격: 방어선에 가까운 적부터 피해를 준다
        damage = self.total_dps() * dt
        for enemy in sorted(self.enemies, key=lambda e: e["x"]):
            if damage <= EPS:
                break
            hit = min(damage, enemy["hp"])
            enemy["hp"] -= hit
            damage -= hit
            if enemy["hp"] <= EPS:
                self.enemies.remove(enemy)
                self.kills += 1
                self.wave_kills += 1
        # 3. 이동: 방어선을 지나가면 하트가 줄고, 0 이하가 되면 그 자리에서 전투가 끝난다
        speed = enemy_speed(self.wave)
        for enemy in list(self.enemies):
            enemy["x"] -= speed * dt
            if enemy["x"] <= 0:
                self.enemies.remove(enemy)
                self.hearts -= LEAK_BOSS if enemy["boss"] else LEAK_NORMAL
                if self.hearts <= 0:
                    return

    def finish_wave(self):
        """끝난 전투를 판정한다. 하트가 남으면 보상을 주고 다음 웨이브 준비로 "clear", 아니면 "over"."""
        if self.hearts <= 0:
            self.phase = "over"
            return "over"
        self.cleared += 1
        self.gold += WAVE_GOLD + self.wave_kills * KILL_GOLD
        self.wave += 1
        self.spins = 0
        self.queue = []
        self.enemies = []
        self.board = []
        self.lines = 0
        self.phase = "prepare"
        return "clear"

    # ---- 상점 ----

    def shop_offer(self, rng):
        """상점 4가지 중 서로 다른 3개를 고른다. "총알 추가"는 어떤 총알인지도 정한다. [(항목, 총알 또는 None)]."""
        items = rng.sample(SHOP_ITEMS, 3)
        return [(item, rng.choice(BULLET_ORDER) if item == "총알 추가" else None) for item in items]

    def apply_shop(self, item, bullet=None):
        """상점에서 고른 항목의 효과를 적용한다."""
        if item == "총알 추가":
            self.add_to_deck(bullet)
        elif item == "하트 +1":
            self.hearts = min(MAX_HEARTS, self.hearts + 1)
        elif item == "공격력 +10%":
            self.attack_bonus += 1
        elif item == "첫 스핀 무료":
            self.free_spin = True
        else:
            raise ValueError("없는 상점 항목: " + str(item))


def shop_label(item, bullet):
    """상점 항목을 보여 줄 글자 ("총알 추가: 철갑탄" 등)."""
    return item + ": " + bullet if bullet else item


def play_in_console():
    """화면 없이 콘솔에서 한 판을 해 본다 (Enter로 스핀, b로 전투, 숫자로 상점 선택)."""
    rng = random.Random()
    g = Game()
    while True:
        print("\n[" + str(g.wave) + "웨이브] 계급", g.rank, "/ 하트", g.hearts, "/ 점수", g.score)
        while True:
            soldiers = ", ".join(SOLDIERS[k]["name"] + "★" + str(s) for k, s in g.soldiers) or "없음"
            print("골드", g.gold, "/ 다음 스핀", g.spin_cost(), "/ 병사:", soldiers)
            answer = input("Enter = 스핀, b = 전투 시작: ").strip().lower()
            if answer == "b":
                break
            if not g.can_spin():
                print("골드가 모자랍니다.")
                continue
            g.spin(rng)
            for row in range(3):
                print("  ".join(g.board[row * 3:row * 3 + 3]))
            print(g.message)
        g.start_battle()
        while not g.battle_over:
            g.battle_step(0.1)
        if g.finish_wave() == "over":
            print("\n게임 오버! 점수", g.score, "/ 도달 웨이브", g.wave, "/ 처치", g.kills, "/ 계급", g.rank)
            return
        print("\n웨이브를 막았습니다! 계급:", g.rank, "/ 처치", g.wave_kills, "/ 골드", g.gold)
        offer = g.shop_offer(rng)
        for number, (item, bullet) in enumerate(offer, 1):
            print(number, shop_label(item, bullet))
        choice = input("고를 번호 (1~3): ").strip()
        g.apply_shop(*offer[int(choice) - 1] if choice in ("1", "2", "3") else offer[0])


if __name__ == "__main__":
    play_in_console()
